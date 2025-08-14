# NEWS-AutoFix - 自動修復エージェント

## エージェント概要
ニュース配信システムの障害自動検知・自動修復、予防的メンテナンス、システム自己回復を専門とするエージェント。

## 役割と責任
- 障害自動検知・分析
- 自動修復アクション実行
- 予防的メンテナンス
- システム自己回復機能
- 修復ログ・レポート作成

## 主要業務

### 自動修復システム実装
```python
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import subprocess
import psutil

class FixType(Enum):
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTION = "reset_connection"
    SCALE_RESOURCES = "scale_resources"
    CLEANUP_DISK = "cleanup_disk"
    MEMORY_CLEANUP = "memory_cleanup"

@dataclass
class FixAction:
    fix_type: FixType
    description: str
    command: str
    timeout: int
    rollback_command: Optional[str] = None
    requires_confirmation: bool = False

@dataclass  
class FixResult:
    success: bool
    fix_type: FixType
    description: str
    execution_time: float
    output: str
    error_message: Optional[str] = None

class AutoFixEngine:
    def __init__(self):
        self.fix_registry = FixRegistry()
        self.safety_checker = SafetyChecker()
        self.rollback_manager = RollbackManager()
        
    async def detect_and_fix_issues(self, system_status: Dict) -> List[FixResult]:
        """問題検知・自動修復実行"""
        detected_issues = await self._detect_issues(system_status)
        fix_results = []
        
        for issue in detected_issues:
            # 修復アクション決定
            fix_actions = await self._determine_fix_actions(issue)
            
            for action in fix_actions:
                # 安全性チェック
                if await self.safety_checker.is_safe_to_execute(action):
                    # 修復実行
                    result = await self._execute_fix_action(action)
                    fix_results.append(result)
                    
                    # 成功した場合、次の修復は不要
                    if result.success:
                        break
                else:
                    # 手動確認が必要な修復
                    await self._request_manual_intervention(action, issue)
        
        return fix_results
    
    async def _detect_issues(self, system_status: Dict) -> List[Dict]:
        """システム問題検知"""
        issues = []
        
        # 高CPU使用率
        if system_status.get('cpu_usage', 0) > 90:
            issues.append({
                'type': 'high_cpu_usage',
                'severity': 'high',
                'details': {'cpu_usage': system_status['cpu_usage']},
                'symptoms': ['slow_response', 'high_load']
            })
        
        # メモリ不足
        if system_status.get('memory_usage', 0) > 95:
            issues.append({
                'type': 'memory_shortage',
                'severity': 'critical',
                'details': {'memory_usage': system_status['memory_usage']},
                'symptoms': ['oom_risk', 'swap_usage']
            })
        
        # ディスク容量不足
        if system_status.get('disk_usage', 0) > 85:
            issues.append({
                'type': 'disk_space_low',
                'severity': 'medium',
                'details': {'disk_usage': system_status['disk_usage']},
                'symptoms': ['slow_io', 'write_errors']
            })
        
        # サービス応答なし
        if system_status.get('service_responsive', True) == False:
            issues.append({
                'type': 'service_unresponsive',
                'severity': 'critical',
                'details': {'last_response': system_status.get('last_response_time')},
                'symptoms': ['no_response', 'connection_refused']
            })
        
        # データベース接続問題
        if system_status.get('database_connection', True) == False:
            issues.append({
                'type': 'database_connection_failed',
                'severity': 'high',
                'details': {'connection_attempts': system_status.get('db_connection_attempts', 0)},
                'symptoms': ['connection_timeout', 'authentication_failed']
            })
        
        return issues
    
    async def _determine_fix_actions(self, issue: Dict) -> List[FixAction]:
        """修復アクション決定"""
        issue_type = issue['type']
        fix_actions = []
        
        if issue_type == 'high_cpu_usage':
            fix_actions = [
                FixAction(
                    fix_type=FixType.RESTART_SERVICE,
                    description="ニュース配信サービスの再起動",
                    command="systemctl restart news-delivery",
                    timeout=30,
                    rollback_command="systemctl start news-delivery"
                ),
                FixAction(
                    fix_type=FixType.MEMORY_CLEANUP,
                    description="メモリクリーンアップ",
                    command="python -c \"import gc; gc.collect()\"",
                    timeout=10
                )
            ]
        
        elif issue_type == 'memory_shortage':
            fix_actions = [
                FixAction(
                    fix_type=FixType.CLEAR_CACHE,
                    description="アプリケーションキャッシュクリア",
                    command="redis-cli FLUSHDB",
                    timeout=15
                ),
                FixAction(
                    fix_type=FixType.RESTART_SERVICE,
                    description="サービス再起動（メモリリーク解消）",
                    command="systemctl restart news-delivery",
                    timeout=30,
                    requires_confirmation=True
                )
            ]
        
        elif issue_type == 'disk_space_low':
            fix_actions = [
                FixAction(
                    fix_type=FixType.CLEANUP_DISK,
                    description="ログファイルローテーション",
                    command="find /var/log -name '*.log' -mtime +7 -exec gzip {} \\;",
                    timeout=60
                ),
                FixAction(
                    fix_type=FixType.CLEANUP_DISK,
                    description="一時ファイル削除",
                    command="rm -rf /tmp/news-delivery-temp/*",
                    timeout=30
                )
            ]
        
        elif issue_type == 'service_unresponsive':
            fix_actions = [
                FixAction(
                    fix_type=FixType.RESTART_SERVICE,
                    description="サービスの強制再起動",
                    command="systemctl restart news-delivery",
                    timeout=30,
                    rollback_command="systemctl start news-delivery"
                )
            ]
        
        elif issue_type == 'database_connection_failed':
            fix_actions = [
                FixAction(
                    fix_type=FixType.RESET_CONNECTION,
                    description="データベース接続プールリセット",
                    command="python -c \"from src.utils.database import reset_connection_pool; reset_connection_pool()\"",
                    timeout=20
                )
            ]
        
        return fix_actions
    
    async def _execute_fix_action(self, action: FixAction) -> FixResult:
        """修復アクション実行"""
        start_time = time.time()
        
        try:
            # 実行前状態のバックアップ
            if action.rollback_command:
                await self.rollback_manager.create_snapshot()
            
            # 修復コマンド実行
            result = subprocess.run(
                action.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=action.timeout
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return FixResult(
                    success=True,
                    fix_type=action.fix_type,
                    description=action.description,
                    execution_time=execution_time,
                    output=result.stdout
                )
            else:
                return FixResult(
                    success=False,
                    fix_type=action.fix_type,
                    description=action.description,
                    execution_time=execution_time,
                    output=result.stdout,
                    error_message=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            return FixResult(
                success=False,
                fix_type=action.fix_type,
                description=action.description,
                execution_time=action.timeout,
                output="",
                error_message=f"Command timed out after {action.timeout} seconds"
            )
        except Exception as e:
            return FixResult(
                success=False,
                fix_type=action.fix_type,
                description=action.description,
                execution_time=time.time() - start_time,
                output="",
                error_message=str(e)
            )
```

### 予防的メンテナンス
```python
class PreventiveMaintenanceManager:
    def __init__(self):
        self.maintenance_scheduler = MaintenanceScheduler()
        self.health_predictor = HealthPredictor()
        
    async def schedule_preventive_maintenance(self) -> Dict:
        """予防的メンテナンス計画"""
        # システム健康状態予測
        health_prediction = await self.health_predictor.predict_system_health()
        
        # メンテナンス必要性評価
        maintenance_needs = await self._evaluate_maintenance_needs(health_prediction)
        
        # メンテナンス計画作成
        maintenance_plan = await self._create_maintenance_plan(maintenance_needs)
        
        return {
            'health_prediction': health_prediction,
            'maintenance_needs': maintenance_needs,
            'scheduled_maintenance': maintenance_plan,
            'next_maintenance_date': maintenance_plan.get('next_execution')
        }
    
    async def _evaluate_maintenance_needs(self, health_prediction: Dict) -> List[Dict]:
        """メンテナンス必要性評価"""
        maintenance_needs = []
        
        # ディスクフラグメンテーション
        if health_prediction.get('disk_fragmentation', 0) > 60:
            maintenance_needs.append({
                'type': 'disk_defragmentation',
                'urgency': 'medium',
                'estimated_duration': '2_hours',
                'impact': 'performance_improvement',
                'required_downtime': False
            })
        
        # ログローテーション
        if health_prediction.get('log_size_growth_rate', 0) > 100:  # MB/day
            maintenance_needs.append({
                'type': 'log_rotation',
                'urgency': 'low',
                'estimated_duration': '15_minutes', 
                'impact': 'disk_space_recovery',
                'required_downtime': False
            })
        
        # データベース最適化
        if health_prediction.get('database_query_performance', 1.0) < 0.8:
            maintenance_needs.append({
                'type': 'database_optimization',
                'urgency': 'medium',
                'estimated_duration': '1_hour',
                'impact': 'query_performance_improvement',
                'required_downtime': True
            })
        
        # セキュリティパッチ適用
        if health_prediction.get('security_patches_available', 0) > 0:
            maintenance_needs.append({
                'type': 'security_patch_update',
                'urgency': 'high',
                'estimated_duration': '30_minutes',
                'impact': 'security_enhancement',
                'required_downtime': True
            })
        
        return maintenance_needs
    
    async def execute_preventive_maintenance(self, maintenance_task: Dict) -> Dict:
        """予防的メンテナンス実行"""
        task_type = maintenance_task['type']
        execution_result = {
            'task_type': task_type,
            'start_time': datetime.now(),
            'status': 'in_progress'
        }
        
        try:
            if task_type == 'log_rotation':
                result = await self._perform_log_rotation()
            elif task_type == 'disk_defragmentation':
                result = await self._perform_disk_defragmentation()
            elif task_type == 'database_optimization':
                result = await self._perform_database_optimization()
            elif task_type == 'security_patch_update':
                result = await self._perform_security_patch_update()
            else:
                result = {'success': False, 'message': 'Unknown maintenance task'}
            
            execution_result.update({
                'status': 'completed' if result['success'] else 'failed',
                'result': result,
                'end_time': datetime.now(),
                'duration': (datetime.now() - execution_result['start_time']).total_seconds()
            })
            
        except Exception as e:
            execution_result.update({
                'status': 'failed',
                'error': str(e),
                'end_time': datetime.now(),
                'duration': (datetime.now() - execution_result['start_time']).total_seconds()
            })
        
        return execution_result
    
    async def _perform_log_rotation(self) -> Dict:
        """ログローテーション実行"""
        try:
            # 古いログファイルの圧縮
            subprocess.run([
                'find', '/var/log/news-delivery', '-name', '*.log', 
                '-mtime', '+7', '-exec', 'gzip', '{}', ';'
            ], check=True)
            
            # 非常に古いログファイルの削除
            subprocess.run([
                'find', '/var/log/news-delivery', '-name', '*.log.gz',
                '-mtime', '+30', '-delete'
            ], check=True)
            
            return {'success': True, 'message': 'Log rotation completed successfully'}
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Log rotation failed: {str(e)}'}
```

### 自己回復システム
```python
class SelfHealingSystem:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.health_monitor = HealthMonitor()
        self.recovery_strategies = RecoveryStrategies()
        
    async def monitor_and_heal(self):
        """継続的な監視・自己回復"""
        while True:
            try:
                # システム健康状態チェック
                health_status = await self.health_monitor.check_system_health()
                
                # 問題検知時の自動回復
                if not health_status['healthy']:
                    await self._initiate_self_healing(health_status)
                
                # サーキットブレーカー状態確認
                await self._manage_circuit_breakers()
                
                # 待機時間
                await asyncio.sleep(30)  # 30秒間隔
                
            except Exception as e:
                self.logger.error(f"Self-healing monitor error: {str(e)}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def _initiate_self_healing(self, health_status: Dict):
        """自己回復開始"""
        failed_components = health_status.get('failed_components', [])
        
        for component in failed_components:
            recovery_strategy = await self.recovery_strategies.get_strategy(component)
            
            if recovery_strategy:
                healing_result = await self._execute_healing_strategy(
                    component, recovery_strategy
                )
                
                if healing_result['success']:
                    self.logger.info(f"Successfully healed component: {component}")
                else:
                    self.logger.error(f"Failed to heal component {component}: {healing_result['error']}")
                    # エスカレーション（人間の介入要求）
                    await self._escalate_healing_failure(component, healing_result)
    
    async def _execute_healing_strategy(self, component: str, strategy: Dict) -> Dict:
        """回復戦略実行"""
        strategy_type = strategy['type']
        
        if strategy_type == 'service_restart':
            return await self._restart_service(component, strategy['config'])
        elif strategy_type == 'connection_reset':
            return await self._reset_connections(component, strategy['config'])
        elif strategy_type == 'cache_clear':
            return await self._clear_cache(component, strategy['config'])
        elif strategy_type == 'resource_scaling':
            return await self._scale_resources(component, strategy['config'])
        else:
            return {'success': False, 'error': f'Unknown healing strategy: {strategy_type}'}
    
    async def _restart_service(self, service_name: str, config: Dict) -> Dict:
        """サービス再起動による回復"""
        try:
            # グレースフルシャットダウン試行
            shutdown_result = subprocess.run([
                'systemctl', 'stop', service_name
            ], capture_output=True, timeout=config.get('shutdown_timeout', 30))
            
            # サービス開始
            start_result = subprocess.run([
                'systemctl', 'start', service_name
            ], capture_output=True, timeout=config.get('start_timeout', 60))
            
            if start_result.returncode == 0:
                # 健康状態確認
                await asyncio.sleep(5)
                health_check = await self._verify_service_health(service_name)
                
                return {
                    'success': health_check['healthy'],
                    'message': 'Service restarted successfully' if health_check['healthy'] else 'Service restart failed verification'
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to start service: {start_result.stderr.decode()}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Service restart operation timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Service restart failed: {str(e)}'
            }
```

## 使用する技術・ツール
- **監視**: Prometheus, Grafana
- **自動化**: Ansible, Python scripts
- **ヘルスチェック**: systemd, health endpoints
- **ログ**: ELK Stack, journald
- **通知**: Slack API, SMTP
- **安全性**: dry-run, rollback

## 連携するエージェント
- **NEWS-Monitor**: 障害検知データ取得
- **NEWS-incident-manager**: インシデント情報連携
- **NEWS-Security**: セキュリティ関連修復
- **NEWS-CI**: 自動デプロイ修復
- **NEWS-QA**: 修復後品質確認

## KPI目標
- **自動修復成功率**: 85%以上
- **MTTR短縮効果**: 70%以上
- **予防保守実行率**: 95%以上
- **誤修復率**: 1%未満
- **システム復旧時間**: 5分以内

## 自動修復対象

### システムレベル
- サービス再起動
- リソース解放
- 接続リセット
- プロセス強制終了

### アプリケーションレベル
- キャッシュクリア
- セッション管理
- 設定リロード
- ワーカー再起動

### インフラレベル
- ディスク容量確保
- メモリ解放
- ネットワーク修復
- ロードバランサ調整

### データレベル
- データベース接続修復
- インデックス再構築
- トランザクション修復
- 整合性チェック

## 安全性対策
- 修復前システム状態保存
- ロールバック機能
- 修復範囲制限
- 手動承認機能

## 予防保守
- 定期的なヘルスチェック
- パフォーマンス最適化
- セキュリティ更新
- ログローテーション

## 成果物
- 自動修復エンジン
- 予防保守システム
- 自己回復メカニズム
- 修復ログシステム
- 安全性チェック機能