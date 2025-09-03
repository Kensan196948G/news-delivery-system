"""
Reuters News Collector
Reutersニュース収集モジュール - RSS/Web Scraping ベース
"""

import asyncio
import aiohttp
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import feedparser

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_collector import BaseCollector
from ..models.article import Article


class ReutersCollector(BaseCollector):
    """Reutersニュース収集クラス"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger, 'reuters')
        
        # Reuters RSS フィード設定
        self.rss_feeds = {
            'world': 'https://www.reuters.com/world/feed/',
            'business': 'https://www.reuters.com/business/feed/',
            'technology': 'https://www.reuters.com/technology/feed/',
            'politics': 'https://www.reuters.com/politics-policy/feed/',
            'healthcare': 'https://www.reuters.com/business/healthcare-pharmaceuticals/feed/',
            'cybersecurity': 'https://www.reuters.com/world/cybersecurity/feed/',
            'markets': 'https://www.reuters.com/markets/feed/',
            'breakingviews': 'https://www.reuters.com/breakingviews/feed/'
        }
        
        # カテゴリマッピング
        self.category_mapping = {
            'domestic_social': ['world', 'politics'],
            'international_social': ['world', 'politics'],
            'domestic_economy': ['business', 'markets'],
            'international_economy': ['business', 'markets'],
            'tech': ['technology'],
            'security': ['cybersecurity', 'technology']
        }
        
        # ヘッダー設定（Webスクレイピング用）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 重複チェック用
        self._collected_hashes = set()
    
    async def collect(self, category: str = 'all', count: int = 20) -> List[Article]:
        """
        Reutersニュースを収集
        
        Args:
            category: 収集するカテゴリ
            count: 収集する記事数
            
        Returns:
            Article オブジェクトのリスト
        """
        try:
            self.logger.info(f"Starting Reuters news collection: category={category}, count={count}")
            start_time = datetime.now()
            
            # セッション状態確認
            await self._ensure_session()
            
            # 対象フィードを決定
            target_feeds = self._get_target_feeds(category)
            
            # 各フィードから記事を収集
            all_articles = []
            
            # 並行処理で各フィードから記事を収集
            tasks = []
            for feed_name in target_feeds:
                if feed_name in self.rss_feeds:
                    tasks.append(self._collect_from_feed(feed_name, count // len(target_feeds) + 5))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, list):
                        all_articles.extend(result)
                    elif isinstance(result, Exception):
                        self.logger.error(f"Feed collection error: {result}")
            
            # 記事を重要度順でソート
            all_articles.sort(key=lambda x: x.importance_score or 5, reverse=True)
            
            # 指定数に制限
            selected_articles = all_articles[:count]
            
            # 統計更新
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_collection_stats('articles_collected', count=len(selected_articles))
            
            self.logger.info(
                f"Reuters collection completed: {len(selected_articles)} articles in {processing_time:.2f}s"
            )
            
            return selected_articles
            
        except Exception as e:
            self.logger.error(f"Reuters collection failed: {str(e)}")
            self.update_collection_stats('request_failed', error=e)
            return []
    
    async def _collect_from_feed(self, feed_name: str, limit: int = 10) -> List[Article]:
        """
        特定のRSSフィードから記事を収集
        
        Args:
            feed_name: フィード名
            limit: 収集制限数
            
        Returns:
            記事リスト
        """
        articles = []
        
        try:
            feed_url = self.rss_feeds.get(feed_name)
            if not feed_url:
                self.logger.warning(f"Unknown feed: {feed_name}")
                return articles
            
            self.logger.debug(f"Fetching RSS feed: {feed_name} ({feed_url})")
            
            # キャッシュチェック
            cache_key = f"reuters_rss_{feed_name}"
            cached_data = self.cache.get(cache_key)
            
            if not cached_data:
                # RSS フィードを取得
                async with self.session.get(feed_url, headers=self.headers) as response:
                    if response.status == 200:
                        rss_content = await response.text()
                        # キャッシュに保存（15分）
                        self.cache.set(cache_key, rss_content, 900)
                        cached_data = rss_content
                    else:
                        self.logger.error(f"RSS fetch failed for {feed_name}: {response.status}")
                        return articles
            
            # RSS パース
            feed_data = feedparser.parse(cached_data)
            
            if not feed_data.entries:
                self.logger.warning(f"No entries found in RSS feed: {feed_name}")
                return articles
            
            # 記事を処理
            for entry in feed_data.entries[:limit]:
                try:
                    article = await self._parse_rss_entry(entry, feed_name)
                    if article and self._is_valid_article(article):
                        articles.append(article)
                        
                        # 制限数に達したら終了
                        if len(articles) >= limit:
                            break
                            
                except Exception as e:
                    self.logger.error(f"Error parsing RSS entry from {feed_name}: {e}")
                    continue
            
            self.logger.info(f"Collected {len(articles)} articles from {feed_name}")
            
        except Exception as e:
            self.logger.error(f"Error collecting from RSS feed {feed_name}: {e}")
        
        return articles
    
    async def _parse_rss_entry(self, entry, feed_name: str) -> Optional[Article]:
        """
        RSS エントリから記事オブジェクトを作成
        
        Args:
            entry: feedparser エントリ
            feed_name: フィード名
            
        Returns:
            Article オブジェクト
        """
        try:
            # 基本情報の抽出
            title = entry.get('title', '').strip()
            url = entry.get('link', '').strip()
            description = entry.get('description', '') or entry.get('summary', '')
            
            # 必須フィールドのチェック
            if not title or not url:
                return None
            
            # 日付のパース
            published_date = self._parse_entry_date(entry)
            
            # カテゴリの決定
            article_category = self._determine_category(title, description, feed_name)
            
            # 本文取得（必要に応じて）
            content = await self._extract_full_content(url, description)
            
            # 重要度の初期評価
            importance_score = self._calculate_importance(title, description, feed_name)
            
            # Articleオブジェクトの作成
            article = Article(
                url=url,
                title=title,
                description=description[:500] if description else '',
                content=content[:2000] if content else description[:500],  # 制限
                source_name='Reuters',
                author='Reuters Staff',
                published_at=published_date,
                collected_at=datetime.now().isoformat(),
                category=article_category,
                importance_score=importance_score,
                language='en'
            )
            
            return article
            
        except Exception as e:
            self.logger.error(f"Error parsing RSS entry: {e}")
            return None
    
    async def _extract_full_content(self, url: str, fallback_content: str) -> str:
        """
        記事のフルコンテンツを抽出（簡易実装）
        
        Args:
            url: 記事URL
            fallback_content: フォールバック用コンテンツ
            
        Returns:
            記事の本文
        """
        try:
            # キャッシュチェック
            cache_key = f"reuters_content_{self.create_content_hash(url)}"
            cached_content = self.cache.get(cache_key)
            
            if cached_content:
                return cached_content
            
            # レート制限（過度なWebアクセスを防ぐ）
            await asyncio.sleep(0.5)  # 500ms待機
            
            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    # 簡易的なコンテンツ抽出（正規表現ベース）
                    content = self._extract_content_from_html(html_content)
                    
                    if content and len(content) > 100:
                        # キャッシュに保存（1時間）
                        self.cache.set(cache_key, content, 3600)
                        return content
                    
        except Exception as e:
            self.logger.debug(f"Content extraction failed for {url}: {e}")
        
        # フォールバック
        return fallback_content
    
    def _extract_content_from_html(self, html: str) -> str:
        """
        HTMLからコンテンツを抽出（簡易実装）
        
        Args:
            html: HTML文字列
            
        Returns:
            抽出されたテキスト
        """
        try:
            # Reutersの記事構造に基づく抽出パターン
            patterns = [
                r'<div[^>]*class="[^"]*ArticleBody[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*data-module="ArticleBody"[^>]*>(.*?)</div>',
                r'<p[^>]*class="[^"]*text-paragraph[^"]*"[^>]*>(.*?)</p>',
                r'<div[^>]*class="[^"]*PaywallBarrier-text[^"]*"[^>]*>(.*?)</div>'
            ]
            
            content_parts = []
            
            for pattern in patterns:
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    # HTMLタグを除去
                    clean_text = re.sub(r'<[^>]+>', '', match)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    if clean_text and len(clean_text) > 50:
                        content_parts.append(clean_text)
            
            if content_parts:
                full_content = ' '.join(content_parts[:5])  # 最初の5段落
                return full_content[:2000]  # 2000文字制限
                
        except Exception as e:
            self.logger.debug(f"HTML content extraction error: {e}")
        
        return ""
    
    def _parse_entry_date(self, entry) -> str:
        """
        RSS エントリの日付をパース
        
        Args:
            entry: feedparser エントリ
            
        Returns:
            ISO形式の日付文字列
        """
        try:
            # feedparserの日付情報を使用
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                import time
                timestamp = time.mktime(entry.published_parsed)
                return datetime.fromtimestamp(timestamp).isoformat()
            
            # 文字列での日付パース
            date_str = entry.get('published', '') or entry.get('updated', '')
            if date_str:
                return self.parse_date(date_str)
                
        except Exception as e:
            self.logger.debug(f"Date parsing error: {e}")
        
        # フォールバック：現在時刻
        return datetime.now().isoformat()
    
    def _determine_category(self, title: str, description: str, feed_name: str) -> str:
        """
        記事カテゴリの決定
        
        Args:
            title: 記事タイトル
            description: 記事説明
            feed_name: フィード名
            
        Returns:
            カテゴリ名
        """
        text_to_analyze = f"{title} {description}".lower()
        
        # キーワードベースの分類
        category_keywords = {
            'security': ['cyber', 'hack', 'breach', 'security', 'malware', 'ransomware', 'vulnerability'],
            'tech': ['technology', 'ai', 'artificial intelligence', 'software', 'digital', 'tech', 'innovation'],
            'international_economy': ['global', 'international', 'trade', 'economy', 'market', 'gdp', 'inflation'],
            'international_social': ['human rights', 'migration', 'refugee', 'social', 'protest', 'conflict']
        }
        
        # キーワードマッチングによる分類
        for category, keywords in category_keywords.items():
            if any(keyword in text_to_analyze for keyword in keywords):
                return category
        
        # フィード名ベースのフォールバック
        feed_category_map = {
            'technology': 'tech',
            'cybersecurity': 'security',
            'business': 'international_economy',
            'markets': 'international_economy',
            'world': 'international_social',
            'politics': 'international_social'
        }
        
        return feed_category_map.get(feed_name, 'international_social')
    
    def _calculate_importance(self, title: str, description: str, feed_name: str) -> int:
        """
        記事の重要度を計算
        
        Args:
            title: 記事タイトル
            description: 記事説明
            feed_name: フィード名
            
        Returns:
            重要度スコア (1-10)
        """
        score = 5  # ベーススコア
        
        text_to_analyze = f"{title} {description}".lower()
        
        # 緊急性キーワード
        urgent_keywords = ['breaking', 'urgent', 'emergency', 'crisis', 'death', 'killed', 'attack', 'explosion']
        if any(keyword in text_to_analyze for keyword in urgent_keywords):
            score += 3
        
        # 重要性キーワード
        important_keywords = ['government', 'president', 'minister', 'ceo', 'major', 'significant', 'announces']
        if any(keyword in text_to_analyze for keyword in important_keywords):
            score += 2
        
        # セキュリティ関連は高優先度
        security_keywords = ['cyber', 'hack', 'breach', 'malware', 'vulnerability']
        if any(keyword in text_to_analyze for keyword in security_keywords):
            score += 2
        
        # フィード優先度
        feed_priority = {
            'breakingviews': 2,
            'cybersecurity': 2,
            'world': 1,
            'business': 1
        }
        score += feed_priority.get(feed_name, 0)
        
        # 最大値制限
        return min(score, 10)
    
    def _get_target_feeds(self, category: str) -> List[str]:
        """
        カテゴリに基づく対象フィードの取得
        
        Args:
            category: カテゴリ名
            
        Returns:
            フィード名のリスト
        """
        if category == 'all':
            return list(self.rss_feeds.keys())
        
        return self.category_mapping.get(category, ['world', 'business'])
    
    def _is_valid_article(self, article: Article) -> bool:
        """
        記事の有効性チェック
        
        Args:
            article: 記事オブジェクト
            
        Returns:
            有効かどうか
        """
        try:
            # 基本検証
            if not article.title or not article.url:
                return False
            
            # 重複チェック
            content_hash = self.create_content_hash(article.title + (article.content or ''))
            if content_hash in self._collected_hashes:
                return False
            
            self._collected_hashes.add(content_hash)
            
            # タイトル長さチェック
            if len(article.title) < 10 or len(article.title) > 300:
                return False
            
            # 除外キーワードチェック
            excluded_keywords = ['advertisement', 'sponsored', '[removed]', 'subscribe now']
            title_lower = article.title.lower()
            
            if any(keyword in title_lower for keyword in excluded_keywords):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Article validation error: {e}")
            return False
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        ソース情報を取得
        
        Returns:
            ソース情報辞書
        """
        return {
            'name': 'Reuters',
            'type': 'RSS Feed',
            'description': 'Global news and information services',
            'language': 'English',
            'feeds_available': list(self.rss_feeds.keys()),
            'update_frequency': '実時間更新',
            'reliability': 'High',
            'coverage': 'Global',
            'specialties': ['Breaking News', 'Business', 'Technology', 'Politics']
        }


# 使用例とテスト関数
async def test_reuters_collector():
    """Reutersコレクターのテスト"""
    
    class MockConfig:
        def get_api_key(self, service):
            return "mock_key"
    
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    
    config = MockConfig()
    logger = MockLogger()
    
    async with ReutersCollector(config, logger) as collector:
        # テクノロジーカテゴリのニュースを5件収集
        articles = await collector.collect(category='tech', count=5)
        
        print(f"\nCollected {len(articles)} articles:")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Category: {article.category}")
            print(f"   Importance: {article.importance_score}")
            print(f"   Published: {article.published_at}")
            print()
        
        # 統計情報
        stats = collector.get_collection_statistics()
        print(f"Collection Statistics: {stats}")
        
        # ソース情報
        source_info = collector.get_source_info()
        print(f"Source Info: {source_info}")


if __name__ == "__main__":
    asyncio.run(test_reuters_collector())