"""
Async Executor Engine
非同期実行エンジン - 並列処理、タスク管理、リソース制御
"""

import asyncio
import time
import psutil
import logging
from typing import Any, Dict, List, Optional, Callable, Union, TypeVar, Awaitable, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from collections import defaultdict, deque
from enum import Enum
import threading
import queue
import weakref
import signal
import contextlib
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')

class TaskPriority(Enum):
    """タスク優先度"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class TaskStatus(Enum):
    """タスク状態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

@dataclass
class TaskResult:
    """タスク結果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    memory_usage: float = 0.0
    retries: int = 0
    
    @property
    def is_successful(self) -> bool:
        """成功判定"""
        return self.status == TaskStatus.COMPLETED and self.error is None

@dataclass
class TaskConfig:
    """タスク設定"""
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[float] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    memory_limit: Optional[float] = None  # MB
    use_thread_pool: bool = False
    use_process_pool: bool = False
    tags: List[str] = field(default_factory=list)

class Task:
    """タスククラス"""
    
    def __init__(self, 
                 task_id: str,
                 func: Callable,
                 args: tuple = (),
                 kwargs: dict = None,
                 config: TaskConfig = None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.config = config or TaskConfig()
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.retries = 0
        self.asyncio_task = None
        
    @property
    def execution_time(self) -> float:
        """実行時間"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    def __lt__(self, other):
        """優先度比較（優先度キューでの使用）"""
        return self.config.priority.value > other.config.priority.value

class RateLimiter:
    """レート制限器"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """レート制限取得"""
        async with self.lock:
            now = time.time()
            
            # 期限切れの呼び出しを削除
            while self.calls and self.calls[0] <= now - self.time_window:
                self.calls.popleft()
            
            # レート制限チェック
            if len(self.calls) >= self.max_calls:
                sleep_time = self.time_window - (now - self.calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            self.calls.append(now)

class ResourceMonitor:
    """リソース監視"""
    
    def __init__(self, memory_limit: float = 2048, cpu_limit: float = 80):
        self.memory_limit = memory_limit  # MB
        self.cpu_limit = cpu_limit  # %
        self.monitoring = False
        self.stats = {
            'memory_usage': 0.0,
            'cpu_usage': 0.0,
            'memory_peak': 0.0,
            'cpu_peak': 0.0
        }
    
    async def start_monitoring(self):
        """監視開始"""
        self.monitoring = True
        asyncio.create_task(self._monitor_resources())
    
    async def _monitor_resources(self):
        """リソース監視ループ"""
        while self.monitoring:
            try:
                # メモリ使用量
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                self.stats['memory_usage'] = memory_mb
                self.stats['cpu_usage'] = cpu_percent
                self.stats['memory_peak'] = max(self.stats['memory_peak'], memory_mb)
                self.stats['cpu_peak'] = max(self.stats['cpu_peak'], cpu_percent)
                
                # 制限チェック
                if memory_mb > self.memory_limit:
                    logger.warning(f"Memory limit exceeded: {memory_mb:.1f}MB > {self.memory_limit}MB")
                
                if cpu_percent > self.cpu_limit:
                    logger.warning(f"CPU limit exceeded: {cpu_percent:.1f}% > {self.cpu_limit}%")
                
                await asyncio.sleep(1.0)  # 1秒間隔
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {str(e)}")
                await asyncio.sleep(5.0)
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
    
    def get_stats(self) -> Dict[str, float]:
        """統計取得"""
        return self.stats.copy()

class TaskQueue:
    """タスクキュー"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queues = {
            TaskPriority.URGENT: asyncio.PriorityQueue(),
            TaskPriority.HIGH: asyncio.PriorityQueue(), 
            TaskPriority.NORMAL: asyncio.PriorityQueue(),
            TaskPriority.LOW: asyncio.PriorityQueue()
        }
        self.task_counter = 0
    
    async def put(self, task: Task):
        """タスク追加"""
        priority_queue = self.queues[task.config.priority]
        
        # キューサイズチェック
        if priority_queue.qsize() >= self.max_size:
            raise asyncio.QueueFull(f"Task queue full for priority {task.config.priority}")
        
        # 優先度付きでキューに追加
        await priority_queue.put((self.task_counter, task))
        self.task_counter += 1
    
    async def get(self) -> Optional[Task]:
        """タスク取得（優先度順）"""
        # 緊急 > 高 > 通常 > 低の順で取得
        for priority in [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
            priority_queue = self.queues[priority]
            if not priority_queue.empty():
                try:
                    _, task = await asyncio.wait_for(priority_queue.get(), timeout=0.01)
                    return task
                except asyncio.TimeoutError:
                    continue
        return None
    
    def qsize(self) -> Dict[TaskPriority, int]:
        """キューサイズ"""
        return {priority: queue.qsize() for priority, queue in self.queues.items()}

class WorkerPool:
    """ワーカープール"""
    
    def __init__(self, 
                 max_workers: int = 10,
                 thread_pool_size: int = 4,
                 process_pool_size: int = 2):
        self.max_workers = max_workers
        self.active_workers = 0
        self.worker_tasks = []
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        self.process_pool = ProcessPoolExecutor(max_workers=process_pool_size)
        self.running = False
        self.task_queue = None
        self.rate_limiters = {}
        
    async def start(self, task_queue: TaskQueue):
        """ワーカー開始"""
        self.running = True
        self.task_queue = task_queue
        
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(worker)
        
        logger.info(f"Started {self.max_workers} workers")
    
    async def _worker(self, worker_name: str):
        """ワーカータスク"""
        logger.debug(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # タスク取得
                task = await self.task_queue.get()
                if task is None:
                    await asyncio.sleep(0.1)
                    continue
                
                self.active_workers += 1
                logger.debug(f"Worker {worker_name} processing task {task.task_id}")
                
                # タスク実行
                result = await self._execute_task(task, worker_name)
                
                self.active_workers -= 1
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {str(e)}")
                self.active_workers = max(0, self.active_workers - 1)
                await asyncio.sleep(1.0)
    
    async def _execute_task(self, task: Task, worker_name: str) -> TaskResult:
        """タスク実行"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # タイムアウト設定
            timeout = task.config.timeout
            
            # 実行方式選択
            if task.config.use_process_pool:
                result = await self._run_in_process_pool(task)
            elif task.config.use_thread_pool:
                result = await self._run_in_thread_pool(task)
            else:
                result = await self._run_async(task)
            
            # タイムアウト処理
            if timeout:
                try:
                    result = await asyncio.wait_for(result, timeout=timeout)
                except asyncio.TimeoutError:
                    task.status = TaskStatus.TIMEOUT
                    task.error = TimeoutError(f"Task {task.task_id} timed out after {timeout}s")
                    return self._create_task_result(task, initial_memory)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            
            # リトライ判定
            if task.retries < task.config.max_retries:
                task.retries += 1
                retry_delay = task.config.retry_delay * (task.config.retry_backoff ** (task.retries - 1))
                logger.info(f"Retrying task {task.task_id} in {retry_delay}s (attempt {task.retries})")
                
                await asyncio.sleep(retry_delay)
                task.status = TaskStatus.PENDING
                await self.task_queue.put(task)
                return None
        
        finally:
            task.completed_at = datetime.now()
        
        return self._create_task_result(task, initial_memory)
    
    async def _run_async(self, task: Task):
        """非同期実行"""
        if asyncio.iscoroutinefunction(task.func):
            return await task.func(*task.args, **task.kwargs)
        else:
            # 同期関数を非同期で実行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: task.func(*task.args, **task.kwargs))
    
    async def _run_in_thread_pool(self, task: Task):
        """スレッドプール実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool, 
            lambda: task.func(*task.args, **task.kwargs)
        )
    
    async def _run_in_process_pool(self, task: Task):
        """プロセスプール実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.process_pool, 
            lambda: task.func(*task.args, **task.kwargs)
        )
    
    def _create_task_result(self, task: Task, initial_memory: float) -> TaskResult:
        """タスク結果作成"""
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        return TaskResult(
            task_id=task.task_id,
            status=task.status,
            result=task.result,
            error=task.error,
            start_time=task.started_at,
            end_time=task.completed_at,
            execution_time=task.execution_time,
            memory_usage=final_memory - initial_memory,
            retries=task.retries
        )
    
    async def stop(self):
        """ワーカー停止"""
        self.running = False
        
        # ワーカータスクのキャンセル
        for worker in self.worker_tasks:
            worker.cancel()
        
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # エグゼキューターのシャットダウン
        self.thread_pool.shutdown(wait=False)
        self.process_pool.shutdown(wait=False)
        
        logger.info("Workers stopped")

class AsyncExecutor:
    """非同期実行エンジン"""
    
    def __init__(self, 
                 max_workers: int = 10,
                 max_queue_size: int = 1000,
                 memory_limit: float = 2048,
                 enable_monitoring: bool = True):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.task_queue = TaskQueue(max_queue_size)
        self.worker_pool = WorkerPool(max_workers)
        self.resource_monitor = ResourceMonitor(memory_limit) if enable_monitoring else None
        self.task_results = {}
        self.running = False
        self.stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0.0
        }
        
    async def start(self):
        """エグゼキューター開始"""
        if self.running:
            return
        
        self.running = True
        await self.worker_pool.start(self.task_queue)
        
        if self.resource_monitor:
            await self.resource_monitor.start_monitoring()
        
        logger.info("AsyncExecutor started")
    
    async def submit_task(self, 
                         task_id: str,
                         func: Callable,
                         args: tuple = (),
                         kwargs: dict = None,
                         config: TaskConfig = None) -> str:
        """タスク投入"""
        if not self.running:
            await self.start()
        
        task = Task(task_id, func, args, kwargs, config)
        await self.task_queue.put(task)
        
        self.stats['tasks_submitted'] += 1
        logger.debug(f"Task {task_id} submitted")
        
        return task_id
    
    async def submit_batch(self, 
                          tasks: List[Dict[str, Any]],
                          default_config: TaskConfig = None) -> List[str]:
        """バッチタスク投入"""
        task_ids = []
        
        for i, task_info in enumerate(tasks):
            task_id = task_info.get('task_id', f"batch_task_{i}_{int(time.time())}")
            func = task_info['func']
            args = task_info.get('args', ())
            kwargs = task_info.get('kwargs', {})
            config = task_info.get('config', default_config)
            
            await self.submit_task(task_id, func, args, kwargs, config)
            task_ids.append(task_id)
        
        return task_ids
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """タスク完了待機"""
        start_time = time.time()
        
        while True:
            if task_id in self.task_results:
                result = self.task_results[task_id]
                del self.task_results[task_id]  # メモリ節約
                return result
            
            if timeout and time.time() - start_time > timeout:
                raise asyncio.TimeoutError(f"Task {task_id} did not complete within {timeout}s")
            
            await asyncio.sleep(0.1)
    
    async def wait_for_batch(self, 
                            task_ids: List[str], 
                            timeout: Optional[float] = None,
                            return_when: str = 'ALL_COMPLETED') -> List[TaskResult]:
        """バッチタスク完了待機"""
        if return_when == 'ALL_COMPLETED':
            results = []
            for task_id in task_ids:
                result = await self.wait_for_task(task_id, timeout)
                results.append(result)
            return results
        
        elif return_when == 'FIRST_COMPLETED':
            while True:
                for task_id in task_ids:
                    if task_id in self.task_results:
                        result = self.task_results[task_id]
                        del self.task_results[task_id]
                        return [result]
                await asyncio.sleep(0.1)
        
        else:
            raise ValueError(f"Invalid return_when value: {return_when}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """タスクキャンセル"""
        # 実装詳細はタスク状態管理に依存
        logger.info(f"Cancelling task {task_id}")
        return True
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """キュー統計"""
        queue_sizes = self.task_queue.qsize()
        return {
            'total_queued': sum(queue_sizes.values()),
            'by_priority': {p.name: size for p, size in queue_sizes.items()},
            'active_workers': self.worker_pool.active_workers,
            'max_workers': self.max_workers
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計"""
        stats = self.stats.copy()
        
        if self.resource_monitor:
            stats.update(self.resource_monitor.get_stats())
        
        # 成功率計算
        total_completed = stats['tasks_completed'] + stats['tasks_failed']
        stats['success_rate'] = (
            stats['tasks_completed'] / max(1, total_completed)
        )
        
        # 平均実行時間
        stats['avg_execution_time'] = (
            stats['total_execution_time'] / max(1, stats['tasks_completed'])
        )
        
        return stats
    
    async def process_parallel_batches(self,
                                     items: List[Any],
                                     processor_func: Callable,
                                     batch_size: int = 50,
                                     max_concurrent: int = 5,
                                     config: TaskConfig = None) -> List[Any]:
        """並列バッチ処理"""
        # バッチに分割
        batches = [
            items[i:i + batch_size] 
            for i in range(0, len(items), batch_size)
        ]
        
        # タスク投入
        task_configs = []
        for i, batch in enumerate(batches):
            task_config = {
                'task_id': f"batch_process_{i}",
                'func': processor_func,
                'args': (batch,),
                'config': config
            }
            task_configs.append(task_config)
        
        # 同時実行数制限
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_batch_with_semaphore(task_config):
            async with semaphore:
                task_id = await self.submit_task(**task_config)
                return await self.wait_for_task(task_id)
        
        # 実行・結果集約
        batch_tasks = [
            process_batch_with_semaphore(config) 
            for config in task_configs
        ]
        
        batch_results = await asyncio.gather(*batch_tasks)
        
        # 結果をフラット化
        flattened_results = []
        for result in batch_results:
            if result.is_successful and isinstance(result.result, list):
                flattened_results.extend(result.result)
            elif result.is_successful:
                flattened_results.append(result.result)
            else:
                logger.error(f"Batch processing failed: {result.error}")
        
        return flattened_results
    
    async def stop(self):
        """エグゼキューター停止"""
        if not self.running:
            return
        
        self.running = False
        
        if self.resource_monitor:
            self.resource_monitor.stop_monitoring()
        
        await self.worker_pool.stop()
        
        logger.info("AsyncExecutor stopped")

# 便利なデコレータとヘルパー関数

def async_task(executor: AsyncExecutor = None, 
              priority: TaskPriority = TaskPriority.NORMAL,
              timeout: Optional[float] = None,
              max_retries: int = 3):
    """非同期タスクデコレータ"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if executor is None:
                # デフォルトエグゼキューター使用
                return await func(*args, **kwargs)
            
            config = TaskConfig(
                priority=priority,
                timeout=timeout,
                max_retries=max_retries
            )
            
            task_id = f"{func.__name__}_{int(time.time())}"
            submitted_task_id = await executor.submit_task(
                task_id, func, args, kwargs, config
            )
            
            result = await executor.wait_for_task(submitted_task_id)
            
            if result.is_successful:
                return result.result
            else:
                raise result.error or Exception("Task failed")
        
        return wrapper
    return decorator

# グローバルエグゼキューター
_global_executor = None

def get_global_executor() -> AsyncExecutor:
    """グローバルエグゼキューター取得"""
    global _global_executor
    if _global_executor is None:
        _global_executor = AsyncExecutor()
    return _global_executor

async def execute_parallel(func: Callable, 
                          items: List[Any],
                          max_concurrent: int = 10,
                          timeout: Optional[float] = None) -> List[Any]:
    """並列実行ヘルパー"""
    executor = get_global_executor()
    
    if not executor.running:
        await executor.start()
    
    config = TaskConfig(timeout=timeout)
    
    tasks = []
    for i, item in enumerate(items):
        task_id = f"parallel_{func.__name__}_{i}"
        task_id = await executor.submit_task(task_id, func, (item,), {}, config)
        tasks.append(task_id)
    
    results = await executor.wait_for_batch(tasks)
    return [r.result if r.is_successful else r.error for r in results]