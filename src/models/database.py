"""
Database Module for News Delivery System
ニュース配信システム データベースモジュール
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import hashlib

from utils.config import load_config
from utils.logger import setup_logger


class Database:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.logger = setup_logger(__name__)
        
        # Try multiple database paths
        db_dir = self.config.get_storage_path('database')
        
        # Create database directory if it doesn't exist
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Use news.db as the primary database file
        self.db_path = db_dir / 'news.db'
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """データベースの初期化"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create tables
                self._create_articles_table(cursor)
                self._create_delivery_history_table(cursor)
                self._create_api_usage_table(cursor)
                self._create_cache_table(cursor)
                self._create_security_vulnerabilities_table(cursor)
                self._create_system_metrics_table(cursor)
                
                # Create indexes
                self._create_indexes(cursor)
                
                conn.commit()
                self.logger.info("データベースを正常に初期化しました")
                
        except Exception as e:
            self.logger.error(f"データベース初期化に失敗しました: {e}")
            raise
    
    def _create_articles_table(self, cursor):
        """記事テーブル作成 - CLAUDE.md仕様準拠"""
        cursor.execute('''
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
                keywords TEXT,  -- JSON配列
                sentiment TEXT,
                processed BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_delivery_history_table(self, cursor):
        """配信履歴テーブル作成 - CLAUDE.md仕様準拠"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delivery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_type TEXT NOT NULL,  -- 'scheduled', 'urgent'
                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                article_count INTEGER,
                categories TEXT,  -- JSON
                status TEXT NOT NULL,  -- 'sent', 'failed'
                error_message TEXT,
                html_path TEXT,
                pdf_path TEXT,
                delivered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_api_usage_table(self, cursor):
        """API使用履歴テーブル作成 - CLAUDE.md仕様準拠"""
        cursor.execute('''
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
    
    def _create_cache_table(self, cursor):
        """キャッシュテーブル作成 - CLAUDE.md仕様準拠"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expire_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_security_vulnerabilities_table(self, cursor):
        """セキュリティ脆弱性テーブル作成"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cve_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                cvss_score REAL NOT NULL,
                cvss_vector TEXT,
                severity TEXT NOT NULL,
                affected_products TEXT,  -- JSON array
                published_date TEXT NOT NULL,
                modified_date TEXT,
                reference_urls TEXT,  -- JSON array (renamed from 'references' to avoid SQL keyword conflict)
                cwe_ids TEXT,  -- JSON array
                processed BOOLEAN DEFAULT FALSE,
                notified BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_system_metrics_table(self, cursor):
        """システムメトリクステーブル作成"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                metric_category TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_indexes(self, cursor):
        """インデックス作成 - CLAUDE.md仕様準拠"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_published_at ON articles(published_at)",
            "CREATE INDEX IF NOT EXISTS idx_category ON articles(category)",
            "CREATE INDEX IF NOT EXISTS idx_importance ON articles(importance_score)",
            "CREATE INDEX IF NOT EXISTS idx_url_hash ON articles(url_hash)",
            "CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed)",
            "CREATE INDEX IF NOT EXISTS idx_delivery_history_delivered_at ON delivery_history(delivered_at)",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_api_name ON api_usage(api_name)",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_cache_expire_at ON cache(expire_at)",
            "CREATE INDEX IF NOT EXISTS idx_vulnerabilities_cvss ON security_vulnerabilities(cvss_score)",
            "CREATE INDEX IF NOT EXISTS idx_vulnerabilities_published ON security_vulnerabilities(published_date)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    @contextmanager
    def get_connection(self):
        """データベース接続コンテキストマネージャー"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row  # Dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _generate_article_hash(self, article) -> str:
        """記事のハッシュ値生成（重複チェック用）"""
        # Handle both dict and Article dataclass objects
        if hasattr(article, 'title'):  # Article dataclass
            title = article.title or ''
            url = article.url or ''
            published_at = article.published_at.isoformat() if isinstance(article.published_at, datetime) else str(article.published_at)
        else:  # Dictionary
            title = article.get('title', '')
            url = article.get('url', '')
            published_at = str(article.get('published_at', ''))
        
        content = f"{title}{url}{published_at}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def save_articles(self, articles) -> int:
        """記事をデータベースに保存 - CLAUDE.md仕様準拠"""
        try:
            saved_count = 0
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for article in articles:
                    # Generate hash for deduplication
                    url_hash = self._generate_article_hash(article)
                    
                    # Extract values - CLAUDE.md仕様に準拠した形式
                    if hasattr(article, 'title'):  # Article dataclass
                        title = getattr(article, 'title', '')
                        translated_title = getattr(article, 'translated_title', '')
                        description = getattr(article, 'description', '')
                        content = getattr(article, 'content', '')
                        translated_content = getattr(article, 'translated_content', '')
                        summary = getattr(article, 'summary', '')
                        url = getattr(article, 'url', '')
                        source_name = getattr(article, 'source_name', '')
                        author = getattr(article, 'author', '')
                        category_raw = getattr(article, 'category', '')
                        category = str(category_raw.value) if hasattr(category_raw, 'value') else str(category_raw) if category_raw else ''
                        published_at = article.published_at.isoformat() if isinstance(article.published_at, datetime) else str(article.published_at)
                        collected_at = article.collected_at.isoformat() if hasattr(article, 'collected_at') and isinstance(article.collected_at, datetime) else datetime.now().isoformat()
                        importance_score = getattr(article, 'importance_score', 5)
                        keywords = getattr(article, 'keywords', [])
                        sentiment = getattr(article, 'sentiment', 'neutral')
                    else:  # Dictionary
                        title = article.get('title', '')
                        translated_title = article.get('translated_title', '')
                        description = article.get('description', '')
                        content = article.get('content', '')
                        translated_content = article.get('translated_content', '')
                        summary = article.get('summary', '')
                        url = article.get('url', '')
                        source_name = article.get('source_name', '')
                        author = article.get('author', '')
                        category = article.get('category', '')
                        published_at = str(article.get('published_at', ''))
                        collected_at = article.get('collected_at', datetime.now().isoformat())
                        importance_score = article.get('importance_score', 5)
                        keywords = article.get('keywords', [])
                        sentiment = article.get('sentiment', 'neutral')
                    
                    # Check if article already exists by URL hash
                    cursor.execute("SELECT id FROM articles WHERE url_hash = ?", (url_hash,))
                    if cursor.fetchone():
                        self.logger.debug(f"Article already exists: {title}")
                        continue
                    
                    # Insert new article with CLAUDE.md schema
                    cursor.execute('''
                        INSERT INTO articles (
                            url, url_hash, title, translated_title, description, content,
                            translated_content, summary, source_name, author, published_at,
                            collected_at, category, importance_score, keywords, sentiment, processed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        url, url_hash, title, translated_title, description, content,
                        translated_content, summary, source_name, author, published_at,
                        collected_at, category, importance_score, json.dumps(keywords, ensure_ascii=False),
                        sentiment, False
                    ))
                    saved_count += 1
                
                conn.commit()
                self.logger.info(f"データベースに {saved_count} 件の新しい記事を保存しました")
                return saved_count
                
        except Exception as e:
            self.logger.error(f"記事の保存でエラーが発生しました: {e}")
            raise
    
    def get_articles(self, 
                    category: Optional[str] = None,
                    days_back: int = 7,
                    min_importance: int = 0,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """記事を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM articles 
                    WHERE published_at >= ? AND importance_score >= ?
                """
                params = [
                    (datetime.now() - timedelta(days=days_back)).isoformat(),
                    min_importance
                ]
                
                if category:
                    query += " AND category = ?"
                    params.append(category)
                
                query += " ORDER BY published_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                articles = []
                for row in rows:
                    article = dict(row)
                    # Parse JSON fields
                    if article['keywords']:
                        article['keywords'] = json.loads(article['keywords'])
                    articles.append(article)
                
                return articles
                
        except Exception as e:
            self.logger.error(f"Error retrieving articles: {e}")
            return []
    
    def log_delivery(self, 
                    delivery_type: str,
                    recipient_email: str,
                    subject: str,
                    article_count: int,
                    categories: list = None,
                    status: str = 'sent',
                    error_message: str = None,
                    html_path: str = None,
                    pdf_path: str = None):
        """配信履歴をログ - CLAUDE.md仕様準拠"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO delivery_history (
                        delivery_type, recipient_email, subject, article_count,
                        categories, status, error_message, html_path, pdf_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    delivery_type,
                    recipient_email,
                    subject,
                    article_count,
                    json.dumps(categories or [], ensure_ascii=False),
                    status,
                    error_message,
                    html_path,
                    pdf_path
                ))
                
                conn.commit()
                self.logger.info(f"Logged delivery: {delivery_type} to {recipient_email}")
                
        except Exception as e:
            self.logger.error(f"Error logging delivery: {e}")
    
    def log_api_usage(self, 
                     api_name: str,
                     endpoint: str = None,
                     request_count: int = 1,
                     response_status: int = None,
                     error_message: str = None):
        """API使用状況をログ - CLAUDE.md仕様準拠"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO api_usage (
                        api_name, endpoint, request_count, response_status, error_message
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    api_name,
                    endpoint,
                    request_count,
                    response_status,
                    error_message
                ))
                
                conn.commit()
                self.logger.debug(f"Logged API usage: {api_name} - {endpoint}")
                
        except Exception as e:
            self.logger.error(f"Error logging API usage: {e}")
    
    def save_vulnerabilities(self, vulnerabilities: List[Dict[str, Any]]) -> int:
        """脆弱性情報を保存"""
        try:
            saved_count = 0
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for vuln in vulnerabilities:
                    # Check if vulnerability already exists
                    cursor.execute("SELECT id FROM security_vulnerabilities WHERE cve_id = ?", 
                                 (vuln.get('cve_id', ''),))
                    if cursor.fetchone():
                        continue
                    
                    cursor.execute('''
                        INSERT INTO security_vulnerabilities (
                            cve_id, title, description, cvss_score, cvss_vector,
                            severity, affected_products, published_date, modified_date,
                            reference_urls, cwe_ids
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        vuln.get('cve_id', ''),
                        vuln.get('title', ''),
                        vuln.get('description', ''),
                        vuln.get('cvss_score', 0.0),
                        vuln.get('cvss_vector', ''),
                        vuln.get('severity', ''),
                        json.dumps(vuln.get('affected_products', [])),
                        vuln.get('published_date', ''),
                        vuln.get('modified_date', ''),
                        json.dumps(vuln.get('references', [])),
                        json.dumps(vuln.get('cwe_ids', []))
                    ))
                    saved_count += 1
                
                conn.commit()
                self.logger.info(f"Saved {saved_count} new vulnerabilities")
                return saved_count
                
        except Exception as e:
            self.logger.error(f"Error saving vulnerabilities: {e}")
            return 0
    
    def cleanup_old_data(self):
        """古いデータのクリーンアップ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Cleanup old articles
                article_cutoff = (datetime.now() - timedelta(
                    days=self.config.get('data_retention', 'articles_days', default=30)
                )).isoformat()
                
                cursor.execute("DELETE FROM articles WHERE published_at < ?", (article_cutoff,))
                articles_deleted = cursor.rowcount
                
                # Cleanup old delivery history
                delivery_cutoff = (datetime.now() - timedelta(
                    days=self.config.get('data_retention', 'delivery_history_days', default=90)
                )).isoformat()
                
                cursor.execute("DELETE FROM delivery_history WHERE delivered_at < ?", (delivery_cutoff,))
                deliveries_deleted = cursor.rowcount
                
                # Cleanup old API usage logs
                api_cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute("DELETE FROM api_usage WHERE called_at < ?", (api_cutoff,))
                api_logs_deleted = cursor.rowcount
                
                conn.commit()
                
                self.logger.info(f"Cleanup completed: {articles_deleted} articles, "
                               f"{deliveries_deleted} delivery records, "
                               f"{api_logs_deleted} API logs deleted")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """システム統計を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Article statistics
                cursor.execute("SELECT COUNT(*) FROM articles")
                stats['total_articles'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM articles WHERE is_emergency = 1")
                stats['emergency_articles'] = cursor.fetchone()[0]
                
                # Recent delivery statistics
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*), AVG(processing_time_seconds), SUM(article_count)
                    FROM delivery_history WHERE delivered_at >= ?
                """, (week_ago,))
                
                delivery_stats = cursor.fetchone()
                stats['deliveries_last_week'] = delivery_stats[0] or 0
                stats['avg_processing_time'] = delivery_stats[1] or 0.0
                stats['total_articles_delivered'] = delivery_stats[2] or 0
                
                # API usage statistics
                cursor.execute("""
                    SELECT service_name, COUNT(*), AVG(response_time_ms)
                    FROM api_usage WHERE called_at >= ?
                    GROUP BY service_name
                """, (week_ago,))
                
                api_stats = cursor.fetchall()
                stats['api_usage'] = {}
                for service, count, avg_time in api_stats:
                    stats['api_usage'][service] = {
                        'calls': count,
                        'avg_response_time_ms': avg_time or 0.0
                    }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {}