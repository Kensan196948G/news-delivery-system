"""
Performance Monitor
パフォーマンス監視システム - リアルタイム監視、アラート、レポート生成
"""

import asyncio
import time
import psutil
import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional, Callable, NamedTuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
import threading
from contextlib import asynccontextmanager
import statistics
import gc
import sys

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """システムメトリクス"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    thread_count: int
    
@dataclass
class ApplicationMetrics:
    """アプリケーションメトリクス"""
    timestamp: datetime
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    cache_hits: int
    cache_misses: int
    api_calls_count: int
    api_calls_failed: int
    database_queries: int
    database_query_time: float
    memory_usage_mb: float
    gc_collections: int

@dataclass
class PerformanceAlert:
    """パフォーマンスアラート"""
    alert_id: str
    timestamp: datetime
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    category: str  # CPU, MEMORY, DISK, NETWORK, APPLICATION
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class MetricsCollector:
    """メトリクス収集器"""
    
    def __init__(self):
        self.system_metrics_history = deque(maxlen=1000)
        self.app_metrics_history = deque(maxlen=1000)
        self.network_counters = None
        self.last_network_check = None
        
    def collect_system_metrics(self) -> SystemMetrics:
        """システムメトリクス収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # メモリ情報
            memory = psutil.virtual_memory()
            
            # ディスク情報 - ルートディスクの代わりにカレントディスクを使用
            try:
                disk = psutil.disk_usage('/')
            except (OSError, FileNotFoundError):
                # Windowsや他の環境での対応
                import os
                disk = psutil.disk_usage(os.getcwd())
            
            # ネットワーク情報
            network_sent_mb, network_recv_mb = self._get_network_stats()
            
            # プロセス情報
            try:
                process_count = len(psutil.pids())
            except (psutil.AccessDenied, OSError):
                logger.warning("Cannot access process list, using estimated count")
                process_count = -1
            
            # 現在のプロセスのスレッド数
            try:
                current_process = psutil.Process()
                thread_count = current_process.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
                logger.warning(f"Cannot access current process info: {str(e)}")
                thread_count = -1
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=disk.percent,
                disk_free_gb=disk.free / 1024 / 1024 / 1024,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                process_count=process_count,
                thread_count=thread_count
            )
            
            self.system_metrics_history.append(metrics)
            return metrics
            
        except (psutil.Error, OSError) as e:
            logger.error(f"System error collecting metrics: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error collecting system metrics: {str(e)}")
            return None
    
    def _get_network_stats(self) -> tuple:
        """ネットワーク統計取得"""
        try:
            current_counters = psutil.net_io_counters()
            if current_counters is None:
                logger.warning("Network interface counters not available")
                return 0.0, 0.0
                
            current_time = time.time()
            
            if self.network_counters and self.last_network_check:
                time_diff = current_time - self.last_network_check
                
                if time_diff > 0:
                    # Handle counter rollover or negative values
                    sent_diff = max(0, current_counters.bytes_sent - self.network_counters.bytes_sent)
                    recv_diff = max(0, current_counters.bytes_recv - self.network_counters.bytes_recv)
                    
                    sent_mb = (sent_diff / time_diff) / 1024 / 1024
                    recv_mb = (recv_diff / time_diff) / 1024 / 1024
                else:
                    sent_mb = recv_mb = 0.0
            else:
                sent_mb = recv_mb = 0.0
            
            self.network_counters = current_counters
            self.last_network_check = current_time
            
            return sent_mb, recv_mb
            
        except (OSError, AttributeError, ValueError) as e:
            logger.error(f"Failed to get network statistics: {str(e)}")
            return 0.0, 0.0
        except Exception as e:
            logger.error(f"Unexpected error getting network statistics: {str(e)}")
            return 0.0, 0.0
    
    def get_system_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """システムメトリクスサマリ"""
        if not self.system_metrics_history:
            return {}
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.system_metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            'cpu_avg': statistics.mean(cpu_values),
            'cpu_max': max(cpu_values),
            'cpu_min': min(cpu_values),
            'memory_avg': statistics.mean(memory_values),
            'memory_max': max(memory_values),
            'memory_min': min(memory_values),
            'sample_count': len(recent_metrics),
            'time_range_minutes': minutes
        }

class ApplicationMetricsCollector:
    """アプリケーションメトリクス収集器"""
    
    def __init__(self):
        self.metrics = {
            'active_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls_count': 0,
            'api_calls_failed': 0,
            'database_queries': 0,
            'database_query_time': 0.0,
            'gc_collections': 0
        }
        self.lock = threading.Lock()
        
    def increment(self, metric_name: str, value: int = 1):
        """メトリクス増分"""
        with self.lock:
            if metric_name in self.metrics:
                self.metrics[metric_name] += value
    
    def set_value(self, metric_name: str, value: float):
        """メトリクス値設定"""
        with self.lock:
            self.metrics[metric_name] = value
    
    def get_current_metrics(self) -> ApplicationMetrics:
        """現在のメトリクス取得"""
        with self.lock:
            # メモリ使用量
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # GC統計
            gc_stats = gc.get_stats()
            total_collections = sum(stat['collections'] for stat in gc_stats)
            
            return ApplicationMetrics(
                timestamp=datetime.now(),
                memory_usage_mb=memory_mb,
                gc_collections=total_collections,
                **self.metrics.copy()
            )

class AlertManager:
    """アラート管理"""
    
    def __init__(self):
        self.thresholds = {
            'cpu_percent': {'warning': 70, 'critical': 90},
            'memory_percent': {'warning': 80, 'critical': 95},
            'disk_usage_percent': {'warning': 85, 'critical': 95},
            'active_tasks': {'warning': 100, 'critical': 200},
            'failed_tasks_rate': {'warning': 0.1, 'critical': 0.25}
        }
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_callbacks = []
        
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """アラートコールバック追加"""
        self.alert_callbacks.append(callback)
    
    def check_system_metrics(self, metrics: SystemMetrics):
        """システムメトリクスアラートチェック"""
        checks = [
            ('cpu_percent', metrics.cpu_percent),
            ('memory_percent', metrics.memory_percent),
            ('disk_usage_percent', metrics.disk_usage_percent)
        ]
        
        for metric_name, value in checks:
            self._check_threshold(metric_name, value, 'SYSTEM')
    
    def check_application_metrics(self, metrics: ApplicationMetrics):
        """アプリケーションメトリクスアラートチェック"""
        checks = [
            ('active_tasks', metrics.active_tasks)
        ]
        
        # 失敗率計算
        total_tasks = metrics.completed_tasks + metrics.failed_tasks
        if total_tasks > 0:
            failed_rate = metrics.failed_tasks / total_tasks
            checks.append(('failed_tasks_rate', failed_rate))
        
        for metric_name, value in checks:
            self._check_threshold(metric_name, value, 'APPLICATION')
    
    def _check_threshold(self, metric_name: str, value: float, category: str):
        """閾値チェック"""
        if metric_name not in self.thresholds:
            return
        
        thresholds = self.thresholds[metric_name]
        alert_key = f"{category}_{metric_name}"
        
        # 重要度判定
        severity = None
        threshold_value = None
        
        if value >= thresholds.get('critical', float('inf')):
            severity = 'CRITICAL'
            threshold_value = thresholds['critical']
        elif value >= thresholds.get('warning', float('inf')):
            severity = 'WARNING'
            threshold_value = thresholds['warning']
        
        if severity:
            # 新しいアラート
            if alert_key not in self.active_alerts:
                alert = PerformanceAlert(
                    alert_id=f"{alert_key}_{int(time.time())}",
                    timestamp=datetime.now(),
                    severity=severity,
                    category=category,
                    metric_name=metric_name,
                    current_value=value,
                    threshold_value=threshold_value,
                    message=f"{metric_name} is {value:.2f}, exceeding {severity.lower()} threshold of {threshold_value}"
                )
                
                self.active_alerts[alert_key] = alert
                self.alert_history.append(alert)
                self._trigger_alert(alert)
        else:
            # アラート解決
            if alert_key in self.active_alerts:
                alert = self.active_alerts[alert_key]
                alert.resolved = True
                alert.resolved_at = datetime.now()
                del self.active_alerts[alert_key]
                self._trigger_alert_resolved(alert)
    
    def _trigger_alert(self, alert: PerformanceAlert):
        """アラート発生"""
        logger.warning(f"Performance Alert: {alert.message}")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {str(e)}")
    
    def _trigger_alert_resolved(self, alert: PerformanceAlert):
        """アラート解決"""
        logger.info(f"Performance Alert Resolved: {alert.metric_name}")
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """アクティブアラート取得"""
        return list(self.active_alerts.values())

class PerformanceDataStore:
    """パフォーマンスデータストア"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベース初期化"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute('PRAGMA journal_mode = WAL')  # Enable WAL mode for better concurrency
            conn.execute('PRAGMA synchronous = NORMAL')  # Balance between safety and performance
            
            # システムメトリクステーブル
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_used_mb REAL,
                    memory_available_mb REAL,
                    disk_usage_percent REAL,
                    disk_free_gb REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    process_count INTEGER,
                    thread_count INTEGER
                )
            ''')
            
            # アプリケーションメトリクステーブル
            conn.execute('''
                CREATE TABLE IF NOT EXISTS app_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    active_tasks INTEGER,
                    completed_tasks INTEGER,
                    failed_tasks INTEGER,
                    cache_hits INTEGER,
                    cache_misses INTEGER,
                    api_calls_count INTEGER,
                    api_calls_failed INTEGER,
                    database_queries INTEGER,
                    database_query_time REAL,
                    memory_usage_mb REAL,
                    gc_collections INTEGER
                )
            ''')
            
            # アラートテーブル
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    current_value REAL,
                    threshold_value REAL,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TEXT
                )
            ''')
            
            # インデックス作成
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_app_timestamp ON app_metrics(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
            
            conn.commit()
            logger.debug("Database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def store_system_metrics(self, metrics: SystemMetrics):
        """システムメトリクス保存"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute('''
                INSERT INTO system_metrics (
                    timestamp, cpu_percent, memory_percent, memory_used_mb,
                    memory_available_mb, disk_usage_percent, disk_free_gb,
                    network_sent_mb, network_recv_mb, process_count, thread_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.memory_used_mb,
                metrics.memory_available_mb,
                metrics.disk_usage_percent,
                metrics.disk_free_gb,
                metrics.network_sent_mb,
                metrics.network_recv_mb,
                metrics.process_count,
                metrics.thread_count
            ))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing system metrics: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error storing system metrics: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def store_app_metrics(self, metrics: ApplicationMetrics):
        """アプリケーションメトリクス保存"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute('''
                INSERT INTO app_metrics (
                    timestamp, active_tasks, completed_tasks, failed_tasks,
                    cache_hits, cache_misses, api_calls_count, api_calls_failed,
                    database_queries, database_query_time, memory_usage_mb, gc_collections
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.active_tasks,
                metrics.completed_tasks,
                metrics.failed_tasks,
                metrics.cache_hits,
                metrics.cache_misses,
                metrics.api_calls_count,
                metrics.api_calls_failed,
                metrics.database_queries,
                metrics.database_query_time,
                metrics.memory_usage_mb,
                metrics.gc_collections
            ))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing app metrics: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error storing app metrics: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def store_alert(self, alert: PerformanceAlert):
        """アラート保存"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute('''
                INSERT OR REPLACE INTO alerts (
                    alert_id, timestamp, severity, category, metric_name,
                    current_value, threshold_value, message, resolved, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.timestamp.isoformat(),
                alert.severity,
                alert.category,
                alert.metric_name,
                alert.current_value,
                alert.threshold_value,
                alert.message,
                alert.resolved,
                alert.resolved_at.isoformat() if alert.resolved_at else None
            ))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing alert: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error storing alert: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def get_metrics_history(self, table: str, hours: int = 24) -> List[Dict]:
        """メトリクス履歴取得"""
        conn = None
        try:
            # Validate table name to prevent SQL injection
            allowed_tables = ['system_metrics', 'app_metrics', 'alerts']
            if table not in allowed_tables:
                logger.error(f"Invalid table name: {table}")
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f'''
                SELECT * FROM {table} 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            ''', (cutoff_time.isoformat(),))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting metrics history from {table}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting metrics history from {table}: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()

class PerformanceMonitor:
    """パフォーマンス監視メインクラス"""
    
    def __init__(self, 
                 db_path: str = "performance_metrics.db",
                 collection_interval: float = 30.0,
                 enable_alerts: bool = True):
        self.collection_interval = collection_interval
        self.enable_alerts = enable_alerts
        
        self.metrics_collector = MetricsCollector()
        self.app_metrics_collector = ApplicationMetricsCollector()
        self.alert_manager = AlertManager() if enable_alerts else None
        self.data_store = PerformanceDataStore(db_path)
        
        self.monitoring = False
        self.monitor_task = None
        
        # アラートコールバック設定
        if self.alert_manager:
            self.alert_manager.add_alert_callback(self._handle_alert)
    
    async def start_monitoring(self):
        """監視開始"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """監視停止"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """監視ループ"""
        while self.monitoring:
            try:
                # システムメトリクス収集
                system_metrics = self.metrics_collector.collect_system_metrics()
                if system_metrics:
                    self.data_store.store_system_metrics(system_metrics)
                    
                    if self.alert_manager:
                        self.alert_manager.check_system_metrics(system_metrics)
                
                # アプリケーションメトリクス収集
                app_metrics = self.app_metrics_collector.get_current_metrics()
                self.data_store.store_app_metrics(app_metrics)
                
                if self.alert_manager:
                    self.alert_manager.check_application_metrics(app_metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {str(e)}")
                await asyncio.sleep(self.collection_interval)
    
    def _handle_alert(self, alert: PerformanceAlert):
        """アラートハンドリング"""
        # データベースに保存
        self.data_store.store_alert(alert)
        
        # 必要に応じて追加のアクション（メール送信等）
        if alert.severity == 'CRITICAL':
            logger.critical(f"CRITICAL ALERT: {alert.message}")
    
    def get_app_metrics(self) -> ApplicationMetricsCollector:
        """アプリケーションメトリクス取得"""
        return self.app_metrics_collector
    
    def get_current_status(self) -> Dict[str, Any]:
        """現在のステータス取得"""
        system_summary = self.metrics_collector.get_system_metrics_summary()
        app_metrics = self.app_metrics_collector.get_current_metrics()
        
        status = {
            'monitoring_active': self.monitoring,
            'collection_interval': self.collection_interval,
            'system_summary': system_summary,
            'current_app_metrics': asdict(app_metrics),
            'timestamp': datetime.now().isoformat()
        }
        
        if self.alert_manager:
            active_alerts = self.alert_manager.get_active_alerts()
            status['active_alerts'] = [asdict(alert) for alert in active_alerts]
            status['alert_count'] = len(active_alerts)
        
        return status
    
    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """パフォーマンスレポート生成"""
        system_history = self.data_store.get_metrics_history('system_metrics', hours)
        app_history = self.data_store.get_metrics_history('app_metrics', hours)
        
        report = {
            'report_generated_at': datetime.now().isoformat(),
            'time_range_hours': hours,
            'system_metrics_count': len(system_history),
            'app_metrics_count': len(app_history)
        }
        
        # システムメトリクス統計
        if system_history:
            cpu_values = [m['cpu_percent'] for m in system_history if m['cpu_percent'] is not None]
            memory_values = [m['memory_percent'] for m in system_history if m['memory_percent'] is not None]
            
            if cpu_values:
                report['cpu_stats'] = {
                    'avg': statistics.mean(cpu_values),
                    'max': max(cpu_values),
                    'min': min(cpu_values),
                    'median': statistics.median(cpu_values)
                }
            
            if memory_values:
                report['memory_stats'] = {
                    'avg': statistics.mean(memory_values),
                    'max': max(memory_values),
                    'min': min(memory_values),
                    'median': statistics.median(memory_values)
                }
        
        # アプリケーションメトリクス統計
        if app_history:
            latest_app = app_history[0]  # 最新のメトリクス
            report['app_stats'] = {
                'total_completed_tasks': latest_app['completed_tasks'],
                'total_failed_tasks': latest_app['failed_tasks'],
                'success_rate': (
                    latest_app['completed_tasks'] / 
                    max(1, latest_app['completed_tasks'] + latest_app['failed_tasks'])
                ),
                'cache_hit_rate': (
                    latest_app['cache_hits'] / 
                    max(1, latest_app['cache_hits'] + latest_app['cache_misses'])
                ),
                'api_success_rate': (
                    (latest_app['api_calls_count'] - latest_app['api_calls_failed']) /
                    max(1, latest_app['api_calls_count'])
                )
            }
        
        return report

# パフォーマンス監視デコレータ
def monitor_performance(monitor: PerformanceMonitor = None):
    """パフォーマンス監視デコレータ"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            if monitor:
                app_metrics = monitor.get_app_metrics()
                app_metrics.increment('active_tasks')
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                if monitor:
                    app_metrics.increment('completed_tasks')
                return result
            except Exception as e:
                if monitor:
                    app_metrics.increment('failed_tasks')
                raise
            finally:
                if monitor:
                    app_metrics.increment('active_tasks', -1)
                    execution_time = time.time() - start_time
                    logger.debug(f"Function {func.__name__} executed in {execution_time:.3f}s")
        
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# グローバル監視インスタンス
_global_monitor = None

def get_performance_monitor(db_path: str = "performance_metrics.db") -> PerformanceMonitor:
    """グローバルパフォーマンス監視取得"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor(db_path)
    return _global_monitor