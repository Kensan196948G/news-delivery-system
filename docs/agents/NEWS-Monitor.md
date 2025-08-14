# NEWS-Monitor - システム監視エージェント

## エージェント概要
ニュース配信システムの包括的な監視、パフォーマンス分析、アラート管理を専門とするエージェント。

## 役割と責任
- システムパフォーマンス監視
- アプリケーション監視
- インフラストラクチャ監視
- ログ分析・集約
- アラート管理・通知

## 主要業務

### システム監視実装
```python
import psutil
import asyncio
from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    process_count: int
    load_average: float

@dataclass
class ApplicationMetrics:
    timestamp: datetime
    response_time: float
    throughput: float
    error_rate: float
    active_connections: int
    queue_size: int
    cache_hit_rate: float

class SystemMonitor:
    def __init__(self):
        self.alert_manager = AlertManager()
        self.metrics_collector = MetricsCollector()
        self.threshold_config = ThresholdConfig()
        
    async def collect_system_metrics(self) -> SystemMetrics:
        """システムメトリクス収集"""
        # CPU使用率
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # ディスク使用率
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100
        
        # ネットワークI/O
        network_io = psutil.net_io_counters()._asdict()
        
        # プロセス数
        process_count = len(psutil.pids())
        
        # ロードアベレージ
        load_average = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            network_io=network_io,
            process_count=process_count,
            load_average=load_average
        )
    
    async def collect_application_metrics(self) -> ApplicationMetrics:
        """アプリケーションメトリクス収集"""
        # レスポンス時間測定
        response_time = await self._measure_response_time()
        
        # スループット計算
        throughput = await self._calculate_throughput()
        
        # エラー率計算
        error_rate = await self._calculate_error_rate()
        
        # アクティブ接続数
        active_connections = await self._count_active_connections()
        
        # キューサイズ
        queue_size = await self._get_queue_size()
        
        # キャッシュヒット率
        cache_hit_rate = await self._calculate_cache_hit_rate()
        
        return ApplicationMetrics(
            timestamp=datetime.now(),
            response_time=response_time,
            throughput=throughput,
            error_rate=error_rate,
            active_connections=active_connections,
            queue_size=queue_size,
            cache_hit_rate=cache_hit_rate
        )
    
    async def monitor_news_collection_process(self) -> Dict:
        """ニュース収集プロセス監視"""
        collection_metrics = {
            'collection_status': await self._check_collection_status(),
            'articles_collected_last_hour': await self._count_recent_articles(),
            'api_response_times': await self._measure_api_response_times(),
            'translation_queue_size': await self._check_translation_queue(),
            'ai_analysis_backlog': await self._check_analysis_backlog(),
            'delivery_queue_status': await self._check_delivery_queue()
        }
        
        # 異常検知
        anomalies = await self._detect_collection_anomalies(collection_metrics)
        
        return {
            'metrics': collection_metrics,
            'anomalies': anomalies,
            'health_status': self._calculate_collection_health(collection_metrics, anomalies)
        }
    
    async def _measure_api_response_times(self) -> Dict[str, float]:
        """外部API応答時間測定"""
        api_endpoints = [
            ('newsapi', 'https://newsapi.org/v2/top-headlines'),
            ('deepl', 'https://api-free.deepl.com/v2/translate'),
            ('anthropic', 'https://api.anthropic.com/v1/messages')
        ]
        
        response_times = {}
        
        for api_name, endpoint in api_endpoints:
            try:
                start_time = time.time()
                response = await aiohttp.ClientSession().get(
                    endpoint, 
                    timeout=aiohttp.ClientTimeout(total=10)
                )
                end_time = time.time()
                response_times[api_name] = (end_time - start_time) * 1000  # ms
            except Exception as e:
                response_times[api_name] = -1  # エラー表示
                
        return response_times
```

### アラート管理システム
```python
from enum import Enum
import smtplib
from email.mime.text import MIMEText

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"  
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class Alert:
    id: str
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    source: str
    metrics: Dict[str, Any]
    acknowledged: bool = False

class AlertManager:
    def __init__(self):
        self.active_alerts = {}
        self.alert_history = []
        self.notification_channels = NotificationChannels()
        
    async def evaluate_alerts(self, system_metrics: SystemMetrics, 
                            app_metrics: ApplicationMetrics) -> List[Alert]:
        """アラート評価"""
        alerts = []
        
        # システムリソースアラート
        if system_metrics.cpu_usage > 85:
            alerts.append(Alert(
                id=f"cpu_high_{int(time.time())}",
                severity=AlertSeverity.WARNING if system_metrics.cpu_usage < 95 else AlertSeverity.CRITICAL,
                title="高CPU使用率検出",
                description=f"CPU使用率が {system_metrics.cpu_usage:.1f}% に達しました",
                timestamp=datetime.now(),
                source="system_monitor",
                metrics={"cpu_usage": system_metrics.cpu_usage}
            ))
        
        if system_metrics.memory_usage > 90:
            alerts.append(Alert(
                id=f"memory_high_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                title="メモリ不足警告",
                description=f"メモリ使用率が {system_metrics.memory_usage:.1f}% に達しました",
                timestamp=datetime.now(),
                source="system_monitor",
                metrics={"memory_usage": system_metrics.memory_usage}
            ))
        
        # アプリケーションパフォーマンスアラート
        if app_metrics.response_time > 5000:  # 5秒以上
            alerts.append(Alert(
                id=f"response_slow_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                title="応答時間遅延",
                description=f"平均応答時間が {app_metrics.response_time:.0f}ms に達しました",
                timestamp=datetime.now(),
                source="application_monitor",
                metrics={"response_time": app_metrics.response_time}
            ))
        
        if app_metrics.error_rate > 0.05:  # 5%以上
            alerts.append(Alert(
                id=f"error_rate_high_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                title="エラー率上昇",
                description=f"エラー率が {app_metrics.error_rate:.1%} に達しました",
                timestamp=datetime.now(),
                source="application_monitor",
                metrics={"error_rate": app_metrics.error_rate}
            ))
        
        # 新規アラートの処理
        for alert in alerts:
            if alert.id not in self.active_alerts:
                await self._handle_new_alert(alert)
                self.active_alerts[alert.id] = alert
        
        return alerts
    
    async def _handle_new_alert(self, alert: Alert):
        """新規アラート処理"""
        # アラート履歴に追加
        self.alert_history.append(alert)
        
        # 通知送信
        await self._send_alert_notification(alert)
        
        # 自動対応アクション（該当する場合）
        await self._trigger_automated_response(alert)
    
    async def _send_alert_notification(self, alert: Alert):
        """アラート通知送信"""
        notification_message = f"""
        【{alert.severity.value.upper()}】{alert.title}
        
        時刻: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        ソース: {alert.source}
        
        詳細: {alert.description}
        
        メトリクス: {alert.metrics}
        """
        
        # Slack通知
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            await self.notification_channels.send_slack_notification(
                channel="#alerts",
                message=notification_message,
                severity=alert.severity
            )
        
        # メール通知（クリティカル以上）
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            await self.notification_channels.send_email_notification(
                to="admin@newsdelivery.local",
                subject=f"[ALERT] {alert.title}",
                body=notification_message
            )
```

### ログ分析・集約
```python
import re
from collections import defaultdict, Counter

class LogAnalyzer:
    def __init__(self):
        self.log_parsers = LogParsers()
        self.pattern_detector = PatternDetector()
        
    async def analyze_application_logs(self, log_entries: List[str]) -> Dict:
        """アプリケーションログ分析"""
        analysis_result = {
            'total_entries': len(log_entries),
            'log_levels': defaultdict(int),
            'error_patterns': [],
            'performance_issues': [],
            'security_events': [],
            'api_usage_stats': defaultdict(int)
        }
        
        for entry in log_entries:
            parsed_entry = await self._parse_log_entry(entry)
            
            # ログレベル集計
            analysis_result['log_levels'][parsed_entry.get('level', 'UNKNOWN')] += 1
            
            # エラーパターン検出
            if parsed_entry.get('level') == 'ERROR':
                error_pattern = await self._detect_error_pattern(parsed_entry)
                analysis_result['error_patterns'].append(error_pattern)
            
            # パフォーマンス問題検出
            if 'slow' in entry.lower() or 'timeout' in entry.lower():
                performance_issue = await self._analyze_performance_issue(parsed_entry)
                analysis_result['performance_issues'].append(performance_issue)
            
            # セキュリティイベント検出
            if self._is_security_event(parsed_entry):
                security_event = await self._analyze_security_event(parsed_entry)
                analysis_result['security_events'].append(security_event)
            
            # API使用統計
            api_call = self._extract_api_call(parsed_entry)
            if api_call:
                analysis_result['api_usage_stats'][api_call] += 1
        
        # トレンド分析
        trends = await self._analyze_log_trends(analysis_result)
        analysis_result['trends'] = trends
        
        return analysis_result
    
    async def _detect_error_pattern(self, parsed_entry: Dict) -> Dict:
        """エラーパターン検出"""
        common_patterns = [
            {
                'pattern': r'Connection timeout',
                'category': 'network_timeout',
                'severity': 'medium'
            },
            {
                'pattern': r'API rate limit exceeded',
                'category': 'rate_limiting',
                'severity': 'low'
            },
            {
                'pattern': r'Database connection failed',
                'category': 'database_error',
                'severity': 'high'
            },
            {
                'pattern': r'Memory allocation failed',
                'category': 'memory_error',
                'severity': 'critical'
            }
        ]
        
        message = parsed_entry.get('message', '')
        
        for pattern_config in common_patterns:
            if re.search(pattern_config['pattern'], message, re.IGNORECASE):
                return {
                    'timestamp': parsed_entry.get('timestamp'),
                    'category': pattern_config['category'],
                    'severity': pattern_config['severity'],
                    'message': message,
                    'count': 1
                }
        
        return {
            'timestamp': parsed_entry.get('timestamp'),
            'category': 'unknown_error',
            'severity': 'medium',
            'message': message,
            'count': 1
        }
```

### パフォーマンス分析・最適化
```python
class PerformanceAnalyzer:
    def __init__(self):
        self.baseline_metrics = BaselineMetrics()
        self.trend_analyzer = TrendAnalyzer()
        
    async def analyze_performance_trends(self, metrics_history: List[Dict]) -> Dict:
        """パフォーマンストレンド分析"""
        if len(metrics_history) < 10:
            return {'status': 'insufficient_data'}
        
        trends = {}
        
        # CPU使用率トレンド
        cpu_values = [m.get('cpu_usage', 0) for m in metrics_history]
        trends['cpu_trend'] = await self._calculate_trend(cpu_values)
        
        # メモリ使用率トレンド  
        memory_values = [m.get('memory_usage', 0) for m in metrics_history]
        trends['memory_trend'] = await self._calculate_trend(memory_values)
        
        # 応答時間トレンド
        response_times = [m.get('response_time', 0) for m in metrics_history]
        trends['response_time_trend'] = await self._calculate_trend(response_times)
        
        # エラー率トレンド
        error_rates = [m.get('error_rate', 0) for m in metrics_history]
        trends['error_rate_trend'] = await self._calculate_trend(error_rates)
        
        # 異常値検出
        anomalies = await self._detect_performance_anomalies(metrics_history)
        
        # 予測分析
        predictions = await self._predict_performance_issues(trends)
        
        return {
            'trends': trends,
            'anomalies': anomalies,
            'predictions': predictions,
            'recommendations': await self._generate_performance_recommendations(trends, anomalies)
        }
    
    async def _calculate_trend(self, values: List[float]) -> Dict:
        """トレンド計算"""
        if len(values) < 2:
            return {'direction': 'unknown', 'slope': 0, 'confidence': 0}
        
        # 線形回帰による傾き計算
        n = len(values)
        x = list(range(n))
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # 方向判定
        if slope > 0.1:
            direction = 'increasing'
        elif slope < -0.1:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        # 信頼度計算（R²）
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y) ** 2 for y in values)
        ss_res = sum((values[i] - (slope * x[i] + (sum_y - slope * sum_x) / n)) ** 2 for i in range(n))
        confidence = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return {
            'direction': direction,
            'slope': slope,
            'confidence': confidence
        }
```

## 使用する技術・ツール
- **システム監視**: Prometheus, Grafana, Zabbix
- **アプリケーション監視**: APM (New Relic, Datadog)
- **ログ管理**: ELK Stack, Fluentd
- **アラート**: PagerDuty, OpsGenie
- **メトリクス**: InfluxDB, TimescaleDB
- **可視化**: Grafana, Kibana

## 連携するエージェント
- **NEWS-AutoFix**: 自動修復トリガー
- **NEWS-incident-manager**: インシデント管理連携
- **NEWS-Security**: セキュリティ監視
- **NEWS-CI**: パイプライン監視
- **NEWS-AIPlanner**: 予測分析活用

## KPI目標
- **システム可用性**: 99.9%以上
- **アラート精度**: 95%以上（誤報5%未満）
- **平均検知時間**: 1分以内
- **平均通知時間**: 30秒以内
- **ダッシュボード応答時間**: 3秒以内

## 監視対象領域

### システムリソース
- CPU使用率・負荷
- メモリ使用量・利用率
- ディスク容量・I/O
- ネットワーク通信量

### アプリケーション
- レスポンス時間
- スループット
- エラー率
- 可用性

### 外部依存関係
- 外部API応答時間
- データベース接続
- 第三者サービス状態
- ネットワーク接続

### ビジネスメトリクス
- ニュース収集件数
- 配信成功率
- ユーザーエンゲージメント
- システム使用量

## アラート戦略
- 段階的エスカレーション
- 重要度別通知先
- 自動抑制機能
- 根本原因分析

## ダッシュボード
- システム概要ダッシュボード
- アプリケーション詳細監視
- ビジネスメトリクス表示
- トラブルシューティング支援

## 成果物
- 監視システム構築
- アラート管理システム
- パフォーマンス分析ツール
- 監視ダッシュボード
- 運用手順書