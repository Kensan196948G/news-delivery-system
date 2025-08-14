"""
NewsAPI Collector
NewsAPI.org からのニュース収集
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_collector import BaseCollector
from models.article import Article, ArticleCategory, ArticleLanguage


class NewsAPICollector(BaseCollector):
    """NewsAPI.org からのニュース収集"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger, 'newsapi')
        self.base_url = "https://newsapi.org/v2"
        
        # NewsAPI固有設定
        self.daily_limit = config.get('news_sources', 'newsapi', 'rate_limit_per_day', default=1000)
        self.request_count = 0
        
        # カテゴリマッピング
        self.category_mapping = {
            'general': ArticleCategory.DOMESTIC_SOCIAL,
            'business': ArticleCategory.DOMESTIC_ECONOMY,
            'technology': ArticleCategory.TECH,
            'science': ArticleCategory.TECH,
            'health': ArticleCategory.DOMESTIC_SOCIAL,
            'sports': ArticleCategory.DOMESTIC_SOCIAL,
            'entertainment': ArticleCategory.DOMESTIC_SOCIAL,
        }
    
    async def collect(self, category: str = 'general', 
                     country: str = 'jp', 
                     language: str = 'ja',
                     page_size: int = 50) -> List[Article]:
        """NewsAPIからニュースを収集"""
        
        # 日次制限チェック
        if self.request_count >= self.daily_limit:
            self.logger.warning(f"NewsAPI daily limit reached: {self.daily_limit}")
            return []
        
        # リクエストパラメータ
        url = f"{self.base_url}/top-headlines"
        params = {
            'apiKey': self.api_key,
            'category': category,
            'country': country,
            'language': language,
            'pageSize': min(page_size, 100),
            'sortBy': 'publishedAt'
        }
        
        try:
            self.logger.info(f"Fetching NewsAPI articles: category={category}, country={country}")
            
            # APIリクエスト実行
            data = await self.fetch_with_cache(url, params, cache_ttl=3600)
            
            if not data:
                return []
            
            # レスポンス処理
            articles_data = data.get('articles', [])
            total_results = data.get('totalResults', 0)
            
            self.logger.info(f"NewsAPI returned {len(articles_data)} articles (total: {total_results})")
            
            # 記事変換
            articles = self._process_articles(articles_data, category, country)
            
            self.request_count += 1
            self.logger.info(f"NewsAPI: Successfully collected {len(articles)} articles")
            
            return articles
            
        except Exception as e:
            self.logger.error(f"NewsAPI collection failed: {e}")
            return []
    
    async def collect_everything(self, query: str, 
                                language: str = 'en',
                                sort_by: str = 'relevancy',
                                page_size: int = 50) -> List[Article]:
        """NewsAPI Everythingエンドポイントでクエリ検索"""
        
        if self.request_count >= self.daily_limit:
            self.logger.warning(f"NewsAPI daily limit reached: {self.daily_limit}")
            return []
        
        url = f"{self.base_url}/everything"
        params = {
            'apiKey': self.api_key,
            'q': query,
            'language': language,
            'sortBy': sort_by,
            'pageSize': min(page_size, 100)
        }
        
        try:
            self.logger.info(f"Searching NewsAPI: query='{query}', language={language}")
            
            data = await self.fetch_with_cache(url, params, cache_ttl=1800)  # 30分キャッシュ
            
            if not data:
                return []
            
            articles_data = data.get('articles', [])
            
            # カテゴリ推定
            category = self._infer_category_from_query(query)
            
            articles = self._process_articles(articles_data, category, 'international')
            
            self.request_count += 1
            self.logger.info(f"NewsAPI Everything: Successfully collected {len(articles)} articles")
            
            return articles
            
        except Exception as e:
            self.logger.error(f"NewsAPI Everything search failed: {e}")
            return []
    
    def _process_articles(self, articles_data: List[Dict[str, Any]], 
                         category: str, country: str) -> List[Article]:
        """記事データの処理・変換"""
        processed_articles = []
        
        for article_data in articles_data:
            try:
                # 基本検証
                if not self.validate_article_data(article_data):
                    continue
                
                # 記事オブジェクト作成
                article = self._create_article(article_data, category, country)
                
                if article:
                    processed_articles.append(article)
                    
            except Exception as e:
                self.logger.warning(f"Failed to process article: {e}")
                continue
        
        self.logger.debug(f"Processed {len(processed_articles)} valid articles")
        return processed_articles
    
    def _create_article(self, article_data: Dict[str, Any], 
                       category: str, country: str) -> Optional[Article]:
        """記事オブジェクトの作成"""
        try:
            # ソース情報
            source = article_data.get('source', {})
            source_name = source.get('name', 'NewsAPI') if isinstance(source, dict) else str(source)
            
            # カテゴリ・言語判定
            article_category = self.category_mapping.get(category, ArticleCategory.DOMESTIC_SOCIAL)
            
            if country == 'jp':
                language = ArticleLanguage.JAPANESE
            else:
                language = ArticleLanguage.ENGLISH
            
            # 記事内容
            content = article_data.get('content') or article_data.get('description', '')
            
            # URLのドメイン抽出
            url = article_data.get('url', '')
            if url and len(url) > 2000:  # URL長すぎる場合は切り詰め
                url = url[:2000]
            
            article = Article(
                title=article_data.get('title', '').strip(),
                content=content.strip(),
                url=url,
                source_name=source_name,
                category=article_category,
                published_at=self.parse_date(article_data.get('publishedAt')),
                author=article_data.get('author')
            )
            
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to create Article object: {e}")
            return None
    
    def _infer_category_from_query(self, query: str) -> str:
        """検索クエリからカテゴリを推定"""
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ['technology', 'ai', 'tech', 'software']):
            return 'technology'
        elif any(keyword in query_lower for keyword in ['business', 'economy', 'market', 'finance']):
            return 'business'
        elif any(keyword in query_lower for keyword in ['health', 'medical', 'healthcare']):
            return 'health'
        elif any(keyword in query_lower for keyword in ['security', 'cyber', 'vulnerability']):
            return 'technology'  # セキュリティはテクノロジーとして分類
        else:
            return 'general'
    
    def get_remaining_requests(self) -> int:
        """残りリクエスト数を取得"""
        return max(0, self.daily_limit - self.request_count)
    
    def get_service_status(self) -> Dict[str, Any]:
        """サービス状況を取得"""
        return {
            'service': 'newsapi',
            'daily_limit': self.daily_limit,
            'requests_made': self.request_count,
            'remaining_requests': self.get_remaining_requests(),
            'rate_limit_status': self.get_rate_limit_status(),
            'api_key_configured': bool(self.api_key)
        }