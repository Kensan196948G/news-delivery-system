"""
GNews Collector - Enhanced Version
GNews API からのニュース収集 - 強化版
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base_collector import BaseCollector, CollectionError, APIError
from models.article import Article, ArticleCategory, ArticleLanguage


class GNewsCollector(BaseCollector):
    """GNews API からのニュース収集"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger, 'gnews')
        self.base_url = "https://gnews.io/api/v4"
        
        # GNews固有設定
        self.daily_limit = config.get('news_sources', 'gnews', 'rate_limit_per_day', default=100)
        self.request_count = 0
        
        # 重複チェック用ハッシュセット初期化
        self._collected_hashes = set()
        
        # カテゴリマッピング
        self.category_mapping = {
            'general': ArticleCategory.INTERNATIONAL_SOCIAL,
            'world': ArticleCategory.INTERNATIONAL_SOCIAL,
            'nation': ArticleCategory.INTERNATIONAL_SOCIAL,
            'business': ArticleCategory.INTERNATIONAL_ECONOMY,
            'technology': ArticleCategory.TECH,
            'entertainment': ArticleCategory.INTERNATIONAL_SOCIAL,
            'sports': ArticleCategory.INTERNATIONAL_SOCIAL,
            'science': ArticleCategory.TECH,
            'health': ArticleCategory.INTERNATIONAL_SOCIAL,
        }
        
        # 人権関連キーワード（国際社会ニュースで優先）
        self.human_rights_keywords = [
            'human rights', 'social justice', 'migration', 'refugee',
            'discrimination', 'equality', 'civil rights', 'freedom',
            'democracy', 'protest', 'activism', 'minority rights',
            'humanitarian crisis', 'war crimes', 'genocide', 'persecution'
        ]
        
        # 技術関連キーワード拡張
        self.tech_keywords = {
            'artificial intelligence': ['AI', 'machine learning', 'deep learning', 'neural networks'],
            'cybersecurity': ['cyber attack', 'data breach', 'vulnerability', 'ransomware'],
            'blockchain': ['cryptocurrency', 'bitcoin', 'ethereum', 'NFT'],
            'cloud computing': ['AWS', 'Azure', 'Google Cloud', 'serverless'],
            'quantum computing': ['quantum', 'qubit', 'quantum supremacy'],
            'autonomous vehicles': ['self-driving', 'autonomous car', 'Tesla autopilot']
        }
        
        # 地域・言語優先度設定
        self.region_priority = {
            'us': ['en'],
            'uk': ['en'], 
            'ca': ['en'],
            'au': ['en'],
            'in': ['en'],
            'sg': ['en']
        }
        
        # 品質向上設定
        self.quality_filters = {
            'min_content_words': 50,
            'exclude_domains': ['reddit.com', 'twitter.com', 'facebook.com'],
            'prefer_domains': ['reuters.com', 'ap.org', 'bbc.com', 'cnn.com', 'npr.org'],
            'exclude_title_patterns': [r'\[.*\]$', r'UPDATE \d+', r'LIVE:']
        }
    
    async def collect(self, query: str = None, 
                     category: str = 'general',
                     language: str = 'en',
                     country: str = 'us',
                     max_results: int = 50) -> List[Article]:
        """GNewsからニュースを収集"""
        
        # 日次制限チェック
        if self.request_count >= self.daily_limit:
            self.logger.warning(f"GNews daily limit reached: {self.daily_limit}")
            return []
        
        # エンドポイントとパラメータ決定
        if query:
            url = f"{self.base_url}/search"
            params = {
                'apikey': self.api_key,
                'q': query,
                'lang': language,
                'country': country,
                'max': min(max_results, 100),
                'sortby': 'relevancy'
            }
        else:
            url = f"{self.base_url}/top-headlines"
            params = {
                'apikey': self.api_key,
                'category': category,
                'lang': language,
                'country': country,
                'max': min(max_results, 100),
                'sortby': 'publishedAt'
            }
        
        try:
            if query:
                self.logger.info(f"Searching GNews: query='{query}', lang={language}")
            else:
                self.logger.info(f"Fetching GNews headlines: category={category}, country={country}")
            
            # APIリクエスト実行
            data = await self.fetch_with_cache(url, params, cache_ttl=3600)
            
            if not data:
                return []
            
            # レスポンス処理
            articles_data = data.get('articles', [])
            total_articles = data.get('totalArticles', 0)
            
            self.logger.info(f"GNews returned {len(articles_data)} articles (total: {total_articles})")
            
            # 記事変換
            articles = self._process_articles(articles_data, category, query)
            
            self.request_count += 1
            self.logger.info(f"GNews: Successfully collected {len(articles)} articles")
            
            return articles
            
        except Exception as e:
            self.logger.error(f"GNews collection failed: {e}")
            return []
    
    async def collect_human_rights_news(self, max_results: int = 30) -> List[Article]:
        """人権関連ニュースを優先収集"""
        all_articles = []
        
        for keyword in self.human_rights_keywords[:5]:  # 上位5キーワードで検索
            try:
                articles = await self.collect(
                    query=keyword,
                    language='en',
                    country='us',
                    max_results=max_results // 5
                )
                all_articles.extend(articles)
                
            except Exception as e:
                self.logger.warning(f"Failed to collect human rights news for '{keyword}': {e}")
                continue
        
        # 重複除去と重要度順ソート
        unique_articles = self._deduplicate_by_title(all_articles)
        
        self.logger.info(f"Collected {len(unique_articles)} unique human rights articles")
        return unique_articles
    
    async def collect_tech_news(self, max_results: int = 40) -> List[Article]:
        """IT/AI技術ニュースを収集"""
        tech_queries = [
            'artificial intelligence',
            'machine learning',
            'cybersecurity',
            'blockchain',
            'cloud computing'
        ]
        
        all_articles = []
        
        for query in tech_queries:
            try:
                articles = await self.collect(
                    query=query,
                    language='en',
                    country='us',
                    max_results=max_results // len(tech_queries)
                )
                all_articles.extend(articles)
                
            except Exception as e:
                self.logger.warning(f"Failed to collect tech news for '{query}': {e}")
                continue
        
        unique_articles = self._deduplicate_by_title(all_articles)
        
        self.logger.info(f"Collected {len(unique_articles)} unique tech articles")
        return unique_articles
    
    def _process_articles(self, articles_data: List[Dict[str, Any]], 
                         category: str, query: Optional[str] = None) -> List[Article]:
        """記事データの処理・変換"""
        processed_articles = []
        
        for article_data in articles_data:
            try:
                # 基本検証
                if not self.validate_article_data(article_data):
                    continue
                
                # 記事オブジェクト作成
                article = self._create_article(article_data, category, query)
                
                if article:
                    processed_articles.append(article)
                    
            except Exception as e:
                self.logger.warning(f"Failed to process GNews article: {e}")
                continue
        
        self.logger.debug(f"Processed {len(processed_articles)} valid articles")
        return processed_articles
    
    def _create_article(self, article_data: Dict[str, Any], 
                       category: str, query: Optional[str] = None) -> Optional[Article]:
        """記事オブジェクトの作成"""
        try:
            # ソース情報
            source = article_data.get('source', {})
            source_name = source.get('name', 'GNews') if isinstance(source, dict) else str(source)
            
            # カテゴリ決定
            if query and any(keyword in query.lower() for keyword in self.human_rights_keywords):
                article_category = ArticleCategory.INTERNATIONAL_SOCIAL
            elif query and 'tech' in query.lower() or 'ai' in query.lower():
                article_category = ArticleCategory.TECH
            else:
                article_category = self.category_mapping.get(category, ArticleCategory.INTERNATIONAL_SOCIAL)
            
            # 記事内容
            content = article_data.get('content') or article_data.get('description', '')
            
            # 画像URL
            image_url = article_data.get('image')
            
            article = Article(
                title=article_data.get('title', '').strip(),
                content=content.strip(),
                url=article_data.get('url', ''),
                source_name=source_name,
                category=article_category,
                published_at=self.parse_date(article_data.get('publishedAt'))
            )
            
            # 人権関連記事の重要度アップ
            if query and any(keyword in query.lower() for keyword in self.human_rights_keywords):
                article.importance_score = 7  # 基準より高い重要度
            
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to create Article object: {e}")
            return None
    
    def _deduplicate_by_title(self, articles: List[Article]) -> List[Article]:
        """タイトルによる重複除去"""
        seen_titles = set()
        unique_articles = []
        
        for article in articles:
            normalized_title = article.title.lower().strip()
            
            if normalized_title not in seen_titles and len(normalized_title) > 10:
                seen_titles.add(normalized_title)
                unique_articles.append(article)
        
        return unique_articles
    
    def get_remaining_requests(self) -> int:
        """残りリクエスト数を取得"""
        return max(0, self.daily_limit - self.request_count)
    
    def get_service_status(self) -> Dict[str, Any]:
        """サービス状況を取得"""
        return {
            'service': 'gnews',
            'daily_limit': self.daily_limit,
            'requests_made': self.request_count,
            'remaining_requests': self.get_remaining_requests(),
            'rate_limit_status': self.get_rate_limit_status(),
            'api_key_configured': bool(self.api_key)
        }
    
    # Main.pyとの統合用メソッド追加
    async def collect_by_query(self, query: str, count: int, language: str = 'en', country: str = 'us') -> List[Article]:
        """クエリによる記事収集（main.py統合用）"""
        return await self.collect(
            query=query,
            language=language, 
            country=country,
            max_results=count
        )
    
    async def collect_by_category(self, category: str, count: int, language: str = 'en', country: str = 'us') -> List[Article]:
        """カテゴリによる記事収集（main.py統合用）"""
        return await self.collect(
            category=category,
            language=language,
            country=country,
            max_results=count
        )