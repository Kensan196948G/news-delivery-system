"""
統合監視システム
既存のperformance_monitor、新しいlog_analyzer、dashboard、alert_systemを統合
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import json
import threading

# 既存の監視システム
from .performance_monitor import PerformanceMonitor, ApplicationMetricsCollector

# 新しい監視コンポーネント
from .log_analyzer import LogAnalysisEngine, LogPattern, AnomalyDetection
from .dashboard import (
    DashboardManager, WebSocketServer, MetricsCollector as DashboardMetricsCollector,
    AlertManager as DashboardAlertManager, AlertData
)
from .alert_system import (
    IntelligentAlertSystem, Alert, AlertRule, AlertSeverity, AlertStatus,
    NotificationChannel, DynamicThresholdManager, NotificationManager
)

logger = logging.getLogger(__name__)

class IntegratedMonitoringSystem:
    """統合監視システムのメインクラス"""
    
    def __init__(
        self,
        db_path: str = "integrated_monitoring.db",
        log_directory: str = "logs",
        dashboard_config: Dict[str, Any] = None,
        notification_config: Dict[str, Any] = None
    ):
        self.db_path = db_path
        self.log_directory = Path(log_directory)
        
        # コンポーネント初期化
        self.performance_monitor = PerformanceMonitor(
            db_path=f"{db_path}_performance.db"
        )
        
        self.log_analyzer = LogAnalysisEngine(
            log_directory=str(self.log_directory),
            db_path=f"{db_path}_logs.db"
        )
        
        self.alert_system = IntelligentAlertSystem(
            db_path=f"{db_path}_alerts.db"
        )
        
        # ダッシュボード設定
        dashboard_config = dashboard_config or {}
        self.dashboard_manager = DashboardManager(
            websocket_host=dashboard_config.get('websocket_host', 'localhost'),
            websocket_port=dashboard_config.get('websocket_port', 8765),
            http_host=dashboard_config.get('http_host', 'localhost'),
            http_port=dashboard_config.get('http_port', 8080),
            static_dir=dashboard_config.get('static_dir', 'static')
        )
        
        # 統合された状態管理
        self.running = False
        self.monitoring_tasks = []
        
        # イベントハンドラ
        self.event_handlers: Dict[str, List[Callable]] = {
            'alert_created': [],
            'pattern_detected': [],
            'anomaly_detected': [],
            'performance_threshold_exceeded': []
        }
        
        # 設定統合監視を開始
        self._setup_integrations()
        
    def _setup_integrations(self):
        """各コンポーネント間の統合設定"""
        # パフォーマンス監視のアラートを統合アラートシステムに転送
        if hasattr(self.performance_monitor, 'alert_manager') and self.performance_monitor.alert_manager:
            self.performance_monitor.alert_manager.add_alert_callback(
                self._handle_performance_alert
            )
        
        # ダッシュボードにアラートシステムを統合
        self.dashboard_manager.websocket_server.alert_manager = self.alert_system
        
        logger.info("Component integrations configured")
    
    def _handle_performance_alert(self, perf_alert):
        """パフォーマンスアラートを統合アラートシステムに転送"""
        try:
            # パフォーマンスアラートを統合アラート形式に変換
            severity_map = {
                'WARNING': AlertSeverity.MEDIUM,
                'CRITICAL': AlertSeverity.CRITICAL,
                'ERROR': AlertSeverity.HIGH
            }
            
            severity = severity_map.get(perf_alert.severity, AlertSeverity.LOW)
            
            # 統合アラートシステムでアラートを作成
            alert_rule = AlertRule(
                rule_id=f"performance_{perf_alert.category.lower()}_{perf_alert.metric_name}",
                name=f"Performance Alert: {perf_alert.metric_name}",
                description=perf_alert.message,
                condition=f"{perf_alert.metric_name} > {perf_alert.threshold_value}",
                severity=severity,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DESKTOP]
            )
            
            # ルールが存在しない場合は登録
            if alert_rule.rule_id not in self.alert_system.alert_rules:
                self.alert_system.register_rule(alert_rule)
            
            # アラートを評価（非同期で実行）
            metrics = {perf_alert.metric_name: perf_alert.current_value}
            asyncio.create_task(self._evaluate_performance_alert(metrics))
            
        except Exception as e:
            logger.error(f"Error handling performance alert: {e}")
    
    async def _evaluate_performance_alert(self, metrics: Dict[str, Any]):
        """パフォーマンスアラートの評価を非同期で実行"""
        try:
            alerts = await self.alert_system.evaluate_metrics(metrics)
            
            # ダッシュボードに通知
            for alert in alerts:
                dashboard_alert = AlertData(
                    id=alert.id,
                    timestamp=alert.created_at,
                    severity=alert.severity.value,
                    category=f"Performance/{alert.rule_id}",
                    message=alert.message,
                    details=alert.details
                )
                
                await self.dashboard_manager.websocket_server.broadcast_alert(dashboard_alert)
                
        except Exception as e:
            logger.error(f"Error evaluating performance alert: {e}")
    
    async def start_monitoring(self, enable_components: Dict[str, bool] = None):
        """統合監視システムを開始"""
        if self.running:
            logger.warning("Monitoring system is already running")
            return
        
        enable_components = enable_components or {
            'performance': True,
            'logs': True,
            'alerts': True,
            'dashboard': True
        }
        
        self.running = True
        logger.info("Starting integrated monitoring system...")
        
        try:
            # パフォーマンス監視開始
            if enable_components.get('performance', True):
                await self.performance_monitor.start_monitoring()
                logger.info("Performance monitoring started")
            
            # アラートシステム開始
            if enable_components.get('alerts', True):
                await self.alert_system.start_background_monitoring()
                logger.info("Alert system started")
            
            # 統合監視ループを開始
            monitoring_tasks = []
            
            # ログ分析タスク
            if enable_components.get('logs', True):
                monitoring_tasks.append(
                    asyncio.create_task(self._log_analysis_loop())
                )
                
            # メトリクス統合タスク
            monitoring_tasks.append(
                asyncio.create_task(self._metrics_integration_loop())
            )
            
            # ダッシュボード（別タスクで起動）
            if enable_components.get('dashboard', True):
                monitoring_tasks.append(
                    asyncio.create_task(self.dashboard_manager.start())
                )
            
            self.monitoring_tasks = monitoring_tasks
            
            logger.info("Integrated monitoring system started successfully")
            
            # メインタスクを待機
            await asyncio.gather(*monitoring_tasks)
            
        except Exception as e:
            logger.error(f"Error starting monitoring system: {e}")
            await self.stop_monitoring()
            raise
    
    async def stop_monitoring(self):
        """統合監視システムを停止"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping integrated monitoring system...")
        
        try:
            # 監視タスクをキャンセル
            for task in self.monitoring_tasks:
                if not task.done():
                    task.cancel()
            
            # 完了を待つ
            if self.monitoring_tasks:
                await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            
            # 各コンポーネントを停止
            await self.performance_monitor.stop_monitoring()
            await self.alert_system.stop_background_monitoring()
            
            logger.info("Integrated monitoring system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring system: {e}")
    
    async def _log_analysis_loop(self):
        """ログ分析ループ"""
        logger.info("Starting log analysis loop")
        
        while self.running:
            try:
                # 過去1時間のログを分析
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=1)
                
                analysis_results = await self.log_analyzer.analyze_logs(
                    time_range=(start_time, end_time),
                    log_levels=['ERROR', 'WARNING', 'CRITICAL']
                )
                
                # パターンが検出された場合はアラートを生成
                if analysis_results['patterns']:
                    await self._handle_log_patterns(analysis_results['patterns'])
                
                # 異常が検出された場合はアラートを生成
                if analysis_results['anomalies']:
                    await self._handle_log_anomalies(analysis_results['anomalies'])
                
                # 推奨アクションがある場合は通知
                if analysis_results['recommendations']:
                    await self._handle_recommendations(analysis_results['recommendations'])
                
                # 30分間隔で実行
                await asyncio.sleep(1800)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Log analysis loop error: {e}")
                await asyncio.sleep(300)  # エラー時は5分待機
        
        logger.info("Log analysis loop stopped")
    
    async def _handle_log_patterns(self, patterns: List[Dict[str, Any]]):
        """ログパターン検出時の処理"""
        for pattern in patterns:
            if pattern['severity'] in ['CRITICAL', 'HIGH']:
                # 重要度の高いパターンはアラートを生成
                alert_rule = AlertRule(
                    rule_id=f"log_pattern_{pattern['pattern_id']}",
                    name=f"Log Pattern Alert: {pattern['description']}",
                    description=f"Detected pattern: {pattern['description']} (frequency: {pattern['frequency']})",
                    condition="True",  # パターン検出済みなのでTrue
                    severity=AlertSeverity.HIGH if pattern['severity'] == 'HIGH' else AlertSeverity.CRITICAL,
                    notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DESKTOP]
                )
                
                if alert_rule.rule_id not in self.alert_system.alert_rules:
                    self.alert_system.register_rule(alert_rule)
                
                # アラート作成
                alerts = await self.alert_system.evaluate_metrics({'pattern_detected': 1})
                
                # イベントハンドラを呼び出し
                for handler in self.event_handlers['pattern_detected']:
                    try:
                        await handler(pattern, alerts)
                    except Exception as e:
                        logger.error(f"Pattern detection handler error: {e}")
    
    async def _handle_log_anomalies(self, anomalies: List[Dict[str, Any]]):
        """ログ異常検出時の処理"""
        for anomaly in anomalies:
            if anomaly['severity'] > 0.7:  # 高重要度異常
                alert_rule = AlertRule(
                    rule_id=f"log_anomaly_{anomaly['anomaly_type']}",
                    name=f"Log Anomaly Alert: {anomaly['description']}",
                    description=f"Anomaly detected: {anomaly['description']} (confidence: {anomaly['confidence_score']:.2f})",
                    condition="True",
                    severity=AlertSeverity.HIGH,
                    notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DESKTOP]
                )
                
                if alert_rule.rule_id not in self.alert_system.alert_rules:
                    self.alert_system.register_rule(alert_rule)
                
                # アラート作成
                alerts = await self.alert_system.evaluate_metrics({'anomaly_detected': anomaly['severity']})
                
                # イベントハンドラを呼び出し
                for handler in self.event_handlers['anomaly_detected']:
                    try:
                        await handler(anomaly, alerts)
                    except Exception as e:
                        logger.error(f"Anomaly detection handler error: {e}")
    
    async def _handle_recommendations(self, recommendations: List[Dict[str, Any]]):
        """推奨アクション処理"""
        for recommendation in recommendations:
            if recommendation['priority'] == 'HIGH':
                logger.warning(f"HIGH PRIORITY RECOMMENDATION: {recommendation['description']}")
                logger.warning(f"Action required: {recommendation['action']}")
                
                # 高優先度の推奨は通知として送信
                alert_rule = AlertRule(
                    rule_id=f"recommendation_{recommendation['category']}",
                    name=f"System Recommendation: {recommendation['category']}",
                    description=recommendation['description'],
                    condition="True",
                    severity=AlertSeverity.MEDIUM,
                    notification_channels=[NotificationChannel.EMAIL]
                )
                
                if alert_rule.rule_id not in self.alert_system.alert_rules:
                    self.alert_system.register_rule(alert_rule)
                
                await self.alert_system.evaluate_metrics({'recommendation_triggered': 1})
    
    async def _metrics_integration_loop(self):
        """メトリクス統合ループ"""
        logger.info("Starting metrics integration loop")
        
        while self.running:
            try:
                # パフォーマンス監視から現在のステータスを取得
                perf_status = self.performance_monitor.get_current_status()
                
                # システムメトリクスをアラートシステムに送信
                system_metrics = {}
                if 'system_summary' in perf_status:
                    summary = perf_status['system_summary']
                    system_metrics = {
                        'cpu_percent': summary.get('cpu_avg', 0),
                        'memory_percent': summary.get('memory_avg', 0),
                        'cpu_max': summary.get('cpu_max', 0),
                        'memory_max': summary.get('memory_max', 0)
                    }
                
                # アプリケーションメトリクス
                app_metrics = {}
                if 'current_app_metrics' in perf_status:
                    app_data = perf_status['current_app_metrics']
                    total_tasks = app_data.get('completed_tasks', 0) + app_data.get('failed_tasks', 0)
                    error_rate = (app_data.get('failed_tasks', 0) / max(1, total_tasks)) * 100
                    
                    app_metrics = {
                        'error_rate': error_rate,
                        'active_tasks': app_data.get('active_tasks', 0),
                        'memory_usage_mb': app_data.get('memory_usage_mb', 0)
                    }
                
                # 統合メトリクスをアラートシステムで評価
                combined_metrics = {**system_metrics, **app_metrics}
                if combined_metrics:
                    alerts = await self.alert_system.evaluate_metrics(combined_metrics)
                    
                    # 新しいアラートをダッシュボードに送信
                    for alert in alerts:
                        dashboard_alert = AlertData(
                            id=alert.id,
                            timestamp=alert.created_at,
                            severity=alert.severity.value,
                            category=f"Integrated/{alert.rule_id}",
                            message=alert.message,
                            details=alert.details
                        )
                        
                        await self.dashboard_manager.websocket_server.broadcast_alert(dashboard_alert)
                
                # 1分間隔で実行
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics integration loop error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Metrics integration loop stopped")
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """イベントハンドラを追加"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
        else:
            self.event_handlers[event_type] = [handler]
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """イベントハンドラを削除"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """包括的なシステム状態を取得"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'system_running': self.running
        }
        
        try:
            # パフォーマンス監視状態
            perf_status = self.performance_monitor.get_current_status()
            status['performance'] = perf_status
            
            # アラートシステム状態
            active_alerts = self.alert_system.get_active_alerts()
            alert_stats = self.alert_system.get_alert_statistics()
            
            status['alerts'] = {
                'active_alerts': [alert.to_dict() for alert in active_alerts],
                'statistics': alert_stats
            }
            
            # ログ分析の履歴状態
            log_history = await self.log_analyzer.get_historical_analysis(days=1)
            status['log_analysis'] = log_history
            
            # ダッシュボード接続状態
            status['dashboard'] = {
                'websocket_clients': len(self.dashboard_manager.websocket_server.clients),
                'websocket_port': self.dashboard_manager.websocket_server.port,
                'http_port': self.dashboard_manager.http_server.port
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive status: {e}")
            status['error'] = str(e)
        
        return status
    
    async def generate_comprehensive_report(self, hours: int = 24) -> Dict[str, Any]:
        """包括的なシステムレポートを生成"""
        report = {
            'report_generated_at': datetime.now().isoformat(),
            'time_range_hours': hours,
            'system_overview': {}
        }
        
        try:
            # パフォーマンスレポート
            perf_report = self.performance_monitor.generate_performance_report(hours)
            report['performance'] = perf_report
            
            # ログ分析レポート
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            log_analysis = await self.log_analyzer.analyze_logs(
                time_range=(start_time, end_time)
            )
            report['log_analysis'] = {
                'summary': log_analysis['summary'],
                'patterns_count': len(log_analysis['patterns']),
                'anomalies_count': len(log_analysis['anomalies']),
                'top_patterns': log_analysis['patterns'][:5],
                'recommendations': log_analysis['recommendations']
            }
            
            # アラート統計
            alert_stats = self.alert_system.get_alert_statistics(days=hours//24 if hours >= 24 else 1)
            report['alerts'] = alert_stats
            
            # 総合評価
            report['system_overview'] = self._calculate_system_health_score(report)
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            report['error'] = str(e)
        
        return report
    
    def _calculate_system_health_score(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """システム健康度スコアを計算"""
        health_score = 100  # 最大スコア
        issues = []
        
        try:
            # パフォーマンスによる減点
            perf_data = report.get('performance', {})
            if 'cpu_stats' in perf_data:
                cpu_avg = perf_data['cpu_stats'].get('avg', 0)
                if cpu_avg > 80:
                    health_score -= 20
                    issues.append(f"高CPU使用率 (平均: {cpu_avg:.1f}%)")
                elif cpu_avg > 60:
                    health_score -= 10
                    issues.append(f"中程度CPU使用率 (平均: {cpu_avg:.1f}%)")
            
            if 'memory_stats' in perf_data:
                memory_avg = perf_data['memory_stats'].get('avg', 0)
                if memory_avg > 85:
                    health_score -= 15
                    issues.append(f"高メモリ使用率 (平均: {memory_avg:.1f}%)")
                elif memory_avg > 70:
                    health_score -= 8
                    issues.append(f"中程度メモリ使用率 (平均: {memory_avg:.1f}%)")
            
            # アラートによる減点
            alert_data = report.get('alerts', {})
            total_alerts = alert_data.get('total_alerts', 0)
            if total_alerts > 50:
                health_score -= 25
                issues.append(f"多数のアラート ({total_alerts}件)")
            elif total_alerts > 20:
                health_score -= 15
                issues.append(f"中程度のアラート ({total_alerts}件)")
            elif total_alerts > 10:
                health_score -= 10
                issues.append(f"少数のアラート ({total_alerts}件)")
            
            escalation_rate = alert_data.get('escalation_rate', 0)
            if escalation_rate > 20:
                health_score -= 10
                issues.append(f"高エスカレーション率 ({escalation_rate:.1f}%)")
            
            # ログ分析による減点
            log_data = report.get('log_analysis', {})
            anomalies_count = log_data.get('anomalies_count', 0)
            if anomalies_count > 10:
                health_score -= 15
                issues.append(f"多数の異常検出 ({anomalies_count}件)")
            elif anomalies_count > 5:
                health_score -= 8
                issues.append(f"中程度の異常検出 ({anomalies_count}件)")
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            health_score = 50  # エラー時はデフォルトスコア
            issues.append("健康度計算エラー")
        
        # スコア範囲を制限
        health_score = max(0, min(100, health_score))
        
        # 健康度ランク
        if health_score >= 90:
            rank = "EXCELLENT"
        elif health_score >= 80:
            rank = "GOOD"
        elif health_score >= 70:
            rank = "FAIR"
        elif health_score >= 50:
            rank = "POOR"
        else:
            rank = "CRITICAL"
        
        return {
            'health_score': health_score,
            'health_rank': rank,
            'issues': issues,
            'recommendations': self._generate_health_recommendations(health_score, issues)
        }
    
    def _generate_health_recommendations(self, health_score: int, issues: List[str]) -> List[str]:
        """健康度に基づく推奨アクションを生成"""
        recommendations = []
        
        if health_score < 70:
            recommendations.append("システムの詳細な調査と最適化が推奨されます")
        
        for issue in issues:
            if "高CPU" in issue:
                recommendations.append("CPU集約的なプロセスを確認し、最適化を検討してください")
            elif "高メモリ" in issue:
                recommendations.append("メモリリークや不要なプロセスを確認してください")
            elif "多数のアラート" in issue:
                recommendations.append("アラート閾値の見直しや根本原因の調査を行ってください")
            elif "異常検出" in issue:
                recommendations.append("ログファイルの詳細な分析と問題の特定を行ってください")
        
        if not recommendations:
            recommendations.append("システムは良好な状態です。定期的な監視を継続してください")
        
        return recommendations

# 便利な関数とデコレータ
def create_monitoring_system(
    config_path: Optional[str] = None,
    **kwargs
) -> IntegratedMonitoringSystem:
    """監視システムを設定ファイルから作成"""
    config = {}
    
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    # デフォルト設定をマージ
    config.update(kwargs)
    
    return IntegratedMonitoringSystem(**config)

def monitoring_required(monitor: IntegratedMonitoringSystem):
    """監視が必要な関数のデコレータ"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            if monitor.performance_monitor:
                app_metrics = monitor.performance_monitor.get_app_metrics()
                app_metrics.increment('active_tasks')
            
            try:
                result = await func(*args, **kwargs)
                if monitor.performance_monitor:
                    app_metrics.increment('completed_tasks')
                return result
            except Exception as e:
                if monitor.performance_monitor:
                    app_metrics.increment('failed_tasks')
                
                # エラーをアラートシステムに通知
                error_metrics = {
                    'function_error': 1,
                    'error_type': type(e).__name__
                }
                asyncio.create_task(monitor.alert_system.evaluate_metrics(error_metrics))
                
                raise
            finally:
                if monitor.performance_monitor:
                    app_metrics.increment('active_tasks', -1)
        
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# テスト・デモ用の関数
async def demo_integrated_monitoring():
    """統合監視システムのデモ"""
    print("=== 統合監視システムデモ ===")
    
    # 監視システムを作成
    monitor = IntegratedMonitoringSystem(
        db_path="demo_monitoring",
        log_directory="logs",
        dashboard_config={
            'websocket_port': 8765,
            'http_port': 8080
        }
    )
    
    # カスタムイベントハンドラを追加
    async def alert_handler(alert_data, alerts):
        print(f"アラート検出: {alert_data}")
        for alert in alerts:
            print(f"  - [{alert.severity.value}] {alert.title}")
    
    monitor.add_event_handler('pattern_detected', alert_handler)
    monitor.add_event_handler('anomaly_detected', alert_handler)
    
    try:
        print("監視システムを開始中...")
        
        # 監視を開始（デモ用に短時間）
        monitoring_task = asyncio.create_task(
            monitor.start_monitoring({
                'performance': True,
                'logs': True,
                'alerts': True,
                'dashboard': True
            })
        )
        
        # 10秒待機してからステータスを表示
        await asyncio.sleep(10)
        
        print("\n=== システムステータス ===")
        status = await monitor.get_comprehensive_status()
        print(f"システム稼働状態: {status['system_running']}")
        print(f"アクティブアラート数: {len(status.get('alerts', {}).get('active_alerts', []))}")
        print(f"ダッシュボード接続数: {status.get('dashboard', {}).get('websocket_clients', 0)}")
        
        # レポート生成
        print("\n=== システムレポート ===")
        report = await monitor.generate_comprehensive_report(hours=1)
        health = report.get('system_overview', {})
        print(f"システム健康度: {health.get('health_score', 'N/A')}/100 ({health.get('health_rank', 'N/A')})")
        
        if health.get('issues'):
            print("検出された問題:")
            for issue in health['issues']:
                print(f"  - {issue}")
        
        if health.get('recommendations'):
            print("推奨アクション:")
            for rec in health['recommendations']:
                print(f"  - {rec}")
        
        print("\nWebダッシュボード: http://localhost:8080")
        print("WebSocket: ws://localhost:8765")
        print("Ctrl+Cで停止...")
        
        # 監視タスクを待機
        await monitoring_task
        
    except KeyboardInterrupt:
        print("\n監視システムを停止中...")
        await monitor.stop_monitoring()
        print("監視システムが停止されました")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        await monitor.stop_monitoring()

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    )
    
    # デモ実行
    asyncio.run(demo_integrated_monitoring())