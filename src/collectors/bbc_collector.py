"""
BBC News Collector
BBC ニュース収集モジュール - RSS ベース
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


class BBCCollector(BaseCollector):
    """BBC ニュース収集クラス"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger, 'bbc')
        
        # BBC RSS フィード設定
        self.rss_feeds = {
            'top_stories': 'http://feeds.bbci.co.uk/news/rss.xml',
            'world': 'http://feeds.bbci.co.uk/news/world/rss.xml',
            'uk': 'http://feeds.bbci.co.uk/news/uk/rss.xml',
            'business': 'http://feeds.bbci.co.uk/news/business/rss.xml',
            'technology': 'http://feeds.bbci.co.uk/news/technology/rss.xml',
            'science': 'http://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
            'health': 'http://feeds.bbci.co.uk/news/health/rss.xml',
            'politics': 'http://feeds.bbci.co.uk/news/politics/rss.xml',
            'entertainment': 'http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml',
            'education': 'http://feeds.bbci.co.uk/news/education/rss.xml'
        }
        
        # カテゴリマッピング
        self.category_mapping = {
            'domestic_social': ['uk', 'politics', 'health'],
            'international_social': ['world', 'politics'],
            'domestic_economy': ['business', 'uk'],
            'international_economy': ['business', 'world'],
            'tech': ['technology', 'science'],
            'security': ['technology', 'world']
        }
        
        # ヘッダー設定
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # 重複チェック用
        self._collected_hashes = set()
    
    async def collect(self, category: str = 'all', count: int = 20) -> List[Article]:
        """
        BBC ニュースを収集
        
        Args:
            category: 収集するカテゴリ
            count: 収集する記事数
            
        Returns:
            Article オブジェクトのリスト
        """
        try:
            self.logger.info(f"Starting BBC news collection: category={category}, count={count}")
            start_time = datetime.now()
            
            # セッション状態確認
            await self._ensure_session()
            
            # 対象フィードを決定
            target_feeds = self._get_target_feeds(category)
            
            # 各フィードから記事を収集
            all_articles = []
            
            # 並行処理で各フィードから記事を収集
            tasks = []
            articles_per_feed = max(1, count // len(target_feeds)) + 3
            
            for feed_name in target_feeds:
                if feed_name in self.rss_feeds:
                    tasks.append(self._collect_from_feed(feed_name, articles_per_feed))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, list):
                        all_articles.extend(result)
                    elif isinstance(result, Exception):
                        self.logger.error(f"Feed collection error: {result}")
            
            # 記事を重要度と日付でソート
            all_articles.sort(
                key=lambda x: (x.importance_score or 5, x.published_at or ''), 
                reverse=True
            )
            
            # 指定数に制限
            selected_articles = all_articles[:count]
            
            # 統計更新
            processing_time = (datetime.now() - start_time).total_seconds()
            self.update_collection_stats('articles_collected', count=len(selected_articles))
            
            self.logger.info(
                f"BBC collection completed: {len(selected_articles)} articles in {processing_time:.2f}s"
            )
            
            return selected_articles
            
        except Exception as e:
            self.logger.error(f"BBC collection failed: {str(e)}")
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
            
            self.logger.debug(f"Fetching BBC RSS feed: {feed_name} ({feed_url})")
            
            # キャッシュチェック
            cache_key = f"bbc_rss_{feed_name}"
            cached_data = self.cache.get(cache_key)
            
            if not cached_data:
                # RSS フィードを取得
                try:
                    async with self.session.get(feed_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 200:
                            rss_content = await response.text()
                            # キャッシュに保存（10分）
                            self.cache.set(cache_key, rss_content, 600)
                            cached_data = rss_content
                        else:
                            self.logger.error(f"RSS fetch failed for {feed_name}: {response.status}")
                            return articles
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout fetching RSS feed: {feed_name}")
                    return articles
            
            # RSS パース
            try:
                feed_data = feedparser.parse(cached_data)
                
                if not feed_data.entries:
                    self.logger.warning(f"No entries found in RSS feed: {feed_name}")
                    return articles
            except Exception as e:
                self.logger.error(f"Failed to parse RSS feed {feed_name}: {e}")
                return articles
            
            # 記事を処理
            processed_count = 0
            for entry in feed_data.entries:
                try:
                    if processed_count >= limit:
                        break
                        
                    article = await self._parse_rss_entry(entry, feed_name)
                    if article and self._is_valid_article(article):
                        articles.append(article)
                        processed_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error parsing RSS entry from {feed_name}: {e}")
                    continue
            
            self.logger.info(f"Collected {len(articles)} articles from BBC {feed_name}")
            
        except Exception as e:
            self.logger.error(f"Error collecting from BBC RSS feed {feed_name}: {e}")
        
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
            
            # BBC URLの正規化
            if url and not url.startswith('http'):
                url = 'https://www.bbc.com' + url
            
            # 日付のパース
            published_date = self._parse_entry_date(entry)
            
            # カテゴリの決定
            article_category = self._determine_category(title, description, feed_name)
            
            # 記事本文の取得（簡易版）
            content = self._clean_description(description)
            
            # 重要度の初期評価
            importance_score = self._calculate_importance(title, description, feed_name)
            
            # 作者情報の抽出
            author = self._extract_author(entry) or "BBC News"
            
            # Articleオブジェクトの作成
            article = Article(
                url=url,
                title=title,
                description=description[:500] if description else '',
                content=content[:1500] if content else description[:500],
                source_name='BBC News',
                author=author,
                published_at=published_date,
                collected_at=datetime.now().isoformat(),
                category=article_category,
                importance_score=importance_score,
                language='en'
            )
            
            return article
            
        except Exception as e:
            self.logger.error(f"Error parsing BBC RSS entry: {e}")
            return None
    
    def _clean_description(self, description: str) -> str:
        """
        記事説明文のクリーニング
        
        Args:
            description: 元の説明文
            
        Returns:
            クリーンな説明文
        """
        if not description:
            return ""
        
        try:
            # HTMLタグの除去
            clean_text = re.sub(r'<[^>]+>', '', description)
            
            # 特殊文字の正規化
            clean_text = re.sub(r'&quot;', '"', clean_text)
            clean_text = re.sub(r'&amp;', '&', clean_text)
            clean_text = re.sub(r'&lt;', '<', clean_text)
            clean_text = re.sub(r'&gt;', '>', clean_text)
            clean_text = re.sub(r'&apos;', "'", clean_text)
            
            # 複数の空白を1つに統一
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            return clean_text
            
        except Exception as e:
            self.logger.debug(f"Description cleaning error: {e}")
            return description
    
    def _extract_author(self, entry) -> Optional[str]:
        """
        記事の作者を抽出
        
        Args:
            entry: feedparser エントリ
            
        Returns:
            作者名
        """
        try:
            # feedparserから作者情報を取得
            author = entry.get('author', '') or entry.get('dc_creator', '')
            
            if author and author.strip():
                return author.strip()
            
            # 記事内から作者を抽出する試み
            description = entry.get('description', '')
            if description:
                # "By [Author Name]" パターンを探索
                author_match = re.search(r'By\s+([A-Za-z\s]+?)(?:\s*,|\s*$)', description)
                if author_match:
                    return author_match.group(1).strip()
            
        except Exception as e:
            self.logger.debug(f"Author extraction error: {e}")
        
        return None
    
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
            
            # updated_parsedも確認
            if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                import time
                timestamp = time.mktime(entry.updated_parsed)
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
            'security': [
                'cyber', 'hack', 'hacker', 'breach', 'security', 'malware', 'ransomware', 
                'vulnerability', 'data breach', 'phishing', 'scam', 'fraud'
            ],
            'tech': [
                'technology', 'tech', 'ai', 'artificial intelligence', 'machine learning',
                'software', 'digital', 'innovation', 'startup', 'google', 'apple', 'microsoft',
                'robot', 'automation', 'internet', 'online', 'app', 'smartphone'
            ],
            'international_economy': [
                'economy', 'economic', 'market', 'markets', 'trade', 'gdp', 'inflation',
                'financial', 'finance', 'stock', 'shares', 'investment', 'global economy',
                'recession', 'growth', 'bank', 'banking'
            ],
            'international_social': [
                'human rights', 'migration', 'refugee', 'protest', 'conflict', 'war',
                'peace', 'democracy', 'election', 'government', 'politics', 'social',
                'climate', 'environment'
            ]
        }
        
        # キーワードマッチングによる分類
        for category, keywords in category_keywords.items():
            if any(keyword in text_to_analyze for keyword in keywords):
                return category
        
        # フィード名ベースのマッピング
        feed_category_map = {
            'technology': 'tech',
            'science': 'tech',
            'business': 'international_economy',
            'world': 'international_social',
            'politics': 'international_social',
            'uk': 'domestic_social',
            'health': 'domestic_social',
            'education': 'domestic_social'
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
        
        # 緊急性キーワード（+3点）
        urgent_keywords = [
            'breaking', 'urgent', 'emergency', 'crisis', 'death', 'dies', 'killed',
            'attack', 'explosion', 'disaster', 'fire', 'crash', 'accident'
        ]
        if any(keyword in text_to_analyze for keyword in urgent_keywords):
            score += 3
        
        # 重要性キーワード（+2点）
        important_keywords = [
            'government', 'prime minister', 'president', 'minister', 'ceo', 'major',
            'significant', 'announces', 'reveal', 'exclusive', 'investigation'
        ]
        if any(keyword in text_to_analyze for keyword in important_keywords):
            score += 2
        
        # 関心度の高いトピック（+2点）
        high_interest_keywords = [
            'covid', 'coronavirus', 'pandemic', 'brexit', 'election', 'vaccine',
            'climate change', 'global warming', 'ai', 'artificial intelligence'
        ]
        if any(keyword in text_to_analyze for keyword in high_interest_keywords):
            score += 2
        
        # セキュリティ・サイバー関連（+2点）
        security_keywords = ['cyber', 'hack', 'breach', 'malware', 'vulnerability', 'ransomware']
        if any(keyword in text_to_analyze for keyword in security_keywords):
            score += 2
        
        # フィード優先度
        feed_priority = {
            'top_stories': 3,     # トップストーリーは最高優先度
            'world': 2,           # 世界ニュース
            'politics': 2,        # 政治
            'business': 1,        # ビジネス
            'technology': 1,      # テクノロジー
            'science': 1          # 科学
        }
        score += feed_priority.get(feed_name, 0)
        
        # 最大値・最小値制限
        return max(1, min(score, 10))
    
    def _get_target_feeds(self, category: str) -> List[str]:
        """
        カテゴリに基づく対象フィードの取得
        
        Args:
            category: カテゴリ名
            
        Returns:
            フィード名のリスト
        """
        if category == 'all':
            # すべてのフィードを使用（トップストーリーを優先）
            return ['top_stories', 'world', 'business', 'technology', 'politics']
        
        return self.category_mapping.get(category, ['world', 'top_stories'])
    
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
            if len(article.title) < 10 or len(article.title) > 400:
                return False
            
            # 除外キーワードチェック
            excluded_keywords = [
                'advertisement', 'sponsored', '[removed]', 'subscribe', 'newsletter',
                'live updates', 'as it happened', 'watch live', 'live blog'
            ]
            title_lower = article.title.lower()
            
            if any(keyword in title_lower for keyword in excluded_keywords):
                return False
            
            # BBC 固有の除外パターン
            if 'bbc.com/sport' in article.url.lower():
                return False  # スポーツニュースは除外（設定可能）
            
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
            'name': 'BBC News',
            'type': 'RSS Feed',
            'description': 'British Broadcasting Corporation - News and Information',
            'language': 'English',
            'feeds_available': list(self.rss_feeds.keys()),
            'update_frequency': 'リアルタイム更新',
            'reliability': 'Very High',
            'coverage': 'Global + UK Focus',
            'specialties': [
                'Breaking News', 'World News', 'UK News', 'Politics', 
                'Business', 'Technology', 'Science', 'Health'
            ],
            'editorial_standards': 'High - BBC Editorial Guidelines',
            'fact_checking': 'Comprehensive',
            'bias_rating': 'Low - Generally neutral'
        }


# 使用例とテスト関数
async def test_bbc_collector():
    """BBC コレクターのテスト"""
    
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
    
    async with BBCCollector(config, logger) as collector:
        # テクノロジーカテゴリのニュースを5件収集
        print("=== Technology News ===")
        tech_articles = await collector.collect(category='tech', count=5)
        
        print(f"Collected {len(tech_articles)} tech articles:")
        for i, article in enumerate(tech_articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Category: {article.category}")
            print(f"   Importance: {article.importance_score}")
            print(f"   Author: {article.author}")
            print(f"   Published: {article.published_at}")
            print(f"   URL: {article.url}")
            print()
        
        # 国際社会ニュース
        print("=== International Social News ===")
        social_articles = await collector.collect(category='international_social', count=3)
        
        print(f"Collected {len(social_articles)} social articles:")
        for i, article in enumerate(social_articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Category: {article.category}")
            print(f"   Importance: {article.importance_score}")
            print()
        
        # 統計情報
        stats = collector.get_collection_statistics()
        print(f"Collection Statistics:")
        for key, value in stats.items():
            if key != 'errors':  # エラーは長いので省略
                print(f"  {key}: {value}")
        
        # ソース情報
        source_info = collector.get_source_info()
        print(f"\nSource Info: {source_info['name']}")
        print(f"Reliability: {source_info['reliability']}")
        print(f"Coverage: {source_info['coverage']}")


if __name__ == "__main__":
    asyncio.run(test_bbc_collector())