"""
Integrated Monitoring System
統合監視システム - エラー処理、パフォーマンス監視、アラート機能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path

from .config import get_config
from .cache_manager import get_cache_manager
from .error_notifier import get_error_notifier, ErrorSeverity
from .performance_monitor import get_performance_monitor


logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """エラーカテゴリ分類"""
    API_RATE_LIMIT = "api_rate_limit"          # 429 エラー
    NETWORK_ERROR = "network_error"            # 接続・タイムアウトエラー
    AUTHENTICATION_ERROR = "authentication_error"  # 401 エラー
    DATA_FORMAT_ERROR = "data_format_error"    # JSON/データ形式エラー
    DISK_SPACE_ERROR = "disk_space_error"      # ディスク容量エラー
    DATABASE_ERROR = "database_error"          # データベースエラー
    TRANSLATION_ERROR = "translation_error"    # 翻訳エラー
    EMAIL_ERROR = "email_error"               # メール送信エラー
    SYSTEM_ERROR = "system_error"             # その他システムエラー


@dataclass
class APIUsageMetrics:
    """API使用量メトリクス"""
    service_name: str
    requests_made: int
    daily_limit: int
    success_rate: float
    avg_response_time: float
    error_count: int
    last_request_time: datetime
    remaining_requests: int


@dataclass
class AlertEvent:
    """アラートイベント"""
    alert_id: str
    category: str
    severity: ErrorSeverity
    message: str
    timestamp: datetime
    context: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class MonitoringSystem:
    """統合監視システム"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache = get_cache_manager()
        self.error_notifier = get_error_notifier()
        self.performance_monitor = get_performance_monitor()
        
        # 監視設定
        self.monitoring_interval = 60  # 1分間隔
        self.api_usage_threshold = 0.8  # 80%使用で警告
        self.disk_usage_threshold = 0.9  # 90%使用で警告
        self.error_rate_threshold = 0.1  # 10%エラー率で警告
        
        # メトリクス履歴
        self.api_metrics: Dict[str, APIUsageMetrics] = {}
        self.alert_history: List[AlertEvent] = []
        self.active_alerts: Dict[str, AlertEvent] = {}
        
        # システム状態
        self.system_status = "healthy"
        self.last_health_check = datetime.now()
        
        # バックグラウンド監視タスク
        self.monitoring_task = None
        self.monitoring_active = False
    
    async def start_monitoring(self):
        """監視開始"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.performance_monitor.start_background_monitoring()
        
        # バックグラウンド監視タスク開始
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Integrated monitoring system started")
    
    async def stop_monitoring(self):
        """監視停止"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.performance_monitor.stop_background_monitoring()
        
        logger.info("Integrated monitoring system stopped")
    
    async def _monitoring_loop(self):
        """監視ループ"""
        while self.monitoring_active:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def _perform_health_check(self):
        """ヘルスチェック実行"""
        try:
            # システムメトリクス収集
            system_metrics = self.performance_monitor.collect_system_metrics()
            
            # API使用量チェック
            await self._check_api_usage()
            
            # ディスク容量チェック
            await self._check_disk_usage(system_metrics.disk_usage_percent)
            
            # エラー率チェック
            await self._check_error_rates()
            
            # システム状態更新
            self._update_system_status()
            
            self.last_health_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            await self._create_alert(
                "health_check_failed",
                "system",
                ErrorSeverity.HIGH,
                f"Health check failed: {str(e)}",
                {"error": str(e)}
            )
    
    async def handle_error_with_classification(self, error: Exception, context: str = "") -> ErrorCategory:
        """エラー分類とハンドリング"""
        try:
            # エラー分類
            error_category = self._classify_error(error)
            
            # カテゴリ別処理
            await self._handle_categorized_error(error, error_category, context)
            
            # エラー統計更新
            self._update_error_statistics(error_category, context)
            
            return error_category
            
        except Exception as handling_error:
            logger.error(f"Error handling failed: {handling_error}")
            return ErrorCategory.SYSTEM_ERROR
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """エラー分類"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # HTTP 429 エラー
        if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
            return ErrorCategory.API_RATE_LIMIT
        
        # HTTP 401 エラー
        if "401" in error_str or "unauthorized" in error_str or "authentication" in error_str:
            return ErrorCategory.AUTHENTICATION_ERROR
        
        # ネットワークエラー
        if any(keyword in error_str for keyword in [
            "connection", "timeout", "network", "dns", "socket", "http"
        ]) or any(keyword in error_type for keyword in [
            "connectionerror", "timeout", "httperror"
        ]):
            return ErrorCategory.NETWORK_ERROR
        
        # データ形式エラー
        if any(keyword in error_str for keyword in [
            "json", "parse", "decode", "format", "invalid"
        ]) or any(keyword in error_type for keyword in [
            "jsondecodeerror", "valueerror", "typeerror"
        ]):
            return ErrorCategory.DATA_FORMAT_ERROR
        
        # ディスク容量エラー
        if any(keyword in error_str for keyword in [
            "no space", "disk full", "storage"
        ]):
            return ErrorCategory.DISK_SPACE_ERROR
        
        # データベースエラー
        if any(keyword in error_str for keyword in [
            "database", "sql", "sqlite", "cursor"
        ]):
            return ErrorCategory.DATABASE_ERROR
        
        # 翻訳エラー
        if any(keyword in error_str for keyword in [
            "translation", "deepl", "translate"
        ]):
            return ErrorCategory.TRANSLATION_ERROR
        
        # メールエラー
        if any(keyword in error_str for keyword in [
            "gmail", "email", "smtp", "mail"
        ]):
            return ErrorCategory.EMAIL_ERROR
        
        return ErrorCategory.SYSTEM_ERROR
    
    async def _handle_categorized_error(self, error: Exception, category: ErrorCategory, context: str):
        """カテゴリ別エラー処理"""
        severity = ErrorSeverity.MEDIUM
        
        if category == ErrorCategory.API_RATE_LIMIT:
            # レート制限エラー: 待機後リトライ (ログのみ、通知なし)
            logger.warning(f"API rate limit hit in {context}: {error}")
            severity = ErrorSeverity.LOW
            
        elif category == ErrorCategory.NETWORK_ERROR:
            # ネットワークエラー: 即座リトライ (ログのみ)
            logger.warning(f"Network error in {context}: {error}")
            severity = ErrorSeverity.LOW
            
        elif category == ErrorCategory.AUTHENTICATION_ERROR:
            # 認証エラー: 即座通知
            severity = ErrorSeverity.HIGH
            await self._create_alert(
                f"auth_error_{context}",
                "authentication",
                severity,
                f"Authentication failed in {context}: {str(error)}",
                {"context": context, "error_type": type(error).__name__}
            )
            
        elif category == ErrorCategory.DATA_FORMAT_ERROR:
            # データ形式エラー: ログ記録・スキップ
            logger.info(f"Data format error in {context}, skipping: {error}")
            severity = ErrorSeverity.LOW
            
        elif category == ErrorCategory.DISK_SPACE_ERROR:
            # ディスク容量エラー: 緊急通知
            severity = ErrorSeverity.CRITICAL
            await self._create_alert(
                "disk_space_critical",
                "system",
                severity,
                f"Disk space critical: {str(error)}",
                {"context": context}
            )
            
        else:
            # その他エラー: 通常処理
            severity = ErrorSeverity.MEDIUM
        
        # エラー通知システムに転送
        await self.error_notifier.handle_error(error, context, severity)
    
    def _update_error_statistics(self, category: ErrorCategory, context: str):
        """エラー統計更新"""
        try:
            stats_key = f"error_stats_{category.value}"
            current_stats = self.cache.get(stats_key, 'monitoring') or {
                'count': 0,
                'contexts': {},
                'last_occurrence': None
            }
            
            current_stats['count'] += 1
            current_stats['contexts'][context] = current_stats['contexts'].get(context, 0) + 1
            current_stats['last_occurrence'] = datetime.now().isoformat()
            
            self.cache.set(stats_key, current_stats, expire=86400, category='monitoring')
            
        except Exception as e:
            logger.error(f"Failed to update error statistics: {e}")
    
    async def track_api_usage(self, service_name: str, success: bool, response_time: float):
        """API使用量トラッキング"""
        try:
            # 既存メトリクス取得または初期化
            if service_name not in self.api_metrics:
                # collectorsからサービス状況取得
                self.api_metrics[service_name] = APIUsageMetrics(
                    service_name=service_name,
                    requests_made=0,
                    daily_limit=1000,  # デフォルト値
                    success_rate=1.0,
                    avg_response_time=0.0,
                    error_count=0,
                    last_request_time=datetime.now(),
                    remaining_requests=1000
                )
            
            metrics = self.api_metrics[service_name]
            
            # メトリクス更新
            metrics.requests_made += 1
            metrics.last_request_time = datetime.now()
            
            if success:
                # 成功率の移動平均計算
                metrics.success_rate = (metrics.success_rate * 0.9 + 1.0 * 0.1)
            else:
                metrics.error_count += 1
                metrics.success_rate = (metrics.success_rate * 0.9 + 0.0 * 0.1)
            
            # レスポンス時間の移動平均
            metrics.avg_response_time = (metrics.avg_response_time * 0.9 + response_time * 0.1)
            metrics.remaining_requests = max(0, metrics.daily_limit - metrics.requests_made)
            
            # 使用量警告チェック
            usage_ratio = metrics.requests_made / metrics.daily_limit
            if usage_ratio >= self.api_usage_threshold:
                await self._create_alert(
                    f"api_usage_high_{service_name}",
                    "api_usage",
                    ErrorSeverity.MEDIUM,
                    f"API usage high for {service_name}: {usage_ratio*100:.1f}% used",
                    {
                        "service": service_name,
                        "usage_ratio": usage_ratio,
                        "requests_made": metrics.requests_made,
                        "daily_limit": metrics.daily_limit
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to track API usage for {service_name}: {e}")
    
    async def _check_api_usage(self):
        """API使用量チェック"""
        try:
            # collectors から実際の使用状況を取得
            from services.news_collector import NewsCollector
            collector = NewsCollector(self.config)
            collector_status = collector.get_collector_status()
            
            for service_name, service_data in collector_status.get('collectors', {}).items():
                if service_data.get('status') != 'disabled':
                    requests_made = service_data.get('requests_made', 0)
                    daily_limit = service_data.get('daily_limit', 1000)
                    remaining = service_data.get('remaining_requests', daily_limit)
                    
                    # API使用量更新
                    self.api_metrics[service_name] = APIUsageMetrics(
                        service_name=service_name,
                        requests_made=requests_made,
                        daily_limit=daily_limit,
                        success_rate=0.95,  # デフォルト値
                        avg_response_time=1000,  # デフォルト値
                        error_count=0,
                        last_request_time=datetime.now(),
                        remaining_requests=remaining
                    )
                    
                    # 警告チェック
                    if remaining < daily_limit * 0.2:  # 残り20%以下
                        await self._create_alert(
                            f"api_limit_warning_{service_name}",
                            "api_usage",
                            ErrorSeverity.MEDIUM,
                            f"API limit warning: {service_name} has {remaining} requests remaining",
                            {"service": service_name, "remaining": remaining, "limit": daily_limit}
                        )
                        
        except Exception as e:
            logger.error(f"Failed to check API usage: {e}")
    
    async def _check_disk_usage(self, disk_usage_percent: float):
        """ディスク容量チェック"""
        try:
            if disk_usage_percent >= self.disk_usage_threshold * 100:
                await self._create_alert(
                    "disk_usage_critical",
                    "system",
                    ErrorSeverity.CRITICAL,
                    f"Disk usage critical: {disk_usage_percent:.1f}%",
                    {"disk_usage_percent": disk_usage_percent}
                )
            elif disk_usage_percent >= 0.8 * 100:  # 80%で警告
                await self._create_alert(
                    "disk_usage_warning",
                    "system",
                    ErrorSeverity.MEDIUM,
                    f"Disk usage high: {disk_usage_percent:.1f}%",
                    {"disk_usage_percent": disk_usage_percent}
                )
                
        except Exception as e:
            logger.error(f"Failed to check disk usage: {e}")
    
    async def _check_error_rates(self):
        """エラー率チェック"""
        try:
            # 過去24時間のエラー統計取得
            total_errors = 0
            total_operations = 0
            
            for category in ErrorCategory:
                stats_key = f"error_stats_{category.value}"
                stats = self.cache.get(stats_key, 'monitoring')
                if stats:
                    total_errors += stats.get('count', 0)
            
            # パフォーマンス履歴から総操作数取得
            perf_summary = self.performance_monitor.get_performance_summary(hours=24)
            total_operations = perf_summary.get('total_operations', 1)
            
            if total_operations > 0:
                error_rate = total_errors / total_operations
                
                if error_rate >= self.error_rate_threshold:
                    await self._create_alert(
                        "high_error_rate",
                        "system",
                        ErrorSeverity.HIGH,
                        f"High error rate detected: {error_rate*100:.1f}%",
                        {
                            "error_rate": error_rate,
                            "total_errors": total_errors,
                            "total_operations": total_operations
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Failed to check error rates: {e}")
    
    async def _create_alert(self, alert_id: str, category: str, severity: ErrorSeverity, 
                           message: str, context: Dict[str, Any]):
        """アラート作成"""
        try:
            # 重複アラートチェック（同じIDのアクティブアラートがあるか）
            if alert_id in self.active_alerts:
                return
            
            alert = AlertEvent(
                alert_id=alert_id,
                category=category,
                severity=severity,
                message=message,
                timestamp=datetime.now(),
                context=context
            )
            
            # アクティブアラートに追加
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # 履歴サイズ制限
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]
            
            # 重要度に応じて通知
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                await self.error_notifier.send_critical_alert(message, f"Alert: {category}")
            
            logger.warning(f"Alert created: {alert_id} - {message}")
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    async def resolve_alert(self, alert_id: str):
        """アラート解決"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = datetime.now()
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert_id}")
    
    def _update_system_status(self):
        """システム状態更新"""
        try:
            # アクティブな重要アラートをチェック
            critical_alerts = [
                alert for alert in self.active_alerts.values()
                if alert.severity == ErrorSeverity.CRITICAL
            ]
            
            high_alerts = [
                alert for alert in self.active_alerts.values()
                if alert.severity == ErrorSeverity.HIGH
            ]
            
            if critical_alerts:
                self.system_status = "critical"
            elif high_alerts:
                self.system_status = "degraded"
            elif len(self.active_alerts) > 5:
                self.system_status = "warning"
            else:
                self.system_status = "healthy"
                
        except Exception as e:
            logger.error(f"Failed to update system status: {e}")
            self.system_status = "unknown"
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """監視ダッシュボード情報取得"""
        try:
            # システム現在状況
            current_status = self.performance_monitor.get_current_status()
            
            # API使用状況
            api_status = {
                service: {
                    "requests_made": metrics.requests_made,
                    "daily_limit": metrics.daily_limit,
                    "usage_percentage": (metrics.requests_made / metrics.daily_limit * 100) if metrics.daily_limit > 0 else 0,
                    "success_rate": metrics.success_rate,
                    "avg_response_time": metrics.avg_response_time,
                    "remaining_requests": metrics.remaining_requests
                }
                for service, metrics in self.api_metrics.items()
            }
            
            # アクティブアラート
            active_alerts_summary = [
                {
                    "alert_id": alert.alert_id,
                    "category": alert.category,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "context": alert.context
                }
                for alert in self.active_alerts.values()
            ]
            
            # エラー統計
            error_stats = {}
            for category in ErrorCategory:
                stats_key = f"error_stats_{category.value}"
                stats = self.cache.get(stats_key, 'monitoring')
                if stats:
                    error_stats[category.value] = stats
            
            return {
                "system_status": self.system_status,
                "last_health_check": self.last_health_check.isoformat(),
                "monitoring_active": self.monitoring_active,
                "current_system_metrics": current_status,
                "api_usage": api_status,
                "active_alerts": active_alerts_summary,
                "alert_count": len(self.active_alerts),
                "error_statistics": error_stats,
                "thresholds": {
                    "api_usage_threshold": self.api_usage_threshold,
                    "disk_usage_threshold": self.disk_usage_threshold,
                    "error_rate_threshold": self.error_rate_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitoring dashboard: {e}")
            return {"error": str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """ヘルス状態取得"""
        return {
            "status": self.system_status,
            "last_check": self.last_health_check.isoformat(),
            "monitoring_active": self.monitoring_active,
            "active_alerts_count": len(self.active_alerts),
            "critical_alerts": len([a for a in self.active_alerts.values() if a.severity == ErrorSeverity.CRITICAL]),
            "high_alerts": len([a for a in self.active_alerts.values() if a.severity == ErrorSeverity.HIGH])
        }


# グローバル監視システムインスタンス
_monitoring_system_instance = None


def get_monitoring_system() -> MonitoringSystem:
    """グローバル監視システムインスタンス取得"""
    global _monitoring_system_instance
    if _monitoring_system_instance is None:
        _monitoring_system_instance = MonitoringSystem()
    return _monitoring_system_instance