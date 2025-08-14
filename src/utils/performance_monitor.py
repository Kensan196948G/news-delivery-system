"""
Performance Monitoring Module
パフォーマンス監視モジュール - システム性能の測定と追跡
"""

import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
import asyncio
import threading

from .config import get_config
from .cache_manager import get_cache_manager


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """パフォーマンス測定結果"""
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool = True
    error_message: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """システム全体のメトリクス"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    process_count: int
    uptime_seconds: float


class PerformanceMonitor:
    """パフォーマンス監視システム"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache = get_cache_manager()
        
        # パフォーマンス履歴
        self.metrics_history: List[PerformanceMetrics] = []
        self.system_metrics_history: List[SystemMetrics] = []
        
        # システム開始時刻
        self.start_time = datetime.now()
        
        # 監視設定
        self.max_history_size = self.config.get('monitoring.max_history_size', 1000)
        self.system_monitor_interval = self.config.get('monitoring.system_monitor_interval', 60)
        
        # バックグラウンド監視
        self.monitoring_active = False
        self.monitor_thread = None
        
        # アラート閾値
        self.alert_thresholds = {
            'cpu_percent': self.config.get('monitoring.alert_thresholds.cpu_percent', 80),
            'memory_percent': self.config.get('monitoring.alert_thresholds.memory_percent', 80),
            'disk_usage_percent': self.config.get('monitoring.alert_thresholds.disk_usage_percent', 90),
            'operation_duration': self.config.get('monitoring.alert_thresholds.operation_duration', 300)  # 5分
        }
    
    @contextmanager
    def measure_operation(self, operation_name: str, **additional_data):
        """操作のパフォーマンス測定コンテキストマネージャー"""
        start_time = datetime.now()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        success = True
        error_message = None
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = datetime.now()
            end_memory = self._get_memory_usage()
            
            duration = (end_time - start_time).total_seconds()
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                memory_usage_mb=end_memory - start_memory,
                cpu_usage_percent=self._get_cpu_usage() - start_cpu,
                success=success,
                error_message=error_message,
                additional_data=additional_data
            )
            
            self._record_metrics(metrics)
            
            # アラートチェック
            self._check_performance_alerts(metrics)
    
    def _get_memory_usage(self) -> float:
        """現在のメモリ使用量（MB）を取得"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """現在のCPU使用率を取得"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    def _record_metrics(self, metrics: PerformanceMetrics):
        """メトリクスの記録"""
        try:
            # メモリ履歴に追加
            self.metrics_history.append(metrics)
            
            # 履歴サイズ制限
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            # キャッシュに保存（短期間）
            cache_key = f"perf_metrics:{metrics.operation_name}:{metrics.start_time.isoformat()}"
            self.cache.set(cache_key, metrics.__dict__, expire=3600, category='performance')
            
            logger.debug(f"Performance recorded: {metrics.operation_name} - {metrics.duration_seconds:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to record performance metrics: {e}")
    
    def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """パフォーマンスアラートのチェック"""
        try:
            alerts = []
            
            # 実行時間チェック
            if (metrics.duration_seconds and self.alert_thresholds['operation_duration'] and 
                metrics.duration_seconds > self.alert_thresholds['operation_duration']):
                alerts.append(f"Long operation: {metrics.operation_name} took {metrics.duration_seconds:.2f}s")
            
            # メモリ使用量チェック
            if metrics.memory_usage_mb and metrics.memory_usage_mb > 100:  # 100MB以上の増加
                alerts.append(f"High memory usage: {metrics.operation_name} used {metrics.memory_usage_mb:.1f}MB")
            
            # 失敗チェック
            if not metrics.success:
                alerts.append(f"Operation failed: {metrics.operation_name} - {metrics.error_message}")
            
            if alerts:
                logger.warning(f"Performance alerts: {'; '.join(alerts)}")
                
        except Exception as e:
            logger.error(f"Failed to check performance alerts: {e}")
    
    def collect_system_metrics(self) -> SystemMetrics:
        """システム全体のメトリクス収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # ネットワークI/O
            network_io = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            
            # プロセス数
            process_count = len(psutil.pids())
            
            # システム稼働時間
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                network_io=network_io,
                process_count=process_count,
                uptime_seconds=uptime_seconds
            )
            
            # 履歴に追加
            self.system_metrics_history.append(metrics)
            
            # 履歴サイズ制限
            if len(self.system_metrics_history) > self.max_history_size:
                self.system_metrics_history = self.system_metrics_history[-self.max_history_size:]
            
            # システムアラートチェック
            self._check_system_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0,
                memory_percent=0,
                disk_usage_percent=0,
                network_io={},
                process_count=0,
                uptime_seconds=0
            )
    
    def _check_system_alerts(self, metrics: SystemMetrics):
        """システムアラートのチェック"""
        try:
            alerts = []
            
            if (metrics.cpu_percent and self.alert_thresholds['cpu_percent'] and 
                metrics.cpu_percent > self.alert_thresholds['cpu_percent']):
                alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            
            if (metrics.memory_percent and self.alert_thresholds['memory_percent'] and 
                metrics.memory_percent > self.alert_thresholds['memory_percent']):
                alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            
            if (metrics.disk_usage_percent and self.alert_thresholds['disk_usage_percent'] and 
                metrics.disk_usage_percent > self.alert_thresholds['disk_usage_percent']):
                alerts.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")
            
            if alerts:
                logger.warning(f"System alerts: {'; '.join(alerts)}")
                
        except Exception as e:
            logger.error(f"Failed to check system alerts: {e}")
    
    def start_background_monitoring(self):
        """バックグラウンド監視開始"""
        if self.monitoring_active:
            logger.warning("Background monitoring already active")
            return
        
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    self.collect_system_metrics()
                    time.sleep(self.system_monitor_interval)
                except Exception as e:
                    logger.error(f"Background monitoring error: {e}")
                    time.sleep(60)  # エラー時は1分待機
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Background performance monitoring started")
    
    def stop_background_monitoring(self):
        """バックグラウンド監視停止"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Background performance monitoring stopped")
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """パフォーマンスサマリーの取得"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 指定時間内のメトリクス
            recent_metrics = [
                m for m in self.metrics_history 
                if m.start_time >= cutoff_time
            ]
            
            recent_system_metrics = [
                m for m in self.system_metrics_history 
                if m.timestamp >= cutoff_time
            ]
            
            # 操作別統計
            operation_stats = {}
            for metrics in recent_metrics:
                op_name = metrics.operation_name
                if op_name not in operation_stats:
                    operation_stats[op_name] = {
                        'count': 0,
                        'total_duration': 0,
                        'success_count': 0,
                        'avg_memory_usage': 0
                    }
                
                stats = operation_stats[op_name]
                stats['count'] += 1
                stats['total_duration'] += metrics.duration_seconds
                if metrics.success:
                    stats['success_count'] += 1
                stats['avg_memory_usage'] += metrics.memory_usage_mb
            
            # 平均値計算
            for stats in operation_stats.values():
                if stats['count'] > 0:
                    stats['avg_duration'] = stats['total_duration'] / stats['count']
                    stats['success_rate'] = stats['success_count'] / stats['count']
                    stats['avg_memory_usage'] = stats['avg_memory_usage'] / stats['count']
            
            # システム統計
            system_stats = {}
            if recent_system_metrics:
                system_stats = {
                    'avg_cpu_percent': sum(m.cpu_percent or 0 for m in recent_system_metrics) / len(recent_system_metrics),
                    'avg_memory_percent': sum(m.memory_percent or 0 for m in recent_system_metrics) / len(recent_system_metrics),
                    'avg_disk_usage_percent': sum(m.disk_usage_percent or 0 for m in recent_system_metrics) / len(recent_system_metrics),
                    'max_cpu_percent': max(m.cpu_percent or 0 for m in recent_system_metrics),
                    'max_memory_percent': max(m.memory_percent or 0 for m in recent_system_metrics),
                    'current_uptime_hours': recent_system_metrics[-1].uptime_seconds / 3600
                }
            
            return {
                'summary_period_hours': hours,
                'total_operations': len(recent_metrics),
                'operation_stats': operation_stats,
                'system_stats': system_stats,
                'monitoring_active': self.monitoring_active,
                'alert_thresholds': self.alert_thresholds
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
    
    def get_current_status(self) -> Dict[str, Any]:
        """現在のシステム状態取得"""
        try:
            current_metrics = self.collect_system_metrics()
            
            return {
                'timestamp': current_metrics.timestamp.isoformat(),
                'cpu_percent': current_metrics.cpu_percent,
                'memory_percent': current_metrics.memory_percent,
                'disk_usage_percent': current_metrics.disk_usage_percent,
                'process_count': current_metrics.process_count,
                'uptime_hours': current_metrics.uptime_seconds / 3600,
                'monitoring_active': self.monitoring_active
            }
            
        except Exception as e:
            logger.error(f"Failed to get current status: {e}")
            return {}
    
    def clear_history(self):
        """履歴のクリア"""
        self.metrics_history.clear()
        self.system_metrics_history.clear()
        
        # キャッシュからも削除
        self.cache.clear_category('performance')
        
        logger.info("Performance monitoring history cleared")


# グローバルパフォーマンス監視インスタンス
_performance_monitor_instance = None


def get_performance_monitor() -> PerformanceMonitor:
    """グローバルパフォーマンス監視インスタンス取得"""
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        _performance_monitor_instance = PerformanceMonitor()
    return _performance_monitor_instance


# 便利なデコレータ
def monitor_performance(operation_name: str = None):
    """パフォーマンス監視デコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            monitor = get_performance_monitor()
            
            with monitor.measure_operation(name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


async def monitor_async_performance(operation_name: str = None):
    """非同期パフォーマンス監視デコレータ"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            monitor = get_performance_monitor()
            
            with monitor.measure_operation(name):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator