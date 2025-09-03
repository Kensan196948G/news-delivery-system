"""
統合監視システムのテストスイート
"""
import pytest
import asyncio
import tempfile
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import logging

# テスト対象のインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from monitoring.log_analyzer import LogAnalysisEngine, LogPattern, AnomalyDetection
from monitoring.alert_system import (
    IntelligentAlertSystem, AlertRule, AlertSeverity, AlertStatus,
    DynamicThresholdManager, ThresholdConfig
)
from monitoring.dashboard import MetricsCollector, AlertManager as DashboardAlertManager
from monitoring.integrated_monitor import IntegratedMonitoringSystem
from monitoring.performance_monitor import PerformanceMonitor

# ログ設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def temp_dir():
    """テスト用一時ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def sample_log_file(temp_dir):
    """サンプルログファイル"""
    log_dir = temp_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "test.log"
    sample_logs = [
        "[2024-01-01 10:00:00,123] [INFO] [test.module] System started successfully",
        "[2024-01-01 10:01:00,456] [WARNING] [test.module] High CPU usage detected: 85%",
        "[2024-01-01 10:02:00,789] [ERROR] [test.module] Database connection failed",
        "[2024-01-01 10:03:00,012] [ERROR] [test.module] Database connection failed", 
        "[2024-01-01 10:04:00,345] [CRITICAL] [test.module] OutOfMemoryError occurred",
        "[2024-01-01 10:05:00,678] [INFO] [test.module] System recovery initiated",
        "[2024-01-01 10:06:00,901] [ERROR] [test.module] API rate limit exceeded",
        "[2024-01-01 10:07:00,234] [WARNING] [test.module] Disk space running low"
    ]
    
    with open(log_file, 'w') as f:
        f.write('\n'.join(sample_logs))
    
    return log_file

@pytest.fixture
def monitoring_config():
    """テスト用監視設定"""
    return {
        "performance_monitoring": {
            "collection_interval_seconds": 1,
            "enable_alerts": True
        },
        "log_analysis": {
            "analysis_interval_minutes": 1,
            "log_levels": ["ERROR", "WARNING", "CRITICAL"]
        },
        "alert_system": {
            "suppression_window_seconds": 10,
            "auto_resolve_hours": 1
        },
        "dashboard": {
            "websocket_port": 8766,  # テスト用ポート
            "http_port": 8081,
            "update_interval_seconds": 1
        }
    }

class TestLogAnalysisEngine:
    """ログ分析エンジンのテスト"""
    
    @pytest.mark.asyncio
    async def test_log_parsing(self, temp_dir, sample_log_file):
        """ログパース機能のテスト"""
        engine = LogAnalysisEngine(
            log_directory=str(sample_log_file.parent),
            db_path=str(temp_dir / "test_logs.db")
        )
        
        # ログを解析
        results = await engine.analyze_logs(log_levels=['ERROR', 'WARNING', 'CRITICAL'])
        
        assert 'summary' in results
        assert results['summary']['total_entries'] > 0
        assert results['summary']['error_entries'] > 0
        assert len(results['patterns']) > 0
        
        # パターン検出の確認
        pattern_ids = [p['pattern_id'] for p in results['patterns']]
        assert 'database_error' in pattern_ids or 'dynamic_cluster_0' in pattern_ids
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, temp_dir):
        """異常検知機能のテスト"""
        engine = LogAnalysisEngine(
            log_directory=str(temp_dir / "logs"),
            db_path=str(temp_dir / "test_logs.db")
        )
        
        # 異常検知テスト用のメトリクス
        test_metrics = {
            'cpu_percent': [50, 52, 48, 95, 51, 49],  # 95%が異常値
            'memory_percent': [60, 62, 58, 61, 59, 85],  # 85%が異常値
            'response_time': [200, 210, 190, 205, 195, 2000]  # 2000msが異常値
        }
        
        anomalies = []
        
        for metric_name, values in test_metrics.items():
            for value in values:
                engine.anomaly_detector.add_metric(metric_name, value)
            
            # 最後の値で異常検知
            metric_anomalies = engine.anomaly_detector.detect_anomalies({metric_name: values[-1]})
            anomalies.extend(metric_anomalies)
        
        # 異常が検出されることを確認
        assert len(anomalies) > 0
        
        # 異常の詳細確認
        for anomaly in anomalies:
            assert hasattr(anomaly, 'severity')
            assert hasattr(anomaly, 'confidence_score')
            assert anomaly.severity > 0

class TestAlertSystem:
    """アラートシステムのテスト"""
    
    def test_threshold_manager(self, temp_dir):
        """動的閾値管理のテスト"""
        manager = DynamicThresholdManager(db_path=str(temp_dir / "thresholds.db"))
        
        # 閾値設定を登録
        config = ThresholdConfig(
            metric_name="cpu_percent",
            base_threshold=80.0,
            min_threshold=60.0,
            max_threshold=95.0
        )
        manager.register_threshold(config)
        
        # メトリクス値を追加
        normal_values = [50, 55, 52, 48, 53, 51, 49, 54, 52, 50] * 5  # 正常値
        for value in normal_values:
            manager.add_metric_value("cpu_percent", value)
        
        # 閾値が更新されることを確認
        threshold = manager.get_threshold("cpu_percent")
        assert threshold is not None
        assert 60.0 <= threshold <= 95.0
        
        # 異常値の判定
        assert not manager.is_anomaly("cpu_percent", 55.0)  # 正常
        assert manager.is_anomaly("cpu_percent", 90.0)     # 異常
    
    @pytest.mark.asyncio
    async def test_alert_creation(self, temp_dir):
        """アラート作成のテスト"""
        alert_system = IntelligentAlertSystem(db_path=str(temp_dir / "alerts.db"))
        
        # テスト用のメトリクス（CPU使用率が高い状況）
        test_metrics = {
            'cpu_percent': 95.0,  # 閾値（80%）を超える
            'memory_percent': 75.0  # 正常範囲
        }
        
        # アラートを評価
        alerts = await alert_system.evaluate_metrics(test_metrics)
        
        # CPU使用率のアラートが生成されることを確認
        assert len(alerts) > 0
        
        cpu_alerts = [a for a in alerts if 'cpu' in a.rule_id.lower()]
        assert len(cpu_alerts) > 0
        
        cpu_alert = cpu_alerts[0]
        assert cpu_alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        assert cpu_alert.status == AlertStatus.ACTIVE
        assert 'cpu_percent' in cpu_alert.message.lower()
    
    @pytest.mark.asyncio  
    async def test_alert_escalation(self, temp_dir):
        """アラートエスカレーションのテスト"""
        alert_system = IntelligentAlertSystem(db_path=str(temp_dir / "alerts.db"))
        
        # エスカレーションルール付きのアラートルールを登録
        escalation_rule = AlertRule(
            rule_id="test_escalation",
            name="Test Escalation Rule",
            description="Test rule for escalation",
            condition="test_metric > 90",
            severity=AlertSeverity.MEDIUM,
            escalation_rules=[
                {
                    'time_threshold': 1,  # 1秒でエスカレーション
                    'actions': [
                        {'type': 'severity_increase', 'new_severity': 'HIGH'}
                    ]
                }
            ]
        )
        
        alert_system.register_rule(escalation_rule)
        
        # アラートを作成
        alerts = await alert_system.evaluate_metrics({'test_metric': 95})
        
        if alerts:
            alert = alerts[0]
            original_severity = alert.severity
            
            # アラート作成時刻を過去に設定（エスカレーション条件を満たすため）
            alert.created_at = datetime.now() - timedelta(seconds=2)
            
            # エスカレーションをチェック
            escalated = await alert_system.escalation_manager.check_escalation(alert)
            
            assert escalated
            assert alert.escalation_level > 0

class TestDashboard:
    """ダッシュボードのテスト"""
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """メトリクス収集のテスト"""
        collector = MetricsCollector()
        
        # システムメトリクス収集
        system_metrics = await collector.collect_system_metrics()
        
        assert system_metrics is not None
        assert hasattr(system_metrics, 'cpu_percent')
        assert hasattr(system_metrics, 'memory_percent')
        assert system_metrics.cpu_percent >= 0
        assert system_metrics.memory_percent >= 0
        
        # アプリケーションメトリクス収集
        app_metrics = await collector.collect_application_metrics()
        
        assert app_metrics is not None
        assert hasattr(app_metrics, 'active_agents')
        assert hasattr(app_metrics, 'error_rate')
        assert app_metrics.active_agents >= 0
        assert app_metrics.error_rate >= 0
    
    @pytest.mark.asyncio
    async def test_alert_manager(self, temp_dir):
        """ダッシュボードアラート管理のテスト"""
        alert_manager = DashboardAlertManager(db_path=str(temp_dir / "dashboard_alerts.db"))
        
        # アラート作成
        alert = alert_manager.create_alert(
            severity="HIGH",
            category="System",
            message="Test alert message",
            details={"test_key": "test_value"}
        )
        
        assert alert is not None
        assert alert.severity == "HIGH"
        assert alert.category == "System"
        assert alert.message == "Test alert message"
        assert not alert.acknowledged
        
        # アラート確認
        success = alert_manager.acknowledge_alert(alert.id)
        assert success
        
        # アクティブアラート取得
        active_alerts = alert_manager.get_active_alerts()
        acknowledged_alert = next((a for a in active_alerts if a.id == alert.id), None)
        assert acknowledged_alert is not None
        assert acknowledged_alert.acknowledged

class TestIntegratedSystem:
    """統合システムのテスト"""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, temp_dir, monitoring_config):
        """システム初期化のテスト"""
        system = IntegratedMonitoringSystem(
            db_path=str(temp_dir / "integrated"),
            log_directory=str(temp_dir / "logs"),
            dashboard_config=monitoring_config["dashboard"]
        )
        
        assert system.performance_monitor is not None
        assert system.log_analyzer is not None
        assert system.alert_system is not None
        assert system.dashboard_manager is not None
        assert not system.running
    
    @pytest.mark.asyncio
    async def test_comprehensive_status(self, temp_dir, monitoring_config):
        """包括的ステータス取得のテスト"""
        system = IntegratedMonitoringSystem(
            db_path=str(temp_dir / "integrated"),
            log_directory=str(temp_dir / "logs")
        )
        
        # ステータス取得
        status = await system.get_comprehensive_status()
        
        assert 'timestamp' in status
        assert 'system_running' in status
        assert 'performance' in status
        assert 'alerts' in status
        assert 'dashboard' in status
        
        # パフォーマンス情報の確認
        perf_status = status['performance']
        assert 'monitoring_active' in perf_status
        assert 'current_app_metrics' in perf_status
    
    @pytest.mark.asyncio  
    async def test_health_score_calculation(self, temp_dir):
        """システム健康度計算のテスト"""
        system = IntegratedMonitoringSystem(
            db_path=str(temp_dir / "integrated"),
            log_directory=str(temp_dir / "logs")
        )
        
        # テスト用レポートデータ
        test_report = {
            'performance': {
                'cpu_stats': {'avg': 85.0, 'max': 95.0},  # 高CPU使用率
                'memory_stats': {'avg': 60.0, 'max': 70.0}  # 正常メモリ
            },
            'alerts': {
                'total_alerts': 15,  # 中程度のアラート数
                'escalation_rate': 5.0
            },
            'log_analysis': {
                'anomalies_count': 3  # 少数の異常
            }
        }
        
        # 健康度計算
        health = system._calculate_system_health_score(test_report)
        
        assert 'health_score' in health
        assert 'health_rank' in health
        assert 'issues' in health
        assert 'recommendations' in health
        
        # スコア範囲の確認
        assert 0 <= health['health_score'] <= 100
        
        # 高CPU使用率による問題検出の確認
        issues = health['issues']
        cpu_issue = any('CPU' in issue for issue in issues)
        assert cpu_issue
    
    @pytest.mark.asyncio
    async def test_event_handlers(self, temp_dir):
        """イベントハンドラのテスト"""
        system = IntegratedMonitoringSystem(
            db_path=str(temp_dir / "integrated"),
            log_directory=str(temp_dir / "logs")
        )
        
        # テスト用イベントハンドラ
        handler_calls = []
        
        async def test_handler(data, alerts):
            handler_calls.append((data, alerts))
        
        # ハンドラ登録
        system.add_event_handler('pattern_detected', test_handler)
        
        # ハンドラの登録確認
        assert len(system.event_handlers['pattern_detected']) == 1
        
        # テストパターンでハンドラ実行
        test_pattern = {'pattern_id': 'test', 'severity': 'HIGH', 'frequency': 5}
        await system._handle_log_patterns([test_pattern])
        
        # ハンドラ削除
        system.remove_event_handler('pattern_detected', test_handler)
        assert len(system.event_handlers['pattern_detected']) == 0

class TestPerformanceMonitoring:
    """パフォーマンス監視のテスト"""
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, temp_dir):
        """監視ループのテスト"""
        monitor = PerformanceMonitor(
            db_path=str(temp_dir / "performance.db"),
            collection_interval=0.1  # 高速テスト用
        )
        
        # 監視開始
        await monitor.start_monitoring()
        assert monitor.monitoring
        
        # 短時間待機してメトリクス収集
        await asyncio.sleep(0.5)
        
        # 現在のステータス取得
        status = monitor.get_current_status()
        assert status['monitoring_active']
        assert 'current_app_metrics' in status
        
        # 監視停止
        await monitor.stop_monitoring()
        assert not monitor.monitoring
    
    def test_metrics_storage(self, temp_dir):
        """メトリクス保存のテスト"""
        from monitoring.performance_monitor import PerformanceDataStore, SystemMetrics
        
        data_store = PerformanceDataStore(str(temp_dir / "metrics.db"))
        
        # テスト用システムメトリクス
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=75.5,
            memory_percent=68.2,
            memory_used_mb=4096.0,
            memory_available_mb=2048.0,
            disk_usage_percent=45.8,
            disk_free_gb=100.5,
            network_sent_mb=1.2,
            network_recv_mb=2.3,
            process_count=156,
            thread_count=8
        )
        
        # メトリクス保存
        data_store.store_system_metrics(metrics)
        
        # 履歴取得
        history = data_store.get_metrics_history('system_metrics', hours=1)
        assert len(history) > 0
        
        saved_metrics = history[0]
        assert saved_metrics['cpu_percent'] == 75.5
        assert saved_metrics['memory_percent'] == 68.2

@pytest.mark.integration
class TestSystemIntegration:
    """システム統合テスト"""
    
    @pytest.mark.asyncio
    async def test_full_system_workflow(self, temp_dir, sample_log_file):
        """フルシステムワークフローのテスト"""
        # 統合監視システム作成
        system = IntegratedMonitoringSystem(
            db_path=str(temp_dir / "integrated"),
            log_directory=str(sample_log_file.parent),
            dashboard_config={
                'websocket_port': 8767,  # テスト用ポート
                'http_port': 8082
            }
        )
        
        # イベント収集用
        events = []
        
        async def event_collector(data, alerts):
            events.append(('pattern', data, alerts))
        
        system.add_event_handler('pattern_detected', event_collector)
        
        try:
            # 短時間の監視実行
            monitoring_task = asyncio.create_task(
                system.start_monitoring({
                    'performance': True,
                    'logs': True,
                    'alerts': True,
                    'dashboard': False  # テストではダッシュボードを無効化
                })
            )
            
            # システムが開始されるまで待機
            await asyncio.sleep(2)
            assert system.running
            
            # 高負荷状態をシミュレート
            high_load_metrics = {
                'cpu_percent': 95.0,
                'memory_percent': 90.0,
                'error_rate': 8.5
            }
            
            # アラート評価
            alerts = await system.alert_system.evaluate_metrics(high_load_metrics)
            assert len(alerts) > 0
            
            # 包括的ステータス確認
            status = await system.get_comprehensive_status()
            assert status['system_running']
            assert len(status['alerts']['active_alerts']) > 0
            
            # レポート生成
            report = await system.generate_comprehensive_report(hours=1)
            assert 'system_overview' in report
            assert 'health_score' in report['system_overview']
            
            # システム停止
            monitoring_task.cancel()
            await system.stop_monitoring()
            assert not system.running
            
        except Exception as e:
            await system.stop_monitoring()
            raise

def test_configuration_loading():
    """設定ファイル読み込みのテスト"""
    from monitoring.integrated_monitor import create_monitoring_system
    
    # テスト設定
    test_config = {
        "db_path": "test_monitoring.db",
        "log_directory": "test_logs",
        "dashboard_config": {
            "websocket_port": 9999,
            "http_port": 9998
        }
    }
    
    # 設定から監視システム作成
    system = create_monitoring_system(**test_config)
    
    assert system.db_path == "test_monitoring.db"
    assert system.log_directory == Path("test_logs")
    assert system.dashboard_manager.websocket_server.port == 9999
    assert system.dashboard_manager.http_server.port == 9998

if __name__ == "__main__":
    # テスト実行
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])