"""
Unit Tests for MonitoringSystem
統合監視システムのユニットテスト
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.utils.error_notifier import ErrorSeverity
from src.utils.monitoring_system import (
    AlertEvent,
    APIUsageMetrics,
    ErrorCategory,
    MonitoringSystem,
    get_monitoring_system,
)


class TestErrorCategory:
    """ErrorCategoryテスト"""

    def test_error_category_values(self):
        """エラーカテゴリの値をテスト"""
        assert ErrorCategory.API_RATE_LIMIT.value == "api_rate_limit"
        assert ErrorCategory.NETWORK_ERROR.value == "network_error"
        assert ErrorCategory.AUTHENTICATION_ERROR.value == "authentication_error"
        assert ErrorCategory.DATA_FORMAT_ERROR.value == "data_format_error"
        assert ErrorCategory.DISK_SPACE_ERROR.value == "disk_space_error"


class TestAPIUsageMetrics:
    """APIUsageMetricsテスト"""

    def test_api_usage_metrics_creation(self):
        """APIUsageMetrics作成テスト"""
        metrics = APIUsageMetrics(
            service_name="newsapi",
            requests_made=150,
            daily_limit=1000,
            success_rate=0.95,
            avg_response_time=1200,
            error_count=5,
            last_request_time=datetime.now(),
            remaining_requests=850,
        )

        assert metrics.service_name == "newsapi"
        assert metrics.requests_made == 150
        assert metrics.success_rate == 0.95


class TestAlertEvent:
    """AlertEventテスト"""

    def test_alert_event_creation(self):
        """AlertEvent作成テスト"""
        alert = AlertEvent(
            alert_id="test_alert",
            category="api_usage",
            severity=ErrorSeverity.HIGH,
            message="Test alert message",
            timestamp=datetime.now(),
            context={"test": "data"},
        )

        assert alert.alert_id == "test_alert"
        assert alert.severity == ErrorSeverity.HIGH
        assert not alert.resolved
        assert alert.resolution_time is None


@pytest.fixture
def mock_config():
    """設定モック"""
    return Mock()


@pytest.fixture
def mock_cache():
    """キャッシュマネージャーモック"""
    cache_mock = Mock()
    cache_mock.get.return_value = None
    cache_mock.set.return_value = None
    return cache_mock


@pytest.fixture
def mock_error_notifier():
    """エラー通知モック"""
    notifier_mock = AsyncMock()
    notifier_mock.handle_error = AsyncMock()
    notifier_mock.send_critical_alert = AsyncMock()
    return notifier_mock


@pytest.fixture
def mock_performance_monitor():
    """パフォーマンス監視モック"""
    monitor_mock = Mock()
    monitor_mock.start_background_monitoring = Mock()
    monitor_mock.stop_background_monitoring = Mock()
    monitor_mock.collect_system_metrics = Mock()
    monitor_mock.get_performance_summary = Mock(return_value={"total_operations": 100})
    monitor_mock.get_current_status = Mock(return_value={"cpu_percent": 50})
    return monitor_mock


@pytest.fixture
def monitoring_system(
    mock_config, mock_cache, mock_error_notifier, mock_performance_monitor
):
    """MonitoringSystemインスタンス"""
    with patch(
        "src.utils.monitoring_system.get_config", return_value=mock_config
    ), patch(
        "src.utils.monitoring_system.get_cache_manager", return_value=mock_cache
    ), patch(
        "src.utils.monitoring_system.get_error_notifier",
        return_value=mock_error_notifier,
    ), patch(
        "src.utils.monitoring_system.get_performance_monitor",
        return_value=mock_performance_monitor,
    ):
        system = MonitoringSystem()
        return system


class TestMonitoringSystem:
    """MonitoringSystemテスト"""

    def test_initialization(self, monitoring_system):
        """初期化テスト"""
        assert monitoring_system.system_status == "healthy"
        assert not monitoring_system.monitoring_active
        assert monitoring_system.api_usage_threshold == 0.8
        assert monitoring_system.disk_usage_threshold == 0.9

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitoring_system):
        """監視開始・停止テスト"""
        # 監視開始
        await monitoring_system.start_monitoring()
        assert monitoring_system.monitoring_active
        assert monitoring_system.monitoring_task is not None

        # 重複開始の確認
        with patch("src.utils.monitoring_system.logger") as mock_logger:
            await monitoring_system.start_monitoring()
            mock_logger.warning.assert_called_with("Monitoring already active")

        # 監視停止
        await monitoring_system.stop_monitoring()
        assert not monitoring_system.monitoring_active

    def test_classify_error(self, monitoring_system):
        """エラー分類テスト"""
        # API制限エラー
        rate_limit_error = Exception("429 Too Many Requests")
        assert (
            monitoring_system._classify_error(rate_limit_error)
            == ErrorCategory.API_RATE_LIMIT
        )

        # 認証エラー
        auth_error = Exception("401 Unauthorized")
        assert (
            monitoring_system._classify_error(auth_error)
            == ErrorCategory.AUTHENTICATION_ERROR
        )

        # ネットワークエラー
        network_error = Exception("Connection timeout")
        assert (
            monitoring_system._classify_error(network_error)
            == ErrorCategory.NETWORK_ERROR
        )

        # データ形式エラー
        json_error = Exception("JSON decode error")
        assert (
            monitoring_system._classify_error(json_error)
            == ErrorCategory.DATA_FORMAT_ERROR
        )

        # ディスク容量エラー
        disk_error = Exception("No space left on device")
        assert (
            monitoring_system._classify_error(disk_error)
            == ErrorCategory.DISK_SPACE_ERROR
        )

        # その他エラー
        other_error = Exception("Unknown error")
        assert (
            monitoring_system._classify_error(other_error) == ErrorCategory.SYSTEM_ERROR
        )

    @pytest.mark.asyncio
    async def test_handle_error_with_classification(self, monitoring_system):
        """エラー分類ハンドリングテスト"""
        test_error = Exception("429 Too Many Requests")

        with patch.object(monitoring_system, "_update_error_statistics") as mock_update:
            category = await monitoring_system.handle_error_with_classification(
                test_error, "test_context"
            )

            assert category == ErrorCategory.API_RATE_LIMIT
            mock_update.assert_called_once_with(
                ErrorCategory.API_RATE_LIMIT, "test_context"
            )

    @pytest.mark.asyncio
    async def test_handle_categorized_error_critical(self, monitoring_system):
        """重要エラー処理テスト"""
        disk_error = Exception("No space left")

        with patch.object(monitoring_system, "_create_alert") as mock_alert:
            await monitoring_system._handle_categorized_error(
                disk_error, ErrorCategory.DISK_SPACE_ERROR, "test_context"
            )

            mock_alert.assert_called_once()
            args, kwargs = mock_alert.call_args
            assert args[2] == ErrorSeverity.CRITICAL  # severity

    @pytest.mark.asyncio
    async def test_track_api_usage(self, monitoring_system):
        """API使用量トラッキングテスト"""
        await monitoring_system.track_api_usage("newsapi", True, 1500)

        assert "newsapi" in monitoring_system.api_metrics
        metrics = monitoring_system.api_metrics["newsapi"]
        assert metrics.service_name == "newsapi"
        assert metrics.requests_made == 1
        assert metrics.avg_response_time > 0

    @pytest.mark.asyncio
    async def test_track_api_usage_warning(self, monitoring_system):
        """API使用量警告テスト"""
        # 高使用量状態を模擬
        monitoring_system.api_metrics["test_api"] = APIUsageMetrics(
            service_name="test_api",
            requests_made=850,  # 85%使用
            daily_limit=1000,
            success_rate=0.95,
            avg_response_time=1000,
            error_count=0,
            last_request_time=datetime.now(),
            remaining_requests=150,
        )

        with patch.object(monitoring_system, "_create_alert") as mock_alert:
            await monitoring_system.track_api_usage("test_api", True, 1000)

            # 警告が発生するはず（85% + 1回 = 86% > 80%閾値）
            mock_alert.assert_called_once()

    def test_update_error_statistics(self, monitoring_system, mock_cache):
        """エラー統計更新テスト"""
        mock_cache.get.return_value = {
            "count": 5,
            "contexts": {"test_context": 2},
            "last_occurrence": None,
        }

        monitoring_system._update_error_statistics(
            ErrorCategory.NETWORK_ERROR, "test_context"
        )

        mock_cache.set.assert_called_once()
        args, kwargs = mock_cache.set.call_args
        updated_stats = args[1]
        assert updated_stats["count"] == 6
        assert updated_stats["contexts"]["test_context"] == 3

    @pytest.mark.asyncio
    async def test_create_alert(self, monitoring_system):
        """アラート作成テスト"""
        await monitoring_system._create_alert(
            "test_alert",
            "test_category",
            ErrorSeverity.HIGH,
            "Test message",
            {"key": "value"},
        )

        assert "test_alert" in monitoring_system.active_alerts
        assert len(monitoring_system.alert_history) == 1

        alert = monitoring_system.active_alerts["test_alert"]
        assert alert.message == "Test message"
        assert alert.severity == ErrorSeverity.HIGH

    @pytest.mark.asyncio
    async def test_create_duplicate_alert(self, monitoring_system):
        """重複アラート防止テスト"""
        # 最初のアラート
        await monitoring_system._create_alert(
            "dup_alert", "category", ErrorSeverity.MEDIUM, "Message 1", {}
        )

        # 重複アラート（作成されないはず）
        await monitoring_system._create_alert(
            "dup_alert", "category", ErrorSeverity.MEDIUM, "Message 2", {}
        )

        assert len(monitoring_system.active_alerts) == 1
        assert monitoring_system.active_alerts["dup_alert"].message == "Message 1"

    @pytest.mark.asyncio
    async def test_resolve_alert(self, monitoring_system):
        """アラート解決テスト"""
        # アラート作成
        await monitoring_system._create_alert(
            "resolve_test", "category", ErrorSeverity.MEDIUM, "Test", {}
        )

        # アラート解決
        await monitoring_system.resolve_alert("resolve_test")

        assert "resolve_test" not in monitoring_system.active_alerts
        # 履歴には残る
        assert len(monitoring_system.alert_history) == 1
        assert monitoring_system.alert_history[0].resolved
        assert monitoring_system.alert_history[0].resolution_time is not None

    def test_update_system_status(self, monitoring_system):
        """システム状態更新テスト"""
        # 正常状態
        monitoring_system._update_system_status()
        assert monitoring_system.system_status == "healthy"

        # CRITICALアラート追加
        monitoring_system.active_alerts["critical_alert"] = AlertEvent(
            alert_id="critical_alert",
            category="system",
            severity=ErrorSeverity.CRITICAL,
            message="Critical error",
            timestamp=datetime.now(),
            context={},
        )

        monitoring_system._update_system_status()
        assert monitoring_system.system_status == "critical"

    @pytest.mark.asyncio
    async def test_check_disk_usage_warning(self, monitoring_system):
        """ディスク使用量警告テスト"""
        with patch.object(monitoring_system, "_create_alert") as mock_alert:
            # 警告レベル（85%）
            await monitoring_system._check_disk_usage(85.0)
            mock_alert.assert_called_once()

            # 警告内容確認
            args, kwargs = mock_alert.call_args
            assert args[0] == "disk_usage_warning"
            assert args[2] == ErrorSeverity.MEDIUM

    @pytest.mark.asyncio
    async def test_check_disk_usage_critical(self, monitoring_system):
        """ディスク使用量重要警告テスト"""
        with patch.object(monitoring_system, "_create_alert") as mock_alert:
            # 重要レベル（95%）
            await monitoring_system._check_disk_usage(95.0)
            mock_alert.assert_called_once()

            # 重要警告内容確認
            args, kwargs = mock_alert.call_args
            assert args[0] == "disk_usage_critical"
            assert args[2] == ErrorSeverity.CRITICAL

    def test_get_monitoring_dashboard(self, monitoring_system):
        """監視ダッシュボード取得テスト"""
        # テストデータ設定
        monitoring_system.api_metrics["test_service"] = APIUsageMetrics(
            service_name="test_service",
            requests_made=100,
            daily_limit=1000,
            success_rate=0.95,
            avg_response_time=1500,
            error_count=5,
            last_request_time=datetime.now(),
            remaining_requests=900,
        )

        dashboard = monitoring_system.get_monitoring_dashboard()

        assert "system_status" in dashboard
        assert "api_usage" in dashboard
        assert "active_alerts" in dashboard
        assert "thresholds" in dashboard

        # API使用状況確認
        api_status = dashboard["api_usage"]["test_service"]
        assert api_status["requests_made"] == 100
        assert api_status["usage_percentage"] == 10.0

    def test_get_health_status(self, monitoring_system):
        """ヘルス状態取得テスト"""
        health = monitoring_system.get_health_status()

        assert "status" in health
        assert "monitoring_active" in health
        assert "active_alerts_count" in health
        assert health["active_alerts_count"] == 0


class TestGlobalFunctions:
    """グローバル関数テスト"""

    def test_get_monitoring_system_singleton(self):
        """シングルトン動作テスト"""
        from src.utils import monitoring_system as ms

        ms._monitoring_system_instance = None

        with patch("src.utils.monitoring_system.MonitoringSystem") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            # 最初の呼び出し
            system1 = get_monitoring_system()
            # 2回目の呼び出し
            system2 = get_monitoring_system()

            # 同じインスタンスが返される
            assert system1 is system2
            # MonitoringSystemは1回だけ作成される
            assert mock_class.call_count == 1


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """統合シナリオテスト"""

    async def test_full_error_handling_workflow(self, monitoring_system):
        """完全なエラーハンドリングワークフローテスト"""
        # 複数のエラーを発生させる
        errors = [
            (Exception("429 Too Many Requests"), "api_test"),
            (Exception("Connection timeout"), "network_test"),
            (Exception("401 Unauthorized"), "auth_test"),
        ]

        with patch.object(monitoring_system, "_create_alert") as mock_alert:
            categories = []
            for error, context in errors:
                category = await monitoring_system.handle_error_with_classification(
                    error, context
                )
                categories.append(category)

            # 期待されるカテゴリ
            expected_categories = [
                ErrorCategory.API_RATE_LIMIT,
                ErrorCategory.NETWORK_ERROR,
                ErrorCategory.AUTHENTICATION_ERROR,
            ]

            assert categories == expected_categories

            # 認証エラーのみアラート生成される（HIGH severity）
            assert mock_alert.call_count == 1

    async def test_monitoring_loop_simulation(self, monitoring_system):
        """監視ループシミュレーション"""
        # ヘルスチェック実行
        with patch.object(
            monitoring_system, "_perform_health_check"
        ) as mock_health_check:
            mock_health_check.return_value = None

            # 短時間の監視ループをシミュレート
            monitoring_system.monitoring_interval = 0.1  # 100ms

            await monitoring_system.start_monitoring()
            await asyncio.sleep(0.3)  # 300ms待機（3回実行される）
            await monitoring_system.stop_monitoring()

            # ヘルスチェックが複数回実行されることを確認
            assert mock_health_check.call_count >= 2
