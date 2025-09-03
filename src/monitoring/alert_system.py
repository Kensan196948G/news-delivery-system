"""
インテリジェントアラートシステム
動的閾値調整、異常パターン学習、自動エスカレーション、通知チャネル統合
"""
import asyncio
import smtplib
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import sqlite3
import logging
import threading
import time
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle
import os

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """アラート重要度"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(Enum):
    """アラート状態"""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"

class NotificationChannel(Enum):
    """通知チャネル"""
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"
    SMS = "SMS"
    DESKTOP = "DESKTOP"

@dataclass
class ThresholdConfig:
    """動的閾値設定"""
    metric_name: str
    base_threshold: float
    adaptive_factor: float = 1.2  # 適応係数
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    window_size: int = 100  # 履歴ウィンドウサイズ
    std_multiplier: float = 2.0  # 標準偏差の倍数
    trend_sensitivity: float = 0.1  # トレンド感度

@dataclass
class AlertRule:
    """アラートルール"""
    rule_id: str
    name: str
    description: str
    condition: str  # Python式として評価
    severity: AlertSeverity
    threshold_config: Optional[ThresholdConfig] = None
    suppression_window: int = 300  # 抑制ウィンドウ（秒）
    escalation_rules: List[Dict[str, Any]] = field(default_factory=list)
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['severity'] = self.severity.value
        data['notification_channels'] = [ch.value for ch in self.notification_channels]
        return data

@dataclass
class Alert:
    """アラートインスタンス"""
    id: str
    rule_id: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalation_level: int = 0
    notification_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data

class DynamicThresholdManager:
    """動的閾値管理システム"""
    
    def __init__(self, db_path: str = "thresholds.db"):
        self.db_path = db_path
        self.thresholds: Dict[str, ThresholdConfig] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.models: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.last_update: Dict[str, datetime] = {}
        
        self._init_database()
        self._load_thresholds()
    
    def _init_database(self):
        """閾値管理用データベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thresholds (
                    metric_name TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    current_threshold REAL,
                    last_updated TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS threshold_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    threshold_value REAL,
                    calculated_at TEXT,
                    reason TEXT
                )
            """)
    
    def register_threshold(self, config: ThresholdConfig):
        """新しい動的閾値を登録"""
        self.thresholds[config.metric_name] = config
        
        # データベースに保存
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO thresholds 
                (metric_name, config, current_threshold, last_updated) 
                VALUES (?, ?, ?, ?)
            """, (
                config.metric_name,
                json.dumps(asdict(config)),
                config.base_threshold,
                datetime.now().isoformat()
            ))
        
        logger.info(f"Registered dynamic threshold for {config.metric_name}")
    
    def add_metric_value(self, metric_name: str, value: float, timestamp: datetime = None):
        """メトリクス値を追加して閾値を更新"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # 履歴に追加
        self.metrics_history[metric_name].append({
            'value': value,
            'timestamp': timestamp
        })
        
        # 閾値を更新（一定間隔で）
        last_update = self.last_update.get(metric_name, datetime.min)
        if timestamp - last_update > timedelta(minutes=5):
            self._update_threshold(metric_name)
            self.last_update[metric_name] = timestamp
    
    def _update_threshold(self, metric_name: str):
        """指定メトリクスの動的閾値を更新"""
        if metric_name not in self.thresholds:
            return
        
        config = self.thresholds[metric_name]
        history = list(self.metrics_history[metric_name])
        
        if len(history) < 10:  # 最小データ数
            return
        
        values = [item['value'] for item in history]
        
        # 統計的閾値計算
        mean = np.mean(values)
        std = np.std(values)
        statistical_threshold = mean + (config.std_multiplier * std)
        
        # トレンド分析
        trend_threshold = self._calculate_trend_based_threshold(values, config)
        
        # 機械学習による異常検知
        ml_threshold = self._calculate_ml_based_threshold(metric_name, values)
        
        # 最終閾値を決定（複数手法の統合）
        candidates = [statistical_threshold, trend_threshold, ml_threshold]
        candidates = [t for t in candidates if t is not None]
        
        if candidates:
            new_threshold = np.median(candidates)  # 中央値を使用
            
            # 適応係数を適用
            adaptive_threshold = config.base_threshold * config.adaptive_factor
            new_threshold = min(new_threshold, adaptive_threshold)
            
            # 最小・最大値の制限
            if config.min_threshold is not None:
                new_threshold = max(new_threshold, config.min_threshold)
            if config.max_threshold is not None:
                new_threshold = min(new_threshold, config.max_threshold)
            
            # 閾値を更新
            old_threshold = config.base_threshold
            config.base_threshold = new_threshold
            
            # データベースに記録
            self._save_threshold_update(metric_name, new_threshold, f"Updated from {old_threshold:.2f}")
            
            logger.info(f"Updated threshold for {metric_name}: {old_threshold:.2f} -> {new_threshold:.2f}")
    
    def _calculate_trend_based_threshold(self, values: List[float], config: ThresholdConfig) -> Optional[float]:
        """トレンドベースの閾値を計算"""
        if len(values) < 20:
            return None
        
        try:
            # 線形回帰でトレンドを計算
            x = np.arange(len(values))
            y = np.array(values)
            
            coeffs = np.polyfit(x, y, 1)
            trend_slope = coeffs[0]
            
            # トレンドが上昇している場合は閾値を上げる
            if trend_slope > config.trend_sensitivity:
                trend_factor = 1 + (trend_slope * 0.1)
                return config.base_threshold * trend_factor
            elif trend_slope < -config.trend_sensitivity:
                trend_factor = 1 - (abs(trend_slope) * 0.05)
                return config.base_threshold * trend_factor
            
            return config.base_threshold
            
        except Exception as e:
            logger.warning(f"Trend calculation failed: {e}")
            return None
    
    def _calculate_ml_based_threshold(self, metric_name: str, values: List[float]) -> Optional[float]:
        """機械学習ベースの閾値を計算"""
        if len(values) < 50:
            return None
        
        try:
            # モデルが存在しない場合は作成
            if metric_name not in self.models:
                self.models[metric_name] = IsolationForest(contamination=0.1, random_state=42)
                self.scalers[metric_name] = StandardScaler()
            
            model = self.models[metric_name]
            scaler = self.scalers[metric_name]
            
            # データの前処理
            reshaped_values = np.array(values).reshape(-1, 1)
            scaled_values = scaler.fit_transform(reshaped_values)
            
            # モデルの訓練
            model.fit(scaled_values)
            
            # 異常スコアを計算
            anomaly_scores = model.decision_function(scaled_values)
            
            # 下位10%の異常スコアを閾値として使用
            threshold_score = np.percentile(anomaly_scores, 10)
            
            # 元のスケールに戻して閾値を計算
            test_values = np.linspace(min(values), max(values) * 2, 1000).reshape(-1, 1)
            scaled_test = scaler.transform(test_values)
            test_scores = model.decision_function(scaled_test)
            
            # 閾値スコア以下の値の中で最大値を取得
            valid_indices = test_scores <= threshold_score
            if np.any(valid_indices):
                ml_threshold = np.max(test_values[valid_indices])
                return float(ml_threshold)
            
            return None
            
        except Exception as e:
            logger.warning(f"ML threshold calculation failed: {e}")
            return None
    
    def _save_threshold_update(self, metric_name: str, threshold: float, reason: str):
        """閾値更新をデータベースに記録"""
        with sqlite3.connect(self.db_path) as conn:
            # 現在の閾値を更新
            conn.execute("""
                UPDATE thresholds 
                SET current_threshold = ?, last_updated = ? 
                WHERE metric_name = ?
            """, (threshold, datetime.now().isoformat(), metric_name))
            
            # 履歴に追加
            conn.execute("""
                INSERT INTO threshold_history 
                (metric_name, threshold_value, calculated_at, reason) 
                VALUES (?, ?, ?, ?)
            """, (metric_name, threshold, datetime.now().isoformat(), reason))
    
    def _load_thresholds(self):
        """データベースから閾値設定を読み込み"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT metric_name, config, current_threshold FROM thresholds")
                
                for row in cursor.fetchall():
                    metric_name, config_json, current_threshold = row
                    config_dict = json.loads(config_json)
                    config = ThresholdConfig(**config_dict)
                    config.base_threshold = current_threshold
                    self.thresholds[metric_name] = config
                    
        except Exception as e:
            logger.warning(f"Failed to load thresholds: {e}")
    
    def get_threshold(self, metric_name: str) -> Optional[float]:
        """指定メトリクスの現在の閾値を取得"""
        config = self.thresholds.get(metric_name)
        return config.base_threshold if config else None
    
    def is_anomaly(self, metric_name: str, value: float) -> bool:
        """指定値が異常かどうかを判定"""
        threshold = self.get_threshold(metric_name)
        if threshold is None:
            return False
        
        return value > threshold

class NotificationManager:
    """通知管理システム"""
    
    def __init__(self, config_path: str = "notification_config.json"):
        self.config_path = config_path
        self.channels_config = self._load_config()
        self.notification_history: deque = deque(maxlen=1000)
        
    def _load_config(self) -> Dict[str, Dict[str, Any]]:
        """通知設定を読み込み"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load notification config: {e}")
        
        # デフォルト設定
        return {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_address': '',
                'to_addresses': []
            },
            'slack': {
                'enabled': False,
                'webhook_url': '',
                'channel': '#alerts',
                'username': 'AlertBot'
            },
            'webhook': {
                'enabled': False,
                'url': '',
                'headers': {},
                'timeout': 30
            },
            'desktop': {
                'enabled': True
            }
        }
    
    def save_config(self):
        """通知設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.channels_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save notification config: {e}")
    
    async def send_notification(
        self, 
        alert: Alert, 
        channels: List[NotificationChannel] = None
    ) -> Dict[NotificationChannel, bool]:
        """指定チャネルに通知を送信"""
        if channels is None:
            channels = [NotificationChannel.EMAIL, NotificationChannel.DESKTOP]
        
        results = {}
        
        # 並行して通知を送信
        tasks = []
        for channel in channels:
            if channel == NotificationChannel.EMAIL and self.channels_config['email']['enabled']:
                tasks.append(self._send_email(alert))
            elif channel == NotificationChannel.SLACK and self.channels_config['slack']['enabled']:
                tasks.append(self._send_slack(alert))
            elif channel == NotificationChannel.WEBHOOK and self.channels_config['webhook']['enabled']:
                tasks.append(self._send_webhook(alert))
            elif channel == NotificationChannel.DESKTOP and self.channels_config['desktop']['enabled']:
                tasks.append(self._send_desktop_notification(alert))
        
        # 全ての通知タスクを実行
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, channel in enumerate(channels):
                if i < len(task_results):
                    result = task_results[i]
                    results[channel] = not isinstance(result, Exception)
                    if isinstance(result, Exception):
                        logger.error(f"Notification failed for {channel.value}: {result}")
        
        # 通知履歴に記録
        self.notification_history.append({
            'alert_id': alert.id,
            'channels': [ch.value for ch in channels],
            'results': {ch.value: success for ch, success in results.items()},
            'timestamp': datetime.now().isoformat()
        })
        
        return results
    
    async def _send_email(self, alert: Alert) -> bool:
        """メール通知を送信"""
        try:
            config = self.channels_config['email']
            
            msg = MIMEMultipart()
            msg['From'] = config['from_address']
            msg['To'] = ', '.join(config['to_addresses'])
            msg['Subject'] = f"[{alert.severity.value}] {alert.title}"
            
            # メール本文を作成
            body = f"""
アラート通知

重要度: {alert.severity.value}
タイトル: {alert.title}
メッセージ: {alert.message}
発生時刻: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

詳細情報:
{json.dumps(alert.details, indent=2, ensure_ascii=False)}

このアラートは自動的に生成されました。
            """.strip()
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # SMTP経由でメールを送信
            with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['username'], config['password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False
    
    async def _send_slack(self, alert: Alert) -> bool:
        """Slack通知を送信"""
        try:
            config = self.channels_config['slack']
            
            # Slackのメッセージ形式
            color_map = {
                AlertSeverity.LOW: 'good',
                AlertSeverity.MEDIUM: 'warning',
                AlertSeverity.HIGH: 'danger',
                AlertSeverity.CRITICAL: 'danger'
            }
            
            payload = {
                'channel': config['channel'],
                'username': config['username'],
                'icon_emoji': ':warning:',
                'attachments': [
                    {
                        'color': color_map.get(alert.severity, 'warning'),
                        'title': f"[{alert.severity.value}] {alert.title}",
                        'text': alert.message,
                        'fields': [
                            {
                                'title': '発生時刻',
                                'value': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                                'short': True
                            },
                            {
                                'title': 'ステータス',
                                'value': alert.status.value,
                                'short': True
                            }
                        ],
                        'footer': 'Alert System',
                        'ts': int(alert.created_at.timestamp())
                    }
                ]
            }
            
            async with asyncio.timeout(30):
                response = requests.post(
                    config['webhook_url'],
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False
    
    async def _send_webhook(self, alert: Alert) -> bool:
        """Webhook通知を送信"""
        try:
            config = self.channels_config['webhook']
            
            payload = {
                'alert_id': alert.id,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'details': alert.details,
                'created_at': alert.created_at.isoformat(),
                'status': alert.status.value
            }
            
            headers = config.get('headers', {})
            headers.setdefault('Content-Type', 'application/json')
            
            async with asyncio.timeout(config.get('timeout', 30)):
                response = requests.post(
                    config['url'],
                    json=payload,
                    headers=headers,
                    timeout=config.get('timeout', 30)
                )
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False
    
    async def _send_desktop_notification(self, alert: Alert) -> bool:
        """デスクトップ通知を送信"""
        try:
            import platform
            
            title = f"[{alert.severity.value}] {alert.title}"
            message = alert.message[:200]  # 長すぎる場合は切り詰め
            
            system = platform.system()
            
            if system == "Windows":
                # Windows Toast通知
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=10)
                    return True
                except ImportError:
                    logger.warning("win10toast not installed, skipping Windows notification")
                    return False
            
            elif system == "Darwin":  # macOS
                os.system(f'''
                    osascript -e 'display notification "{message}" with title "{title}"'
                ''')
                return True
            
            elif system == "Linux":
                os.system(f'''
                    notify-send "{title}" "{message}"
                ''')
                return True
            
            else:
                logger.warning(f"Desktop notifications not supported on {system}")
                return False
                
        except Exception as e:
            logger.error(f"Desktop notification failed: {e}")
            return False

class EscalationManager:
    """エスカレーション管理システム"""
    
    def __init__(self):
        self.escalation_rules: Dict[str, List[Dict[str, Any]]] = {}
        self.escalation_history: deque = deque(maxlen=1000)
    
    def register_escalation_rule(
        self, 
        rule_id: str, 
        escalation_levels: List[Dict[str, Any]]
    ):
        """エスカレーションルールを登録"""
        self.escalation_rules[rule_id] = escalation_levels
        logger.info(f"Registered escalation rule for {rule_id} with {len(escalation_levels)} levels")
    
    async def check_escalation(self, alert: Alert) -> bool:
        """アラートのエスカレーションをチェック"""
        rule_id = alert.rule_id
        
        if rule_id not in self.escalation_rules:
            return False
        
        escalation_levels = self.escalation_rules[rule_id]
        
        if alert.escalation_level >= len(escalation_levels):
            return False  # 最大エスカレーションレベルに達している
        
        current_level = escalation_levels[alert.escalation_level]
        
        # エスカレーション条件をチェック
        time_since_created = datetime.now() - alert.created_at
        time_threshold = timedelta(seconds=current_level.get('time_threshold', 3600))
        
        if time_since_created >= time_threshold:
            # エスカレーションを実行
            await self._execute_escalation(alert, current_level)
            alert.escalation_level += 1
            
            # 履歴に記録
            self.escalation_history.append({
                'alert_id': alert.id,
                'from_level': alert.escalation_level - 1,
                'to_level': alert.escalation_level,
                'timestamp': datetime.now().isoformat(),
                'reason': 'time_threshold_exceeded'
            })
            
            return True
        
        return False
    
    async def _execute_escalation(self, alert: Alert, level_config: Dict[str, Any]):
        """エスカレーションアクションを実行"""
        actions = level_config.get('actions', [])
        
        for action in actions:
            action_type = action.get('type')
            
            if action_type == 'notification':
                # 追加の通知チャネルに送信
                channels = [NotificationChannel(ch) for ch in action.get('channels', [])]
                # 通知管理システムが必要（インジェクション）
                
            elif action_type == 'severity_increase':
                # 重要度を上げる
                new_severity = AlertSeverity(action.get('new_severity', 'HIGH'))
                old_severity = alert.severity
                alert.severity = new_severity
                logger.info(f"Escalated alert {alert.id} severity: {old_severity.value} -> {new_severity.value}")
                
            elif action_type == 'assign_to':
                # 担当者に割り当て
                assignee = action.get('assignee')
                alert.details['assigned_to'] = assignee
                logger.info(f"Assigned alert {alert.id} to {assignee}")
                
            elif action_type == 'custom_webhook':
                # カスタムWebhookを呼び出し
                webhook_url = action.get('url')
                if webhook_url:
                    try:
                        payload = {
                            'alert': alert.to_dict(),
                            'escalation_level': alert.escalation_level,
                            'action': action
                        }
                        response = requests.post(webhook_url, json=payload, timeout=30)
                        response.raise_for_status()
                        logger.info(f"Executed custom webhook for alert {alert.id}")
                    except Exception as e:
                        logger.error(f"Custom webhook failed for alert {alert.id}: {e}")

class IntelligentAlertSystem:
    """インテリジェントアラートシステムのメインクラス"""
    
    def __init__(self, db_path: str = "alerts.db"):
        self.db_path = db_path
        self.threshold_manager = DynamicThresholdManager()
        self.notification_manager = NotificationManager()
        self.escalation_manager = EscalationManager()
        
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.suppressed_rules: Dict[str, datetime] = {}
        
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.pattern_history: Dict[str, List[float]] = defaultdict(list)
        
        self._init_database()
        self._load_default_rules()
        
        # バックグラウンドタスク
        self._running = False
        self._background_task = None
    
    def _init_database(self):
        """アラートシステム用データベースを初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT,
                    severity TEXT,
                    status TEXT,
                    title TEXT,
                    message TEXT,
                    details TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    resolved_at TEXT,
                    escalation_level INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_signature TEXT,
                    frequency INTEGER DEFAULT 1,
                    first_seen TEXT,
                    last_seen TEXT,
                    severity_trend TEXT,
                    pattern_data TEXT
                )
            """)
    
    def _load_default_rules(self):
        """デフォルトのアラートルールを読み込み"""
        default_rules = [
            AlertRule(
                rule_id="high_cpu_usage",
                name="高CPU使用率",
                description="CPU使用率が閾値を超えた場合のアラート",
                condition="cpu_percent > get_threshold('cpu_percent')",
                severity=AlertSeverity.HIGH,
                threshold_config=ThresholdConfig(
                    metric_name="cpu_percent",
                    base_threshold=80.0,
                    adaptive_factor=1.1,
                    min_threshold=60.0,
                    max_threshold=95.0
                ),
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DESKTOP],
                escalation_rules=[
                    {'time_threshold': 1800, 'actions': [{'type': 'severity_increase', 'new_severity': 'CRITICAL'}]},
                    {'time_threshold': 3600, 'actions': [{'type': 'notification', 'channels': ['SLACK']}]}
                ]
            ),
            
            AlertRule(
                rule_id="high_memory_usage",
                name="高メモリ使用率",
                description="メモリ使用率が閾値を超えた場合のアラート",
                condition="memory_percent > get_threshold('memory_percent')",
                severity=AlertSeverity.HIGH,
                threshold_config=ThresholdConfig(
                    metric_name="memory_percent",
                    base_threshold=85.0,
                    adaptive_factor=1.1,
                    min_threshold=70.0,
                    max_threshold=95.0
                ),
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DESKTOP]
            ),
            
            AlertRule(
                rule_id="high_error_rate",
                name="高エラー率",
                description="アプリケーションのエラー率が閾値を超えた場合のアラート",
                condition="error_rate > get_threshold('error_rate')",
                severity=AlertSeverity.CRITICAL,
                threshold_config=ThresholdConfig(
                    metric_name="error_rate",
                    base_threshold=5.0,
                    adaptive_factor=1.2,
                    min_threshold=2.0,
                    max_threshold=20.0
                ),
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.DESKTOP]
            ),
            
            AlertRule(
                rule_id="disk_space_low",
                name="ディスク容量不足",
                description="ディスク使用率が閾値を超えた場合のアラート",
                condition="disk_usage_percent > get_threshold('disk_usage_percent')",
                severity=AlertSeverity.MEDIUM,
                threshold_config=ThresholdConfig(
                    metric_name="disk_usage_percent",
                    base_threshold=80.0,
                    adaptive_factor=1.05,
                    min_threshold=70.0,
                    max_threshold=90.0
                ),
                notification_channels=[NotificationChannel.EMAIL]
            )
        ]
        
        for rule in default_rules:
            self.register_rule(rule)
    
    def register_rule(self, rule: AlertRule):
        """アラートルールを登録"""
        self.alert_rules[rule.rule_id] = rule
        
        # 動的閾値を登録
        if rule.threshold_config:
            self.threshold_manager.register_threshold(rule.threshold_config)
        
        # エスカレーションルールを登録
        if rule.escalation_rules:
            self.escalation_manager.register_escalation_rule(rule.rule_id, rule.escalation_rules)
        
        # データベースに保存
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alert_rules (rule_id, config, enabled) 
                VALUES (?, ?, ?)
            """, (rule.rule_id, json.dumps(rule.to_dict()), int(rule.enabled)))
        
        logger.info(f"Registered alert rule: {rule.rule_id}")
    
    async def evaluate_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """メトリクスを評価してアラートを生成"""
        new_alerts = []
        
        # 各ルールを評価
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # 抑制ウィンドウをチェック
            if self._is_suppressed(rule_id):
                continue
            
            try:
                # 条件を評価
                if self._evaluate_condition(rule, metrics):
                    alert = await self._create_alert(rule, metrics)
                    if alert:
                        new_alerts.append(alert)
                        self._suppress_rule(rule_id, rule.suppression_window)
                        
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_id}: {e}")
        
        # メトリクス値を動的閾値管理に追加
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                self.threshold_manager.add_metric_value(metric_name, float(value))
        
        # パターン学習
        await self._learn_patterns(new_alerts)
        
        return new_alerts
    
    def _evaluate_condition(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """ルール条件を評価"""
        try:
            # 安全な評価環境を作成
            safe_globals = {
                '__builtins__': {},
                'get_threshold': self.threshold_manager.get_threshold,
                'abs': abs,
                'min': min,
                'max': max,
                'len': len,
                'sum': sum,
                'any': any,
                'all': all
            }
            
            # メトリクスを変数として追加
            safe_globals.update(metrics)
            
            # 条件を評価
            result = eval(rule.condition, safe_globals)
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Condition evaluation failed for rule {rule.rule_id}: {e}")
            return False
    
    async def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """新しいアラートを作成"""
        alert_id = self._generate_alert_id(rule.rule_id, metrics)
        
        # 既存のアクティブアラートをチェック
        if alert_id in self.active_alerts:
            return None
        
        alert = Alert(
            id=alert_id,
            rule_id=rule.rule_id,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            title=rule.name,
            message=self._generate_alert_message(rule, metrics),
            details={
                'triggering_metrics': metrics,
                'threshold_values': self._get_relevant_thresholds(rule, metrics),
                'rule_description': rule.description
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # 通知を送信
        await self.notification_manager.send_notification(alert, rule.notification_channels)
        
        # データベースに保存
        self._save_alert(alert)
        
        logger.info(f"Created alert: {alert_id} [{alert.severity.value}] {alert.title}")
        return alert
    
    def _generate_alert_id(self, rule_id: str, metrics: Dict[str, Any]) -> str:
        """アラートIDを生成"""
        content = f"{rule_id}_{datetime.now().date().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_alert_message(self, rule: AlertRule, metrics: Dict[str, Any]) -> str:
        """アラートメッセージを生成"""
        message_parts = [rule.description]
        
        # 関連メトリクスの詳細を追加
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                threshold = self.threshold_manager.get_threshold(key)
                if threshold:
                    message_parts.append(f"{key}: {value:.2f} (閾値: {threshold:.2f})")
                else:
                    message_parts.append(f"{key}: {value:.2f}")
        
        return " | ".join(message_parts)
    
    def _get_relevant_thresholds(self, rule: AlertRule, metrics: Dict[str, Any]) -> Dict[str, float]:
        """関連する閾値を取得"""
        thresholds = {}
        for key in metrics.keys():
            threshold = self.threshold_manager.get_threshold(key)
            if threshold is not None:
                thresholds[key] = threshold
        return thresholds
    
    def _is_suppressed(self, rule_id: str) -> bool:
        """ルールが抑制されているかチェック"""
        if rule_id not in self.suppressed_rules:
            return False
        
        suppressed_until = self.suppressed_rules[rule_id]
        if datetime.now() > suppressed_until:
            del self.suppressed_rules[rule_id]
            return False
        
        return True
    
    def _suppress_rule(self, rule_id: str, duration_seconds: int):
        """ルールを一定時間抑制"""
        self.suppressed_rules[rule_id] = datetime.now() + timedelta(seconds=duration_seconds)
    
    async def _learn_patterns(self, new_alerts: List[Alert]):
        """新しいアラートからパターンを学習"""
        for alert in new_alerts:
            # パターンシグネチャを生成
            signature = f"{alert.rule_id}_{alert.severity.value}"
            
            # パターン履歴を更新
            if signature not in self.pattern_history:
                self.pattern_history[signature] = []
            
            self.pattern_history[signature].append(time.time())
            
            # 最近24時間のパターンを保持
            cutoff_time = time.time() - 86400
            self.pattern_history[signature] = [
                t for t in self.pattern_history[signature] if t > cutoff_time
            ]
            
            # パターンをデータベースに保存
            await self._save_pattern(signature, alert)
    
    async def _save_pattern(self, signature: str, alert: Alert):
        """パターンをデータベースに保存"""
        with sqlite3.connect(self.db_path) as conn:
            # 既存パターンをチェック
            cursor = conn.execute(
                "SELECT frequency, first_seen FROM alert_patterns WHERE pattern_signature = ?",
                (signature,)
            )
            result = cursor.fetchone()
            
            if result:
                # 既存パターンを更新
                frequency, first_seen = result
                conn.execute("""
                    UPDATE alert_patterns 
                    SET frequency = frequency + 1, last_seen = ? 
                    WHERE pattern_signature = ?
                """, (datetime.now().isoformat(), signature))
            else:
                # 新しいパターンを挿入
                conn.execute("""
                    INSERT INTO alert_patterns 
                    (pattern_signature, frequency, first_seen, last_seen, severity_trend, pattern_data) 
                    VALUES (?, 1, ?, ?, ?, ?)
                """, (
                    signature,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    alert.severity.value,
                    json.dumps({'rule_id': alert.rule_id, 'title': alert.title})
                ))
    
    def _save_alert(self, alert: Alert):
        """アラートをデータベースに保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alerts 
                (id, rule_id, severity, status, title, message, details, 
                 created_at, updated_at, escalation_level) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id, alert.rule_id, alert.severity.value, alert.status.value,
                alert.title, alert.message, json.dumps(alert.details),
                alert.created_at.isoformat(), alert.updated_at.isoformat(),
                alert.escalation_level
            ))
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """アラートを確認済みにする"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
        alert.updated_at = datetime.now()
        
        self._save_alert(alert)
        
        logger.info(f"Alert acknowledged: {alert_id}")
        return True
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """アラートを解決済みにする"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        alert.updated_at = datetime.now()
        
        self._save_alert(alert)
        
        # アクティブアラートから削除
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert resolved: {alert_id}")
        return True
    
    async def start_background_monitoring(self):
        """バックグラウンド監視を開始"""
        if self._running:
            return
        
        self._running = True
        self._background_task = asyncio.create_task(self._background_loop())
        logger.info("Started background alert monitoring")
    
    async def stop_background_monitoring(self):
        """バックグラウンド監視を停止"""
        if not self._running:
            return
        
        self._running = False
        
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped background alert monitoring")
    
    async def _background_loop(self):
        """バックグラウンド監視ループ"""
        while self._running:
            try:
                # エスカレーションをチェック
                for alert in list(self.active_alerts.values()):
                    if alert.status == AlertStatus.ACTIVE:
                        await self.escalation_manager.check_escalation(alert)
                
                # 一定時間後に自動解決される古いアラートをチェック
                await self._check_auto_resolution()
                
                await asyncio.sleep(60)  # 1分間隔で実行
                
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_auto_resolution(self):
        """自動解決をチェック"""
        auto_resolution_time = timedelta(hours=24)  # 24時間で自動解決
        cutoff_time = datetime.now() - auto_resolution_time
        
        for alert_id, alert in list(self.active_alerts.items()):
            if alert.created_at < cutoff_time and alert.status == AlertStatus.ACTIVE:
                await self.resolve_alert(alert_id)
                logger.info(f"Auto-resolved alert: {alert_id}")
    
    def get_active_alerts(self, severity_filter: AlertSeverity = None) -> List[Alert]:
        """アクティブなアラートを取得"""
        alerts = list(self.active_alerts.values())
        
        if severity_filter:
            alerts = [alert for alert in alerts if alert.severity == severity_filter]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """アラート統計を取得"""
        cutoff_time = datetime.now() - timedelta(days=days)
        recent_alerts = [
            alert for alert in self.alert_history 
            if alert.created_at >= cutoff_time
        ]
        
        if not recent_alerts:
            return {
                'total_alerts': 0,
                'severity_distribution': {},
                'top_rules': [],
                'resolution_time': 0,
                'escalation_rate': 0
            }
        
        # 重要度別分布
        severity_dist = defaultdict(int)
        for alert in recent_alerts:
            severity_dist[alert.severity.value] += 1
        
        # ルール別集計
        rule_counts = defaultdict(int)
        for alert in recent_alerts:
            rule_counts[alert.rule_id] += 1
        
        top_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 解決時間の平均
        resolved_alerts = [a for a in recent_alerts if a.resolved_at]
        if resolved_alerts:
            resolution_times = [
                (a.resolved_at - a.created_at).total_seconds()
                for a in resolved_alerts
            ]
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        else:
            avg_resolution_time = 0
        
        # エスカレーション率
        escalated_count = sum(1 for a in recent_alerts if a.escalation_level > 0)
        escalation_rate = (escalated_count / len(recent_alerts)) * 100 if recent_alerts else 0
        
        return {
            'total_alerts': len(recent_alerts),
            'severity_distribution': dict(severity_dist),
            'top_rules': top_rules,
            'resolution_time': avg_resolution_time,
            'escalation_rate': escalation_rate,
            'active_alerts': len(self.active_alerts)
        }

# テスト・デモ用の関数
async def demo_alert_system():
    """アラートシステムのデモ"""
    alert_system = IntelligentAlertSystem()
    
    # バックグラウンド監視を開始
    await alert_system.start_background_monitoring()
    
    # サンプルメトリクスでテスト
    test_metrics = [
        {'cpu_percent': 85.5, 'memory_percent': 78.2, 'error_rate': 2.1},
        {'cpu_percent': 92.1, 'memory_percent': 89.7, 'error_rate': 6.8},
        {'cpu_percent': 45.2, 'memory_percent': 65.1, 'error_rate': 1.2},
        {'cpu_percent': 98.9, 'memory_percent': 95.3, 'error_rate': 12.5},
    ]
    
    print("=== アラートシステムデモ開始 ===")
    
    for i, metrics in enumerate(test_metrics, 1):
        print(f"\n--- テストケース {i} ---")
        print(f"メトリクス: {metrics}")
        
        alerts = await alert_system.evaluate_metrics(metrics)
        
        if alerts:
            for alert in alerts:
                print(f"アラート生成: [{alert.severity.value}] {alert.title}")
                print(f"  メッセージ: {alert.message}")
        else:
            print("アラートなし")
        
        await asyncio.sleep(2)  # 2秒待機
    
    # 統計を表示
    print("\n=== アラート統計 ===")
    stats = alert_system.get_alert_statistics()
    print(f"総アラート数: {stats['total_alerts']}")
    print(f"重要度分布: {stats['severity_distribution']}")
    print(f"アクティブアラート: {stats['active_alerts']}")
    
    # バックグラウンド監視を停止
    await alert_system.stop_background_monitoring()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    )
    
    print("Starting Intelligent Alert System Demo...")
    asyncio.run(demo_alert_system())