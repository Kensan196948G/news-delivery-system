"""
Cache Manager for News Delivery System
キャッシュマネージャー - API結果や処理結果のキャッシュ管理
"""

import json
import sqlite3
import hashlib
import pickle
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, Union
from contextlib import contextmanager

from .config import get_config


logger = logging.getLogger(__name__)


class CacheManager:
    """キャッシュマネージャー - メモリとSQLiteによるキャッシュシステム"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache_dir = self.config.get_storage_path('cache')
        self.db_path = self.cache_dir / 'cache.db'
        
        # メモリキャッシュ（セッション中のみ）
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # キャッシュ設定 - CLAUDE.md仕様準拠
        self.default_ttl = {
            'api_cache': 3600,      # 1時間
            'article_cache': 86400,  # 24時間
            'analysis_cache': 604800, # 7日間（CLAUDE.md仕様）
            'translation_cache': 604800, # 7日間（CLAUDE.md仕様）
            'dedup_cache': 86400 * 30, # 30日間
            'processing_cache': 86400 * 3, # 3日間（処理結果）
            'urgent_cache': 3600 * 12, # 12時間（緊急記事）
        }
        
        self._init_database()
    
    def _init_database(self):
        """キャッシュデータベースの初期化"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # キャッシュテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value_type TEXT NOT NULL,
                        value_data BLOB NOT NULL,
                        category TEXT NOT NULL,
                        expire_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1
                    )
                ''')
                
                # インデックス作成
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expire ON cache(expire_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_category ON cache(category)')
                
                conn.commit()
                logger.debug("Cache database initialized")
                
        except Exception as e:
            logger.error(f"Cache database initialization failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """データベース接続コンテキストマネージャー"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Cache database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _generate_key(self, key: str, category: str = 'default') -> str:
        """キー生成（カテゴリ付き）"""
        full_key = f"{category}:{key}"
        return hashlib.md5(full_key.encode('utf-8')).hexdigest()
    
    def _serialize_value(self, value: Any) -> tuple:
        """値のシリアライズ"""
        try:
            if isinstance(value, (str, int, float, bool, type(None))):
                return 'json', json.dumps(value).encode('utf-8')
            elif isinstance(value, (dict, list)):
                return 'json', json.dumps(value, ensure_ascii=False).encode('utf-8')
            else:
                return 'pickle', pickle.dumps(value)
        except Exception as e:
            logger.error(f"Failed to serialize value: {e}")
            raise
    
    def _deserialize_value(self, value_type: str, value_data: bytes) -> Any:
        """値のデシリアライズ"""
        try:
            if value_type == 'json':
                return json.loads(value_data.decode('utf-8'))
            elif value_type == 'pickle':
                return pickle.loads(value_data)
            else:
                raise ValueError(f"Unknown value type: {value_type}")
        except Exception as e:
            logger.error(f"Failed to deserialize value: {e}")
            raise
    
    def set(self, key: str, value: Any, expire: Optional[int] = None, 
            category: str = 'default') -> bool:
        """キャッシュに値を設定"""
        try:
            cache_key = self._generate_key(key, category)
            
            # TTL設定
            if expire is None:
                expire = self.default_ttl.get(f"{category}_cache", 3600)
            
            expire_at = datetime.now() + timedelta(seconds=expire)
            
            # メモリキャッシュに保存
            self._memory_cache[cache_key] = {
                'value': value,
                'expire_at': expire_at,
                'category': category
            }
            
            # データベースに保存
            value_type, value_data = self._serialize_value(value)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cache 
                    (key, value_type, value_data, category, expire_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (cache_key, value_type, value_data, category, expire_at))
                conn.commit()
            
            logger.debug(f"Cached key: {key} (category: {category}, expire: {expire}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache for key '{key}': {e}")
            return False
    
    def get(self, key: str, category: str = 'default') -> Optional[Any]:
        """キャッシュから値を取得"""
        try:
            cache_key = self._generate_key(key, category)
            
            # メモリキャッシュを先にチェック
            if cache_key in self._memory_cache:
                cached = self._memory_cache[cache_key]
                if datetime.now() < cached['expire_at']:
                    logger.debug(f"Cache hit (memory): {key}")
                    return cached['value']
                else:
                    # 期限切れ
                    del self._memory_cache[cache_key]
            
            # データベースキャッシュをチェック
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT value_type, value_data, expire_at 
                    FROM cache 
                    WHERE key = ? AND expire_at > ?
                ''', (cache_key, datetime.now()))
                
                result = cursor.fetchone()
                
                if result:
                    # アクセス回数更新
                    cursor.execute('''
                        UPDATE cache 
                        SET last_accessed = ?, access_count = access_count + 1
                        WHERE key = ?
                    ''', (datetime.now(), cache_key))
                    conn.commit()
                    
                    # 値をデシリアライズ
                    value = self._deserialize_value(result['value_type'], result['value_data'])
                    
                    # メモリキャッシュにも保存
                    self._memory_cache[cache_key] = {
                        'value': value,
                        'expire_at': datetime.fromisoformat(result['expire_at']),
                        'category': category
                    }
                    
                    logger.debug(f"Cache hit (database): {key}")
                    return value
            
            logger.debug(f"Cache miss: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cache for key '{key}': {e}")
            return None
    
    def delete(self, key: str, category: str = 'default') -> bool:
        """キャッシュから値を削除"""
        try:
            cache_key = self._generate_key(key, category)
            
            # メモリキャッシュから削除
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            
            # データベースから削除
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache WHERE key = ?', (cache_key,))
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to delete cache for key '{key}': {e}")
            return False
    
    def clear_category(self, category: str) -> int:
        """特定カテゴリのキャッシュをクリア"""
        try:
            # メモリキャッシュから削除
            memory_keys_to_delete = [
                k for k, v in self._memory_cache.items() 
                if v['category'] == category
            ]
            for key in memory_keys_to_delete:
                del self._memory_cache[key]
            
            # データベースから削除
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache WHERE category = ?', (category,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleared {deleted_count} cache entries for category: {category}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to clear cache for category '{category}': {e}")
            return 0
    
    def cleanup_expired(self) -> int:
        """期限切れキャッシュのクリーンアップ"""
        try:
            now = datetime.now()
            
            # メモリキャッシュクリーンアップ
            memory_keys_to_delete = [
                k for k, v in self._memory_cache.items() 
                if now >= v['expire_at']
            ]
            for key in memory_keys_to_delete:
                del self._memory_cache[key]
            
            # データベースクリーンアップ
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache WHERE expire_at <= ?', (now,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} expired cache entries")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 総キャッシュ数
                cursor.execute('SELECT COUNT(*) FROM cache')
                total_count = cursor.fetchone()[0]
                
                # カテゴリ別統計
                cursor.execute('''
                    SELECT category, COUNT(*), AVG(access_count)
                    FROM cache 
                    GROUP BY category
                ''')
                category_stats = {
                    row[0]: {'count': row[1], 'avg_access': row[2]}
                    for row in cursor.fetchall()
                }
                
                # 期限切れ数
                cursor.execute('SELECT COUNT(*) FROM cache WHERE expire_at <= ?', (datetime.now(),))
                expired_count = cursor.fetchone()[0]
                
                return {
                    'total_entries': total_count,
                    'memory_entries': len(self._memory_cache),
                    'expired_entries': expired_count,
                    'categories': category_stats,
                    'database_path': str(self.db_path),
                    'database_size_mb': self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def exists(self, key: str, category: str = 'default') -> bool:
        """キャッシュキーの存在確認"""
        return self.get(key, category) is not None
    
    def set_api_cache(self, endpoint: str, params: Dict, response: Any, expire: int = 3600):
        """API レスポンスキャッシュ"""
        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return self.set(cache_key, response, expire, 'api')
    
    def get_api_cache(self, endpoint: str, params: Dict) -> Optional[Any]:
        """API レスポンスキャッシュ取得"""
        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return self.get(cache_key, 'api')
    
    def set_translation_cache(self, text: str, translated: str, source_lang: str = 'en', 
                            target_lang: str = 'ja'):
        """翻訳結果キャッシュ"""
        cache_key = f"{source_lang}:{target_lang}:{hashlib.md5(text.encode()).hexdigest()}"
        return self.set(cache_key, translated, expire=self.default_ttl['translation_cache'], 
                       category='translation')
    
    def get_translation_cache(self, text: str, source_lang: str = 'en', 
                            target_lang: str = 'ja') -> Optional[str]:
        """翻訳結果キャッシュ取得"""
        cache_key = f"{source_lang}:{target_lang}:{hashlib.md5(text.encode()).hexdigest()}"
        return self.get(cache_key, 'translation')
    
    def set_analysis_cache(self, content: str, analysis: Dict):
        """AI分析結果キャッシュ"""
        cache_key = hashlib.md5(content.encode()).hexdigest()
        return self.set(cache_key, analysis, expire=self.default_ttl['analysis_cache'], 
                       category='analysis')
    
    def get_analysis_cache(self, content: str) -> Optional[Dict]:
        """AI分析結果キャッシュ取得"""
        cache_key = hashlib.md5(content.encode()).hexdigest()
        return self.get(cache_key, 'analysis')


# グローバルキャッシュインスタンス
_cache_instance = None


def get_cache_manager() -> CacheManager:
    """グローバルキャッシュマネージャー取得"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance