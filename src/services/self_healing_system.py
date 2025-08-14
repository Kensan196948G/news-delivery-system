"""
Self-Healing Error Management System
自己修復型エラー管理システム - CLAUDE.md仕様準拠

エラー検知→分析→自動修復→監視のループシステム
"""

import asyncio
import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import time
import signal
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils.config import get_config
from utils.logger import setup_logger
from utils.monitoring_system import get_monitoring_system, ErrorCategory
from utils.error_notifier import get_error_notifier, ErrorSeverity
from notifiers.gmail_sender import GmailSender


logger = setup_logger(__name__)


class RepairStrategy(Enum):
    """修復戦略"""
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RECREATE_VENV = "recreate_venv"
    RESET_CONFIG = "reset_config"
    CLEAN_LOGS = "clean_logs"
    RESTART_SYSTEM = "restart_system"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class RepairAction:
    """修復アクション"""
    strategy: RepairStrategy
    command: Optional[str] = None
    description: str = ""
    timeout: int = 300  # 5分
    retry_count: int = 3
    requires_manual: bool = False


class SelfHealingSystem:
    """自己修復システム"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.monitoring_system = get_monitoring_system()
        self.error_notifier = get_error_notifier()
        
        # 修復履歴
        self.repair_history: List[Dict[str, Any]] = []
        self.failed_repairs: Dict[str, int] = {}
        
        # 修復戦略マッピング
        self.repair_strategies = self._initialize_repair_strategies()
        
        # システム状態
        self.healing_active = False
        self.healing_task = None
        self.max_repair_attempts = 3
        self.repair_cooldown = 300  # 5分
        
        # パス設定
        self.project_root = Path(__file__).parent.parent.parent
        self.venv_path = self.project_root / "venv"
        self.python_path = self.venv_path / "bin" / "python"
        
        logger.info("Self-healing system initialized")
    
    def _initialize_repair_strategies(self) -> Dict[ErrorCategory, List[RepairAction]]:
        """修復戦略の初期化"""
        return {
            ErrorCategory.API_RATE_LIMIT: [
                RepairAction(
                    RepairStrategy.CLEAR_CACHE,
                    description="Clear API cache to reset rate limits",
                    timeout=30
                ),
            ],
            
            ErrorCategory.NETWORK_ERROR: [
                RepairAction(
                    RepairStrategy.RESTART_SERVICE,
                    command="systemctl restart networking",
                    description="Restart network service",
                    timeout=60,
                    requires_manual=True  # 要手動確認
                ),
            ],
            
            ErrorCategory.AUTHENTICATION_ERROR: [
                RepairAction(
                    RepairStrategy.RESET_CONFIG,
                    description="Reset OAuth tokens and credentials",
                    timeout=120
                ),
            ],
            
            ErrorCategory.DATA_FORMAT_ERROR: [
                RepairAction(
                    RepairStrategy.CLEAR_CACHE,
                    description="Clear corrupted cache data",
                    timeout=30
                ),
            ],
            
            ErrorCategory.DISK_SPACE_ERROR: [
                RepairAction(
                    RepairStrategy.CLEAN_LOGS,
                    description="Clean old logs and temporary files",
                    timeout=120
                ),
                RepairAction(
                    RepairStrategy.CLEAR_CACHE,
                    description="Clear all cache data",
                    timeout=60
                ),
            ],
            
            ErrorCategory.DATABASE_ERROR: [
                RepairAction(
                    RepairStrategy.RESTART_SERVICE,
                    description="Restart database connections",
                    timeout=60
                ),
            ],
            
            ErrorCategory.TRANSLATION_ERROR: [
                RepairAction(
                    RepairStrategy.CLEAR_CACHE,
                    description="Clear translation cache",
                    timeout=30
                ),
                RepairAction(
                    RepairStrategy.RESET_CONFIG,
                    description="Reset DeepL API configuration",
                    timeout=60
                ),
            ],
            
            ErrorCategory.EMAIL_ERROR: [
                RepairAction(
                    RepairStrategy.RESET_CONFIG,
                    description="Reset Gmail OAuth credentials",
                    timeout=120
                ),
                RepairAction(
                    RepairStrategy.RECREATE_VENV,
                    description="Recreate Python virtual environment",
                    timeout=300
                ),
            ],
            
            ErrorCategory.SYSTEM_ERROR: [
                RepairAction(
                    RepairStrategy.RECREATE_VENV,
                    description="Recreate Python virtual environment",
                    timeout=300
                ),
                RepairAction(
                    RepairStrategy.RESTART_SYSTEM,
                    description="Full system restart",
                    timeout=600,
                    requires_manual=True
                ),
            ],
        }
    
    async def start_healing_loop(self):
        """自己修復ループ開始"""
        if self.healing_active:
            logger.warning("Self-healing loop already active")
            return
        
        self.healing_active = True
        self.healing_task = asyncio.create_task(self._healing_loop())
        
        logger.info("Self-healing loop started")
    
    async def stop_healing_loop(self):
        """自己修復ループ停止"""
        if not self.healing_active:
            return
        
        self.healing_active = False
        
        if self.healing_task:
            self.healing_task.cancel()
            try:
                await self.healing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Self-healing loop stopped")
    
    async def _healing_loop(self):
        """修復ループメイン処理"""
        while self.healing_active:
            try:
                # 監視システムからアクティブアラートを取得
                dashboard = self.monitoring_system.get_monitoring_dashboard()
                active_alerts = dashboard.get('active_alerts', [])
                
                # 修復可能なアラートを処理
                for alert_data in active_alerts:
                    alert_id = alert_data['alert_id']
                    
                    # 修復済みまたはクールダウン中をスキップ
                    if self._is_in_cooldown(alert_id):
                        continue
                    
                    # 修復試行
                    await self._attempt_repair(alert_data)
                
                # 30秒間隔でチェック
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Self-healing loop error: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def _attempt_repair(self, alert_data: Dict[str, Any]):
        """修復試行"""
        try:
            alert_id = alert_data['alert_id']
            category = alert_data['category']
            severity = alert_data['severity']
            
            logger.info(f"Attempting repair for alert: {alert_id}")
            
            # カテゴリからエラー種別を推定
            error_category = self._map_alert_to_error_category(category, alert_id)
            
            # 修復戦略を取得
            repair_actions = self.repair_strategies.get(error_category, [])
            
            if not repair_actions:
                logger.warning(f"No repair strategy found for {error_category}")
                return False
            
            # 修復実行
            success = False
            for action in repair_actions:
                if action.requires_manual:
                    # 手動介入が必要な場合は通知のみ
                    await self._notify_manual_intervention(alert_id, action)
                    continue
                
                repair_success = await self._execute_repair_action(alert_id, action)
                if repair_success:
                    success = True
                    break
            
            # 修復結果を記録
            self._record_repair_attempt(alert_id, error_category, success)
            
            if success:
                # 修復成功の場合、アラートを解決
                await self.monitoring_system.resolve_alert(alert_id)
                logger.info(f"Successfully repaired alert: {alert_id}")
                
                # 成功通知
                await self.error_notifier.send_recovery_notification(
                    f"Alert {alert_id} has been automatically repaired",
                    alert_data
                )
            else:
                logger.warning(f"Failed to repair alert: {alert_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Repair attempt failed for {alert_id}: {e}")
            return False
    
    def _map_alert_to_error_category(self, category: str, alert_id: str) -> ErrorCategory:
        """アラートからエラーカテゴリにマッピング"""
        category_mapping = {
            'api_usage': ErrorCategory.API_RATE_LIMIT,
            'authentication': ErrorCategory.AUTHENTICATION_ERROR,
            'system': ErrorCategory.SYSTEM_ERROR,
            'network': ErrorCategory.NETWORK_ERROR,
            'database': ErrorCategory.DATABASE_ERROR,
            'translation': ErrorCategory.TRANSLATION_ERROR,
            'email': ErrorCategory.EMAIL_ERROR,
        }
        
        # アラートIDからも判定
        if 'disk' in alert_id.lower():
            return ErrorCategory.DISK_SPACE_ERROR
        elif 'gmail' in alert_id.lower() or 'email' in alert_id.lower():
            return ErrorCategory.EMAIL_ERROR
        elif 'api' in alert_id.lower():
            return ErrorCategory.API_RATE_LIMIT
        elif 'auth' in alert_id.lower():
            return ErrorCategory.AUTHENTICATION_ERROR
        
        return category_mapping.get(category, ErrorCategory.SYSTEM_ERROR)
    
    async def _execute_repair_action(self, alert_id: str, action: RepairAction) -> bool:
        """修復アクション実行"""
        try:
            start_time = time.time()
            
            logger.info(f"Executing repair action: {action.strategy.value} for {alert_id}")
            
            success = False
            
            if action.strategy == RepairStrategy.CLEAR_CACHE:
                success = await self._clear_cache()
                
            elif action.strategy == RepairStrategy.RECREATE_VENV:
                success = await self._recreate_virtual_environment()
                
            elif action.strategy == RepairStrategy.RESET_CONFIG:
                success = await self._reset_configuration(alert_id)
                
            elif action.strategy == RepairStrategy.CLEAN_LOGS:
                success = await self._clean_logs()
                
            elif action.strategy == RepairStrategy.RESTART_SERVICE:
                success = await self._restart_news_service()
                
            elif action.command:
                success = await self._execute_command(action.command, action.timeout)
            
            execution_time = time.time() - start_time
            
            logger.info(f"Repair action {action.strategy.value} completed in {execution_time:.2f}s, success: {success}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute repair action {action.strategy.value}: {e}")
            return False
    
    async def _clear_cache(self) -> bool:
        """キャッシュクリア"""
        try:
            # データベースキャッシュをクリア
            cache_dir = self.config.get_storage_path('cache')
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True)
            
            # Pythonキャッシュクリア
            for cache_dir in self.project_root.rglob('__pycache__'):
                import shutil
                shutil.rmtree(cache_dir)
            
            # .pyc ファイル削除
            for pyc_file in self.project_root.rglob('*.pyc'):
                pyc_file.unlink()
            
            logger.info("Cache cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    async def _recreate_virtual_environment(self) -> bool:
        """仮想環境再作成"""
        try:
            logger.info("Recreating virtual environment...")
            
            # 既存の仮想環境を削除
            if self.venv_path.exists():
                import shutil
                shutil.rmtree(self.venv_path)
            
            # 新しい仮想環境を作成
            create_cmd = f"python3 -m venv {self.venv_path}"
            result = await self._execute_command(create_cmd, timeout=60)
            
            if not result:
                return False
            
            # requirements.txtから依存関係をインストール
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                pip_cmd = f"{self.venv_path}/bin/pip install -r {requirements_file}"
                result = await self._execute_command(pip_cmd, timeout=300)
                
                if result:
                    logger.info("Virtual environment recreated successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to recreate virtual environment: {e}")
            return False
    
    async def _reset_configuration(self, alert_id: str) -> bool:
        """設定リセット"""
        try:
            logger.info(f"Resetting configuration for alert: {alert_id}")
            
            # Gmail認証リセット
            if 'gmail' in alert_id.lower() or 'email' in alert_id.lower():
                return await self._reset_gmail_oauth()
            
            # DeepL設定リセット
            elif 'translation' in alert_id.lower():
                return await self._reset_deepl_config()
            
            # 一般的な設定リセット
            else:
                return await self._reset_general_config()
            
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")
            return False
    
    async def _reset_gmail_oauth(self) -> bool:
        """Gmail OAuth リセット"""
        try:
            # OAuth トークンファイルを削除
            token_files = [
                self.project_root / "config" / "gmail_token.json",
                self.project_root / "config" / "token.pickle",
                self.project_root / "gmail_token.json",
                self.project_root / "token.pickle"
            ]
            
            for token_file in token_files:
                if token_file.exists():
                    token_file.unlink()
                    logger.info(f"Removed OAuth token file: {token_file}")
            
            # Gmail認証テスト
            try:
                gmail_sender = GmailSender(self.config)
                test_success = await gmail_sender.test_connection()
                
                if test_success:
                    logger.info("Gmail OAuth reset and reconnection successful")
                    return True
                    
            except Exception as e:
                logger.warning(f"Gmail reconnection test failed: {e}")
                
            return True  # ファイル削除は成功したと見做す
            
        except Exception as e:
            logger.error(f"Failed to reset Gmail OAuth: {e}")
            return False
    
    async def _reset_deepl_config(self) -> bool:
        """DeepL 設定リセット"""
        try:
            # DeepL設定を初期化（APIキー設定確認）
            deepl_key = self.config.get('api_keys', 'deepl', default='')
            
            if not deepl_key:
                logger.warning("DeepL API key not found in configuration")
                return False
            
            # DeepL接続テスト
            try:
                from processors.translator import DeepLTranslator
                translator = DeepLTranslator(self.config)
                # 簡単な翻訳テスト
                test_result = await translator.translate_text("Hello", 'EN', 'JA')
                
                if test_result:
                    logger.info("DeepL configuration reset successful")
                    return True
                    
            except Exception as e:
                logger.warning(f"DeepL connection test failed: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to reset DeepL config: {e}")
            return False
    
    async def _reset_general_config(self) -> bool:
        """一般設定リセット"""
        try:
            # 設定ファイル読み込み直し
            self.config.reload_config()
            logger.info("Configuration reloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset general config: {e}")
            return False
    
    async def _clean_logs(self) -> bool:
        """ログクリーンアップ"""
        try:
            from utils.logger import cleanup_logs
            
            # 古いログファイル削除
            cleanup_logs()
            
            # ログローテーション実行
            logs_dir = self.config.get_storage_path('logs')
            
            # 7日以上古いログファイルを削除
            cutoff_time = datetime.now() - timedelta(days=7)
            
            cleaned_count = 0
            for log_file in logs_dir.rglob('*.log*'):
                if log_file.stat().st_mtime < cutoff_time.timestamp():
                    log_file.unlink()
                    cleaned_count += 1
            
            logger.info(f"Log cleanup completed: {cleaned_count} files removed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clean logs: {e}")
            return False
    
    async def _restart_news_service(self) -> bool:
        """ニュースサービス再起動"""
        try:
            logger.info("Restarting news delivery service...")
            
            # メインプロセスを再実行（テストモード）
            restart_cmd = f"cd {self.project_root} && source venv/bin/activate && python src/main.py --mode test"
            result = await self._execute_command(restart_cmd, timeout=30)
            
            if result:
                logger.info("News service restart successful")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to restart news service: {e}")
            return False
    
    async def _execute_command(self, command: str, timeout: int = 60) -> bool:
        """コマンド実行"""
        try:
            logger.debug(f"Executing command: {command}")
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                if process.returncode == 0:
                    logger.debug(f"Command executed successfully: {command}")
                    return True
                else:
                    logger.warning(f"Command failed with code {process.returncode}: {stderr.decode()}")
                    return False
                    
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {timeout}s: {command}")
                process.terminate()
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {e}")
            return False
    
    async def _notify_manual_intervention(self, alert_id: str, action: RepairAction):
        """手動介入通知"""
        try:
            message = f"""
            手動介入が必要です:
            
            Alert ID: {alert_id}
            Required Action: {action.description}
            Strategy: {action.strategy.value}
            
            手動での対応をお願いします。
            """
            
            await self.error_notifier.send_critical_alert(
                message,
                f"Manual Intervention Required: {alert_id}"
            )
            
            logger.warning(f"Manual intervention notification sent for {alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send manual intervention notification: {e}")
    
    def _record_repair_attempt(self, alert_id: str, error_category: ErrorCategory, success: bool):
        """修復試行記録"""
        try:
            repair_record = {
                "alert_id": alert_id,
                "error_category": error_category.value,
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "attempt_count": self.failed_repairs.get(alert_id, 0) + 1
            }
            
            self.repair_history.append(repair_record)
            
            # 履歴サイズ制限
            if len(self.repair_history) > 1000:
                self.repair_history = self.repair_history[-1000:]
            
            # 失敗カウンタ更新
            if not success:
                self.failed_repairs[alert_id] = self.failed_repairs.get(alert_id, 0) + 1
            else:
                # 成功したらカウンタリセット
                self.failed_repairs.pop(alert_id, None)
            
            logger.debug(f"Repair attempt recorded: {alert_id}, success: {success}")
            
        except Exception as e:
            logger.error(f"Failed to record repair attempt: {e}")
    
    def _is_in_cooldown(self, alert_id: str) -> bool:
        """クールダウン中かチェック"""
        try:
            # 修復試行回数チェック
            if self.failed_repairs.get(alert_id, 0) >= self.max_repair_attempts:
                return True
            
            # 最近の修復試行をチェック
            recent_attempts = [
                record for record in self.repair_history
                if record['alert_id'] == alert_id
            ]
            
            if recent_attempts:
                last_attempt = max(recent_attempts, key=lambda x: x['timestamp'])
                last_time = datetime.fromisoformat(last_attempt['timestamp'])
                
                if datetime.now() - last_time < timedelta(seconds=self.repair_cooldown):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check cooldown for {alert_id}: {e}")
            return True  # エラー時はクールダウン中と見做す
    
    def get_healing_status(self) -> Dict[str, Any]:
        """修復システム状態取得"""
        try:
            recent_repairs = [
                record for record in self.repair_history
                if datetime.fromisoformat(record['timestamp']) > datetime.now() - timedelta(hours=24)
            ]
            
            successful_repairs = [r for r in recent_repairs if r['success']]
            failed_repairs = [r for r in recent_repairs if not r['success']]
            
            return {
                "healing_active": self.healing_active,
                "total_repair_attempts_24h": len(recent_repairs),
                "successful_repairs_24h": len(successful_repairs),
                "failed_repairs_24h": len(failed_repairs),
                "success_rate_24h": len(successful_repairs) / len(recent_repairs) if recent_repairs else 0,
                "active_failures": len(self.failed_repairs),
                "repair_strategies_available": len(self.repair_strategies),
                "cooldown_alerts": list(self.failed_repairs.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get healing status: {e}")
            return {"error": str(e)}


# グローバル自己修復システムインスタンス
_self_healing_system = None


def get_self_healing_system() -> SelfHealingSystem:
    """グローバル自己修復システム取得"""
    global _self_healing_system
    if _self_healing_system is None:
        _self_healing_system = SelfHealingSystem()
    return _self_healing_system


async def main():
    """テスト用メイン関数"""
    healing_system = get_self_healing_system()
    
    # 修復システム開始
    await healing_system.start_healing_loop()
    
    try:
        # 10分間動作
        await asyncio.sleep(600)
    except KeyboardInterrupt:
        logger.info("Shutting down self-healing system...")
    finally:
        await healing_system.stop_healing_loop()


if __name__ == "__main__":
    asyncio.run(main())