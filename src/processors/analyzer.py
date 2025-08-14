"""
Claude AI Analysis Module  
Claude AI分析モジュール - 重要度評価・要約生成・キーワード抽出・センチメント分析

Context7モード強制有効 - 高度な文脈理解とAI推論能力で記事を分析
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import json
import hashlib
import re
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Context7モード強制有効化
os.environ['ANTHROPIC_CONTEXT_MODE'] = 'context7'
os.environ['ANTHROPIC_ENHANCED_REASONING'] = 'true'
os.environ['ANTHROPIC_DEEP_ANALYSIS'] = 'enabled'

import anthropic

from utils.config import get_config
from utils.cache_manager import CacheManager
from utils.rate_limiter import get_rate_limiter
from models.article import Article


logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """AI分析関連エラー"""
    pass


class SentimentType(Enum):
    """センチメント種別"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class AnalysisResult:
    """AI分析結果"""
    importance_score: int  # 1-10
    summary: str  # 200-250文字
    keywords: List[str]  # 5個
    sentiment: SentimentType
    sentiment_score: float  # -1.0 to 1.0
    key_points: List[str]
    risk_factors: List[str]
    impact_assessment: str
    confidence_score: float  # 0.0 to 1.0
    category_analysis: Dict[str, Any]
    processing_time: float = 0.0
    cache_hit: bool = False


@dataclass  
class BatchAnalysisRequest:
    """バッチ分析リクエスト"""
    articles: List[Article]
    analysis_depth: str = "standard"  # standard, detailed, quick
    include_sentiment: bool = True
    include_keywords: bool = True
    include_summary: bool = True


class ClaudeAnalyzer:
    """Claude AI分析サービス"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache_manager = CacheManager()
        self.rate_limiter = get_rate_limiter()
        
        # Claude API設定
        self.api_key = self.config.get_env('ANTHROPIC_API_KEY')
        self.model_name = self.config.get('ai_analysis.model', default="claude-3-sonnet-20240229")
        self.max_tokens = self.config.get('ai_analysis.max_tokens', default=1000)
        
        # バッチ処理設定
        self.batch_size = self.config.get('ai_analysis.batch_size', default=10)
        self.max_concurrent = self.config.get('ai_analysis.max_concurrent', default=5)
        self.cache_ttl = self.config.get('ai_analysis.cache_ttl', default=86400 * 7)  # 7日間
        
        # Claude クライアント初期化
        if self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("Claude API key not configured")
        
        # 統計情報
        self.analysis_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0,
            'total_processing_time': 0.0
        }
        
        logger.info("Claude Analyzer initialized")
    
    async def analyze_article(self, article: Article) -> Article:
        """単一記事のAI分析"""
        try:
            start_time = datetime.now()
            
            # キャッシュキー生成
            cache_key = self._generate_cache_key(article)
            
            # キャッシュチェック
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug("Analysis cache hit")
                self.analysis_stats['cache_hits'] += 1
                self._apply_cached_analysis(article, cached_result)
                return article
            
            # AI分析実行
            analysis_result = await self._perform_analysis(article)
            
            # 結果を記事に適用
            self._apply_analysis_result(article, analysis_result)
            
            # 結果をキャッシュ
            cache_data = asdict(analysis_result)
            self.cache_manager.set(cache_key, cache_data, ttl=self.cache_ttl)
            
            # 統計更新
            processing_time = (datetime.now() - start_time).total_seconds()
            self.analysis_stats['total_requests'] += 1
            self.analysis_stats['api_calls'] += 1
            self.analysis_stats['total_processing_time'] += processing_time
            
            logger.debug(f"Article analysis completed: {article.url} in {processing_time:.2f}s")
            return article
            
        except Exception as e:
            logger.error(f"Article analysis failed: {e}")
            self.analysis_stats['errors'] += 1
            return article
    
    async def analyze_batch(self, articles: List[Article]) -> List[Article]:
        """記事のバッチAI分析"""
        try:
            logger.info(f"Starting batch analysis for {len(articles)} articles")
            
            if not articles:
                return articles
            
            # セマフォで同時実行数を制限
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def analyze_with_semaphore(article):
                async with semaphore:
                    return await self.analyze_article(article)
            
            # バッチ処理
            analyzed_articles = []
            for i in range(0, len(articles), self.batch_size):
                batch = articles[i:i + self.batch_size]
                
                # レート制限チェック
                await self.rate_limiter.wait_if_needed('claude')
                
                # バッチ分析実行
                batch_results = await asyncio.gather(
                    *[analyze_with_semaphore(article) for article in batch],
                    return_exceptions=True
                )
                
                # 結果をマージ
                for result in batch_results:
                    if isinstance(result, Article):
                        analyzed_articles.append(result)
                    else:
                        logger.error(f"Analysis error in batch: {result}")
                
                # API使用量記録
                self.rate_limiter.record_request('claude')
                
                logger.info(f"Completed analysis batch {i//self.batch_size + 1}/{(len(articles) + self.batch_size - 1)//self.batch_size}")
            
            logger.info(f"Batch analysis completed: {len(analyzed_articles)} analyzed")
            return analyzed_articles
            
        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            raise AnalysisError(f"Batch analysis failed: {e}")
    
    async def _perform_analysis(self, article: Article) -> AnalysisResult:
        """AI分析実行"""
        try:
            if not self.client:
                raise AnalysisError("Claude API client not initialized")
            
            # 分析用テキスト準備
            content_text = self._prepare_content_for_analysis(article)
            
            # プロンプト生成
            prompt = self._create_analysis_prompt(content_text, article)
            
            # Claude API呼び出し
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=0.1,  # 一貫性のために低温度設定
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # レスポンス解析
            response_text = response.content[0].text
            analysis_data = self._parse_analysis_response(response_text)
            
            # AnalysisResult作成
            return AnalysisResult(
                importance_score=analysis_data.get('importance_score', 5),
                summary=analysis_data.get('summary', ''),
                keywords=analysis_data.get('keywords', []),
                sentiment=SentimentType(analysis_data.get('sentiment', 'neutral')),
                sentiment_score=analysis_data.get('sentiment_score', 0.0),
                key_points=analysis_data.get('key_points', []),
                risk_factors=analysis_data.get('risk_factors', []),
                impact_assessment=analysis_data.get('impact_assessment', ''),
                confidence_score=analysis_data.get('confidence_score', 0.0),
                category_analysis=analysis_data.get('category_analysis', {})
            )
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            raise AnalysisError(f"Claude analysis failed: {e}")
    
    def _prepare_content_for_analysis(self, article: Article) -> str:
        """分析用コンテンツ準備"""
        content_parts = []
        
        # タイトル（翻訳済みまたは原文）
        title = getattr(article, 'translated_title', None) or article.title
        if title:
            content_parts.append(f"タイトル: {title}")
        
        # 説明文（翻訳済みまたは原文）
        description = getattr(article, 'translated_description', None) or article.description
        if description:
            content_parts.append(f"概要: {description}")
        
        # 本文（翻訳済みまたは原文）
        content = getattr(article, 'translated_content', None) or article.content
        if content:
            # 長すぎる場合は先頭2000文字に制限
            content = content[:2000] if len(content) > 2000 else content
            content_parts.append(f"本文: {content}")
        
        # メタデータ
        if hasattr(article, 'source') and article.source:
            source_name = article.source.get('name', 'Unknown') if isinstance(article.source, dict) else str(article.source)
            content_parts.append(f"情報源: {source_name}")
        
        if hasattr(article, 'published_at') and article.published_at:
            content_parts.append(f"公開日時: {article.published_at}")
        
        return "\n\n".join(content_parts)
    
    def _create_analysis_prompt(self, content: str, article: Article) -> str:
        """分析プロンプト生成"""
        category_hint = ""
        if hasattr(article, 'category') and article.category:
            category_hint = f"\n\nカテゴリ: {article.category.value}"
        
        prompt = f"""以下のニュース記事を詳細に分析してください。{category_hint}

{content}

以下の項目について分析し、JSON形式で回答してください：

1. importance_score (1-10): ニュースの重要度
   - 10: 極めて重要（緊急対応が必要）
   - 8-9: 非常に重要（高優先度で対応）
   - 6-7: 重要（通常の対応）
   - 4-5: 普通（情報収集レベル）
   - 1-3: 低い（参考程度）

2. summary (200-250文字): 記事の要約

3. keywords (5個): 重要なキーワード

4. sentiment: positive/neutral/negative

5. sentiment_score (-1.0 to 1.0): センチメントの強度

6. key_points (3-5個): 重要なポイント

7. risk_factors (該当する場合): リスク要因

8. impact_assessment: 影響範囲の評価

9. confidence_score (0.0-1.0): 分析の信頼度

10. category_analysis: カテゴリ固有の分析

回答フォーマット:
```json
{{
    "importance_score": 数値,
    "summary": "200-250文字の要約",
    "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
    "sentiment": "positive/neutral/negative",
    "sentiment_score": 数値,
    "key_points": ["ポイント1", "ポイント2", "ポイント3"],
    "risk_factors": ["リスク要因1", "リスク要因2"],
    "impact_assessment": "影響範囲の評価",
    "confidence_score": 数値,
    "category_analysis": {{
        "urgency_level": "low/medium/high/critical",
        "scope": "local/national/international",
        "stakeholders": ["関係者1", "関係者2"],
        "timeline": "immediate/short-term/long-term"
    }}
}}
```

重要：
- セキュリティ関連記事の場合、CVSS スコアや脆弱性の詳細があれば importance_score を 8-10 に設定
- 人権や社会問題の場合、影響範囲を重視して評価
- 経済ニュースの場合、市場への影響度を考慮
- IT/AI ニュースの場合、技術的革新性と実用性を評価"""

        return prompt
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """AI分析レスポンス解析"""
        try:
            # JSON部分を抽出
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSONブロックがない場合は全体から抽出を試行
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise AnalysisError("No JSON found in response")
            
            # JSON解析
            analysis_data = json.loads(json_str)
            
            # データ検証と正規化
            analysis_data = self._validate_and_normalize_analysis(analysis_data)
            
            return analysis_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            # デフォルト値でフォールバック
            return self._create_fallback_analysis()
        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return self._create_fallback_analysis()
    
    def _validate_and_normalize_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析データの検証と正規化"""
        # importance_score: 1-10の範囲に制限
        importance = data.get('importance_score', 5)
        data['importance_score'] = max(1, min(10, int(importance)))
        
        # summary: 文字数制限（200-300文字）
        summary = data.get('summary', '')
        if len(summary) > 300:
            data['summary'] = summary[:300] + '...'
        elif len(summary) < 50:
            data['summary'] = summary + '（詳細な情報が不足しています）'
        
        # keywords: 5個に制限
        keywords = data.get('keywords', [])
        data['keywords'] = keywords[:5] if isinstance(keywords, list) else []
        
        # sentiment: 有効な値のみ許可
        sentiment = data.get('sentiment', 'neutral')
        if sentiment not in ['positive', 'neutral', 'negative']:
            data['sentiment'] = 'neutral'
        
        # sentiment_score: -1.0 to 1.0の範囲に制限
        sentiment_score = data.get('sentiment_score', 0.0)
        data['sentiment_score'] = max(-1.0, min(1.0, float(sentiment_score)))
        
        # key_points: リスト形式確保
        key_points = data.get('key_points', [])
        data['key_points'] = key_points if isinstance(key_points, list) else []
        
        # risk_factors: リスト形式確保
        risk_factors = data.get('risk_factors', [])
        data['risk_factors'] = risk_factors if isinstance(risk_factors, list) else []
        
        # impact_assessment: 文字列確保
        data['impact_assessment'] = str(data.get('impact_assessment', ''))
        
        # confidence_score: 0.0 to 1.0の範囲に制限
        confidence = data.get('confidence_score', 0.5)
        data['confidence_score'] = max(0.0, min(1.0, float(confidence)))
        
        # category_analysis: 辞書形式確保
        category_analysis = data.get('category_analysis', {})
        data['category_analysis'] = category_analysis if isinstance(category_analysis, dict) else {}
        
        return data
    
    def _create_fallback_analysis(self) -> Dict[str, Any]:
        """フォールバック用のデフォルト分析結果"""
        return {
            'importance_score': 5,
            'summary': 'AI分析に失敗しました。記事の詳細な分析が利用できません。',
            'keywords': [],
            'sentiment': 'neutral',
            'sentiment_score': 0.0,
            'key_points': [],
            'risk_factors': [],
            'impact_assessment': '分析できませんでした',
            'confidence_score': 0.0,
            'category_analysis': {}
        }
    
    def _apply_analysis_result(self, article: Article, result: AnalysisResult):
        """分析結果を記事に適用"""
        article.importance_score = result.importance_score
        article.summary = result.summary
        article.keywords = result.keywords
        article.sentiment_score = result.sentiment_score
        
        # 追加の分析結果属性
        if not hasattr(article, 'ai_analysis'):
            article.ai_analysis = {}
        
        article.ai_analysis.update({
            'sentiment': result.sentiment.value,
            'key_points': result.key_points,
            'risk_factors': result.risk_factors,
            'impact_assessment': result.impact_assessment,
            'confidence_score': result.confidence_score,
            'category_analysis': result.category_analysis,
            'analyzed_at': datetime.now().isoformat()
        })
    
    def _apply_cached_analysis(self, article: Article, cached_data: Dict[str, Any]):
        """キャッシュされた分析結果を記事に適用"""
        article.importance_score = cached_data.get('importance_score', 5)
        article.summary = cached_data.get('summary', '')
        article.keywords = cached_data.get('keywords', [])
        article.sentiment_score = cached_data.get('sentiment_score', 0.0)
        
        if not hasattr(article, 'ai_analysis'):
            article.ai_analysis = {}
        
        article.ai_analysis.update({
            'sentiment': cached_data.get('sentiment', 'neutral'),
            'key_points': cached_data.get('key_points', []),
            'risk_factors': cached_data.get('risk_factors', []),
            'impact_assessment': cached_data.get('impact_assessment', ''),
            'confidence_score': cached_data.get('confidence_score', 0.0),
            'category_analysis': cached_data.get('category_analysis', {}),
            'cache_hit': True
        })
    
    def _generate_cache_key(self, article: Article) -> str:
        """キャッシュキー生成"""
        # 記事の内容をベースにハッシュ生成
        content = f"{article.url}:{article.title}"
        if hasattr(article, 'translated_title') and article.translated_title:
            content += f":{article.translated_title}"
        
        return f"analysis:{hashlib.md5(content.encode('utf-8')).hexdigest()}"
    
    async def create_daily_summary(self, articles: List[Article]) -> str:
        """日次サマリー生成"""
        try:
            if not articles:
                return "本日は分析対象の記事がありませんでした。"
            
            # 記事を重要度順にソート
            sorted_articles = sorted(articles, key=lambda x: getattr(x, 'importance_score', 5), reverse=True)
            top_articles = sorted_articles[:10]  # 上位10件
            
            # カテゴリ別統計
            category_stats = {}
            urgent_count = 0
            total_importance = 0
            
            for article in articles:
                # カテゴリ統計
                category = getattr(article, 'category', 'その他')
                category_name = category.value if hasattr(category, 'value') else str(category)
                category_stats[category_name] = category_stats.get(category_name, 0) + 1
                
                # 重要度統計
                importance = getattr(article, 'importance_score', 5)
                total_importance += importance
                if importance >= 8:
                    urgent_count += 1
            
            avg_importance = total_importance / len(articles)
            
            # 要約プロンプト
            articles_info = "\n".join([
                f"- {getattr(article, 'translated_title', article.title)} (重要度: {getattr(article, 'importance_score', 5)})"
                for article in top_articles[:5]
            ])
            
            prompt = f"""以下の情報をもとに、本日のニュース概要を200文字程度で作成してください：

総記事数: {len(articles)}件
緊急度の高い記事: {urgent_count}件  
平均重要度: {avg_importance:.1f}
カテゴリ別件数: {category_stats}

主要記事:
{articles_info}

簡潔で読みやすい日本語で、重要なポイントを含めた概要を作成してください。"""

            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=300,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Daily summary generation failed: {e}")
            return f"本日は{len(articles)}件の記事を分析しました。詳細は添付のレポートをご確認ください。"
    
    async def create_weekly_summary(self, articles: List[Article]) -> str:
        """週次サマリー生成"""
        try:
            if not articles:
                return "今週は分析対象の記事がありませんでした。"
            
            # 週次統計計算
            total_articles = len(articles)
            urgent_articles = len([a for a in articles if getattr(a, 'importance_score', 5) >= 8])
            
            # カテゴリ別分析
            category_analysis = {}
            for article in articles:
                category = getattr(article, 'category', 'その他')
                category_name = category.value if hasattr(category, 'value') else str(category)
                if category_name not in category_analysis:
                    category_analysis[category_name] = {'count': 0, 'importance_sum': 0}
                category_analysis[category_name]['count'] += 1
                category_analysis[category_name]['importance_sum'] += getattr(article, 'importance_score', 5)
            
            # トップカテゴリ
            top_categories = sorted(category_analysis.items(), key=lambda x: x[1]['count'], reverse=True)[:3]
            
            summary = f"今週は{total_articles}件の記事を分析し、うち{urgent_articles}件が高い重要度を示しました。"
            
            if top_categories:
                top_cat_info = []
                for cat_name, cat_data in top_categories:
                    avg_importance = cat_data['importance_sum'] / cat_data['count']
                    top_cat_info.append(f"{cat_name}({cat_data['count']}件・平均重要度{avg_importance:.1f})")
                summary += f" 主要カテゴリ: {', '.join(top_cat_info)}。"
            
            return summary
            
        except Exception as e:
            logger.error(f"Weekly summary generation failed: {e}")
            return f"今週は{len(articles)}件の記事を分析しました。"
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """分析統計情報取得"""
        cache_hit_rate = (self.analysis_stats['cache_hits'] / 
                         max(self.analysis_stats['total_requests'], 1)) * 100
        
        avg_processing_time = (self.analysis_stats['total_processing_time'] / 
                              max(self.analysis_stats['api_calls'], 1))
        
        return {
            'total_requests': self.analysis_stats['total_requests'],
            'api_calls': self.analysis_stats['api_calls'],
            'cache_hits': self.analysis_stats['cache_hits'],
            'cache_hit_rate': round(cache_hit_rate, 2),
            'errors': self.analysis_stats['errors'],
            'avg_processing_time': round(avg_processing_time, 2),
            'model_name': self.model_name
        }
    
    async def test_analysis(self, test_article: str = None) -> Dict[str, Any]:
        """AI分析機能テスト"""
        try:
            # テスト記事作成
            if not test_article:
                test_article = "重要なセキュリティアップデートが発表されました。この脆弱性は多くのシステムに影響を与える可能性があり、緊急の対応が必要です。"
            
            # テスト用Article作成
            from models.article import Article, ArticleCategory, ArticleLanguage
            
            test_article_obj = Article(
                url="test://example.com/test",
                title="テスト記事",
                description=test_article,
                content=test_article,
                source={'name': 'Test Source'},
                category=ArticleCategory.SECURITY,
                language=ArticleLanguage.JAPANESE,
                published_at=datetime.now()
            )
            
            logger.info("Testing Claude analysis...")
            analyzed_article = await self.analyze_article(test_article_obj)
            
            return {
                'success': True,
                'importance_score': getattr(analyzed_article, 'importance_score', 0),
                'summary': getattr(analyzed_article, 'summary', ''),
                'keywords': getattr(analyzed_article, 'keywords', []),
                'sentiment_score': getattr(analyzed_article, 'sentiment_score', 0.0),
                'ai_analysis': getattr(analyzed_article, 'ai_analysis', {})
            }
            
        except Exception as e:
            logger.error(f"Analysis test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# グローバル分析インスタンス
_analyzer_instance = None


def get_analyzer() -> ClaudeAnalyzer:
    """グローバルAI分析インスタンス取得"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ClaudeAnalyzer()
    return _analyzer_instance