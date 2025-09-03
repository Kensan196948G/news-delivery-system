#!/usr/bin/env python3
"""
Advanced System Metrics Monitor
高度なシステムメトリクス監視モジュール
"""

import asyncio
import json
import logging
import os
import psutil
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Deque
import aiohttp
import sqlite3
import statistics

from ..utils.path_resolver import get_path_resolver
from ..utils.config import get_config
from ..utils.logger import setup_logger


class MetricsCollector:
    """メトリクス収集クラス"""
    
    def __init__(self):
        self.path_resolver = get_path_resolver()
        self.config = get_config()
        self.logger = setup_logger(__name__)
        
        # メトリクス収集設定
        self.collection_interval = 60  # 1分ごとに収集
        self.detailed_interval = 300  # 5分ごとに詳細収集
        
        # メトリクス履歴（時系列データ）
        self.metrics_buffer: Deque[Dict] = deque(maxlen=1440)  # 24時間分（1分間隔）
        self.detailed_buffer: Deque[Dict] = deque(maxlen=288)  # 24時間分（5分間隔）
        
        # パフォーマンスしきい値（動的調整）
        self.dynamic_thresholds = {
            'cpu_percent': {'base': 80.0, 'current': 80.0, 'min': 60.0, 'max': 95.0},
            'memory_percent': {'base': 85.0, 'current': 85.0, 'min': 70.0, 'max': 95.0},
            'disk_percent': {'base': 90.0, 'current': 90.0, 'min': 80.0, 'max': 95.0},
            'response_time': {'base': 5.0, 'current': 5.0, 'min': 2.0, 'max': 10.0},
            'error_rate': {'base': 0.1, 'current': 0.1, 'min': 0.05, 'max': 0.2},
        }
        
        # 異常検知用統計
        self.anomaly_detection = {
            'cpu': {'mean': 0, 'std': 0, 'samples': deque(maxlen=100)},
            'memory': {'mean': 0, 'std': 0, 'samples': deque(maxlen=100)},
            'disk_io': {'mean': 0, 'std': 0, 'samples': deque(maxlen=100)},
            'network': {'mean': 0, 'std': 0, 'samples': deque(maxlen=100)},
        }
        
        # プロセス固有メトリクス
        self.process_metrics = {
            'start_time': datetime.now(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_articles': 0,
            'total_translations': 0,
            'total_analyses': 0,
        }
        
        # アラート管理
        self.active_alerts = {}
        self.alert_history = deque(maxlen=100)
        
    async def start_monitoring(self):
        """高精度モニタリング開始"""
        self.logger.info("Starting advanced metrics monitoring")
        
        # 並行タスク起動
        tasks = [
            self._collect_basic_metrics(),
            self._collect_detailed_metrics(),
            self._analyze_trends(),
            self._detect_anomalies(),
        ]
        
        await asyncio.gather(*tasks)
    
    async def _collect_basic_metrics(self):
        """基本メトリクス収集（1分間隔）"""
        while True:
            try:
                metrics = await self._gather_system_metrics()
                self.metrics_buffer.append(metrics)
                
                # 動的しきい値調整
                self._adjust_thresholds(metrics)
                
                # 異常検知用サンプル追加
                self._update_anomaly_samples(metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Basic metrics collection error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_detailed_metrics(self):
        """詳細メトリクス収集（5分間隔）"""
        while True:
            try:
                await asyncio.sleep(self.detailed_interval)
                
                detailed = await self._gather_detailed_metrics()
                self.detailed_buffer.append(detailed)
                
                # レポート生成
                await self._generate_metrics_report(detailed)
                
            except Exception as e:
                self.logger.error(f"Detailed metrics collection error: {e}")
    
    async def _gather_system_metrics(self) -> Dict[str, Any]:
        """システムメトリクス収集"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'type': 'basic',
        }
        
        # CPU メトリクス
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        cpu_count = psutil.cpu_count()
        
        metrics['cpu'] = {
            'percent': cpu_percent,
            'frequency': cpu_freq.current if cpu_freq else 0,
            'cores': cpu_count,
            'per_core': psutil.cpu_percent(interval=0.1, percpu=True),
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
        }
        
        # メモリメトリクス
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        metrics['memory'] = {
            'percent': memory.percent,
            'used_gb': memory.used / (1024**3),
            'available_gb': memory.available / (1024**3),
            'total_gb': memory.total / (1024**3),
            'cached_gb': memory.cached / (1024**3) if hasattr(memory, 'cached') else 0,
            'swap_percent': swap.percent,
            'swap_used_gb': swap.used / (1024**3),
        }
        
        # ディスクメトリクス
        disk = psutil.disk_usage(str(self.path_resolver.data_root))
        disk_io = psutil.disk_io_counters()
        
        metrics['disk'] = {
            'percent': disk.percent,
            'used_gb': disk.used / (1024**3),
            'free_gb': disk.free / (1024**3),
            'total_gb': disk.total / (1024**3),
            'read_mb_s': 0,  # 後で計算
            'write_mb_s': 0,  # 後で計算
        }
        
        # ディスクI/O速度計算
        if hasattr(self, '_last_disk_io'):
            time_delta = time.time() - self._last_disk_io_time
            if time_delta > 0:
                read_delta = disk_io.read_bytes - self._last_disk_io.read_bytes
                write_delta = disk_io.write_bytes - self._last_disk_io.write_bytes
                metrics['disk']['read_mb_s'] = (read_delta / (1024**2)) / time_delta
                metrics['disk']['write_mb_s'] = (write_delta / (1024**2)) / time_delta
        
        self._last_disk_io = disk_io
        self._last_disk_io_time = time.time()
        
        # ネットワークメトリクス
        net_io = psutil.net_io_counters()
        
        metrics['network'] = {
            'bytes_sent_mb': net_io.bytes_sent / (1024**2),
            'bytes_recv_mb': net_io.bytes_recv / (1024**2),
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errors': net_io.errin + net_io.errout,
            'drops': net_io.dropin + net_io.dropout,
        }
        
        # ネットワーク速度計算
        if hasattr(self, '_last_net_io'):
            time_delta = time.time() - self._last_net_io_time
            if time_delta > 0:
                sent_delta = net_io.bytes_sent - self._last_net_io.bytes_sent
                recv_delta = net_io.bytes_recv - self._last_net_io.bytes_recv
                metrics['network']['send_mb_s'] = (sent_delta / (1024**2)) / time_delta
                metrics['network']['recv_mb_s'] = (recv_delta / (1024**2)) / time_delta
        else:
            metrics['network']['send_mb_s'] = 0
            metrics['network']['recv_mb_s'] = 0
        
        self._last_net_io = net_io
        self._last_net_io_time = time.time()
        
        # プロセス固有メトリクス
        current_process = psutil.Process()
        
        metrics['process'] = {
            'pid': current_process.pid,
            'cpu_percent': current_process.cpu_percent(),
            'memory_mb': current_process.memory_info().rss / (1024**2),
            'memory_percent': current_process.memory_percent(),
            'threads': current_process.num_threads(),
            'open_files': len(current_process.open_files()),
            'connections': len(current_process.connections()),
            'status': current_process.status(),
            'create_time': datetime.fromtimestamp(current_process.create_time()).isoformat(),
        }
        
        return metrics
    
    async def _gather_detailed_metrics(self) -> Dict[str, Any]:
        """詳細メトリクス収集"""
        detailed = await self._gather_system_metrics()
        detailed['type'] = 'detailed'
        
        # プロセスリスト（上位10プロセス）
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu': proc.info['cpu_percent'],
                    'memory': proc.info['memory_percent'],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # CPU使用率でソート
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        detailed['top_processes'] = processes[:10]
        
        # ディスク使用状況（全マウントポイント）
        disk_usage = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'percent': usage.percent,
                    'used_gb': usage.used / (1024**3),
                    'free_gb': usage.free / (1024**3),
                })
            except PermissionError:
                continue
        
        detailed['disk_partitions'] = disk_usage
        
        # データベースメトリクス
        detailed['database'] = await self._gather_database_metrics()
        
        # API使用状況
        detailed['api_usage'] = await self._gather_api_metrics()
        
        # キャッシュ状況
        detailed['cache'] = await self._gather_cache_metrics()
        
        return detailed
    
    async def _gather_database_metrics(self) -> Dict[str, Any]:
        """データベースメトリクス収集"""
        try:
            db_path = self.path_resolver.get_database_path()
            
            if not db_path.exists():
                return {'status': 'not_initialized'}
            
            # ファイルサイズ
            size_mb = db_path.stat().st_size / (1024**2)
            
            # データベース統計
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # テーブル統計
            cursor.execute("""
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=m.name) as index_count
                FROM sqlite_master m 
                WHERE type='table'
            """)
            tables = cursor.fetchall()
            
            table_stats = {}
            for table_name, index_count in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                table_stats[table_name] = {
                    'rows': row_count,
                    'indexes': index_count,
                }
            
            # ページ統計
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA freelist_count")
            freelist_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'status': 'healthy',
                'size_mb': size_mb,
                'tables': table_stats,
                'page_count': page_count,
                'page_size': page_size,
                'freelist_count': freelist_count,
                'fragmentation': (freelist_count / page_count * 100) if page_count > 0 else 0,
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def _gather_api_metrics(self) -> Dict[str, Any]:
        """API使用状況メトリクス"""
        api_metrics = {}
        
        # 各APIの使用状況を取得
        for api_name in ['newsapi', 'deepl', 'claude', 'gnews', 'nvd']:
            if self.config.is_service_enabled(api_name):
                # APIごとの統計（実際の実装では各コレクターから取得）
                api_metrics[api_name] = {
                    'enabled': True,
                    'requests_today': 0,  # 実装時は実際の値を取得
                    'rate_limit_remaining': 100,  # 実装時は実際の値を取得
                    'last_request': None,
                    'average_response_time': 0,
                }
        
        return api_metrics
    
    async def _gather_cache_metrics(self) -> Dict[str, Any]:
        """キャッシュメトリクス収集"""
        try:
            cache_dir = self.path_resolver.get_cache_path()
            
            # キャッシュディレクトリの統計
            total_size = 0
            file_count = 0
            oldest_file = None
            newest_file = None
            
            for path in cache_dir.rglob('*'):
                if path.is_file():
                    file_stat = path.stat()
                    total_size += file_stat.st_size
                    file_count += 1
                    
                    mtime = file_stat.st_mtime
                    if oldest_file is None or mtime < oldest_file[1]:
                        oldest_file = (path.name, mtime)
                    if newest_file is None or mtime > newest_file[1]:
                        newest_file = (path.name, mtime)
            
            return {
                'total_size_mb': total_size / (1024**2),
                'file_count': file_count,
                'oldest_file': oldest_file[0] if oldest_file else None,
                'oldest_time': datetime.fromtimestamp(oldest_file[1]).isoformat() if oldest_file else None,
                'newest_file': newest_file[0] if newest_file else None,
                'newest_time': datetime.fromtimestamp(newest_file[1]).isoformat() if newest_file else None,
                'average_file_size_kb': (total_size / file_count / 1024) if file_count > 0 else 0,
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _adjust_thresholds(self, metrics: Dict[str, Any]):
        """動的しきい値調整"""
        # CPU使用率の傾向に基づいて調整
        cpu_percent = metrics['cpu']['percent']
        cpu_threshold = self.dynamic_thresholds['cpu_percent']
        
        # 過去10サンプルの平均を計算
        recent_samples = list(self.metrics_buffer)[-10:]
        if len(recent_samples) >= 10:
            avg_cpu = statistics.mean([s['cpu']['percent'] for s in recent_samples])
            std_cpu = statistics.stdev([s['cpu']['percent'] for s in recent_samples])
            
            # 標準偏差に基づいてしきい値を調整
            new_threshold = avg_cpu + (2 * std_cpu)  # 平均 + 2標準偏差
            
            # 範囲内に収める
            new_threshold = max(cpu_threshold['min'], min(new_threshold, cpu_threshold['max']))
            cpu_threshold['current'] = new_threshold
        
        # メモリも同様に調整
        memory_percent = metrics['memory']['percent']
        memory_threshold = self.dynamic_thresholds['memory_percent']
        
        if len(recent_samples) >= 10:
            avg_memory = statistics.mean([s['memory']['percent'] for s in recent_samples])
            std_memory = statistics.stdev([s['memory']['percent'] for s in recent_samples])
            
            new_threshold = avg_memory + (2 * std_memory)
            new_threshold = max(memory_threshold['min'], min(new_threshold, memory_threshold['max']))
            memory_threshold['current'] = new_threshold
    
    def _update_anomaly_samples(self, metrics: Dict[str, Any]):
        """異常検知用サンプル更新"""
        # CPU異常検知
        cpu_sample = metrics['cpu']['percent']
        self.anomaly_detection['cpu']['samples'].append(cpu_sample)
        
        if len(self.anomaly_detection['cpu']['samples']) >= 20:
            samples = list(self.anomaly_detection['cpu']['samples'])
            self.anomaly_detection['cpu']['mean'] = statistics.mean(samples)
            self.anomaly_detection['cpu']['std'] = statistics.stdev(samples) if len(samples) > 1 else 0
        
        # メモリ異常検知
        memory_sample = metrics['memory']['percent']
        self.anomaly_detection['memory']['samples'].append(memory_sample)
        
        if len(self.anomaly_detection['memory']['samples']) >= 20:
            samples = list(self.anomaly_detection['memory']['samples'])
            self.anomaly_detection['memory']['mean'] = statistics.mean(samples)
            self.anomaly_detection['memory']['std'] = statistics.stdev(samples) if len(samples) > 1 else 0
        
        # ディスクI/O異常検知
        disk_io_sample = metrics['disk'].get('write_mb_s', 0) + metrics['disk'].get('read_mb_s', 0)
        self.anomaly_detection['disk_io']['samples'].append(disk_io_sample)
        
        # ネットワーク異常検知
        network_sample = metrics['network'].get('send_mb_s', 0) + metrics['network'].get('recv_mb_s', 0)
        self.anomaly_detection['network']['samples'].append(network_sample)
    
    async def _analyze_trends(self):
        """トレンド分析"""
        while True:
            try:
                await asyncio.sleep(600)  # 10分ごと
                
                if len(self.metrics_buffer) < 60:  # 最低1時間分のデータ
                    continue
                
                trends = self._calculate_trends()
                
                # トレンドに基づくアラート
                await self._check_trend_alerts(trends)
                
            except Exception as e:
                self.logger.error(f"Trend analysis error: {e}")
    
    def _calculate_trends(self) -> Dict[str, Any]:
        """トレンド計算"""
        recent_metrics = list(self.metrics_buffer)[-60:]  # 過去1時間
        
        trends = {}
        
        # CPU トレンド
        cpu_values = [m['cpu']['percent'] for m in recent_metrics]
        trends['cpu'] = {
            'current': cpu_values[-1],
            'avg_1h': statistics.mean(cpu_values),
            'max_1h': max(cpu_values),
            'min_1h': min(cpu_values),
            'trend': self._calculate_trend_direction(cpu_values),
        }
        
        # メモリトレンド
        memory_values = [m['memory']['percent'] for m in recent_metrics]
        trends['memory'] = {
            'current': memory_values[-1],
            'avg_1h': statistics.mean(memory_values),
            'max_1h': max(memory_values),
            'min_1h': min(memory_values),
            'trend': self._calculate_trend_direction(memory_values),
        }
        
        # ディスクトレンド
        disk_values = [m['disk']['percent'] for m in recent_metrics]
        trends['disk'] = {
            'current': disk_values[-1],
            'avg_1h': statistics.mean(disk_values),
            'growth_rate': self._calculate_growth_rate(disk_values),
            'estimated_full': self._estimate_disk_full_time(disk_values),
        }
        
        return trends
    
    def _calculate_trend_direction(self, values: List[float]) -> str:
        """トレンド方向計算"""
        if len(values) < 10:
            return 'stable'
        
        # 簡単な線形回帰
        n = len(values)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        # トレンド判定
        if slope > 0.5:
            return 'increasing'
        elif slope < -0.5:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_growth_rate(self, values: List[float]) -> float:
        """成長率計算"""
        if len(values) < 2:
            return 0.0
        
        # 時間あたりの増加率（%/hour）
        time_span_hours = len(values) / 60  # 分データを時間に変換
        growth = values[-1] - values[0]
        
        return growth / time_span_hours if time_span_hours > 0 else 0.0
    
    def _estimate_disk_full_time(self, values: List[float]) -> Optional[str]:
        """ディスク満杯予測"""
        growth_rate = self._calculate_growth_rate(values)
        
        if growth_rate <= 0:
            return None
        
        current_usage = values[-1]
        remaining = 100 - current_usage
        
        hours_until_full = remaining / growth_rate
        
        if hours_until_full > 720:  # 30日以上
            return None
        
        estimated_time = datetime.now() + timedelta(hours=hours_until_full)
        return estimated_time.isoformat()
    
    async def _detect_anomalies(self):
        """異常検知"""
        while True:
            try:
                await asyncio.sleep(60)  # 1分ごと
                
                if not self.metrics_buffer:
                    continue
                
                latest_metrics = self.metrics_buffer[-1]
                anomalies = []
                
                # CPU異常検知
                cpu_anomaly = self._detect_metric_anomaly('cpu', latest_metrics['cpu']['percent'])
                if cpu_anomaly:
                    anomalies.append(cpu_anomaly)
                
                # メモリ異常検知
                memory_anomaly = self._detect_metric_anomaly('memory', latest_metrics['memory']['percent'])
                if memory_anomaly:
                    anomalies.append(memory_anomaly)
                
                # 異常があればアラート
                if anomalies:
                    await self._raise_anomaly_alert(anomalies)
                
            except Exception as e:
                self.logger.error(f"Anomaly detection error: {e}")
    
    def _detect_metric_anomaly(self, metric_name: str, value: float) -> Optional[Dict]:
        """メトリクス異常検知"""
        detection = self.anomaly_detection.get(metric_name)
        
        if not detection or detection['std'] == 0:
            return None
        
        # Z-スコア計算
        z_score = abs((value - detection['mean']) / detection['std'])
        
        # 3シグマ以上で異常と判定
        if z_score > 3:
            return {
                'metric': metric_name,
                'value': value,
                'mean': detection['mean'],
                'std': detection['std'],
                'z_score': z_score,
                'severity': 'high' if z_score > 4 else 'medium',
            }
        
        return None
    
    async def _check_trend_alerts(self, trends: Dict):
        """トレンドベースのアラート確認"""
        alerts = []
        
        # CPU増加トレンド
        if trends['cpu']['trend'] == 'increasing' and trends['cpu']['current'] > 70:
            alerts.append({
                'type': 'trend',
                'metric': 'cpu',
                'message': f"CPU usage increasing: {trends['cpu']['avg_1h']:.1f}% avg",
                'severity': 'warning',
            })
        
        # メモリ増加トレンド
        if trends['memory']['trend'] == 'increasing' and trends['memory']['current'] > 75:
            alerts.append({
                'type': 'trend',
                'metric': 'memory',
                'message': f"Memory usage increasing: {trends['memory']['avg_1h']:.1f}% avg",
                'severity': 'warning',
            })
        
        # ディスク満杯予測
        if trends['disk']['estimated_full']:
            alerts.append({
                'type': 'prediction',
                'metric': 'disk',
                'message': f"Disk estimated full at: {trends['disk']['estimated_full']}",
                'severity': 'high',
            })
        
        # アラート処理
        for alert in alerts:
            await self._process_alert(alert)
    
    async def _raise_anomaly_alert(self, anomalies: List[Dict]):
        """異常アラート発生"""
        for anomaly in anomalies:
            alert = {
                'type': 'anomaly',
                'metric': anomaly['metric'],
                'message': f"Anomaly detected in {anomaly['metric']}: {anomaly['value']:.1f} (z-score: {anomaly['z_score']:.2f})",
                'severity': anomaly['severity'],
                'details': anomaly,
            }
            await self._process_alert(alert)
    
    async def _process_alert(self, alert: Dict):
        """アラート処理"""
        alert_key = f"{alert['type']}_{alert['metric']}"
        
        # 重複アラート防止
        if alert_key in self.active_alerts:
            last_alert_time = self.active_alerts[alert_key]
            if (datetime.now() - last_alert_time).total_seconds() < 3600:  # 1時間以内
                return
        
        # アラート記録
        alert['timestamp'] = datetime.now().isoformat()
        self.alert_history.append(alert)
        self.active_alerts[alert_key] = datetime.now()
        
        # ログ出力
        log_method = self.logger.error if alert['severity'] == 'high' else self.logger.warning
        log_method(f"Alert: {alert['message']}")
    
    async def _generate_metrics_report(self, detailed_metrics: Dict):
        """メトリクスレポート生成"""
        try:
            report_path = self.path_resolver.get_data_path(
                'monitoring/metrics',
                f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'summary': self._generate_summary(),
                'detailed_metrics': detailed_metrics,
                'trends': self._calculate_trends() if len(self.metrics_buffer) >= 60 else {},
                'alerts': list(self.alert_history)[-10:],  # 最新10件
                'thresholds': {
                    k: v['current'] for k, v in self.dynamic_thresholds.items()
                },
            }
            
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Metrics report generated: {report_path}")
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
    
    def _generate_summary(self) -> Dict:
        """サマリー生成"""
        if not self.metrics_buffer:
            return {}
        
        recent_metrics = list(self.metrics_buffer)[-60:]  # 過去1時間
        
        return {
            'period': '1 hour',
            'samples': len(recent_metrics),
            'cpu_avg': statistics.mean([m['cpu']['percent'] for m in recent_metrics]),
            'memory_avg': statistics.mean([m['memory']['percent'] for m in recent_metrics]),
            'disk_usage': recent_metrics[-1]['disk']['percent'],
            'active_alerts': len(self.active_alerts),
            'process_uptime': str(datetime.now() - self.process_metrics['start_time']),
        }
    
    def get_current_metrics(self) -> Dict:
        """現在のメトリクス取得"""
        if self.metrics_buffer:
            return self.metrics_buffer[-1]
        return {}
    
    def get_metrics_summary(self, hours: int = 1) -> Dict:
        """メトリクスサマリー取得"""
        samples_needed = hours * 60  # 1分間隔
        recent_metrics = list(self.metrics_buffer)[-samples_needed:]
        
        if not recent_metrics:
            return {'status': 'no_data'}
        
        return {
            'period_hours': hours,
            'samples': len(recent_metrics),
            'cpu': {
                'avg': statistics.mean([m['cpu']['percent'] for m in recent_metrics]),
                'max': max([m['cpu']['percent'] for m in recent_metrics]),
                'min': min([m['cpu']['percent'] for m in recent_metrics]),
            },
            'memory': {
                'avg': statistics.mean([m['memory']['percent'] for m in recent_metrics]),
                'max': max([m['memory']['percent'] for m in recent_metrics]),
                'min': min([m['memory']['percent'] for m in recent_metrics]),
            },
            'alerts': len([a for a in self.alert_history if 
                          (datetime.now() - datetime.fromisoformat(a['timestamp'])).total_seconds() < hours * 3600]),
        }


async def main():
    """メインエントリポイント"""
    collector = MetricsCollector()
    await collector.start_monitoring()


if __name__ == '__main__':
    asyncio.run(main())