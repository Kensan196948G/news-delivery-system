"""
Performance Optimizer Module
包括的なパフォーマンス最適化ユーティリティ
"""

import asyncio
import time
import psutil
import gc
import weakref
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps, lru_cache
import logging
from datetime import datetime, timedelta
import threading
import queue
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""
    execution_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    parallel_tasks: int = 0
    error_count: int = 0
    throughput: float = 0.0
    latency_p95: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

class AsyncTaskPool:
    """非同期タスクプール管理"""
    
    def __init__(self, max_concurrent: int = 10, max_queue_size: int = 1000):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.task_queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_tasks = []
        
    async def start_workers(self, num_workers: int = None):
        """ワーカータスクの開始"""
        if num_workers is None:
            num_workers = min(self.max_concurrent, asyncio.cpu_count() * 2)
            
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(worker)
            
    async def _worker(self, worker_name: str):
        """ワーカータスク"""
        while True:
            try:
                task_func, args, kwargs, future = await self.task_queue.get()
                
                async with self.semaphore:
                    try:
                        result = await task_func(*args, **kwargs)
                        future.set_result(result)
                        self.completed_tasks += 1
                    except Exception as e:
                        future.set_exception(e)
                        self.failed_tasks += 1
                        logger.error(f"Task failed in {worker_name}: {str(e)}")
                    finally:
                        self.task_queue.task_done()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {str(e)}")
                
    async def submit(self, coro_func: Callable, *args, **kwargs):
        """タスクの投入"""
        future = asyncio.Future()
        await self.task_queue.put((coro_func, args, kwargs, future))
        return await future
        
    async def shutdown(self):
        """プールの終了"""
        await self.task_queue.join()
        for worker in self._worker_tasks:
            worker.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)

class MemoryOptimizer:
    """メモリ使用量最適化"""
    
    def __init__(self, max_memory_mb: int = 2048):
        self.max_memory_mb = max_memory_mb
        self.object_pool = {}
        self.weak_refs = weakref.WeakValueDictionary()
        
    @staticmethod
    def memory_usage() -> float:
        """現在のメモリ使用量（MB）"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    @staticmethod
    def force_gc():
        """強制ガベージコレクション"""
        collected = gc.collect()
        logger.debug(f"Garbage collected: {collected} objects")
        return collected
        
    def check_memory_threshold(self) -> bool:
        """メモリ閾値チェック"""
        current_memory = self.memory_usage()
        if current_memory > self.max_memory_mb * 0.8:
            logger.warning(f"Memory usage high: {current_memory:.1f}MB")
            self.force_gc()
            return True
        return False
        
    @asynccontextmanager
    async def memory_managed(self, object_name: str = None):
        """メモリ管理コンテキスト"""
        initial_memory = self.memory_usage()
        try:
            yield
        finally:
            final_memory = self.memory_usage()
            memory_diff = final_memory - initial_memory
            if memory_diff > 100:  # 100MB以上増加時
                logger.warning(f"Memory increased by {memory_diff:.1f}MB in {object_name}")
                self.force_gc()

class BatchProcessor:
    """バッチ処理最適化"""
    
    def __init__(self, batch_size: int = 50, max_wait_time: float = 5.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_items = []
        self.batch_processors = {}
        
    async def add_to_batch(self, item: Any, processor_name: str = "default"):
        """バッチにアイテム追加"""
        if processor_name not in self.batch_processors:
            self.batch_processors[processor_name] = {
                'items': [],
                'last_process_time': time.time()
            }
            
        processor = self.batch_processors[processor_name]
        processor['items'].append(item)
        
        # バッチサイズまたは待機時間の条件をチェック
        should_process = (
            len(processor['items']) >= self.batch_size or
            time.time() - processor['last_process_time'] > self.max_wait_time
        )
        
        if should_process:
            items_to_process = processor['items'].copy()
            processor['items'].clear()
            processor['last_process_time'] = time.time()
            return items_to_process
        
        return None

class CacheOptimizer:
    """キャッシュ最適化"""
    
    def __init__(self):
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
    @staticmethod
    def smart_cache(maxsize: int = 128, ttl: float = 3600):
        """TTL付きLRUキャッシュデコレータ"""
        def decorator(func):
            cache = {}
            timestamps = {}
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                key = str(args) + str(sorted(kwargs.items()))
                now = time.time()
                
                # TTL期限切れチェック
                if key in timestamps and now - timestamps[key] > ttl:
                    cache.pop(key, None)
                    timestamps.pop(key, None)
                
                if key in cache:
                    return cache[key]
                
                # LRUロジック（最大サイズ超過時）
                if len(cache) >= maxsize:
                    oldest_key = min(timestamps.keys(), key=timestamps.get)
                    cache.pop(oldest_key, None)
                    timestamps.pop(oldest_key, None)
                
                result = func(*args, **kwargs)
                cache[key] = result
                timestamps[key] = now
                
                return result
            return wrapper
        return decorator

class PerformanceProfiler:
    """パフォーマンスプロファイラ"""
    
    def __init__(self):
        self.profiles = {}
        self.active_profiles = {}
        
    @asynccontextmanager
    async def profile(self, operation_name: str):
        """プロファイルコンテキスト"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            profile_data = {
                'execution_time': end_time - start_time,
                'memory_delta': (end_memory - start_memory) / 1024 / 1024,
                'timestamp': datetime.now()
            }
            
            if operation_name not in self.profiles:
                self.profiles[operation_name] = []
            self.profiles[operation_name].append(profile_data)
            
    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリ取得"""
        summary = {}
        
        for operation, profiles in self.profiles.items():
            if profiles:
                execution_times = [p['execution_time'] for p in profiles]
                memory_deltas = [p['memory_delta'] for p in profiles]
                
                summary[operation] = {
                    'avg_execution_time': sum(execution_times) / len(execution_times),
                    'max_execution_time': max(execution_times),
                    'min_execution_time': min(execution_times),
                    'avg_memory_delta': sum(memory_deltas) / len(memory_deltas),
                    'max_memory_delta': max(memory_deltas),
                    'total_calls': len(profiles)
                }
        
        return summary

class OptimizedExecutor:
    """最適化実行エンジン"""
    
    def __init__(self):
        self.task_pool = AsyncTaskPool()
        self.memory_optimizer = MemoryOptimizer()
        self.batch_processor = BatchProcessor()
        self.profiler = PerformanceProfiler()
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.process_pool = ProcessPoolExecutor(max_workers=2)
        
    async def initialize(self):
        """初期化"""
        await self.task_pool.start_workers()
        
    async def execute_optimized_task(
        self,
        task_func: Callable,
        task_args: tuple = (),
        task_kwargs: dict = None,
        use_thread: bool = False,
        use_process: bool = False,
        profile_name: str = None
    ):
        """最適化されたタスク実行"""
        task_kwargs = task_kwargs or {}
        
        async with self.profiler.profile(profile_name or task_func.__name__):
            async with self.memory_optimizer.memory_managed(profile_name):
                if use_process:
                    # プロセスプールで実行
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        self.process_pool, task_func, *task_args
                    )
                elif use_thread:
                    # スレッドプールで実行
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        self.thread_pool, task_func, *task_args
                    )
                else:
                    # 非同期タスクプールで実行
                    if asyncio.iscoroutinefunction(task_func):
                        return await self.task_pool.submit(task_func, *task_args, **task_kwargs)
                    else:
                        # 同期関数を非同期でラップ
                        async def async_wrapper():
                            return task_func(*task_args, **task_kwargs)
                        return await self.task_pool.submit(async_wrapper)
    
    async def batch_execute(
        self,
        items: List[Any],
        processor_func: Callable,
        batch_size: int = 50,
        max_concurrent: int = 5
    ):
        """バッチ実行"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_batch(batch):
            async with semaphore:
                return await processor_func(batch)
        
        # バッチに分割
        batches = [
            items[i:i + batch_size]
            for i in range(0, len(items), batch_size)
        ]
        
        # 並列実行
        tasks = [process_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果をフラット化
        flattened_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {str(result)}")
                continue
            if isinstance(result, list):
                flattened_results.extend(result)
            else:
                flattened_results.append(result)
        
        return flattened_results
    
    def get_metrics(self) -> PerformanceMetrics:
        """メトリクス取得"""
        return PerformanceMetrics(
            memory_usage=self.memory_optimizer.memory_usage(),
            cpu_usage=psutil.cpu_percent(),
            parallel_tasks=len(self.task_pool.active_tasks),
            throughput=self.task_pool.completed_tasks / max(1, time.time()),
            timestamp=datetime.now()
        )
    
    async def shutdown(self):
        """リソースクリーンアップ"""
        await self.task_pool.shutdown()
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        self.memory_optimizer.force_gc()

# パフォーマンス最適化デコレータ
def optimize_performance(
    cache_size: int = 128,
    cache_ttl: float = 3600,
    profile: bool = True,
    memory_monitor: bool = True
):
    """パフォーマンス最適化デコレータ"""
    def decorator(func):
        cached_func = CacheOptimizer.smart_cache(cache_size, cache_ttl)(func)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            profiler = PerformanceProfiler() if profile else None
            memory_optimizer = MemoryOptimizer() if memory_monitor else None
            
            if profiler and memory_optimizer:
                async with profiler.profile(func.__name__):
                    async with memory_optimizer.memory_managed(func.__name__):
                        return await cached_func(*args, **kwargs)
            elif profiler:
                async with profiler.profile(func.__name__):
                    return await cached_func(*args, **kwargs)
            elif memory_optimizer:
                async with memory_optimizer.memory_managed(func.__name__):
                    return await cached_func(*args, **kwargs)
            else:
                return await cached_func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return cached_func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# グローバル最適化エンジンインスタンス
_global_optimizer = None

def get_optimizer() -> OptimizedExecutor:
    """グローバル最適化エンジン取得"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = OptimizedExecutor()
    return _global_optimizer

async def initialize_optimizer():
    """最適化エンジン初期化"""
    optimizer = get_optimizer()
    await optimizer.initialize()
    return optimizer