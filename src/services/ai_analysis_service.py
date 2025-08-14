"""
AI Analysis Service Integration
AI分析サービス統合 - キーワード抽出・センチメント分析・重要度評価
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .ai_analyzer import ClaudeAnalyzer, AIAnalysisError
from processors.analyzer import ClaudeAnalyzer as ProcessorAnalyzer
from utils.config import get_config
from utils.cache_manager import CacheManager
from utils.rate_limiter import RateLimiter
from models.article import Article


logger = logging.getLogger(__name__)


class AnalysisPriority(Enum):
    """分析優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AnalysisJobResult:
    """分析ジョブ結果"""
    total_articles: int
    analyzed_articles: int
    skipped_articles: int
    failed_articles: int
    processing_time: float
    cache_hit_rate: float
    errors: List[str]
    urgent_articles_found: int


class AIAnalysisService:
    """統合AI分析サービス"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache_manager = CacheManager()
        self.rate_limiter = RateLimiter()
        
        # AI分析エンジン初期化
        try:
            self.claude_analyzer = ClaudeAnalyzer(config)
            self.processor_analyzer = ProcessorAnalyzer(config)
        except Exception as e:
            logger.warning(f"AI analyzers initialization failed: {e}")
            self.claude_analyzer = None
            self.processor_analyzer = None
        
        # バッチ処理設定
        self.batch_size = self.config.get('ai_analysis.batch_size', default=10)
        self.max_concurrent = self.config.get('ai_analysis.max_concurrent', default=5)
        self.max_retries = self.config.get('ai_analysis.max_retries', default=3)
        
        # パフォーマンス設定
        self.request_delay = self.config.get('ai_analysis.request_delay', default=1.0)
        self.timeout_seconds = self.config.get('ai_analysis.timeout', default=60)
        
        # 統計情報
        self.service_stats = {
            'total_jobs': 0,
            'successful_jobs': 0,
            'failed_jobs': 0,
            'total_articles_processed': 0,
            'total_articles_analyzed': 0,
            'total_processing_time': 0.0,
            'urgent_articles_detected': 0
        }
        
        logger.info("AI Analysis Service initialized")
    
    async def analyze_articles_batch(self, articles: List[Article], 
                                   priority: AnalysisPriority = AnalysisPriority.NORMAL) -> AnalysisJobResult:
        """記事の一括AI分析"""
        try:
            start_time = datetime.now()
            logger.info(f"Starting AI analysis job for {len(articles)} articles (priority: {priority.value})")
            
            # 分析が必要な記事をフィルタリング
            articles_to_analyze = self._filter_articles_for_analysis(articles)
            skipped_count = len(articles) - len(articles_to_analyze)
            
            if not articles_to_analyze:
                logger.info("No articles require analysis")
                return AnalysisJobResult(
                    total_articles=len(articles),
                    analyzed_articles=0,
                    skipped_articles=skipped_count,
                    failed_articles=0,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    cache_hit_rate=100.0,
                    errors=[],
                    urgent_articles_found=0
                )
            
            logger.info(f"Analyzing {len(articles_to_analyze)} articles (skipped {skipped_count})")
            
            # 優先度に応じてバッチサイズ調整
            batch_size = self._get_batch_size_for_priority(priority)
            
            # バッチ分析実行
            analyzed_articles = []
            analysis_errors = []
            urgent_count = 0
            
            for i in range(0, len(articles_to_analyze), batch_size):
                batch = articles_to_analyze[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(articles_to_analyze) + batch_size - 1) // batch_size
                
                logger.info(f"Processing analysis batch {batch_num}/{total_batches}")
                
                try:
                    # レート制限チェック
                    await self.rate_limiter.wait_if_needed('claude')
                    
                    # バッチ分析実行
                    batch_result = await self._process_analysis_batch(batch, priority)
                    analyzed_articles.extend(batch_result['articles'])
                    analysis_errors.extend(batch_result['errors'])
                    urgent_count += batch_result['urgent_count']
                    
                    # API使用量記録
                    self.rate_limiter.record_request('claude')
                    
                    # 優先度が低い場合は遅延を入れる
                    if priority in [AnalysisPriority.LOW, AnalysisPriority.NORMAL]:
                        await asyncio.sleep(self.request_delay)
                    
                except Exception as e:
                    error_msg = f"Analysis batch {batch_num} failed: {str(e)}"
                    analysis_errors.append(error_msg)
                    logger.error(error_msg)
            
            # 結果の統合
            final_articles = self._merge_analysis_results(articles, analyzed_articles)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            analyzed_count = len(analyzed_articles)
            failed_count = len(articles_to_analyze) - analyzed_count
            
            # キャッシュヒット率計算
            cache_hit_rate = self._calculate_cache_hit_rate()
            
            # 統計更新
            self._update_service_stats(len(articles), analyzed_count, processing_time, 
                                     len(analysis_errors) == 0, urgent_count)
            
            result = AnalysisJobResult(
                total_articles=len(articles),
                analyzed_articles=analyzed_count,
                skipped_articles=skipped_count,
                failed_articles=failed_count,
                processing_time=processing_time,
                cache_hit_rate=cache_hit_rate,
                errors=analysis_errors,
                urgent_articles_found=urgent_count
            )
            
            logger.info(f"AI analysis job completed: {analyzed_count} analyzed, {urgent_count} urgent, {failed_count} failed, {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"AI analysis job failed: {e}")
            self.service_stats['failed_jobs'] += 1
            raise AIAnalysisError(f"AI analysis job failed: {e}")
    
    async def _process_analysis_batch(self, articles: List[Article], 
                                    priority: AnalysisPriority) -> Dict[str, Any]:
        """分析バッチ処理"""
        try:
            # 並列度設定
            concurrent_limit = self._get_concurrent_limit_for_priority(priority)
            semaphore = asyncio.Semaphore(concurrent_limit)
            
            async def analyze_with_semaphore(article):
                async with semaphore:
                    return await self._analyze_single_article_with_retry(article)
            
            # 並列分析実行
            results = await asyncio.gather(
                *[analyze_with_semaphore(article) for article in articles],
                return_exceptions=True
            )
            
            # 結果の分類
            analyzed_articles = []
            errors = []
            urgent_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Article):
                    analyzed_articles.append(result)
                    # 緊急記事カウント
                    if getattr(result, 'is_urgent', False) or getattr(result, 'importance_score', 0) >= 9:
                        urgent_count += 1
                elif isinstance(result, Exception):
                    error_msg = f"Article {articles[i].url} analysis failed: {str(result)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                'articles': analyzed_articles,
                'errors': errors,
                'urgent_count': urgent_count
            }
            
        except Exception as e:
            logger.error(f"Analysis batch processing failed: {e}")
            raise AIAnalysisError(f"Batch processing failed: {e}")
    
    async def _analyze_single_article_with_retry(self, article: Article) -> Article:
        """リトライ機能付き単一記事分析"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # タイムアウト付きで分析実行
                if self.processor_analyzer:
                    # 新しい詳細な分析エンジンを優先使用
                    analyzed_article = await asyncio.wait_for(
                        self.processor_analyzer.analyze_article(article),
                        timeout=self.timeout_seconds
                    )
                elif self.claude_analyzer:
                    # フォールバック分析エンジン
                    analyzed_article = await asyncio.wait_for(
                        self.claude_analyzer._analyze_article(article),
                        timeout=self.timeout_seconds
                    )
                else:
                    raise AIAnalysisError("No AI analyzers available")
                
                logger.debug(f"Article analyzed successfully: {article.url} (attempt {attempt + 1})")
                return analyzed_article
                
            except asyncio.TimeoutError:
                last_error = f"Analysis timeout after {self.timeout_seconds}s"
                logger.warning(f"Analysis timeout for {article.url} (attempt {attempt + 1})")
            except AIAnalysisError as e:
                last_error = str(e)
                logger.warning(f"Analysis error for {article.url} (attempt {attempt + 1}): {e}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Unexpected error analyzing {article.url} (attempt {attempt + 1}): {e}")
            
            # リトライ前の待機（指数バックオフ）
            if attempt < self.max_retries - 1:
                wait_time = (2 ** attempt) * self.request_delay
                logger.info(f"Retrying analysis for {article.url} in {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        # 全てのリトライが失敗した場合
        logger.error(f"Analysis failed for {article.url} after {self.max_retries} attempts: {last_error}")
        raise AIAnalysisError(f"Analysis failed after {self.max_retries} attempts: {last_error}")
    
    def _filter_articles_for_analysis(self, articles: List[Article]) -> List[Article]:
        """分析が必要な記事をフィルタリング"""
        filtered_articles = []
        
        for article in articles:
            # 既に分析済みの記事はスキップ
            if (hasattr(article, 'summary') and article.summary and
                hasattr(article, 'importance_score') and article.importance_score > 0 and
                hasattr(article, 'keywords') and article.keywords):
                logger.debug(f"Skipping already analyzed article: {article.url}")
                continue
            
            # 内容が短すぎる記事はスキップ
            title_length = len(article.title or '')
            content_length = len(getattr(article, 'content', '') or getattr(article, 'description', '') or '')
            if title_length + content_length < 50:
                logger.debug(f"Skipping too short article: {article.url}")
                continue
            
            filtered_articles.append(article)
        
        return filtered_articles
    
    def _merge_analysis_results(self, original_articles: List[Article], 
                              analyzed_articles: List[Article]) -> List[Article]:
        """分析結果をマージ"""
        # URLベースのマッピング作成
        analyzed_map = {article.url: article for article in analyzed_articles}
        
        # 元の記事リストと分析結果をマージ
        merged_articles = []
        for article in original_articles:
            if article.url in analyzed_map:
                merged_articles.append(analyzed_map[article.url])
            else:
                merged_articles.append(article)
        
        return merged_articles
    
    def _get_batch_size_for_priority(self, priority: AnalysisPriority) -> int:
        """優先度に応じたバッチサイズ取得"""
        size_mapping = {
            AnalysisPriority.URGENT: min(self.batch_size // 2, 5),
            AnalysisPriority.HIGH: min(self.batch_size // 1.5, 8),
            AnalysisPriority.NORMAL: self.batch_size,
            AnalysisPriority.LOW: min(self.batch_size * 1.5, 15)
        }
        return int(size_mapping.get(priority, self.batch_size))
    
    def _get_concurrent_limit_for_priority(self, priority: AnalysisPriority) -> int:
        """優先度に応じた並列度制限取得"""
        limit_mapping = {
            AnalysisPriority.URGENT: min(self.max_concurrent * 2, 10),
            AnalysisPriority.HIGH: self.max_concurrent,
            AnalysisPriority.NORMAL: max(self.max_concurrent - 1, 1),
            AnalysisPriority.LOW: max(self.max_concurrent - 2, 1)
        }
        return limit_mapping.get(priority, self.max_concurrent)
    
    def _calculate_cache_hit_rate(self) -> float:
        """キャッシュヒット率計算"""
        try:
            if self.processor_analyzer:
                stats = self.processor_analyzer.get_analysis_statistics()
                return stats.get('cache_hit_rate', 0.0)
            elif self.claude_analyzer:
                stats = self.claude_analyzer.get_performance_stats()
                return stats.get('cache_hit_rate_percent', 0.0)
            return 0.0
        except Exception:
            return 0.0
    
    def _update_service_stats(self, total_articles: int, analyzed_count: int, 
                            processing_time: float, success: bool, urgent_count: int):
        """サービス統計更新"""
        self.service_stats['total_jobs'] += 1
        self.service_stats['total_articles_processed'] += total_articles
        self.service_stats['total_articles_analyzed'] += analyzed_count
        self.service_stats['total_processing_time'] += processing_time
        self.service_stats['urgent_articles_detected'] += urgent_count
        
        if success:
            self.service_stats['successful_jobs'] += 1
        else:
            self.service_stats['failed_jobs'] += 1
    
    async def analyze_urgent_articles(self, articles: List[Article]) -> AnalysisJobResult:
        """緊急記事の分析（高優先度）"""
        logger.info(f"Processing urgent analysis for {len(articles)} articles")
        return await self.analyze_articles_batch(articles, AnalysisPriority.URGENT)
    
    async def analyze_daily_batch(self, articles: List[Article]) -> AnalysisJobResult:
        """日次バッチ分析（通常優先度）"""
        logger.info(f"Processing daily analysis batch for {len(articles)} articles")
        return await self.analyze_articles_batch(articles, AnalysisPriority.NORMAL)
    
    async def get_analysis_status(self) -> Dict[str, Any]:
        """AI分析サービスステータス取得"""
        try:
            # 基本統計
            processor_stats = {}
            claude_stats = {}
            
            if self.processor_analyzer:
                processor_stats = self.processor_analyzer.get_analysis_statistics()
            
            if self.claude_analyzer:
                claude_stats = self.claude_analyzer.get_performance_stats()
            
            # サービス統計
            total_jobs = self.service_stats['total_jobs']
            success_rate = (self.service_stats['successful_jobs'] / max(total_jobs, 1)) * 100
            avg_processing_time = (self.service_stats['total_processing_time'] / max(total_jobs, 1))
            urgent_detection_rate = (self.service_stats['urgent_articles_detected'] / 
                                   max(self.service_stats['total_articles_analyzed'], 1)) * 100
            
            return {
                'service_status': 'operational' if (self.processor_analyzer or self.claude_analyzer) else 'no_analyzers',
                'processor_analyzer_stats': processor_stats,
                'claude_analyzer_stats': claude_stats,
                'service_stats': {
                    'total_jobs': total_jobs,
                    'success_rate': round(success_rate, 2),
                    'avg_processing_time': round(avg_processing_time, 2),
                    'total_articles_processed': self.service_stats['total_articles_processed'],
                    'total_articles_analyzed': self.service_stats['total_articles_analyzed'],
                    'urgent_articles_detected': self.service_stats['urgent_articles_detected'],
                    'urgent_detection_rate': round(urgent_detection_rate, 2)
                },
                'configuration': {
                    'batch_size': self.batch_size,
                    'max_concurrent': self.max_concurrent,
                    'max_retries': self.max_retries,
                    'request_delay': self.request_delay,
                    'timeout_seconds': self.timeout_seconds
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis status: {e}")
            return {'error': str(e)}
    
    async def create_comprehensive_summary(self, articles: List[Article]) -> Dict[str, Any]:
        """包括的な記事サマリー作成"""
        try:
            if not articles:
                return {'daily_summary': '本日は分析対象の記事がありませんでした。'}
            
            # 日次サマリー生成
            daily_summary = ""
            if self.processor_analyzer:
                daily_summary = await self.processor_analyzer.create_daily_summary(articles)
            elif self.claude_analyzer:
                daily_summary = await self.claude_analyzer.create_daily_summary(articles)
            
            # 統計情報計算
            total_articles = len(articles)
            urgent_articles = len([a for a in articles if getattr(a, 'is_urgent', False)])
            high_importance = len([a for a in articles if getattr(a, 'importance_score', 0) >= 8])
            
            # カテゴリ別統計
            category_stats = {}
            for article in articles:
                category = getattr(article, 'category', 'その他')
                category_name = category.value if hasattr(category, 'value') else str(category)
                category_stats[category_name] = category_stats.get(category_name, 0) + 1
            
            # センチメント分析
            sentiment_scores = [getattr(a, 'sentiment_score', 0.0) for a in articles]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
            
            # トップキーワード
            all_keywords = []
            for article in articles:
                keywords = getattr(article, 'keywords', [])
                if keywords:
                    all_keywords.extend(keywords)
            
            keyword_counts = {}
            for keyword in all_keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'daily_summary': daily_summary,
                'statistics': {
                    'total_articles': total_articles,
                    'urgent_articles': urgent_articles,
                    'high_importance_articles': high_importance,
                    'avg_sentiment': round(avg_sentiment, 3),
                    'category_distribution': category_stats,
                    'top_keywords': top_keywords
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create comprehensive summary: {e}")
            return {
                'daily_summary': '要約生成中にエラーが発生しました。',
                'error': str(e)
            }
    
    async def test_analysis_service(self) -> Dict[str, Any]:
        """AI分析サービステスト"""
        try:
            logger.info("Testing AI analysis service...")
            
            # テスト記事作成
            from models.article import ArticleCategory, ArticleLanguage
            
            test_article = Article(
                url="test://analysis.test",
                title="重要なセキュリティアップデート発表",
                description="新しいセキュリティ脆弱性に対する緊急パッチが発表されました。",
                content="セキュリティ研究者により新たな脆弱性が発見され、この脆弱性は多くのシステムに影響を与える可能性があります。開発者は緊急パッチの適用を推奨しています。",
                source={'name': 'Test Security News'},
                category=ArticleCategory.SECURITY,
                language=ArticleLanguage.JAPANESE,
                published_at=datetime.now()
            )
            
            # 分析実行
            result = await self.analyze_articles_batch([test_article], AnalysisPriority.HIGH)
            
            # 結果確認
            success = result.analyzed_articles > 0 and len(result.errors) == 0
            
            # 分析結果詳細取得
            analyzed_article = None
            if success and result.analyzed_articles > 0:
                # 分析された記事を検索
                for article in [test_article]:  # merge_analysis_resultsの結果から取得するべきだが、簡略化
                    if getattr(article, 'summary', None):
                        analyzed_article = article
                        break
            
            return {
                'success': success,
                'result': {
                    'analyzed_articles': result.analyzed_articles,
                    'processing_time': result.processing_time,
                    'cache_hit_rate': result.cache_hit_rate,
                    'urgent_articles_found': result.urgent_articles_found,
                    'errors': result.errors
                },
                'analysis_details': {
                    'importance_score': getattr(analyzed_article, 'importance_score', None) if analyzed_article else None,
                    'summary': getattr(analyzed_article, 'summary', None) if analyzed_article else None,
                    'keywords': getattr(analyzed_article, 'keywords', None) if analyzed_article else None,
                    'sentiment_score': getattr(analyzed_article, 'sentiment_score', None) if analyzed_article else None
                } if analyzed_article else None,
                'message': 'AI analysis test completed successfully' if success else 'AI analysis test failed'
            }
            
        except Exception as e:
            logger.error(f"AI analysis service test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'AI analysis service test failed'
            }
    
    def get_estimated_processing_time(self, articles: List[Article]) -> Dict[str, Any]:
        """分析処理時間見積もり"""
        try:
            # 分析対象記事のフィルタリング
            articles_to_analyze = self._filter_articles_for_analysis(articles)
            
            # 見積もり時間計算（経験的な値）
            base_time_per_article = 3.0  # 1記事あたり3秒の基本時間
            batch_overhead = 1.0  # バッチあたり1秒のオーバーヘッド
            
            estimated_batches = (len(articles_to_analyze) + self.batch_size - 1) // self.batch_size
            estimated_time_seconds = (len(articles_to_analyze) * base_time_per_article) + (estimated_batches * batch_overhead)
            
            return {
                'articles_to_analyze': len(articles_to_analyze),
                'total_articles': len(articles),
                'estimated_time_seconds': round(estimated_time_seconds, 1),
                'estimated_time_minutes': round(estimated_time_seconds / 60, 1),
                'estimated_batches': estimated_batches,
                'estimated_api_calls': len(articles_to_analyze)
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate processing time: {e}")
            return {'error': str(e)}


# グローバルAI分析サービスインスタンス
_ai_analysis_service_instance = None


def get_ai_analysis_service() -> AIAnalysisService:
    """グローバルAI分析サービスインスタンス取得"""
    global _ai_analysis_service_instance
    if _ai_analysis_service_instance is None:
        _ai_analysis_service_instance = AIAnalysisService()
    return _ai_analysis_service_instance