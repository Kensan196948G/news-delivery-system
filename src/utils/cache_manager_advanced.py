"""
Advanced Cache Manager
高度なキャッシュマネージャー - Redis/Memcached統合、LRU、TTL、圧縮対応
"""

import asyncio
import json
import pickle
import gzip
import hashlib
import time
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum
import logging
import threading
from contextlib import asynccontextmanager
import weakref

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Using in-memory cache only.")

try:
    import aiomemcache
    MEMCACHED_AVAILABLE = True
except ImportError:
    MEMCACHED_AVAILABLE = False

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheBackend(Enum):
    """キャッシュバックエンド種別"""
    MEMORY = "memory"
    REDIS = "redis"
    MEMCACHED = "memcached"
    HYBRID = "hybrid"

@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[float] = None
    size: int = 0
    compressed: bool = False
    
    @property
    def is_expired(self) -> bool:
        """有効期限チェック"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """エントリの年齢（秒）"""
        return time.time() - self.created_at

@dataclass
class CacheStats:
    """キャッシュ統計"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    memory_usage: int = 0
    total_entries: int = 0
    hit_rate: float = 0.0
    
    def update_hit_rate(self):
        """ヒット率更新"""
        total = self.hits + self.misses
        self.hit_rate = (self.hits / total) if total > 0 else 0.0

class CacheSerializer:
    """キャッシュシリアライザー"""
    
    @staticmethod
    def serialize(obj: Any, compress: bool = False) -> bytes:
        """オブジェクトシリアライズ"""
        try:
            # JSON可能な場合はJSONを使用（高速）
            data = json.dumps(obj, default=str).encode('utf-8')
            method = b'json'
        except (TypeError, ValueError):
            # Pickle使用（遅いが汎用的）
            data = pickle.dumps(obj)
            method = b'pickle'
        
        if compress and len(data) > 1024:  # 1KB以上で圧縮
            data = gzip.compress(data)
            method += b':gzip'
        
        return method + b':' + data
    
    @staticmethod
    def deserialize(data: bytes) -> Any:
        """オブジェクトデシリアライズ"""
        parts = data.split(b':', 2)
        if len(parts) != 3:
            raise ValueError("Invalid serialized data format")
        
        method_part = parts[1]
        obj_data = parts[2]
        
        # 圧縮解除
        if b'gzip' in method_part:
            obj_data = gzip.decompress(obj_data)
        
        # デシリアライズ
        if b'json' in method_part:
            return json.loads(obj_data.decode('utf-8'))
        elif b'pickle' in method_part:
            return pickle.loads(obj_data)
        else:
            raise ValueError(f"Unknown serialization method: {method_part}")

class BaseCacheBackend(ABC):
    """キャッシュバックエンド基底クラス"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """値取得"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """値設定"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """値削除"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """キー存在チェック"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """全削除"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """統計取得"""
        pass

class MemoryCacheBackend(BaseCacheBackend):
    """インメモリキャッシュバックエンド"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order = []  # LRU用
        self.stats = CacheStats()
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """値取得"""
        async with self.lock:
            if key not in self.cache:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
            
            entry = self.cache[key]
            
            # 有効期限チェック
            if entry.is_expired:
                await self._evict_key(key)
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
            
            # アクセス情報更新
            entry.accessed_at = time.time()
            entry.access_count += 1
            
            # LRU更新
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            self.stats.hits += 1
            self.stats.update_hit_rate()
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """値設定"""
        async with self.lock:
            ttl = ttl or self.default_ttl
            
            # サイズ計算（近似値）
            try:
                size = len(pickle.dumps(value))
            except:
                size = 0
            
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl,
                size=size
            )
            
            # 容量チェック・LRU削除
            await self._ensure_capacity()
            
            self.cache[key] = entry
            if key not in self.access_order:
                self.access_order.append(key)
            
            self.stats.sets += 1
            self.stats.total_entries = len(self.cache)
            self.stats.memory_usage += size
            
            return True
    
    async def delete(self, key: str) -> bool:
        """値削除"""
        async with self.lock:
            return await self._evict_key(key)
    
    async def exists(self, key: str) -> bool:
        """キー存在チェック"""
        async with self.lock:
            if key not in self.cache:
                return False
            return not self.cache[key].is_expired
    
    async def clear(self) -> bool:
        """全削除"""
        async with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.stats.total_entries = 0
            self.stats.memory_usage = 0
            return True
    
    async def _evict_key(self, key: str) -> bool:
        """キー削除"""
        if key in self.cache:
            entry = self.cache[key]
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            self.stats.deletes += 1
            self.stats.total_entries = len(self.cache)
            self.stats.memory_usage -= entry.size
            return True
        return False
    
    async def _ensure_capacity(self):
        """容量確保（LRU削除）"""
        while len(self.cache) >= self.max_size and self.access_order:
            oldest_key = self.access_order[0]
            await self._evict_key(oldest_key)
            self.stats.evictions += 1
    
    async def get_stats(self) -> Dict[str, Any]:
        """統計取得"""
        return {
            "backend": "memory",
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": self.stats.hit_rate,
            "total_entries": self.stats.total_entries,
            "memory_usage": self.stats.memory_usage,
            "evictions": self.stats.evictions
        }

class RedisCacheBackend(BaseCacheBackend):
    """Redisキャッシュバックエンド"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 key_prefix: str = "news_cache:",
                 compress_threshold: int = 1024):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.compress_threshold = compress_threshold
        self.redis_client = None
        self.stats = CacheStats()
        self.serializer = CacheSerializer()
    
    async def connect(self):
        """Redis接続"""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available")
        
        self.redis_client = redis.from_url(self.redis_url)
        await self.redis_client.ping()
        logger.info("Connected to Redis")
    
    async def disconnect(self):
        """Redis切断"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _make_key(self, key: str) -> str:
        """キー生成"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """値取得"""
        if not self.redis_client:
            await self.connect()
        
        redis_key = self._make_key(key)
        
        try:
            data = await self.redis_client.get(redis_key)
            if data is None:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
            
            value = self.serializer.deserialize(data)
            self.stats.hits += 1
            self.stats.update_hit_rate()
            return value
            
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            self.stats.misses += 1
            self.stats.update_hit_rate()
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """値設定"""
        if not self.redis_client:
            await self.connect()
        
        redis_key = self._make_key(key)
        
        try:
            # シリアライズ（必要に応じて圧縮）
            data = self.serializer.serialize(
                value, 
                compress=len(str(value)) > self.compress_threshold
            )
            
            if ttl:
                await self.redis_client.setex(redis_key, int(ttl), data)
            else:
                await self.redis_client.set(redis_key, data)
            
            self.stats.sets += 1
            return True
            
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """値削除"""
        if not self.redis_client:
            await self.connect()
        
        redis_key = self._make_key(key)
        
        try:
            result = await self.redis_client.delete(redis_key)
            if result > 0:
                self.stats.deletes += 1
                return True
            return False
            
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """キー存在チェック"""
        if not self.redis_client:
            await self.connect()
        
        redis_key = self._make_key(key)
        
        try:
            return bool(await self.redis_client.exists(redis_key))
        except Exception as e:
            logger.error(f"Redis exists error: {str(e)}")
            return False
    
    async def clear(self) -> bool:
        """全削除"""
        if not self.redis_client:
            await self.connect()
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis_client.delete(*keys)
            return True
            
        except Exception as e:
            logger.error(f"Redis clear error: {str(e)}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """統計取得"""
        redis_info = {}
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                redis_info = {
                    "redis_memory": info.get("used_memory_human", "N/A"),
                    "redis_keys": info.get("db0", {}).get("keys", 0) if "db0" in info else 0
                }
            except:
                pass
        
        return {
            "backend": "redis",
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": self.stats.hit_rate,
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            **redis_info
        }

class HybridCacheBackend(BaseCacheBackend):
    """ハイブリッドキャッシュバックエンド（L1: Memory, L2: Redis）"""
    
    def __init__(self, 
                 l1_max_size: int = 500,
                 l1_ttl: float = 1800,  # 30分
                 redis_url: str = "redis://localhost:6379",
                 redis_ttl: float = 86400):  # 24時間
        self.l1_cache = MemoryCacheBackend(l1_max_size, l1_ttl)
        self.l2_cache = RedisCacheBackend(redis_url) if REDIS_AVAILABLE else None
        self.redis_ttl = redis_ttl
        self.stats = CacheStats()
    
    async def get(self, key: str) -> Optional[Any]:
        """値取得（L1→L2の順）"""
        # L1キャッシュから取得
        value = await self.l1_cache.get(key)
        if value is not None:
            self.stats.hits += 1
            self.stats.update_hit_rate()
            return value
        
        # L2キャッシュから取得
        if self.l2_cache:
            value = await self.l2_cache.get(key)
            if value is not None:
                # L1にプロモート
                await self.l1_cache.set(key, value)
                self.stats.hits += 1
                self.stats.update_hit_rate()
                return value
        
        self.stats.misses += 1
        self.stats.update_hit_rate()
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """値設定（L1とL2の両方）"""
        l1_result = await self.l1_cache.set(key, value, ttl)
        
        l2_result = True
        if self.l2_cache:
            redis_ttl = ttl or self.redis_ttl
            l2_result = await self.l2_cache.set(key, value, redis_ttl)
        
        if l1_result or l2_result:
            self.stats.sets += 1
        
        return l1_result or l2_result
    
    async def delete(self, key: str) -> bool:
        """値削除（L1とL2の両方）"""
        l1_result = await self.l1_cache.delete(key)
        
        l2_result = True
        if self.l2_cache:
            l2_result = await self.l2_cache.delete(key)
        
        if l1_result or l2_result:
            self.stats.deletes += 1
        
        return l1_result or l2_result
    
    async def exists(self, key: str) -> bool:
        """キー存在チェック"""
        if await self.l1_cache.exists(key):
            return True
        
        if self.l2_cache:
            return await self.l2_cache.exists(key)
        
        return False
    
    async def clear(self) -> bool:
        """全削除"""
        l1_result = await self.l1_cache.clear()
        
        l2_result = True
        if self.l2_cache:
            l2_result = await self.l2_cache.clear()
        
        return l1_result and l2_result
    
    async def get_stats(self) -> Dict[str, Any]:
        """統計取得"""
        l1_stats = await self.l1_cache.get_stats()
        
        combined_stats = {
            "backend": "hybrid",
            "l1_stats": l1_stats,
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": self.stats.hit_rate,
            "sets": self.stats.sets,
            "deletes": self.stats.deletes
        }
        
        if self.l2_cache:
            l2_stats = await self.l2_cache.get_stats()
            combined_stats["l2_stats"] = l2_stats
        
        return combined_stats

class AdvancedCacheManager:
    """高度なキャッシュマネージャー"""
    
    def __init__(self, 
                 backend: CacheBackend = CacheBackend.HYBRID,
                 config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.backend_type = backend
        self.backend = self._create_backend(backend)
        self.namespace_separators = {}
        self.warming_tasks = {}
        
    def _create_backend(self, backend_type: CacheBackend) -> BaseCacheBackend:
        """バックエンド作成"""
        if backend_type == CacheBackend.MEMORY:
            return MemoryCacheBackend(
                max_size=self.config.get('memory_max_size', 1000),
                default_ttl=self.config.get('memory_ttl', 3600)
            )
        elif backend_type == CacheBackend.REDIS and REDIS_AVAILABLE:
            return RedisCacheBackend(
                redis_url=self.config.get('redis_url', 'redis://localhost:6379'),
                key_prefix=self.config.get('redis_prefix', 'news_cache:')
            )
        elif backend_type == CacheBackend.HYBRID:
            return HybridCacheBackend(
                l1_max_size=self.config.get('l1_max_size', 500),
                l1_ttl=self.config.get('l1_ttl', 1800),
                redis_url=self.config.get('redis_url', 'redis://localhost:6379')
            )
        else:
            logger.warning(f"Backend {backend_type} not available, using memory cache")
            return MemoryCacheBackend()
    
    def _make_namespaced_key(self, key: str, namespace: Optional[str] = None) -> str:
        """名前空間付きキー生成"""
        if namespace:
            return f"{namespace}:{key}"
        return key
    
    async def get(self, key: str, namespace: Optional[str] = None) -> Optional[Any]:
        """値取得"""
        namespaced_key = self._make_namespaced_key(key, namespace)
        return await self.backend.get(namespaced_key)
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None, 
                  namespace: Optional[str] = None) -> bool:
        """値設定"""
        namespaced_key = self._make_namespaced_key(key, namespace)
        return await self.backend.set(namespaced_key, value, ttl)
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """値削除"""
        namespaced_key = self._make_namespaced_key(key, namespace)
        return await self.backend.delete(namespaced_key)
    
    async def get_or_set(self, 
                         key: str, 
                         factory: Callable, 
                         ttl: Optional[float] = None,
                         namespace: Optional[str] = None,
                         factory_args: tuple = (),
                         factory_kwargs: dict = None) -> Any:
        """値取得または生成して設定"""
        factory_kwargs = factory_kwargs or {}
        
        # キャッシュから取得試行
        cached_value = await self.get(key, namespace)
        if cached_value is not None:
            return cached_value
        
        # ファクトリで生成
        if asyncio.iscoroutinefunction(factory):
            value = await factory(*factory_args, **factory_kwargs)
        else:
            value = factory(*factory_args, **factory_kwargs)
        
        # キャッシュに設定
        await self.set(key, value, ttl, namespace)
        return value
    
    async def mget(self, keys: List[str], namespace: Optional[str] = None) -> Dict[str, Any]:
        """複数値取得"""
        results = {}
        for key in keys:
            value = await self.get(key, namespace)
            if value is not None:
                results[key] = value
        return results
    
    async def mset(self, items: Dict[str, Any], ttl: Optional[float] = None, 
                   namespace: Optional[str] = None) -> Dict[str, bool]:
        """複数値設定"""
        results = {}
        for key, value in items.items():
            results[key] = await self.set(key, value, ttl, namespace)
        return results
    
    async def cache_warming(self, 
                           keys_factory: Callable[[], List[str]], 
                           value_factory: Callable[[str], Any],
                           namespace: Optional[str] = None,
                           ttl: Optional[float] = None,
                           batch_size: int = 10) -> int:
        """キャッシュ予熱"""
        try:
            keys = await keys_factory() if asyncio.iscoroutinefunction(keys_factory) else keys_factory()
            warmed_count = 0
            
            # バッチ処理で予熱
            for i in range(0, len(keys), batch_size):
                batch_keys = keys[i:i + batch_size]
                tasks = []
                
                for key in batch_keys:
                    # 既にキャッシュされているかチェック
                    if not await self.backend.exists(self._make_namespaced_key(key, namespace)):
                        if asyncio.iscoroutinefunction(value_factory):
                            task = asyncio.create_task(value_factory(key))
                        else:
                            task = asyncio.create_task(asyncio.to_thread(value_factory, key))
                        tasks.append((key, task))
                
                # バッチ実行
                if tasks:
                    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
                    
                    for (key, _), result in zip(tasks, results):
                        if not isinstance(result, Exception):
                            await self.set(key, result, ttl, namespace)
                            warmed_count += 1
                        else:
                            logger.warning(f"Cache warming failed for key {key}: {str(result)}")
            
            logger.info(f"Cache warming completed: {warmed_count}/{len(keys)} keys warmed")
            return warmed_count
            
        except Exception as e:
            logger.error(f"Cache warming error: {str(e)}")
            return 0
    
    async def invalidate_namespace(self, namespace: str) -> bool:
        """名前空間の無効化"""
        # 実装は具体的なバックエンドに依存
        # Redisの場合はパターンマッチング削除
        logger.info(f"Invalidating namespace: {namespace}")
        return True
    
    def cache_decorator(self, 
                       ttl: Optional[float] = None,
                       namespace: Optional[str] = None,
                       key_func: Optional[Callable] = None):
        """キャッシュデコレータ"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # キー生成
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # 引数からハッシュ生成
                    key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                    cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
                return await self.get_or_set(
                    cache_key, func, ttl, namespace, args, kwargs
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(async_wrapper(*args, **kwargs))
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def get_stats(self) -> Dict[str, Any]:
        """統計取得"""
        backend_stats = await self.backend.get_stats()
        return {
            **backend_stats,
            "cache_manager_version": "1.0.0",
            "backend_type": self.backend_type.value,
            "warming_tasks": len(self.warming_tasks)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        start_time = time.time()
        
        try:
            # テストキーでの読み書きチェック
            test_key = f"health_check_{int(time.time())}"
            test_value = {"timestamp": datetime.now().isoformat(), "test": True}
            
            # 書き込みテスト
            write_success = await self.set(test_key, test_value, ttl=60)
            
            # 読み込みテスト
            read_value = await self.get(test_key)
            read_success = read_value is not None
            
            # クリーンアップ
            await self.delete(test_key)
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy" if (write_success and read_success) else "unhealthy",
                "response_time": response_time,
                "write_success": write_success,
                "read_success": read_success,
                "backend": self.backend_type.value,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time": time.time() - start_time,
                "backend": self.backend_type.value,
                "timestamp": datetime.now().isoformat()
            }

# デフォルトキャッシュマネージャーインスタンス
_default_cache_manager = None

def get_cache_manager(backend: CacheBackend = CacheBackend.HYBRID, 
                     config: Optional[Dict[str, Any]] = None) -> AdvancedCacheManager:
    """デフォルトキャッシュマネージャー取得"""
    global _default_cache_manager
    if _default_cache_manager is None:
        _default_cache_manager = AdvancedCacheManager(backend, config)
    return _default_cache_manager

# 便利な関数
async def cached_function(ttl: float = 3600, namespace: str = None):
    """キャッシュ付き関数デコレータ"""
    cache_manager = get_cache_manager()
    return cache_manager.cache_decorator(ttl=ttl, namespace=namespace)