"""
Database ORM Module for News Delivery System
ニュース配信システム データベースORM - 高度なデータアクセス層実装
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import asynccontextmanager
import aiosqlite
import hashlib
from dataclasses import dataclass, asdict

from utils.config import load_config
from utils.logger import setup_logger


@dataclass
class Article:
    """記事データクラス - CLAUDE.md仕様準拠"""
    url: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    translated_title: Optional[str] = None
    translated_content: Optional[str] = None
    summary: Optional[str] = None
    source_name: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    category: Optional[str] = None
    importance_score: int = 5
    keywords: List[str] = None
    sentiment: str = 'neutral'
    processed: bool = False
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.collected_at is None:
            self.collected_at = datetime.now()


@dataclass
class DeliveryHistory:
    """配信履歴データクラス"""
    delivery_type: str
    recipient_email: str
    subject: str
    article_count: int
    categories: List[str] = None
    status: str = 'sent'
    error_message: Optional[str] = None
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None
    delivered_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.delivered_at is None:
            self.delivered_at = datetime.now()


@dataclass
class ApiUsage:
    """API使用履歴データクラス"""
    api_name: str
    endpoint: Optional[str] = None
    request_count: int = 1
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class AsyncDatabase:
    """非同期SQLiteデータベース管理クラス - 高パフォーマンス実装"""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.logger = setup_logger(__name__)
        self.db_path = self.config.get_storage_path('database') / 'news_system.db'
        
        # バッチ処理設定
        self.batch_size = 100
        self.connection_timeout = 30.0
        
    async def initialize(self):
        """データベースの非同期初期化"""
        try:
            async with self.get_connection() as conn:
                await self._create_tables(conn)
                await self._create_indexes(conn)
                await conn.commit()
                self.logger.info("Async database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Async database initialization failed: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """非同期データベース接続コンテキストマネージャー"""
        conn = None
        try:
            conn = await aiosqlite.connect(str(self.db_path), timeout=self.connection_timeout)
            conn.row_factory = aiosqlite.Row
            # パフォーマンス最適化
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            await conn.execute("PRAGMA temp_store=memory")
            yield conn
        except Exception as e:
            if conn:
                await conn.rollback()
            self.logger.error(f"Async database connection error: {e}")
            raise
        finally:
            if conn:
                await conn.close()
    
    async def _create_tables(self, conn):
        """テーブル作成 - CLAUDE.md仕様準拠"""
        
        # 記事テーブル
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                url_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                translated_title TEXT,
                description TEXT,
                content TEXT,
                translated_content TEXT,
                summary TEXT,
                source_name TEXT,
                author TEXT,
                published_at DATETIME,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                category TEXT,
                importance_score INTEGER DEFAULT 5,
                keywords TEXT,
                sentiment TEXT DEFAULT 'neutral',
                processed BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 配信履歴テーブル
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS delivery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_type TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                article_count INTEGER,
                categories TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                html_path TEXT,
                pdf_path TEXT,
                delivered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # API使用履歴テーブル
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                endpoint TEXT,
                request_count INTEGER DEFAULT 1,
                response_status INTEGER,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # キャッシュテーブル
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expire_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    async def _create_indexes(self, conn):
        """インデックス作成 - パフォーマンス最適化"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at)",
            "CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)", 
            "CREATE INDEX IF NOT EXISTS idx_articles_importance ON articles(importance_score)",
            "CREATE INDEX IF NOT EXISTS idx_articles_url_hash ON articles(url_hash)",
            "CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed)",
            "CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment)",
            "CREATE INDEX IF NOT EXISTS idx_delivery_history_delivered_at ON delivery_history(delivered_at)",
            "CREATE INDEX IF NOT EXISTS idx_delivery_history_status ON delivery_history(status)",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_api_name ON api_usage(api_name)",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_cache_expire_at ON cache(expire_at)"
        ]
        
        for index_sql in indexes:
            await conn.execute(index_sql)
    
    def _generate_url_hash(self, url: str) -> str:
        """URL ハッシュ生成（重複チェック用）"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    async def save_article(self, article: Article) -> bool:
        """単一記事の保存"""
        try:
            async with self.get_connection() as conn:
                url_hash = self._generate_url_hash(article.url)
                
                # 重複チェック
                async with conn.execute("SELECT id FROM articles WHERE url_hash = ?", (url_hash,)) as cursor:
                    if await cursor.fetchone():
                        self.logger.debug(f"Article already exists: {article.title}")
                        return False
                
                # 記事挿入
                await conn.execute('''
                    INSERT INTO articles (
                        url, url_hash, title, translated_title, description, content,
                        translated_content, summary, source_name, author, published_at,
                        collected_at, category, importance_score, keywords, sentiment, processed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.url, url_hash, article.title, article.translated_title,
                    article.description, article.content, article.translated_content,
                    article.summary, article.source_name, article.author,
                    article.published_at.isoformat() if article.published_at else None,
                    article.collected_at.isoformat() if article.collected_at else datetime.now().isoformat(),
                    article.category, article.importance_score,
                    json.dumps(article.keywords, ensure_ascii=False),
                    article.sentiment, article.processed
                ))
                
                await conn.commit()
                self.logger.debug(f"Saved article: {article.title}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving article: {e}")
            return False
    
    async def save_articles_batch(self, articles: List[Article]) -> int:
        """記事のバッチ保存 - 高パフォーマンス"""
        saved_count = 0
        
        try:
            async with self.get_connection() as conn:
                # バッチサイズごとに分割処理
                for i in range(0, len(articles), self.batch_size):
                    batch = articles[i:i + self.batch_size]
                    
                    # 重複チェック用ハッシュ生成
                    url_hashes = [self._generate_url_hash(article.url) for article in batch]
                    
                    # 既存記事チェック
                    placeholders = ','.join(['?' for _ in url_hashes])
                    existing_query = f"SELECT url_hash FROM articles WHERE url_hash IN ({placeholders})"
                    
                    async with conn.execute(existing_query, url_hashes) as cursor:
                        existing_hashes = {row[0] for row in await cursor.fetchall()}
                    
                    # 新規記事のみ挿入
                    new_articles = [
                        article for article in batch 
                        if self._generate_url_hash(article.url) not in existing_hashes
                    ]
                    
                    if new_articles:
                        # バッチ挿入用データ準備
                        insert_data = []
                        for article in new_articles:
                            url_hash = self._generate_url_hash(article.url)
                            insert_data.append((
                                article.url, url_hash, article.title, article.translated_title,
                                article.description, article.content, article.translated_content,
                                article.summary, article.source_name, article.author,
                                article.published_at.isoformat() if article.published_at else None,
                                article.collected_at.isoformat() if article.collected_at else datetime.now().isoformat(),
                                article.category, article.importance_score,
                                json.dumps(article.keywords, ensure_ascii=False),
                                article.sentiment, article.processed
                            ))
                        
                        # バッチ挿入実行
                        await conn.executemany('''
                            INSERT INTO articles (
                                url, url_hash, title, translated_title, description, content,
                                translated_content, summary, source_name, author, published_at,
                                collected_at, category, importance_score, keywords, sentiment, processed
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', insert_data)
                        
                        saved_count += len(new_articles)
                
                await conn.commit()
                self.logger.info(f"Batch saved {saved_count} new articles")
                return saved_count
                
        except Exception as e:
            self.logger.error(f"Error in batch save: {e}")
            return saved_count
    
    async def get_articles(self, 
                          category: Optional[str] = None,
                          days_back: int = 7,
                          min_importance: int = 0,
                          limit: int = 100,
                          processed_only: bool = False) -> List[Dict[str, Any]]:
        """記事取得 - 柔軟な検索条件"""
        try:
            async with self.get_connection() as conn:
                query = "SELECT * FROM articles WHERE published_at >= ? AND importance_score >= ?"
                params = [
                    (datetime.now() - timedelta(days=days_back)).isoformat(),
                    min_importance
                ]
                
                if category:
                    query += " AND category = ?"
                    params.append(category)
                
                if processed_only:
                    query += " AND processed = 1"
                
                query += " ORDER BY importance_score DESC, published_at DESC LIMIT ?"
                params.append(limit)
                
                async with conn.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                
                articles = []
                for row in rows:
                    article = dict(row)
                    # JSON フィールドのパース
                    if article['keywords']:
                        article['keywords'] = json.loads(article['keywords'])
                    articles.append(article)
                
                return articles
                
        except Exception as e:
            self.logger.error(f"Error retrieving articles: {e}")
            return []
    
    async def get_urgent_articles(self, cvss_threshold: float = 9.0, 
                                 importance_threshold: int = 10) -> List[Dict[str, Any]]:
        """緊急記事の取得"""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT * FROM articles 
                    WHERE importance_score >= ? 
                    ORDER BY importance_score DESC, published_at DESC
                """
                
                async with conn.execute(query, (importance_threshold,)) as cursor:
                    rows = await cursor.fetchall()
                
                articles = []
                for row in rows:
                    article = dict(row)
                    if article['keywords']:
                        article['keywords'] = json.loads(article['keywords'])
                    articles.append(article)
                
                return articles
                
        except Exception as e:
            self.logger.error(f"Error retrieving urgent articles: {e}")
            return []
    
    async def update_article_processed(self, article_id: int, processed: bool = True) -> bool:
        """記事の処理状態更新"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "UPDATE articles SET processed = ? WHERE id = ?",
                    (processed, article_id)
                )
                await conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating article processed status: {e}")
            return False
    
    async def log_delivery(self, delivery: DeliveryHistory) -> bool:
        """配信履歴の記録"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO delivery_history (
                        delivery_type, recipient_email, subject, article_count,
                        categories, status, error_message, html_path, pdf_path, delivered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    delivery.delivery_type, delivery.recipient_email, delivery.subject,
                    delivery.article_count, json.dumps(delivery.categories, ensure_ascii=False),
                    delivery.status, delivery.error_message, delivery.html_path,
                    delivery.pdf_path, delivery.delivered_at.isoformat()
                ))
                
                await conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error logging delivery: {e}")
            return False
    
    async def log_api_usage(self, usage: ApiUsage) -> bool:
        """API使用履歴の記録"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO api_usage (
                        api_name, endpoint, request_count, response_status, 
                        error_message, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    usage.api_name, usage.endpoint, usage.request_count,
                    usage.response_status, usage.error_message,
                    usage.created_at.isoformat()
                ))
                
                await conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error logging API usage: {e}")
            return False
    
    async def get_delivery_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """配信統計の取得"""
        try:
            async with self.get_connection() as conn:
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                
                # 配信成功率
                async with conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as success,
                        SUM(article_count) as total_articles
                    FROM delivery_history 
                    WHERE delivered_at >= ?
                ''', (cutoff_date,)) as cursor:
                    stats = await cursor.fetchone()
                
                # 配信タイプ別統計
                async with conn.execute('''
                    SELECT delivery_type, COUNT(*), AVG(article_count)
                    FROM delivery_history 
                    WHERE delivered_at >= ?
                    GROUP BY delivery_type
                ''', (cutoff_date,)) as cursor:
                    type_stats = await cursor.fetchall()
                
                return {
                    'total_deliveries': stats[0] or 0,
                    'successful_deliveries': stats[1] or 0,
                    'success_rate': (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
                    'total_articles_delivered': stats[2] or 0,
                    'delivery_types': {
                        row[0]: {'count': row[1], 'avg_articles': row[2]}
                        for row in type_stats
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting delivery statistics: {e}")
            return {}
    
    async def get_api_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """API使用統計の取得"""
        try:
            async with self.get_connection() as conn:
                cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
                
                async with conn.execute('''
                    SELECT 
                        api_name,
                        COUNT(*) as total_requests,
                        SUM(request_count) as total_count,
                        AVG(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1.0 ELSE 0.0 END) as success_rate
                    FROM api_usage 
                    WHERE created_at >= ?
                    GROUP BY api_name
                ''', (cutoff_date,)) as cursor:
                    stats = await cursor.fetchall()
                
                return {
                    row[0]: {
                        'total_requests': row[1],
                        'total_count': row[2],
                        'success_rate': (row[3] * 100) if row[3] else 0
                    }
                    for row in stats
                }
                
        except Exception as e:
            self.logger.error(f"Error getting API statistics: {e}")
            return {}
    
    async def cleanup_old_data(self, 
                              articles_days: int = 30,
                              delivery_days: int = 90,
                              api_usage_days: int = 30) -> Dict[str, int]:
        """古いデータのクリーンアップ"""
        try:
            async with self.get_connection() as conn:
                cleanup_counts = {}
                
                # 古い記事削除
                article_cutoff = (datetime.now() - timedelta(days=articles_days)).isoformat()
                result = await conn.execute("DELETE FROM articles WHERE published_at < ?", (article_cutoff,))
                cleanup_counts['articles'] = result.rowcount
                
                # 古い配信履歴削除
                delivery_cutoff = (datetime.now() - timedelta(days=delivery_days)).isoformat()
                result = await conn.execute("DELETE FROM delivery_history WHERE delivered_at < ?", (delivery_cutoff,))
                cleanup_counts['delivery_history'] = result.rowcount
                
                # 古いAPI使用履歴削除
                api_cutoff = (datetime.now() - timedelta(days=api_usage_days)).isoformat()
                result = await conn.execute("DELETE FROM api_usage WHERE created_at < ?", (api_cutoff,))
                cleanup_counts['api_usage'] = result.rowcount
                
                await conn.commit()
                
                self.logger.info(f"Cleanup completed: {cleanup_counts}")
                return cleanup_counts
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return {}
    
    async def optimize_database(self):
        """データベース最適化（VACUUM、ANALYZE）"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("VACUUM")
                await conn.execute("ANALYZE")
                self.logger.info("Database optimization completed")
                
        except Exception as e:
            self.logger.error(f"Error during database optimization: {e}")


# グローバル非同期データベースインスタンス
_async_db_instance = None


async def get_async_database() -> AsyncDatabase:
    """グローバル非同期データベースインスタンス取得"""
    global _async_db_instance
    if _async_db_instance is None:
        _async_db_instance = AsyncDatabase()
        await _async_db_instance.initialize()
    return _async_db_instance