"""
Performance Benchmark Tests
パフォーマンスベンチマークテスト - 包括的な性能測定とレポート生成
"""

import asyncio
import time
import statistics
import json
import psutil
import gc
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
import sys
import os
import random
import string
import concurrent.futures
from contextlib import asynccontextmanager

# プロジェクトモジュールのインポート
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.performance_optimizer import OptimizedExecutor, PerformanceMetrics, get_optimizer
from utils.cache_manager_advanced import AdvancedCacheManager, CacheBackend
from utils.async_executor import AsyncExecutor, TaskConfig, TaskPriority
from monitoring.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """ベンチマーク結果"""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    iterations: int
    throughput: float  # operations per second
    memory_usage_before: float  # MB
    memory_usage_after: float  # MB
    memory_peak: float  # MB
    cpu_usage_avg: float  # %
    success_rate: float  # 0-1
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def avg_operation_time(self) -> float:
        """平均操作時間（秒）"""
        return self.duration / max(1, self.iterations)

@dataclass
class BenchmarkSuite:
    """ベンチマークスイート"""
    name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: BenchmarkResult):
        """結果追加"""
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """サマリ取得"""
        if not self.results:
            return {}
        
        total_duration = sum(r.duration for r in self.results)
        total_iterations = sum(r.iterations for r in self.results)
        avg_throughput = statistics.mean(r.throughput for r in self.results if r.throughput > 0)
        avg_success_rate = statistics.mean(r.success_rate for r in self.results)
        
        return {
            'total_tests': len(self.results),
            'total_duration': total_duration,
            'total_iterations': total_iterations,
            'avg_throughput': avg_throughput,
            'avg_success_rate': avg_success_rate,
            'memory_peak': max(r.memory_peak for r in self.results),
            'environment': self.environment
        }

class BenchmarkRunner:
    """ベンチマーク実行エンジン"""
    
    def __init__(self):
        self.suites = {}
        self.current_suite = None
        
    @asynccontextmanager
    async def benchmark_context(self, test_name: str):
        """ベンチマークコンテキスト"""
        # 開始前のメトリクス
        start_time = datetime.now()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        cpu_samples = []
        
        # CPU監視タスク
        monitoring = True
        
        async def monitor_cpu():
            nonlocal peak_memory, cpu_samples, monitoring
            while monitoring:
                try:
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    cpu_samples.append(cpu_percent)
                    
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    peak_memory = max(peak_memory, current_memory)
                    
                    await asyncio.sleep(0.1)
                except:
                    break
        
        monitor_task = asyncio.create_task(monitor_cpu())
        
        try:
            yield {
                'start_time': start_time,
                'initial_memory': initial_memory
            }
        finally:
            monitoring = False
            monitor_task.cancel()
            
            end_time = datetime.now()
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0.0
            
            # 結果データ提供
            yield {
                'end_time': end_time,
                'final_memory': final_memory,
                'peak_memory': peak_memory,
                'avg_cpu': avg_cpu,
                'duration': (end_time - start_time).total_seconds()
            }
    
    async def run_benchmark(self, 
                           test_name: str,
                           test_func: Callable,
                           iterations: int = 100,
                           *args, **kwargs) -> BenchmarkResult:
        """ベンチマーク実行"""
        errors = []
        successful_iterations = 0
        
        async with self.benchmark_context(test_name) as context:
            start_context = await context.__anext__()
            
            for i in range(iterations):
                try:
                    if asyncio.iscoroutinefunction(test_func):
                        await test_func(*args, **kwargs)
                    else:
                        test_func(*args, **kwargs)
                    successful_iterations += 1
                except Exception as e:
                    errors.append(f"Iteration {i}: {str(e)}")
            
            end_context = await context.__anext__()
        
        # 結果作成
        duration = end_context['duration']
        throughput = successful_iterations / duration if duration > 0 else 0
        success_rate = successful_iterations / iterations if iterations > 0 else 0
        
        result = BenchmarkResult(
            test_name=test_name,
            start_time=start_context['start_time'],
            end_time=end_context['end_time'],
            duration=duration,
            iterations=successful_iterations,
            throughput=throughput,
            memory_usage_before=start_context['initial_memory'],
            memory_usage_after=end_context['final_memory'],
            memory_peak=end_context['peak_memory'],
            cpu_usage_avg=end_context['avg_cpu'],
            success_rate=success_rate,
            errors=errors[:10]  # 最初の10エラーのみ保存
        )
        
        if self.current_suite:
            self.current_suite.add_result(result)
        
        return result
    
    def create_suite(self, name: str, config: Dict[str, Any] = None) -> BenchmarkSuite:
        """ベンチマークスイート作成"""
        # 環境情報収集
        environment = {
            'python_version': sys.version,
            'platform': sys.platform,
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'timestamp': datetime.now().isoformat()
        }
        
        suite = BenchmarkSuite(
            name=name,
            config=config or {},
            environment=environment
        )
        
        self.suites[name] = suite
        self.current_suite = suite
        return suite

class PerformanceBenchmarks:
    """パフォーマンステスト集"""
    
    def __init__(self):
        self.runner = BenchmarkRunner()
        
    async def run_all_benchmarks(self) -> Dict[str, BenchmarkSuite]:
        """全ベンチマーク実行"""
        results = {}
        
        # キャッシュベンチマーク
        cache_suite = await self.run_cache_benchmarks()
        results['cache'] = cache_suite
        
        # 並列処理ベンチマーク
        parallel_suite = await self.run_parallel_benchmarks()
        results['parallel'] = parallel_suite
        
        # データベースベンチマーク
        db_suite = await self.run_database_benchmarks()
        results['database'] = db_suite
        
        # API処理ベンチマーク
        api_suite = await self.run_api_benchmarks()
        results['api'] = api_suite
        
        # メモリ効率ベンチマーク
        memory_suite = await self.run_memory_benchmarks()
        results['memory'] = memory_suite
        
        return results
    
    async def run_cache_benchmarks(self) -> BenchmarkSuite:
        """キャッシュベンチマーク"""
        suite = self.runner.create_suite("Cache Performance", {
            'cache_sizes': [100, 500, 1000],
            'backends': ['memory', 'hybrid']
        })
        
        # メモリキャッシュテスト
        memory_cache = AdvancedCacheManager(CacheBackend.MEMORY)
        
        await self.runner.run_benchmark(
            "cache_set_memory",
            self._cache_set_test,
            iterations=1000,
            cache_manager=memory_cache
        )
        
        await self.runner.run_benchmark(
            "cache_get_memory",
            self._cache_get_test,
            iterations=1000,
            cache_manager=memory_cache
        )
        
        # ハイブリッドキャッシュテスト
        hybrid_cache = AdvancedCacheManager(CacheBackend.HYBRID)
        
        await self.runner.run_benchmark(
            "cache_set_hybrid",
            self._cache_set_test,
            iterations=500,
            cache_manager=hybrid_cache
        )
        
        await self.runner.run_benchmark(
            "cache_get_hybrid",
            self._cache_get_test,
            iterations=500,
            cache_manager=hybrid_cache
        )
        
        return suite
    
    async def _cache_set_test(self, cache_manager: AdvancedCacheManager):
        """キャッシュ設定テスト"""
        key = f"test_key_{random.randint(1, 1000)}"
        value = {
            'data': ''.join(random.choices(string.ascii_letters, k=100)),
            'timestamp': datetime.now().isoformat(),
            'number': random.randint(1, 1000000)
        }
        await cache_manager.set(key, value, ttl=3600)
    
    async def _cache_get_test(self, cache_manager: AdvancedCacheManager):
        """キャッシュ取得テスト"""
        key = f"test_key_{random.randint(1, 1000)}"
        await cache_manager.get(key)
    
    async def run_parallel_benchmarks(self) -> BenchmarkSuite:
        """並列処理ベンチマーク"""
        suite = self.runner.create_suite("Parallel Processing", {
            'worker_counts': [5, 10, 20],
            'task_counts': [100, 500, 1000]
        })
        
        executor = AsyncExecutor(max_workers=10)
        await executor.start()
        
        try:
            # 並列タスク実行テスト
            await self.runner.run_benchmark(
                "parallel_light_tasks",
                self._parallel_light_tasks_test,
                iterations=5,
                executor=executor,
                task_count=100
            )
            
            await self.runner.run_benchmark(
                "parallel_heavy_tasks",
                self._parallel_heavy_tasks_test,
                iterations=3,
                executor=executor,
                task_count=50
            )
            
            # バッチ処理テスト
            await self.runner.run_benchmark(
                "batch_processing",
                self._batch_processing_test,
                iterations=5,
                executor=executor
            )
            
        finally:
            await executor.stop()
        
        return suite
    
    async def _parallel_light_tasks_test(self, executor: AsyncExecutor, task_count: int):
        """軽量並列タスクテスト"""
        async def light_task(x):
            await asyncio.sleep(0.01)  # 10ms
            return x * 2
        
        tasks = []
        for i in range(task_count):
            task_id = await executor.submit_task(f"light_{i}", light_task, (i,))
            tasks.append(task_id)
        
        results = await executor.wait_for_batch(tasks)
        return len([r for r in results if r.is_successful])
    
    async def _parallel_heavy_tasks_test(self, executor: AsyncExecutor, task_count: int):
        """重い並列タスクテスト"""
        def heavy_task(x):
            # CPU集約的タスク
            result = 0
            for i in range(100000):
                result += i * x
            return result
        
        config = TaskConfig(use_thread_pool=True)
        tasks = []
        for i in range(task_count):
            task_id = await executor.submit_task(f"heavy_{i}", heavy_task, (i,), config=config)
            tasks.append(task_id)
        
        results = await executor.wait_for_batch(tasks)
        return len([r for r in results if r.is_successful])
    
    async def _batch_processing_test(self, executor: AsyncExecutor):
        """バッチ処理テスト"""
        items = list(range(1000))
        
        async def process_batch(batch):
            await asyncio.sleep(0.1)  # 模擬処理時間
            return [x * 2 for x in batch]
        
        results = await executor.process_parallel_batches(
            items, process_batch, batch_size=50, max_concurrent=5
        )
        
        return len(results)
    
    async def run_database_benchmarks(self) -> BenchmarkSuite:
        """データベースベンチマーク"""
        suite = self.runner.create_suite("Database Performance", {
            'operations': ['insert', 'select', 'update', 'delete'],
            'batch_sizes': [10, 50, 100]
        })
        
        # SQLiteテスト（インメモリ）
        import sqlite3
        
        conn = sqlite3.connect(':memory:')
        conn.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                data TEXT,
                value INTEGER,
                timestamp TEXT
            )
        ''')
        
        await self.runner.run_benchmark(
            "db_insert_single",
            self._db_insert_test,
            iterations=1000,
            connection=conn,
            batch_size=1
        )
        
        await self.runner.run_benchmark(
            "db_insert_batch",
            self._db_insert_test,
            iterations=100,
            connection=conn,
            batch_size=10
        )
        
        await self.runner.run_benchmark(
            "db_select",
            self._db_select_test,
            iterations=1000,
            connection=conn
        )
        
        conn.close()
        return suite
    
    def _db_insert_test(self, connection, batch_size: int = 1):
        """データベース挿入テスト"""
        data_batch = []
        for i in range(batch_size):
            data_batch.append((
                f"test_data_{random.randint(1, 10000)}",
                random.randint(1, 1000),
                datetime.now().isoformat()
            ))
        
        if batch_size == 1:
            connection.execute(
                'INSERT INTO test_table (data, value, timestamp) VALUES (?, ?, ?)',
                data_batch[0]
            )
        else:
            connection.executemany(
                'INSERT INTO test_table (data, value, timestamp) VALUES (?, ?, ?)',
                data_batch
            )
        connection.commit()
    
    def _db_select_test(self, connection):
        """データベース選択テスト"""
        cursor = connection.execute(
            'SELECT * FROM test_table WHERE value > ? LIMIT 10',
            (random.randint(1, 500),)
        )
        return cursor.fetchall()
    
    async def run_api_benchmarks(self) -> BenchmarkSuite:
        """API処理ベンチマーク"""
        suite = self.runner.create_suite("API Processing", {
            'simulated_apis': ['news', 'translation', 'analysis'],
            'concurrent_requests': [1, 5, 10]
        })
        
        await self.runner.run_benchmark(
            "api_news_simulation",
            self._api_simulation_test,
            iterations=100,
            api_type="news",
            response_time=0.2
        )
        
        await self.runner.run_benchmark(
            "api_translation_simulation",
            self._api_simulation_test,
            iterations=50,
            api_type="translation",
            response_time=0.5
        )
        
        await self.runner.run_benchmark(
            "api_analysis_simulation",
            self._api_simulation_test,
            iterations=30,
            api_type="analysis",
            response_time=1.0
        )
        
        return suite
    
    async def _api_simulation_test(self, api_type: str, response_time: float):
        """API呼び出しシミュレーション"""
        # 模擬レスポンス時間
        await asyncio.sleep(response_time + random.uniform(-0.1, 0.1))
        
        # 模擬データ生成
        if api_type == "news":
            return {
                'articles': [
                    {
                        'title': f'Article {i}',
                        'content': ''.join(random.choices(string.ascii_letters, k=500))
                    }
                    for i in range(10)
                ]
            }
        elif api_type == "translation":
            return {
                'translated_text': ''.join(random.choices(string.ascii_letters, k=200))
            }
        elif api_type == "analysis":
            return {
                'summary': ''.join(random.choices(string.ascii_letters, k=150)),
                'keywords': [f'keyword_{i}' for i in range(5)],
                'importance': random.randint(1, 10)
            }
    
    async def run_memory_benchmarks(self) -> BenchmarkSuite:
        """メモリ効率ベンチマーク"""
        suite = self.runner.create_suite("Memory Efficiency", {
            'data_sizes': ['small', 'medium', 'large'],
            'operations': ['create', 'process', 'cleanup']
        })
        
        await self.runner.run_benchmark(
            "memory_large_data_processing",
            self._memory_large_data_test,
            iterations=10
        )
        
        await self.runner.run_benchmark(
            "memory_generator_vs_list",
            self._memory_generator_test,
            iterations=5
        )
        
        await self.runner.run_benchmark(
            "memory_gc_efficiency",
            self._memory_gc_test,
            iterations=20
        )
        
        return suite
    
    def _memory_large_data_test(self):
        """大量データ処理テスト"""
        # 大きなデータ構造作成
        data = [
            {
                'id': i,
                'content': ''.join(random.choices(string.ascii_letters, k=1000)),
                'numbers': [random.randint(1, 1000) for _ in range(100)]
            }
            for i in range(1000)
        ]
        
        # データ処理
        processed = []
        for item in data:
            processed.append({
                'id': item['id'],
                'content_length': len(item['content']),
                'number_sum': sum(item['numbers'])
            })
        
        return len(processed)
    
    def _memory_generator_test(self):
        """ジェネレータ vs リスト メモリ効率テスト"""
        def data_generator():
            for i in range(10000):
                yield ''.join(random.choices(string.ascii_letters, k=100))
        
        # ジェネレータ使用
        gen_result = sum(len(item) for item in data_generator())
        
        # リスト使用
        data_list = [
            ''.join(random.choices(string.ascii_letters, k=100))
            for i in range(10000)
        ]
        list_result = sum(len(item) for item in data_list)
        
        return gen_result == list_result
    
    def _memory_gc_test(self):
        """ガベージコレクション効率テスト"""
        # 一時的な大きなオブジェクト作成
        temp_data = []
        for i in range(1000):
            temp_data.append({
                'data': ''.join(random.choices(string.ascii_letters, k=500))
            })
        
        # 明示的な削除
        del temp_data
        
        # ガベージコレクション実行
        collected = gc.collect()
        
        return collected

class BenchmarkReporter:
    """ベンチマークレポート生成"""
    
    @staticmethod
    def generate_report(suites: Dict[str, BenchmarkSuite], output_path: str = None) -> Dict[str, Any]:
        """総合レポート生成"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {},
            'suites': {},
            'recommendations': []
        }
        
        total_tests = 0
        total_duration = 0.0
        all_success_rates = []
        
        for suite_name, suite in suites.items():
            suite_summary = suite.get_summary()
            report['suites'][suite_name] = {
                'summary': suite_summary,
                'results': [asdict(result) for result in suite.results]
            }
            
            total_tests += suite_summary.get('total_tests', 0)
            total_duration += suite_summary.get('total_duration', 0)
            if suite_summary.get('avg_success_rate'):
                all_success_rates.append(suite_summary['avg_success_rate'])
        
        # 総合サマリ
        report['summary'] = {
            'total_test_suites': len(suites),
            'total_tests': total_tests,
            'total_duration': total_duration,
            'overall_success_rate': statistics.mean(all_success_rates) if all_success_rates else 0,
            'fastest_test': BenchmarkReporter._find_fastest_test(suites),
            'slowest_test': BenchmarkReporter._find_slowest_test(suites)
        }
        
        # 推奨事項生成
        report['recommendations'] = BenchmarkReporter._generate_recommendations(suites)
        
        # ファイル出力
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    @staticmethod
    def _find_fastest_test(suites: Dict[str, BenchmarkSuite]) -> Dict[str, Any]:
        """最高速テスト検索"""
        fastest = None
        best_throughput = 0
        
        for suite_name, suite in suites.items():
            for result in suite.results:
                if result.throughput > best_throughput:
                    best_throughput = result.throughput
                    fastest = {
                        'suite': suite_name,
                        'test': result.test_name,
                        'throughput': result.throughput,
                        'avg_time': result.avg_operation_time
                    }
        
        return fastest
    
    @staticmethod
    def _find_slowest_test(suites: Dict[str, BenchmarkSuite]) -> Dict[str, Any]:
        """最低速テスト検索"""
        slowest = None
        worst_throughput = float('inf')
        
        for suite_name, suite in suites.items():
            for result in suite.results:
                if 0 < result.throughput < worst_throughput:
                    worst_throughput = result.throughput
                    slowest = {
                        'suite': suite_name,
                        'test': result.test_name,
                        'throughput': result.throughput,
                        'avg_time': result.avg_operation_time
                    }
        
        return slowest
    
    @staticmethod
    def _generate_recommendations(suites: Dict[str, BenchmarkSuite]) -> List[str]:
        """最適化推奨事項生成"""
        recommendations = []
        
        for suite_name, suite in suites.items():
            if suite_name == 'cache':
                cache_recommendations = BenchmarkReporter._analyze_cache_performance(suite)
                recommendations.extend(cache_recommendations)
            elif suite_name == 'parallel':
                parallel_recommendations = BenchmarkReporter._analyze_parallel_performance(suite)
                recommendations.extend(parallel_recommendations)
            elif suite_name == 'memory':
                memory_recommendations = BenchmarkReporter._analyze_memory_performance(suite)
                recommendations.extend(memory_recommendations)
        
        return recommendations
    
    @staticmethod
    def _analyze_cache_performance(suite: BenchmarkSuite) -> List[str]:
        """キャッシュパフォーマンス分析"""
        recommendations = []
        
        memory_results = [r for r in suite.results if 'memory' in r.test_name]
        hybrid_results = [r for r in suite.results if 'hybrid' in r.test_name]
        
        if memory_results and hybrid_results:
            memory_avg = statistics.mean(r.throughput for r in memory_results)
            hybrid_avg = statistics.mean(r.throughput for r in hybrid_results)
            
            if memory_avg > hybrid_avg * 1.5:
                recommendations.append("メモリキャッシュがハイブリッドキャッシュより大幅に高速です。Redis設定を確認してください。")
            elif hybrid_avg > memory_avg * 1.2:
                recommendations.append("ハイブリッドキャッシュが効果的に動作しています。本番環境での採用を推奨します。")
        
        return recommendations
    
    @staticmethod
    def _analyze_parallel_performance(suite: BenchmarkSuite) -> List[str]:
        """並列処理パフォーマンス分析"""
        recommendations = []
        
        light_results = [r for r in suite.results if 'light' in r.test_name]
        heavy_results = [r for r in suite.results if 'heavy' in r.test_name]
        
        if heavy_results:
            heavy_avg_memory = statistics.mean(r.memory_peak for r in heavy_results)
            if heavy_avg_memory > 1000:  # 1GB以上
                recommendations.append("重い並列タスクでメモリ使用量が多いです。プロセスプールのサイズを調整してください。")
        
        if light_results:
            light_avg_cpu = statistics.mean(r.cpu_usage_avg for r in light_results)
            if light_avg_cpu < 30:
                recommendations.append("軽量タスクでCPU使用率が低いです。並列度を上げることができます。")
        
        return recommendations
    
    @staticmethod
    def _analyze_memory_performance(suite: BenchmarkSuite) -> List[str]:
        """メモリパフォーマンス分析"""
        recommendations = []
        
        for result in suite.results:
            memory_increase = result.memory_usage_after - result.memory_usage_before
            if memory_increase > 100:  # 100MB以上増加
                recommendations.append(f"{result.test_name}でメモリ使用量が{memory_increase:.1f}MB増加しました。メモリリークの可能性があります。")
            
            if result.memory_peak > 1000:  # 1GB以上
                recommendations.append(f"{result.test_name}でメモリ使用量のピークが{result.memory_peak:.1f}MBでした。大量データ処理の最適化を検討してください。")
        
        return recommendations

async def main():
    """メインベンチマーク実行"""
    print("🚀 Performance Benchmark Tests Starting...")
    
    # ベンチマーク実行
    benchmarks = PerformanceBenchmarks()
    
    try:
        results = await benchmarks.run_all_benchmarks()
        
        # レポート生成
        report_path = f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report = BenchmarkReporter.generate_report(results, report_path)
        
        # 結果表示
        print("\n📊 Benchmark Results Summary:")
        print(f"Total test suites: {report['summary']['total_test_suites']}")
        print(f"Total tests: {report['summary']['total_tests']}")
        print(f"Total duration: {report['summary']['total_duration']:.2f}s")
        print(f"Overall success rate: {report['summary']['overall_success_rate']:.2%}")
        
        if report['summary']['fastest_test']:
            fastest = report['summary']['fastest_test']
            print(f"\nFastest test: {fastest['test']} ({fastest['throughput']:.2f} ops/sec)")
        
        if report['summary']['slowest_test']:
            slowest = report['summary']['slowest_test']
            print(f"Slowest test: {slowest['test']} ({slowest['throughput']:.2f} ops/sec)")
        
        print(f"\n📋 Recommendations ({len(report['recommendations'])}):")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        
    except Exception as e:
        logger.error(f"Benchmark execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())