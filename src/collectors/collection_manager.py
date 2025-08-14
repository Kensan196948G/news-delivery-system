"""
Collection Manager
ニュース収集の統合管理システム - 強化版
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from .base_collector import BaseCollector, CollectionError
from .newsapi_collector import NewsAPICollector
from .gnews_collector import GNewsCollector
from .nvd_collector import NVDCollector
from models.article import Article, ArticleCategory, ArticleLanguage
from utils.config import get_config
from utils.logger import setup_logger


@dataclass
class CollectionTarget:
    """収集対象の設定"""
    source: str
    category: str
    count: int
    priority: int
    enabled: bool = True
    filters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


@dataclass
class CollectionResult:
    """収集結果"""
    source: str
    category: str
    articles_collected: int
    articles_filtered: int
    processing_time: float
    success: bool
    error_message: str = ""
    articles: List[Article] = None
    
    def __post_init__(self):
        if self.articles is None:
            self.articles = []


class CollectionManager:
    """ニュース収集の統合管理システム"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        
        # 収集器の初期化
        self.collectors = {}
        self._initialize_collectors()
        
        # 収集設定
        self.collection_targets = self._load_collection_targets()
        
        # パフォーマンス追跡
        self.collection_sessions = []
        self.deduplication_cache = set()
        
        # 統計情報
        self.global_stats = {
            'total_sessions': 0,
            'total_articles_collected': 0,
            'total_articles_filtered': 0,
            'total_processing_time': 0.0,
            'success_rate': 0.0,
            'average_articles_per_session': 0.0,
            'last_collection_time': None,
            'collector_performance': {}
        }
        
        # 並行処理設定
        self.max_concurrent_collectors = self.config.get('collection', 'max_concurrent', default=3)
        self.collection_timeout = self.config.get('collection', 'timeout_seconds', default=300)
        
        # 品質管理設定
        self.quality_thresholds = {
            'min_articles_per_source': 5,
            'max_duplicate_rate': 30.0,  # パーセント
            'min_success_rate': 80.0,    # パーセント
            'max_response_time': 60.0    # 秒
        }
    
    def _initialize_collectors(self):
        """収集器の初期化"""
        try:
            # NewsAPI収集器
            if self.config.get('news_sources', 'newsapi', 'enabled', default=True):
                self.collectors['newsapi'] = NewsAPICollector(self.config, self.logger)
                
            # GNews収集器
            if self.config.get('news_sources', 'gnews', 'enabled', default=True):
                self.collectors['gnews'] = GNewsCollector(self.config, self.logger)
                
            # NVD収集器
            if self.config.get('news_sources', 'nvd', 'enabled', default=True):
                self.collectors['nvd'] = NVDCollector(self.config, self.logger)
                
            self.logger.info(f"Initialized {len(self.collectors)} collectors: {list(self.collectors.keys())}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize collectors: {e}")
            raise CollectionError(f"Collector initialization failed: {e}")
    
    def _load_collection_targets(self) -> List[CollectionTarget]:
        """収集対象設定の読み込み"""
        targets = []
        
        # デフォルト収集設定
        default_targets = [
            # 国内ニュース
            CollectionTarget('newsapi', 'general', 10, 1, True, {'country': 'jp', 'language': 'ja'}),
            CollectionTarget('newsapi', 'business', 8, 3, True, {'country': 'jp', 'language': 'ja'}),
            
            # 国際ニュース
            CollectionTarget('gnews', 'general', 15, 2, True, {'language': 'en', 'country': 'us'}),
            CollectionTarget('gnews', 'human_rights', 15, 2, True, {'special_collection': True}),
            
            # 技術ニュース
            CollectionTarget('newsapi', 'technology', 20, 5, True, {'language': 'en'}),
            CollectionTarget('gnews', 'technology', 20, 5, True, {'special_collection': True}),
            
            # セキュリティ
            CollectionTarget('nvd', 'vulnerabilities', 20, 6, True, {'days_back': 7, 'cvss_severity': 'HIGH,CRITICAL'}),
        ]
        
        # 設定ファイルからカスタム設定を読み込み
        try:
            custom_targets = self.config.get('collection', 'targets', default=[])
            
            for target_config in custom_targets:
                target = CollectionTarget(
                    source=target_config.get('source'),
                    category=target_config.get('category'),
                    count=target_config.get('count', 10),
                    priority=target_config.get('priority', 5),
                    enabled=target_config.get('enabled', True),
                    filters=target_config.get('filters', {})
                )
                targets.append(target)
                
        except Exception as e:
            self.logger.warning(f"Failed to load custom collection targets: {e}")
        
        # デフォルト設定を追加
        targets.extend(default_targets)
        
        # 優先度順にソート
        targets.sort(key=lambda x: x.priority)
        
        self.logger.info(f"Loaded {len(targets)} collection targets")
        return targets
    
    async def collect_all_news(self, max_articles_per_category: int = None) -> Dict[str, Any]:
        """全カテゴリのニュースを並行収集"""
        session_start = time.time()
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"Starting collection session: {session_id}")
        
        try:
            # 並行収集の実行
            collection_results = await self._execute_parallel_collection(max_articles_per_category)
            
            # 結果の統合と重複除去
            all_articles = []
            collection_summary = {
                'session_id': session_id,
                'start_time': datetime.fromtimestamp(session_start).isoformat(),
                'end_time': datetime.now().isoformat(),
                'processing_time': time.time() - session_start,
                'total_articles_collected': 0,
                'total_articles_after_dedup': 0,
                'sources_used': set(),
                'categories_collected': set(),
                'collection_results': []
            }
            
            # 各収集結果を処理
            for result in collection_results:
                collection_summary['collection_results'].append(asdict(result))
                collection_summary['total_articles_collected'] += result.articles_collected
                collection_summary['sources_used'].add(result.source)
                collection_summary['categories_collected'].add(result.category)
                
                if result.success and result.articles:
                    all_articles.extend(result.articles)
            
            # 重複除去
            unique_articles = self._deduplicate_articles(all_articles)
            collection_summary['total_articles_after_dedup'] = len(unique_articles)
            collection_summary['duplicate_rate'] = (
                (len(all_articles) - len(unique_articles)) / max(len(all_articles), 1) * 100
            )
            
            # カテゴリ別統計
            category_stats = self._calculate_category_statistics(unique_articles)
            collection_summary['category_statistics'] = category_stats
            
            # 品質評価
            quality_assessment = self._assess_collection_quality(collection_summary, collection_results)
            collection_summary['quality_assessment'] = quality_assessment
            
            # セッション記録の保存
            self._record_collection_session(collection_summary)
            
            # 統計更新
            self._update_global_stats(collection_summary)
            
            self.logger.info(
                f"Collection session completed: {len(unique_articles)} unique articles from "
                f"{len(collection_summary['sources_used'])} sources in "
                f"{collection_summary['processing_time']:.2f}s"
            )
            
            return {
                'articles': unique_articles,
                'summary': collection_summary,
                'success': quality_assessment['overall_quality'] >= 0.7
            }
            
        except Exception as e:
            session_time = time.time() - session_start
            self.logger.error(f"Collection session failed after {session_time:.2f}s: {e}")
            
            return {
                'articles': [],
                'summary': {
                    'session_id': session_id,
                    'error': str(e),
                    'processing_time': session_time,
                    'success': False
                },
                'success': False
            }
    
    async def _execute_parallel_collection(self, max_articles_per_category: int = None) -> List[CollectionResult]:
        """並行収集の実行"""
        collection_tasks = []
        
        # 有効な収集対象に対してタスク作成
        for target in self.collection_targets:
            if not target.enabled or target.source not in self.collectors:
                continue
            
            count = min(target.count, max_articles_per_category) if max_articles_per_category else target.count
            
            task = asyncio.create_task(
                self._collect_from_source(target.source, target.category, count, target.filters)
            )
            collection_tasks.append(task)
        
        # 並行実行制限
        semaphore = asyncio.Semaphore(self.max_concurrent_collectors)
        
        async def limited_collect(task):
            async with semaphore:
                return await task
        
        # タイムアウト付きで並行実行
        try:
            limited_tasks = [limited_collect(task) for task in collection_tasks]
            results = await asyncio.wait_for(
                asyncio.gather(*limited_tasks, return_exceptions=True),
                timeout=self.collection_timeout
            )
            
            # 例外処理
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    target = self.collection_targets[i]
                    error_result = CollectionResult(
                        source=target.source,
                        category=target.category,
                        articles_collected=0,
                        articles_filtered=0,
                        processing_time=0,
                        success=False,
                        error_message=str(result)
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            self.logger.error(f"Collection timeout after {self.collection_timeout}s")
            return [CollectionResult(
                source="timeout",
                category="all",
                articles_collected=0,
                articles_filtered=0,
                processing_time=self.collection_timeout,
                success=False,
                error_message="Collection timeout"
            )]
    
    async def _collect_from_source(self, source: str, category: str, 
                                 count: int, filters: Dict[str, Any]) -> CollectionResult:
        """単一ソースからの収集"""
        start_time = time.time()
        
        try:
            collector = self.collectors[source]
            
            # ソース別収集ロジック
            if source == 'newsapi':
                articles = await self._collect_from_newsapi(collector, category, count, filters)
            elif source == 'gnews':
                articles = await self._collect_from_gnews(collector, category, count, filters)
            elif source == 'nvd':
                articles = await self._collect_from_nvd(collector, category, count, filters)
            else:
                raise CollectionError(f"Unknown source: {source}")
            
            # フィルタリング
            filtered_articles = self._apply_quality_filters(articles)
            
            processing_time = time.time() - start_time
            
            self.logger.debug(
                f"{source}.{category}: {len(filtered_articles)}/{len(articles)} articles "
                f"in {processing_time:.2f}s"
            )
            
            return CollectionResult(
                source=source,
                category=category,
                articles_collected=len(articles),
                articles_filtered=len(articles) - len(filtered_articles),
                processing_time=processing_time,
                success=True,
                articles=filtered_articles
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Collection failed for {source}.{category}: {e}")
            
            return CollectionResult(
                source=source,
                category=category,
                articles_collected=0,
                articles_filtered=0,
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def _collect_from_newsapi(self, collector: NewsAPICollector, 
                                   category: str, count: int, filters: Dict[str, Any]) -> List[Article]:
        """NewsAPIからの収集"""
        country = filters.get('country', 'us')
        language = filters.get('language', 'en')
        
        if category in ['technology', 'cybersecurity']:
            # Everything エンドポイントでキーワード検索
            query = 'technology OR AI OR cybersecurity' if category == 'technology' else 'cybersecurity OR vulnerability'
            return await collector.collect_everything(query=query, language=language, page_size=count)
        else:
            # Top Headlines エンドポイント
            return await collector.collect(category=category, country=country, language=language, page_size=count)
    
    async def _collect_from_gnews(self, collector: GNewsCollector, 
                                 category: str, count: int, filters: Dict[str, Any]) -> List[Article]:
        """GNewsからの収集"""
        if filters.get('special_collection'):
            if category == 'human_rights':
                return await collector.collect_human_rights_news(max_results=count)
            elif category == 'technology':
                return await collector.collect_tech_news(max_results=count)
        
        language = filters.get('language', 'en')
        country = filters.get('country', 'us')
        
        return await collector.collect(category=category, language=language, country=country, max_results=count)
    
    async def _collect_from_nvd(self, collector: NVDCollector, 
                               category: str, count: int, filters: Dict[str, Any]) -> List[Article]:
        """NVDからの収集"""
        days_back = filters.get('days_back', 7)
        cvss_severity = filters.get('cvss_severity', 'HIGH,CRITICAL')
        
        return await collector.collect(days_back=days_back, cvss_severity=cvss_severity)
    
    def _apply_quality_filters(self, articles: List[Article]) -> List[Article]:
        """品質フィルターの適用"""
        if not articles:
            return articles
        
        filtered = []
        
        for article in articles:
            # 基本品質チェック
            if not article.title or len(article.title.strip()) < 10:
                continue
            
            # 重複チェック（簡易版）
            title_hash = hash(article.title.lower().strip())
            if title_hash in self.deduplication_cache:
                continue
            
            self.deduplication_cache.add(title_hash)
            filtered.append(article)
            
            # キャッシュサイズ制限
            if len(self.deduplication_cache) > 10000:
                self.deduplication_cache = set(list(self.deduplication_cache)[-5000:])
        
        return filtered
    
    def _deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """高度な重複除去"""
        if not articles:
            return articles
        
        unique_articles = []
        seen_signatures = set()
        
        for article in articles:
            # シグネチャ生成（タイトル + URL）
            signature = self._generate_article_signature(article)
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_articles.append(article)
        
        self.logger.debug(f"Deduplication: {len(articles)} -> {len(unique_articles)} articles")
        return unique_articles
    
    def _generate_article_signature(self, article: Article) -> str:
        """記事のシグネチャ生成"""
        import hashlib
        
        # タイトルの正規化
        normalized_title = article.title.lower().strip()
        
        # URL存在チェック
        url_part = article.url[:100] if article.url else ""
        
        # シグネチャ文字列生成
        signature_string = f"{normalized_title}|{url_part}"
        
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()
    
    def _calculate_category_statistics(self, articles: List[Article]) -> Dict[str, Any]:
        """カテゴリ別統計の計算"""
        category_stats = {}
        
        for article in articles:
            category = article.category.value if hasattr(article.category, 'value') else str(article.category)
            
            if category not in category_stats:
                category_stats[category] = {
                    'count': 0,
                    'sources': set(),
                    'languages': set(),
                    'avg_importance': 0,
                    'urgent_count': 0
                }
            
            stats = category_stats[category]
            stats['count'] += 1
            stats['sources'].add(str(article.source))
            stats['languages'].add(str(article.language))
            
            if hasattr(article, 'importance_score') and article.importance_score:
                current_avg = stats['avg_importance']
                stats['avg_importance'] = (current_avg * (stats['count'] - 1) + article.importance_score) / stats['count']
            
            if hasattr(article, 'is_urgent') and article.is_urgent:
                stats['urgent_count'] += 1
        
        # セットをリストに変換
        for category, stats in category_stats.items():
            stats['sources'] = list(stats['sources'])
            stats['languages'] = list(stats['languages'])
        
        return category_stats
    
    def _assess_collection_quality(self, summary: Dict[str, Any], 
                                 results: List[CollectionResult]) -> Dict[str, Any]:
        """収集品質の評価"""
        assessment = {
            'overall_quality': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        # 成功率チェック
        successful_collections = sum(1 for r in results if r.success)
        success_rate = (successful_collections / max(len(results), 1)) * 100
        
        # 重複率チェック
        duplicate_rate = summary.get('duplicate_rate', 0)
        
        # 記事数チェック
        total_articles = summary.get('total_articles_after_dedup', 0)
        
        # 処理時間チェック
        processing_time = summary.get('processing_time', 0)
        
        # 品質スコア計算
        quality_score = 1.0
        
        if success_rate < self.quality_thresholds['min_success_rate']:
            quality_score -= 0.3
            assessment['issues'].append(f"Low success rate: {success_rate:.1f}%")
            assessment['recommendations'].append("Check API keys and network connectivity")
        
        if duplicate_rate > self.quality_thresholds['max_duplicate_rate']:
            quality_score -= 0.2
            assessment['issues'].append(f"High duplicate rate: {duplicate_rate:.1f}%")
            assessment['recommendations'].append("Improve deduplication logic")
        
        if total_articles < self.quality_thresholds['min_articles_per_source'] * len(self.collectors):
            quality_score -= 0.2
            assessment['issues'].append(f"Low article count: {total_articles}")
            assessment['recommendations'].append("Increase collection targets or check source availability")
        
        if processing_time > self.quality_thresholds['max_response_time']:
            quality_score -= 0.1
            assessment['issues'].append(f"Slow processing: {processing_time:.1f}s")
            assessment['recommendations'].append("Optimize parallel processing")
        
        assessment['overall_quality'] = max(0.0, quality_score)
        assessment['success_rate'] = success_rate
        assessment['duplicate_rate'] = duplicate_rate
        
        return assessment
    
    def _record_collection_session(self, summary: Dict[str, Any]):
        """収集セッションの記録"""
        self.collection_sessions.append(summary)
        
        # セッション履歴の制限（最新100件）
        if len(self.collection_sessions) > 100:
            self.collection_sessions = self.collection_sessions[-100:]
    
    def _update_global_stats(self, summary: Dict[str, Any]):
        """グローバル統計の更新"""
        self.global_stats['total_sessions'] += 1
        self.global_stats['total_articles_collected'] += summary.get('total_articles_collected', 0)
        self.global_stats['total_articles_filtered'] += summary.get('total_articles_after_dedup', 0)
        self.global_stats['total_processing_time'] += summary.get('processing_time', 0)
        self.global_stats['last_collection_time'] = summary.get('end_time')
        
        # 平均値計算
        total_sessions = self.global_stats['total_sessions']
        if total_sessions > 0:
            self.global_stats['average_articles_per_session'] = (
                self.global_stats['total_articles_filtered'] / total_sessions
            )
            
            # 成功率計算（直近10セッション）
            recent_sessions = self.collection_sessions[-10:]
            if recent_sessions:
                successful_sessions = sum(
                    1 for s in recent_sessions 
                    if s.get('quality_assessment', {}).get('overall_quality', 0) >= 0.7
                )
                self.global_stats['success_rate'] = (successful_sessions / len(recent_sessions)) * 100
    
    async def get_health_status(self) -> Dict[str, Any]:
        """全体的なヘルスステータス"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'collectors': {},
            'global_stats': self.global_stats.copy()
        }
        
        # 各収集器のヘルスチェック
        health_checks = []
        for name, collector in self.collectors.items():
            health_checks.append(collector.health_check())
        
        collector_healths = await asyncio.gather(*health_checks, return_exceptions=True)
        
        healthy_count = 0
        for i, (name, health) in enumerate(zip(self.collectors.keys(), collector_healths)):
            if isinstance(health, Exception):
                health_status['collectors'][name] = {
                    'status': 'error',
                    'error': str(health)
                }
            else:
                health_status['collectors'][name] = health
                if health.get('status') == 'healthy':
                    healthy_count += 1
        
        # 全体ステータス判定
        total_collectors = len(self.collectors)
        if healthy_count == total_collectors:
            health_status['overall_status'] = 'healthy'
        elif healthy_count >= total_collectors // 2:
            health_status['overall_status'] = 'degraded'
        else:
            health_status['overall_status'] = 'unhealthy'
        
        return health_status
    
    def get_collection_statistics(self) -> Dict[str, Any]:
        """詳細な収集統計を取得"""
        stats = self.global_stats.copy()
        
        # 収集器別統計
        collector_stats = {}
        for name, collector in self.collectors.items():
            try:
                collector_stats[name] = collector.get_collection_statistics()
            except Exception as e:
                collector_stats[name] = {'error': str(e)}
        
        stats['collector_statistics'] = collector_stats
        
        # 直近セッション統計
        if self.collection_sessions:
            recent_sessions = self.collection_sessions[-10:]
            stats['recent_sessions'] = recent_sessions
            
            # パフォーマンス傾向
            processing_times = [s.get('processing_time', 0) for s in recent_sessions]
            article_counts = [s.get('total_articles_after_dedup', 0) for s in recent_sessions]
            
            stats['performance_trends'] = {
                'avg_processing_time': sum(processing_times) / len(processing_times),
                'avg_articles_per_session': sum(article_counts) / len(article_counts),
                'processing_time_trend': self._calculate_trend(processing_times),
                'article_count_trend': self._calculate_trend(article_counts)
            }
        
        return stats
    
    def _calculate_trend(self, values: List[float]) -> str:
        """トレンド計算（簡易版）"""
        if len(values) < 2:
            return 'insufficient_data'
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            return 'increasing'
        elif second_avg < first_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    async def cleanup(self):
        """リソースクリーンアップ"""
        for collector in self.collectors.values():
            try:
                if hasattr(collector, 'session') and collector.session:
                    await collector.session.close()
            except Exception as e:
                self.logger.warning(f"Error closing collector session: {e}")
        
        self.logger.info("Collection manager cleanup completed")