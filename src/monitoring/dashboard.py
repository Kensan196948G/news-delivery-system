"""
リアルタイムモニタリングダッシュボード
WebSocketベースのリアルタイム更新、システムメトリクス可視化、アラート表示
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import logging
from collections import deque, defaultdict
import threading
import sqlite3

# WebSocketサーバー関連
import websockets
from websockets.server import serve
from websockets.exceptions import ConnectionClosed

# HTTP サーバー関連
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from urllib.parse import parse_qs, urlparse

# データ可視化
import json
import base64
from io import BytesIO
try:
    import matplotlib
    matplotlib.use('Agg')  # GUIバックエンドを無効化
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# システムメトリクス取得
import psutil
import platform
import socket
import subprocess

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """システムメトリクスデータ"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available: int
    disk_usage_percent: float
    disk_free: int
    network_sent: int
    network_recv: int
    process_count: int
    load_average: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class ApplicationMetrics:
    """アプリケーションメトリクスデータ"""
    timestamp: datetime
    active_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    error_rate: float
    avg_response_time: float
    api_calls_count: int
    cache_hit_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class AlertData:
    """アラートデータ"""
    id: str
    timestamp: datetime
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    category: str
    message: str
    details: Dict[str, Any]
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class MetricsCollector:
    """システムとアプリケーションメトリクスの収集"""
    
    def __init__(self):
        self.system_metrics_history = deque(maxlen=1000)
        self.app_metrics_history = deque(maxlen=1000)
        self.last_network_stats = None
        self.collection_interval = 5  # 5秒間隔
        
    async def collect_system_metrics(self) -> SystemMetrics:
        """システムメトリクスを収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free = disk.free
            
            # ネットワークI/O
            network = psutil.net_io_counters()
            network_sent = network.bytes_sent
            network_recv = network.bytes_recv
            
            # プロセス数
            process_count = len(psutil.pids())
            
            # ロードアベレージ（Linux/Unix系のみ）
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                # Windowsの場合は代替値
                load_average = [cpu_percent / 100, cpu_percent / 100, cpu_percent / 100]
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available=memory_available,
                disk_usage_percent=disk_usage_percent,
                disk_free=disk_free,
                network_sent=network_sent,
                network_recv=network_recv,
                process_count=process_count,
                load_average=load_average
            )
            
            self.system_metrics_history.append(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available=0,
                disk_usage_percent=0.0,
                disk_free=0,
                network_sent=0,
                network_recv=0,
                process_count=0,
                load_average=[0.0, 0.0, 0.0]
            )
    
    async def collect_application_metrics(self, db_path: str = None) -> ApplicationMetrics:
        """アプリケーションメトリクスを収集"""
        try:
            # データベースから統計を取得
            if db_path and Path(db_path).exists():
                stats = self._get_app_stats_from_db(db_path)
            else:
                # デフォルト値を使用
                stats = {
                    'active_agents': 0,
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'failed_tasks': 0,
                    'error_rate': 0.0,
                    'avg_response_time': 0.0,
                    'api_calls_count': 0,
                    'cache_hit_rate': 0.0
                }
            
            metrics = ApplicationMetrics(
                timestamp=datetime.now(),
                **stats
            )
            
            self.app_metrics_history.append(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return ApplicationMetrics(
                timestamp=datetime.now(),
                active_agents=0,
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                error_rate=0.0,
                avg_response_time=0.0,
                api_calls_count=0,
                cache_hit_rate=0.0
            )
    
    def _get_app_stats_from_db(self, db_path: str) -> Dict[str, Any]:
        """データベースからアプリケーション統計を取得"""
        try:
            with sqlite3.connect(db_path) as conn:
                # 過去1時間の統計
                one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                
                # エラー率の計算
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_logs,
                        SUM(CASE WHEN level IN ('ERROR', 'CRITICAL') THEN 1 ELSE 0 END) as error_logs
                    FROM logs 
                    WHERE timestamp >= ?
                """, (one_hour_ago,))
                
                result = cursor.fetchone()
                total_logs = result[0] if result else 0
                error_logs = result[1] if result else 0
                error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0.0
                
                # その他の統計（仮の値）
                return {
                    'active_agents': min(4, max(1, total_logs // 100)),  # 推定値
                    'total_tasks': total_logs,
                    'completed_tasks': total_logs - error_logs,
                    'failed_tasks': error_logs,
                    'error_rate': error_rate,
                    'avg_response_time': 250.0,  # デフォルト値
                    'api_calls_count': total_logs // 2,  # 推定値
                    'cache_hit_rate': 75.0  # デフォルト値
                }
                
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return {
                'active_agents': 0,
                'total_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'error_rate': 0.0,
                'avg_response_time': 0.0,
                'api_calls_count': 0,
                'cache_hit_rate': 0.0
            }
    
    def get_metrics_history(self, minutes: int = 60) -> Dict[str, List[Dict]]:
        """過去N分間のメトリクス履歴を取得"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        system_history = [
            metrics.to_dict() for metrics in self.system_metrics_history
            if metrics.timestamp >= cutoff_time
        ]
        
        app_history = [
            metrics.to_dict() for metrics in self.app_metrics_history
            if metrics.timestamp >= cutoff_time
        ]
        
        return {
            'system_metrics': system_history,
            'application_metrics': app_history
        }

class ChartGenerator:
    """グラフ生成クラス"""
    
    def __init__(self):
        if not PLOTTING_AVAILABLE:
            logger.warning("matplotlib not available, charts will be disabled")
        
        if PLOTTING_AVAILABLE:
            plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
    
    def generate_system_metrics_chart(self, metrics_history: List[Dict]) -> Optional[str]:
        """システムメトリクスのチャートを生成してBase64エンコードした画像を返す"""
        if not PLOTTING_AVAILABLE or not metrics_history:
            return None
        
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle('System Metrics', fontsize=16)
            
            timestamps = [datetime.fromisoformat(m['timestamp']) for m in metrics_history]
            
            # CPU使用率
            cpu_data = [m['cpu_percent'] for m in metrics_history]
            ax1.plot(timestamps, cpu_data, 'b-', linewidth=2)
            ax1.set_title('CPU Usage (%)')
            ax1.set_ylabel('Percentage')
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            # メモリ使用率
            memory_data = [m['memory_percent'] for m in metrics_history]
            ax2.plot(timestamps, memory_data, 'r-', linewidth=2)
            ax2.set_title('Memory Usage (%)')
            ax2.set_ylabel('Percentage')
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            # ディスク使用率
            disk_data = [m['disk_usage_percent'] for m in metrics_history]
            ax3.plot(timestamps, disk_data, 'g-', linewidth=2)
            ax3.set_title('Disk Usage (%)')
            ax3.set_ylabel('Percentage')
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            # ネットワークI/O（送信）
            network_sent_data = [m['network_sent'] / (1024*1024) for m in metrics_history]  # MB
            ax4.plot(timestamps, network_sent_data, 'orange', linewidth=2)
            ax4.set_title('Network Sent (MB)')
            ax4.set_ylabel('Megabytes')
            ax4.grid(True, alpha=0.3)
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            plt.tight_layout()
            
            # Base64エンコード
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error generating system metrics chart: {e}")
            return None
    
    def generate_application_metrics_chart(self, metrics_history: List[Dict]) -> Optional[str]:
        """アプリケーションメトリクスのチャートを生成"""
        if not PLOTTING_AVAILABLE or not metrics_history:
            return None
        
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle('Application Metrics', fontsize=16)
            
            timestamps = [datetime.fromisoformat(m['timestamp']) for m in metrics_history]
            
            # エラー率
            error_rate_data = [m['error_rate'] for m in metrics_history]
            ax1.plot(timestamps, error_rate_data, 'r-', linewidth=2)
            ax1.set_title('Error Rate (%)')
            ax1.set_ylabel('Percentage')
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            # アクティブエージェント数
            active_agents_data = [m['active_agents'] for m in metrics_history]
            ax2.plot(timestamps, active_agents_data, 'b-', linewidth=2, marker='o')
            ax2.set_title('Active Agents')
            ax2.set_ylabel('Count')
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            # 平均レスポンス時間
            response_time_data = [m['avg_response_time'] for m in metrics_history]
            ax3.plot(timestamps, response_time_data, 'g-', linewidth=2)
            ax3.set_title('Average Response Time (ms)')
            ax3.set_ylabel('Milliseconds')
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            # キャッシュヒット率
            cache_hit_data = [m['cache_hit_rate'] for m in metrics_history]
            ax4.plot(timestamps, cache_hit_data, 'purple', linewidth=2)
            ax4.set_title('Cache Hit Rate (%)')
            ax4.set_ylabel('Percentage')
            ax4.grid(True, alpha=0.3)
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            
            plt.tight_layout()
            
            # Base64エンコード
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error generating application metrics chart: {e}")
            return None

class AlertManager:
    """アラート管理クラス"""
    
    def __init__(self, db_path: str = "alerts.db"):
        self.db_path = db_path
        self.active_alerts: Dict[str, AlertData] = {}
        self.alert_history = deque(maxlen=1000)
        self._init_database()
    
    def _init_database(self):
        """アラート用データベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    severity TEXT,
                    category TEXT,
                    message TEXT,
                    details TEXT,
                    acknowledged INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def create_alert(
        self,
        severity: str,
        category: str,
        message: str,
        details: Dict[str, Any] = None
    ) -> AlertData:
        """新しいアラートを作成"""
        alert_id = f"{category}_{int(time.time() * 1000)}"
        
        alert = AlertData(
            id=alert_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=message,
            details=details or {},
            acknowledged=False
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # データベースに保存
        self._save_alert(alert)
        
        logger.info(f"Alert created: [{severity}] {category} - {message}")
        return alert
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """アラートを確認済みにする"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            
            # データベースを更新
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE alerts SET acknowledged = 1 WHERE id = ?",
                    (alert_id,)
                )
            
            logger.info(f"Alert acknowledged: {alert_id}")
            return True
        
        return False
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """アラートを削除"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            logger.info(f"Alert dismissed: {alert_id}")
            return True
        
        return False
    
    def get_active_alerts(self, severity_filter: Optional[str] = None) -> List[AlertData]:
        """アクティブなアラートを取得"""
        alerts = list(self.active_alerts.values())
        
        if severity_filter:
            alerts = [alert for alert in alerts if alert.severity == severity_filter]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def _save_alert(self, alert: AlertData):
        """アラートをデータベースに保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alerts 
                (id, timestamp, severity, category, message, details, acknowledged) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id,
                alert.timestamp.isoformat(),
                alert.severity,
                alert.category,
                alert.message,
                json.dumps(alert.details),
                int(alert.acknowledged)
            ))

class WebSocketServer:
    """WebSocketサーバー"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.metrics_collector = MetricsCollector()
        self.chart_generator = ChartGenerator()
        self.alert_manager = AlertManager()
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """新しいクライアントを登録"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        
        # 初期データを送信
        await self.send_initial_data(websocket)
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """クライアントの登録を解除"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected: {websocket.remote_address}")
    
    async def send_initial_data(self, websocket: websockets.WebSocketServerProtocol):
        """初期データをクライアントに送信"""
        try:
            # システムメトリクス
            system_metrics = await self.metrics_collector.collect_system_metrics()
            app_metrics = await self.metrics_collector.collect_application_metrics()
            
            # メトリクス履歴
            history = self.metrics_collector.get_metrics_history(60)
            
            # アクティブアラート
            active_alerts = self.alert_manager.get_active_alerts()
            
            initial_data = {
                'type': 'initial_data',
                'data': {
                    'current_system_metrics': system_metrics.to_dict(),
                    'current_app_metrics': app_metrics.to_dict(),
                    'metrics_history': history,
                    'active_alerts': [alert.to_dict() for alert in active_alerts],
                    'system_info': self._get_system_info()
                }
            }
            
            await websocket.send(json.dumps(initial_data))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def broadcast_metrics_update(self):
        """すべてのクライアントにメトリクス更新を送信"""
        if not self.clients:
            return
        
        try:
            # メトリクス収集
            system_metrics = await self.metrics_collector.collect_system_metrics()
            app_metrics = await self.metrics_collector.collect_application_metrics()
            
            # チャート生成
            history = self.metrics_collector.get_metrics_history(60)
            system_chart = self.chart_generator.generate_system_metrics_chart(
                history['system_metrics']
            )
            app_chart = self.chart_generator.generate_application_metrics_chart(
                history['application_metrics']
            )
            
            update_data = {
                'type': 'metrics_update',
                'data': {
                    'system_metrics': system_metrics.to_dict(),
                    'app_metrics': app_metrics.to_dict(),
                    'system_chart': system_chart,
                    'app_chart': app_chart,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # 接続が切れたクライアントを特定するためのリスト
            disconnected_clients = []
            
            # すべてのクライアントに送信
            for client in self.clients.copy():
                try:
                    await client.send(json.dumps(update_data))
                except ConnectionClosed:
                    disconnected_clients.append(client)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    disconnected_clients.append(client)
            
            # 切断されたクライアントを削除
            for client in disconnected_clients:
                self.clients.discard(client)
                
        except Exception as e:
            logger.error(f"Error broadcasting metrics: {e}")
    
    async def broadcast_alert(self, alert: AlertData):
        """アラートをすべてのクライアントに送信"""
        if not self.clients:
            return
        
        alert_data = {
            'type': 'new_alert',
            'data': alert.to_dict()
        }
        
        disconnected_clients = []
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(alert_data))
            except ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                logger.error(f"Error sending alert to client: {e}")
                disconnected_clients.append(client)
        
        for client in disconnected_clients:
            self.clients.discard(client)
    
    async def handle_client_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        """クライアントからのメッセージを処理"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'acknowledge_alert':
                alert_id = data.get('alert_id')
                if alert_id:
                    success = self.alert_manager.acknowledge_alert(alert_id)
                    response = {
                        'type': 'alert_acknowledged',
                        'success': success,
                        'alert_id': alert_id
                    }
                    await websocket.send(json.dumps(response))
            
            elif action == 'dismiss_alert':
                alert_id = data.get('alert_id')
                if alert_id:
                    success = self.alert_manager.dismiss_alert(alert_id)
                    response = {
                        'type': 'alert_dismissed',
                        'success': success,
                        'alert_id': alert_id
                    }
                    await websocket.send(json.dumps(response))
            
            elif action == 'get_history':
                minutes = data.get('minutes', 60)
                history = self.metrics_collector.get_metrics_history(minutes)
                response = {
                    'type': 'history_data',
                    'data': history
                }
                await websocket.send(json.dumps(response))
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
    
    def _get_system_info(self) -> Dict[str, Any]:
        """システム情報を取得"""
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'hostname': socket.gethostname(),
            'cpu_count': psutil.cpu_count(),
            'total_memory': psutil.virtual_memory().total,
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
    
    async def websocket_handler(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """WebSocketコネクションハンドラー"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_metrics_loop(self):
        """メトリクス収集・配信ループを開始"""
        logger.info("Starting metrics collection loop")
        
        while True:
            try:
                await self.broadcast_metrics_update()
                await asyncio.sleep(5)  # 5秒間隔で更新
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(10)  # エラー時は10秒待機
    
    async def start(self):
        """WebSocketサーバーを開始"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        # メトリクスループを並行実行
        metrics_task = asyncio.create_task(self.start_metrics_loop())
        
        # WebSocketサーバーを開始
        async with serve(self.websocket_handler, self.host, self.port):
            logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")
            await metrics_task  # メトリクスループを実行

class HTTPStaticServer:
    """静的ファイル配信用HTTPサーバー"""
    
    def __init__(self, host: str = "localhost", port: int = 8080, static_dir: str = "static"):
        self.host = host
        self.port = port
        self.static_dir = Path(static_dir)
        
        # 静的ディレクトリが存在しない場合は作成
        self.static_dir.mkdir(exist_ok=True)
        
        # デフォルトのHTMLファイルを作成
        self._create_default_dashboard()
    
    def _create_default_dashboard(self):
        """デフォルトのダッシュボードHTMLを作成"""
        html_content = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-time Monitoring Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .header h1 {
            color: white;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4CAF50;
            margin-left: 10px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            color: white;
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        .metric-title {
            font-size: 1.1rem;
            margin-bottom: 15px;
            color: #E8EAF6;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .metric-unit {
            font-size: 1rem;
            opacity: 0.8;
        }
        
        .charts-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .chart-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        
        .chart-title {
            color: white;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }
        
        .chart-placeholder {
            width: 100%;
            height: 300px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .chart-image {
            max-width: 100%;
            height: auto;
            border-radius: 10px;
        }
        
        .alerts-container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
        }
        
        .alerts-title {
            color: white;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }
        
        .alert-item {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid;
        }
        
        .alert-critical { border-color: #f44336; }
        .alert-high { border-color: #ff9800; }
        .alert-medium { border-color: #ffeb3b; }
        .alert-low { border-color: #4caf50; }
        
        .alert-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .alert-severity {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .alert-message {
            color: white;
        }
        
        .alert-time {
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.9rem;
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 15px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
        }
        
        .connected { background: #4CAF50; }
        .disconnected { background: #f44336; }
        
        @media (max-width: 768px) {
            .charts-container {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 1.8rem;
            }
        }
    </style>
</head>
<body>
    <div class="connection-status disconnected" id="connectionStatus">
        接続中...
    </div>
    
    <div class="dashboard">
        <div class="header">
            <h1>リアルタイム監視ダッシュボード<span class="status-indicator"></span></h1>
            <p>システムメトリクスとアラートをリアルタイムで監視</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">CPU使用率</div>
                <div class="metric-value" id="cpuUsage">0</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">メモリ使用率</div>
                <div class="metric-value" id="memoryUsage">0</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">ディスク使用率</div>
                <div class="metric-value" id="diskUsage">0</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">アクティブエージェント</div>
                <div class="metric-value" id="activeAgents">0</div>
                <div class="metric-unit">台</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">エラー率</div>
                <div class="metric-value" id="errorRate">0</div>
                <div class="metric-unit">%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">平均レスポンス時間</div>
                <div class="metric-value" id="avgResponseTime">0</div>
                <div class="metric-unit">ms</div>
            </div>
        </div>
        
        <div class="charts-container">
            <div class="chart-card">
                <div class="chart-title">システムメトリクス</div>
                <div class="chart-placeholder" id="systemChart">
                    データを読み込み中...
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">アプリケーションメトリクス</div>
                <div class="chart-placeholder" id="appChart">
                    データを読み込み中...
                </div>
            </div>
        </div>
        
        <div class="alerts-container">
            <div class="alerts-title">アクティブアラート</div>
            <div id="alertsList">
                <p style="color: rgba(255, 255, 255, 0.7);">アラートはありません</p>
            </div>
        </div>
    </div>
    
    <script>
        class DashboardClient {
            constructor() {
                this.ws = null;
                this.reconnectInterval = 5000;
                this.maxReconnectAttempts = 10;
                this.reconnectAttempts = 0;
                
                this.connect();
            }
            
            connect() {
                try {
                    this.ws = new WebSocket('ws://localhost:8765');
                    
                    this.ws.onopen = () => {
                        console.log('WebSocket connected');
                        this.updateConnectionStatus(true);
                        this.reconnectAttempts = 0;
                    };
                    
                    this.ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    };
                    
                    this.ws.onclose = () => {
                        console.log('WebSocket disconnected');
                        this.updateConnectionStatus(false);
                        this.scheduleReconnect();
                    };
                    
                    this.ws.onerror = (error) => {
                        console.error('WebSocket error:', error);
                        this.updateConnectionStatus(false);
                    };
                    
                } catch (error) {
                    console.error('Connection error:', error);
                    this.updateConnectionStatus(false);
                    this.scheduleReconnect();
                }
            }
            
            scheduleReconnect() {
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    setTimeout(() => {
                        console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                        this.connect();
                    }, this.reconnectInterval);
                }
            }
            
            updateConnectionStatus(connected) {
                const statusElement = document.getElementById('connectionStatus');
                if (connected) {
                    statusElement.textContent = '接続済み';
                    statusElement.className = 'connection-status connected';
                } else {
                    statusElement.textContent = '切断';
                    statusElement.className = 'connection-status disconnected';
                }
            }
            
            handleMessage(data) {
                switch (data.type) {
                    case 'initial_data':
                        this.updateInitialData(data.data);
                        break;
                    case 'metrics_update':
                        this.updateMetrics(data.data);
                        break;
                    case 'new_alert':
                        this.addAlert(data.data);
                        break;
                    default:
                        console.log('Unknown message type:', data.type);
                }
            }
            
            updateInitialData(data) {
                if (data.current_system_metrics) {
                    this.updateSystemMetrics(data.current_system_metrics);
                }
                
                if (data.current_app_metrics) {
                    this.updateAppMetrics(data.current_app_metrics);
                }
                
                if (data.active_alerts) {
                    this.updateAlerts(data.active_alerts);
                }
            }
            
            updateMetrics(data) {
                if (data.system_metrics) {
                    this.updateSystemMetrics(data.system_metrics);
                }
                
                if (data.app_metrics) {
                    this.updateAppMetrics(data.app_metrics);
                }
                
                if (data.system_chart) {
                    this.updateChart('systemChart', data.system_chart);
                }
                
                if (data.app_chart) {
                    this.updateChart('appChart', data.app_chart);
                }
            }
            
            updateSystemMetrics(metrics) {
                document.getElementById('cpuUsage').textContent = metrics.cpu_percent.toFixed(1);
                document.getElementById('memoryUsage').textContent = metrics.memory_percent.toFixed(1);
                document.getElementById('diskUsage').textContent = metrics.disk_usage_percent.toFixed(1);
            }
            
            updateAppMetrics(metrics) {
                document.getElementById('activeAgents').textContent = metrics.active_agents;
                document.getElementById('errorRate').textContent = metrics.error_rate.toFixed(2);
                document.getElementById('avgResponseTime').textContent = metrics.avg_response_time.toFixed(0);
            }
            
            updateChart(elementId, chartData) {
                const element = document.getElementById(elementId);
                if (chartData) {
                    element.innerHTML = `<img class="chart-image" src="data:image/png;base64,${chartData}" alt="Chart">`;
                } else {
                    element.innerHTML = 'チャート生成中...';
                }
            }
            
            updateAlerts(alerts) {
                const alertsList = document.getElementById('alertsList');
                
                if (alerts.length === 0) {
                    alertsList.innerHTML = '<p style="color: rgba(255, 255, 255, 0.7);">アラートはありません</p>';
                    return;
                }
                
                alertsList.innerHTML = alerts.map(alert => this.createAlertHtml(alert)).join('');
            }
            
            addAlert(alert) {
                const alertsList = document.getElementById('alertsList');
                const alertHtml = this.createAlertHtml(alert);
                
                if (alertsList.querySelector('p')) {
                    alertsList.innerHTML = '';
                }
                
                alertsList.insertAdjacentHTML('afterbegin', alertHtml);
            }
            
            createAlertHtml(alert) {
                const severityClass = `alert-${alert.severity.toLowerCase()}`;
                const time = new Date(alert.timestamp).toLocaleString('ja-JP');
                
                return `
                    <div class="alert-item ${severityClass}">
                        <div class="alert-header">
                            <span class="alert-severity">${alert.severity}</span>
                            <span class="alert-time">${time}</span>
                        </div>
                        <div class="alert-message">${alert.message}</div>
                    </div>
                `;
            }
        }
        
        // ダッシュボードクライアントを初期化
        document.addEventListener('DOMContentLoaded', () => {
            new DashboardClient();
        });
    </script>
</body>
</html>'''
        
        dashboard_path = self.static_dir / "index.html"
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Created dashboard at: {dashboard_path}")
    
    def start(self):
        """HTTPサーバーを開始"""
        import os
        os.chdir(self.static_dir)
        
        class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                super().end_headers()
        
        with socketserver.TCPServer((self.host, self.port), CustomHTTPRequestHandler) as httpd:
            logger.info(f"HTTP server running on http://{self.host}:{self.port}")
            httpd.serve_forever()

class DashboardManager:
    """ダッシュボード統合管理クラス"""
    
    def __init__(
        self,
        websocket_host: str = "localhost",
        websocket_port: int = 8765,
        http_host: str = "localhost",
        http_port: int = 8080,
        static_dir: str = "static"
    ):
        self.websocket_server = WebSocketServer(websocket_host, websocket_port)
        self.http_server = HTTPStaticServer(http_host, http_port, static_dir)
        
    async def start(self):
        """ダッシュボードシステム全体を開始"""
        logger.info("Starting dashboard system")
        
        # HTTPサーバーを別スレッドで開始
        http_thread = threading.Thread(target=self.http_server.start, daemon=True)
        http_thread.start()
        
        # WebSocketサーバーを開始（メインスレッド）
        await self.websocket_server.start()

# デモとテスト用の関数
async def demo_dashboard():
    """ダッシュボードのデモ実行"""
    dashboard = DashboardManager()
    
    # アラート生成デモ用のタスク
    async def generate_demo_alerts():
        await asyncio.sleep(10)  # 10秒後に開始
        
        while True:
            # サンプルアラートを作成
            alerts = [
                ("HIGH", "System", "CPU使用率が90%を超えました", {"cpu_usage": 92.5}),
                ("MEDIUM", "Application", "エラー率が増加しています", {"error_rate": 5.2}),
                ("LOW", "Network", "ネットワーク遅延が検出されました", {"latency": 250}),
            ]
            
            import random
            severity, category, message, details = random.choice(alerts)
            alert = dashboard.websocket_server.alert_manager.create_alert(
                severity, category, message, details
            )
            
            await dashboard.websocket_server.broadcast_alert(alert)
            await asyncio.sleep(30)  # 30秒間隔でアラートを生成
    
    # デモアラート生成タスクを並行実行
    alert_task = asyncio.create_task(generate_demo_alerts())
    
    try:
        await dashboard.start()
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
        alert_task.cancel()

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    )
    
    # デモ実行
    print("Starting Real-time Monitoring Dashboard...")
    print("Web Interface: http://localhost:8080")
    print("WebSocket Endpoint: ws://localhost:8765")
    print("Press Ctrl+C to stop")
    
    asyncio.run(demo_dashboard())