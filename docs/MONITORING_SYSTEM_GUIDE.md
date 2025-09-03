# 統合監視システム ガイド

## 概要

ニュース配信システムの高度な監視システムです。リアルタイムでのパフォーマンス監視、ログ分析、インテリジェントアラート、WebSocketベースのダッシュボードを提供します。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    統合監視システム                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  ログ分析エンジン   │  │ パフォーマンス監視 │  │ アラートシステム   │  │
│  │                │  │                │  │                │  │
│  │ - パターン検出    │  │ - メトリクス収集  │  │ - 動的閾値調整    │  │
│  │ - 異常検知       │  │ - リアルタイム監視│  │ - エスカレーション │  │
│  │ - 機械学習       │  │ - データベース保存│  │ - 通知統合       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                              │                                  │
│  ┌─────────────────────────────┼─────────────────────────────┐  │
│  │          リアルタイムダッシュボード         │                 │  │
│  │                           │                                │  │
│  │ - WebSocket通信           │ - HTTP静的ファイル配信          │  │
│  │ - リアルタイム更新          │ - グラフ生成                  │  │
│  │ - アラート表示            │ - レスポンシブUI               │  │
│  └─────────────────────────────┼─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌─────────────────────┐
                    │   外部通知チャネル    │
                    │                   │
                    │ - メール           │
                    │ - Slack           │
                    │ - Webhook         │
                    │ - デスクトップ通知  │
                    └─────────────────────┘
```

## 主要機能

### 1. ログ分析エンジン (`log_analyzer.py`)

#### パターン検出
- **事前定義パターン**: HTTP エラー、データベースエラー、SSL エラーなど
- **動的パターン検出**: 機械学習によるクラスタリング（DBSCAN + TF-IDF）
- **頻度分析**: パターンの出現頻度と重要度評価

```python
# 使用例
from monitoring.log_analyzer import LogAnalysisEngine

engine = LogAnalysisEngine("logs", "analysis.db")
results = await engine.analyze_logs(
    time_range=(start_time, end_time),
    log_levels=['ERROR', 'WARNING', 'CRITICAL']
)

# 検出されたパターン
for pattern in results['patterns']:
    print(f"パターン: {pattern['description']}")
    print(f"頻度: {pattern['frequency']}")
    print(f"重要度: {pattern['severity']}")
```

#### 異常検知
- **統計的手法**: Z-scoreによる3σ異常検知
- **機械学習**: Isolation Forestによる異常検知
- **時系列分析**: LSTMベースの予測と異常検出
- **アンサンブル**: 複数手法による投票システム

### 2. インテリジェントアラートシステム (`alert_system.py`)

#### 動的閾値調整
```python
# 動的閾値設定
from monitoring.alert_system import DynamicThresholdManager, ThresholdConfig

threshold_config = ThresholdConfig(
    metric_name="cpu_percent",
    base_threshold=80.0,
    adaptive_factor=1.2,
    min_threshold=60.0,
    max_threshold=95.0,
    std_multiplier=2.0,
    trend_sensitivity=0.1
)

manager = DynamicThresholdManager()
manager.register_threshold(threshold_config)

# メトリクス値追加（閾値が自動調整される）
manager.add_metric_value("cpu_percent", 75.5)
current_threshold = manager.get_threshold("cpu_percent")
```

#### 多チャネル通知
```python
# 通知設定
notification_config = {
    'email': {
        'enabled': True,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': 'your-email@gmail.com',
        'password': 'app-password',
        'from_address': 'alerts@yourdomain.com',
        'to_addresses': ['admin@yourdomain.com']
    },
    'slack': {
        'enabled': True,
        'webhook_url': 'https://hooks.slack.com/services/...',
        'channel': '#alerts',
        'username': 'NewsSystem Bot'
    }
}
```

#### エスカレーション
```python
# エスカレーションルール
escalation_rules = [
    {
        'time_threshold': 1800,  # 30分後
        'actions': [
            {'type': 'severity_increase', 'new_severity': 'CRITICAL'}
        ]
    },
    {
        'time_threshold': 3600,  # 1時間後
        'actions': [
            {'type': 'notification', 'channels': ['slack']},
            {'type': 'assign_to', 'assignee': 'on-call-engineer'}
        ]
    }
]
```

### 3. リアルタイムダッシュボード (`dashboard.py`)

#### WebSocketベースのリアルタイム更新
```javascript
// JavaScript クライアント側
const ws = new WebSocket('ws://localhost:8765');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'metrics_update':
            updateMetrics(data.data);
            break;
        case 'new_alert':
            showAlert(data.data);
            break;
    }
};
```

#### メトリクス可視化
- **システムメトリクス**: CPU、メモリ、ディスク、ネットワーク
- **アプリケーションメトリクス**: タスク実行、エラー率、レスポンス時間
- **動的グラフ**: Matplotlib によるリアルタイムグラフ生成
- **Base64エンコード**: 画像をWebSocket経由で配信

### 4. 統合監視システム (`integrated_monitor.py`)

```python
# 統合システムの起動
from monitoring.integrated_monitor import IntegratedMonitoringSystem

system = IntegratedMonitoringSystem(
    db_path="monitoring",
    log_directory="logs",
    dashboard_config={
        'websocket_port': 8765,
        'http_port': 8080
    }
)

# 監視開始
await system.start_monitoring({
    'performance': True,
    'logs': True,
    'alerts': True,
    'dashboard': True
})
```

## 設定

### メイン設定ファイル (`config/monitoring_config.json`)

```json
{
  "performance_monitoring": {
    "collection_interval_seconds": 30,
    "thresholds": {
      "cpu_percent": {"warning": 70, "critical": 90},
      "memory_percent": {"warning": 80, "critical": 95},
      "error_rate": {"warning": 5.0, "critical": 15.0}
    }
  },
  "log_analysis": {
    "analysis_interval_minutes": 30,
    "log_levels": ["ERROR", "WARNING", "CRITICAL"],
    "pattern_detection": {
      "min_frequency": 3,
      "enable_ml_detection": true
    }
  },
  "alert_system": {
    "enable_dynamic_thresholds": true,
    "suppression_window_seconds": 300,
    "notification_channels": {
      "email": {"enabled": true},
      "slack": {"enabled": false},
      "desktop": {"enabled": true}
    }
  }
}
```

## 使用方法

### 1. 基本的な監視開始

```python
import asyncio
from monitoring.integrated_monitor import IntegratedMonitoringSystem

async def main():
    # システム作成
    monitor = IntegratedMonitoringSystem(
        db_path="production_monitoring",
        log_directory="/var/log/newssystem"
    )
    
    # 監視開始
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. カスタムイベントハンドラ

```python
async def custom_alert_handler(alert_data, alerts):
    """カスタムアラート処理"""
    print(f"重要なパターンが検出されました: {alert_data['description']}")
    
    # 外部システムに通知
    if alert_data['severity'] == 'CRITICAL':
        await notify_external_system(alert_data)

# ハンドラ登録
monitor.add_event_handler('pattern_detected', custom_alert_handler)
monitor.add_event_handler('anomaly_detected', custom_alert_handler)
```

### 3. パフォーマンス監視デコレータ

```python
from monitoring.integrated_monitor import monitoring_required

@monitoring_required(monitor)
async def process_news_article(article):
    """ニュース記事処理（監視付き）"""
    # 処理時間とエラーが自動的に監視される
    processed_article = await heavy_processing(article)
    return processed_article
```

### 4. ダッシュボードアクセス

- **Webダッシュボード**: http://localhost:8080
- **WebSocket API**: ws://localhost:8765
- **リアルタイム更新**: 5秒間隔でメトリクス更新

## API仕様

### WebSocket メッセージ

#### クライアント → サーバー
```json
{
  "action": "acknowledge_alert",
  "alert_id": "alert_12345"
}

{
  "action": "get_history", 
  "minutes": 60
}
```

#### サーバー → クライアント
```json
{
  "type": "metrics_update",
  "data": {
    "system_metrics": {
      "cpu_percent": 75.5,
      "memory_percent": 68.2,
      "timestamp": "2024-01-01T12:00:00"
    },
    "system_chart": "base64_encoded_image_data"
  }
}

{
  "type": "new_alert",
  "data": {
    "id": "alert_12345",
    "severity": "HIGH",
    "message": "CPU使用率が閾値を超えました",
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

## データベース構造

### ログ分析 (`logs_analysis.db`)
```sql
-- パターンテーブル
CREATE TABLE log_patterns (
    pattern_id TEXT PRIMARY KEY,
    frequency INTEGER,
    severity TEXT,
    description TEXT,
    examples TEXT
);

-- 異常テーブル  
CREATE TABLE anomalies (
    timestamp TEXT,
    anomaly_type TEXT,
    severity REAL,
    confidence_score REAL,
    details TEXT
);
```

### アラートシステム (`alerts.db`)
```sql
-- アラートテーブル
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,
    severity TEXT,
    status TEXT,
    message TEXT,
    created_at TEXT,
    escalation_level INTEGER
);

-- 閾値履歴
CREATE TABLE threshold_history (
    metric_name TEXT,
    threshold_value REAL,
    calculated_at TEXT,
    reason TEXT
);
```

## パフォーマンス最適化

### 1. データベース最適化
- WALモード有効化
- インデックス最適化
- 自動クリーンアップ（30日後）

### 2. メモリ管理
- 循環バッファ使用（履歴1000件）
- 定期的なGC実行
- メトリクス履歴の制限

### 3. 非同期処理
- 並行メトリクス収集
- 非同期アラート処理
- バックグラウンドタスク分離

## トラブルシューティング

### 一般的な問題

#### 1. WebSocketが接続できない
```bash
# ポート確認
netstat -tlnp | grep 8765

# ファイアウォール確認
sudo ufw status

# ログ確認
tail -f logs/monitoring.log
```

#### 2. メトリクス収集エラー
```python
# デバッグモードでログ確認
logging.getLogger('monitoring').setLevel(logging.DEBUG)

# システムリソースアクセス権限確認
import psutil
try:
    psutil.cpu_percent()
    psutil.virtual_memory()
    psutil.disk_usage('/')
except Exception as e:
    print(f"権限エラー: {e}")
```

#### 3. アラートが送信されない
```python
# 通知設定確認
from monitoring.alert_system import NotificationManager

manager = NotificationManager()
print(manager.channels_config)

# SMTPサーバー接続テスト
import smtplib
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('username', 'password')
    print("SMTP接続成功")
except Exception as e:
    print(f"SMTP接続エラー: {e}")
```

## セキュリティ考慮事項

### 1. 認証・認可
- ダッシュボード基本認証（オプション）
- API レート制限
- HTTPS対応（SSL証明書設定）

### 2. データ保護
- 設定ファイルでの機密情報管理
- ログの個人情報マスキング
- ローカルデータベース暗号化（将来対応）

### 3. ネットワークセキュリティ
- 許可ホストリスト
- CORS設定
- WebSocket接続制限

## 監視メトリクス

### システムメトリクス
- **CPU使用率**: プロセッサ使用率（%）
- **メモリ使用率**: 物理メモリ使用率（%）
- **ディスク使用率**: ストレージ使用率（%）
- **ネットワークI/O**: 送受信トラフィック（MB/s）
- **プロセス数**: システム全体のプロセス数

### アプリケーションメトリクス
- **アクティブタスク数**: 実行中のタスク数
- **完了/失敗タスク数**: タスクの成功/失敗カウント
- **エラー率**: 全体に対するエラーの割合（%）
- **レスポンス時間**: 処理時間の平均値（ms）
- **キャッシュヒット率**: キャッシュ効率（%）
- **API呼び出し数**: 外部API使用回数

### カスタムメトリクス
```python
# カスタムメトリクス追加
monitor.performance_monitor.get_app_metrics().set_value('custom_metric', 42.5)

# 動的閾値設定
custom_threshold = ThresholdConfig(
    metric_name="custom_metric",
    base_threshold=50.0
)
monitor.alert_system.threshold_manager.register_threshold(custom_threshold)
```

## 拡張とカスタマイズ

### 1. カスタムアラートルール
```python
custom_rule = AlertRule(
    rule_id="custom_business_rule",
    name="ビジネスロジックアラート",
    description="重要なビジネス条件の監視",
    condition="article_processing_rate < 100 and error_rate > 2.0",
    severity=AlertSeverity.HIGH,
    notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK]
)

monitor.alert_system.register_rule(custom_rule)
```

### 2. カスタム通知チャネル
```python
class CustomNotificationChannel:
    async def send_notification(self, alert):
        # カスタム通知ロジック
        await self.custom_api_call(alert)

# カスタムチャネル統合
monitor.alert_system.notification_manager.add_channel(
    'custom', CustomNotificationChannel()
)
```

### 3. プラグインアーキテクチャ
```python
class MonitoringPlugin:
    def __init__(self, monitor):
        self.monitor = monitor
    
    async def initialize(self):
        # プラグイン初期化
        pass
    
    async def process_metrics(self, metrics):
        # メトリクス処理
        return metrics

# プラグイン登録
plugin = CustomMonitoringPlugin(monitor)
await plugin.initialize()
```

## ベストプラクティス

### 1. 監視設計
- **適切な閾値設定**: 業務要件に基づく現実的な閾値
- **アラート疲れ防止**: 抑制ウィンドウとエスカレーション
- **可視性の確保**: 重要メトリクスのダッシュボード表示

### 2. 運用管理
- **定期レポート**: 日次・週次・月次レポートの自動生成
- **容量計画**: リソース使用トレンドの分析
- **災害復旧**: 監視システム自体の冗長化

### 3. パフォーマンス
- **データ保持期間**: 古いデータの自動削除
- **インデックス最適化**: クエリ性能の維持
- **リソース制限**: 監視システム自体のリソース使用量制限

## 今後の拡張予定

### 1. 機械学習の強化
- 予測アラート（将来の異常予測）
- 季節性を考慮した閾値調整
- 自然言語処理によるログ分析

### 2. 分散監視
- 複数インスタンス対応
- クラスター監視
- マイクロサービス連携

### 3. 高度なダッシュボード
- カスタムダッシュボード作成
- レポート自動生成・配信
- モバイル対応

---

このドキュメントは統合監視システムの包括的なガイドです。詳細な実装については各モジュールのソースコードとテストファイルを参照してください。