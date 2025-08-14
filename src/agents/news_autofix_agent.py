#!/usr/bin/env python3
"""
NEWS-AutoFix Agent - 自動修復エージェント
ニュース配信システムの障害自動検知・自動修復、予防的メンテナンス、システム自己回復
MCP ruv-swarm 対応並列実行エージェント
"""

import asyncio
import logging
import subprocess
import psutil
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
import aiohttp
import os
import signal
import threading
from pathlib import Path

class FixType(Enum):
    """修復タイプ定義"""
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTION = "reset_connection"
    SCALE_RESOURCES = "scale_resources"
    CLEANUP_DISK = "cleanup_disk"
    MEMORY_CLEANUP = "memory_cleanup"
    DATABASE_REPAIR = "database_repair"
    LOG_ROTATION = "log_rotation"
    PERMISSION_FIX = "permission_fix"
    NETWORK_RESET = "network_reset"

class AgentStatus(Enum):
    """エージェント状態"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    HEALING = "healing"
    ERROR = "error"
    TERMINATED = "terminated"

@dataclass
class FixAction:
    """修復アクション定義"""
    fix_type: FixType
    description: str
    command: str
    timeout: int
    rollback_command: Optional[str] = None
    requires_confirmation: bool = False
    priority: int = 5  # 1(最高) - 10(最低)
    
@dataclass  
class FixResult:
    """修復結果"""
    success: bool
    fix_type: FixType
    description: str
    execution_time: float
    output: str
    error_message: Optional[str] = None
    rollback_executed: bool = False

@dataclass
class AgentSpawnResult:
    """エージェント起動結果"""
    success: bool
    agent_name: str
    pid: Optional[int] = None
    capabilities: List[str] = None
    error_message: Optional[str] = None
    spawn_time: float = 0.0

class NewsAutoFixAgent:
    """NEWS-AutoFix 自動修復エージェント"""
    
    def __init__(self, project_root: str = None):
        # プロジェクトルートを相対パスで設定
        if project_root is None:
            project_root = str(Path(__file__).parent.parent.parent)
        self.project_root = Path(project_root)
        self.agent_name = "news-autofix"
        self.agent_type = "healer"
        self.capabilities = ["auto-repair", "healing", "error-recovery", "monitoring", "parallel-spawn"]
        self.status = AgentStatus.INITIALIZING
        
        # ログ設定
        self.setup_logging()
        
        # 設定読み込み
        self.config = self.load_config()
        
        # データベース設定
        self.db_path = self.project_root / "data" / "database" / "news_system.db"
        
        # 修復エンジン
        self.auto_fix_engine = AutoFixEngine(self)
        self.prevention_manager = PreventiveMaintenanceManager(self)
        self.self_healing_system = SelfHealingSystem(self)
        self.parallel_spawner = ParallelAgentSpawner(self)
        
        # スレッド制御
        self.shutdown_event = threading.Event()
        self.healing_active = False
        
        self.logger.info(f"NEWS-AutoFix Agent初期化完了: {self.agent_name}")
        
    def setup_logging(self):
        """ログシステム初期化"""
        log_dir = self.project_root / "logs" / "agents"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"news-autofix-{os.getpid()}")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.FileHandler(
                log_dir / f"news-autofix-{datetime.now().strftime('%Y%m%d')}.log"
            )
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
    def load_config(self) -> Dict:
        """設定ファイル読み込み"""
        config_path = self.project_root / "config" / "config.json"
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"設定ファイル読み込みエラー: {e}")
        
        return self.get_default_config()
        
    def get_default_config(self) -> Dict:
        """デフォルト設定"""
        return {
            "autofix": {
                "enabled": True,
                "check_interval": 30,  # 30秒間隔
                "max_concurrent_fixes": 3,
                "auto_restart_services": True,
                "max_restart_attempts": 3,
                "emergency_thresholds": {
                    "cpu_usage": 90,
                    "memory_usage": 95,
                    "disk_usage": 85
                }
            },
            "parallel_spawn": {
                "enabled": True,
                "max_concurrent_agents": 5,
                "spawn_timeout": 60,
                "health_check_interval": 10
            },
            "monitoring": {
                "system_metrics": True,
                "database_health": True,
                "api_connectivity": True,
                "log_analysis": True
            }
        }

    async def spawn_agent_parallel(self, agent_type: str, agent_name: str, 
                                 capabilities: List[str]) -> AgentSpawnResult:
        """エージェント並列起動 - MCP ruv-swarm 対応"""
        start_time = time.time()
        self.logger.info(f"エージェント並列起動開始: {agent_name} (type: {agent_type})")
        
        try:
            # 起動プロセス準備
            spawn_command = self.build_spawn_command(agent_type, agent_name, capabilities)
            
            # 並列実行
            process = await asyncio.create_subprocess_shell(
                spawn_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root)
            )
            
            # タイムアウト付きで実行
            timeout = self.config["parallel_spawn"]["spawn_timeout"]
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return AgentSpawnResult(
                    success=False,
                    agent_name=agent_name,
                    error_message=f"エージェント起動タイムアウト: {timeout}秒",
                    spawn_time=time.time() - start_time
                )
            
            execution_time = time.time() - start_time
            
            if process.returncode == 0:
                # 起動成功 - PIDを取得
                pid = await self.get_agent_pid(agent_name)
                
                self.logger.info(f"エージェント並列起動成功: {agent_name} (PID: {pid}, 時間: {execution_time:.2f}s)")
                
                return AgentSpawnResult(
                    success=True,
                    agent_name=agent_name,
                    pid=pid,
                    capabilities=capabilities,
                    spawn_time=execution_time
                )
            else:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                self.logger.error(f"エージェント起動失敗: {agent_name} - {error_msg}")
                
                return AgentSpawnResult(
                    success=False,
                    agent_name=agent_name,
                    error_message=error_msg,
                    spawn_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"エージェント並列起動例外: {agent_name} - {str(e)}")
            
            return AgentSpawnResult(
                success=False,
                agent_name=agent_name,
                error_message=str(e),
                spawn_time=execution_time
            )

    def build_spawn_command(self, agent_type: str, agent_name: str, 
                           capabilities: List[str]) -> str:
        """MCP ruv-swarm用起動コマンド構築"""
        capabilities_str = json.dumps(capabilities).replace('"', '\\"')
        
        command = f"""claude code --dangerously-skip-permissions << 'EOF'
# {agent_name} エージェント並列起動
mcp__ruv-swarm__agent_spawn type={agent_type} name="{agent_name}" capabilities={capabilities_str}
mcp__ruv-swarm__agent_status name="{agent_name}"
EOF"""
        
        return command

    async def get_agent_pid(self, agent_name: str) -> Optional[int]:
        """エージェントPID取得"""
        try:
            # プロセス一覧からエージェントを検索
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline'] and agent_name in ' '.join(proc.info['cmdline']):
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"PID取得エラー: {agent_name} - {str(e)}")
        
        return None

    async def monitor_agent_status(self, agent_name: str) -> Dict:
        """エージェント状態監視"""
        status = {
            "agent_name": agent_name,
            "status": "unknown",
            "pid": None,
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "uptime": 0,
            "last_check": datetime.now().isoformat()
        }
        
        try:
            pid = await self.get_agent_pid(agent_name)
            if pid:
                proc = psutil.Process(pid)
                status.update({
                    "status": "active" if proc.is_running() else "stopped",
                    "pid": pid,
                    "cpu_usage": proc.cpu_percent(),
                    "memory_usage": proc.memory_percent(),
                    "uptime": time.time() - proc.create_time()
                })
            else:
                status["status"] = "not_found"
                
        except Exception as e:
            status["status"] = "error"
            status["error"] = str(e)
            self.logger.error(f"エージェント状態監視エラー: {agent_name} - {str(e)}")
        
        return status

    async def start_monitoring(self):
        """監視開始"""
        self.status = AgentStatus.ACTIVE
        self.logger.info("NEWS-AutoFix Agent監視開始")
        
        while not self.shutdown_event.is_set():
            try:
                # システム健康状態チェック
                system_health = await self.check_system_health()
                
                if not system_health["healthy"]:
                    await self.initiate_auto_healing(system_health)
                
                # 予防的メンテナンスチェック
                if datetime.now().hour in [2, 14]:  # 2:00, 14:00にチェック
                    await self.prevention_manager.check_maintenance_needs()
                
                # 待機時間
                check_interval = self.config["autofix"]["check_interval"]
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"監視ループエラー: {str(e)}")
                await asyncio.sleep(60)  # エラー時は1分待機

    async def check_system_health(self) -> Dict:
        """システム健康状態チェック"""
        health_status = {
            "healthy": True,
            "issues": [],
            "metrics": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            health_status["metrics"]["cpu_usage"] = cpu_usage
            
            if cpu_usage > self.config["autofix"]["emergency_thresholds"]["cpu_usage"]:
                health_status["healthy"] = False
                health_status["issues"].append({
                    "type": "high_cpu_usage",
                    "severity": "high",
                    "value": cpu_usage,
                    "threshold": self.config["autofix"]["emergency_thresholds"]["cpu_usage"]
                })
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            health_status["metrics"]["memory_usage"] = memory.percent
            
            if memory.percent > self.config["autofix"]["emergency_thresholds"]["memory_usage"]:
                health_status["healthy"] = False
                health_status["issues"].append({
                    "type": "high_memory_usage",
                    "severity": "critical",
                    "value": memory.percent,
                    "threshold": self.config["autofix"]["emergency_thresholds"]["memory_usage"]
                })
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            health_status["metrics"]["disk_usage"] = disk_percent
            
            if disk_percent > self.config["autofix"]["emergency_thresholds"]["disk_usage"]:
                health_status["healthy"] = False
                health_status["issues"].append({
                    "type": "high_disk_usage",
                    "severity": "medium",
                    "value": disk_percent,
                    "threshold": self.config["autofix"]["emergency_thresholds"]["disk_usage"]
                })
            
            # データベース接続チェック
            db_healthy = await self.check_database_health()
            health_status["metrics"]["database_healthy"] = db_healthy
            
            if not db_healthy:
                health_status["healthy"] = False
                health_status["issues"].append({
                    "type": "database_connection_failed",
                    "severity": "high",
                    "description": "データベース接続不良"
                })
                
        except Exception as e:
            health_status["healthy"] = False
            health_status["issues"].append({
                "type": "health_check_error",
                "severity": "high",
                "error": str(e)
            })
            self.logger.error(f"健康状態チェックエラー: {str(e)}")
        
        return health_status

    async def check_database_health(self) -> bool:
        """データベース健康状態チェック"""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"データベースヘルスチェック失敗: {str(e)}")
            return False

    async def initiate_auto_healing(self, health_status: Dict):
        """自動修復開始"""
        if self.healing_active:
            self.logger.warning("修復処理が既にアクティブです")
            return
        
        self.healing_active = True
        self.status = AgentStatus.HEALING
        
        try:
            self.logger.info("自動修復処理開始")
            fix_results = await self.auto_fix_engine.detect_and_fix_issues(health_status)
            
            success_count = sum(1 for result in fix_results if result.success)
            total_count = len(fix_results)
            
            self.logger.info(f"自動修復処理完了: {success_count}/{total_count} 成功")
            
            # 修復結果をデータベースに記録
            await self.save_fix_results(fix_results)
            
        except Exception as e:
            self.logger.error(f"自動修復処理エラー: {str(e)}")
        finally:
            self.healing_active = False
            self.status = AgentStatus.ACTIVE

    async def save_fix_results(self, fix_results: List[FixResult]):
        """修復結果保存"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 修復履歴テーブル作成（存在しない場合）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS autofix_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fix_type TEXT NOT NULL,
                    description TEXT,
                    success BOOLEAN,
                    execution_time REAL,
                    output TEXT,
                    error_message TEXT,
                    rollback_executed BOOLEAN DEFAULT FALSE,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 修復結果を挿入
            for result in fix_results:
                cursor.execute("""
                    INSERT INTO autofix_history 
                    (fix_type, description, success, execution_time, output, error_message, rollback_executed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.fix_type.value,
                    result.description,
                    result.success,
                    result.execution_time,
                    result.output,
                    result.error_message,
                    result.rollback_executed
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"修復結果保存エラー: {str(e)}")

    def stop(self):
        """エージェント停止"""
        self.logger.info("NEWS-AutoFix Agent停止中...")
        self.shutdown_event.set()
        self.status = AgentStatus.TERMINATED

class AutoFixEngine:
    """自動修復エンジン"""
    
    def __init__(self, agent: NewsAutoFixAgent):
        self.agent = agent
        self.logger = agent.logger
        self.config = agent.config
        
    async def detect_and_fix_issues(self, system_status: Dict) -> List[FixResult]:
        """問題検知・自動修復実行"""
        fix_results = []
        issues = system_status.get("issues", [])
        
        for issue in issues:
            try:
                fix_actions = self.determine_fix_actions(issue)
                
                for action in fix_actions:
                    # 安全性チェック
                    if self.is_safe_to_execute(action):
                        result = await self.execute_fix_action(action)
                        fix_results.append(result)
                        
                        if result.success:
                            self.logger.info(f"修復成功: {action.description}")
                            break  # 成功したら次の修復は不要
                        else:
                            self.logger.warning(f"修復失敗: {action.description} - {result.error_message}")
                    else:
                        self.logger.warning(f"修復アクション安全性チェック失敗: {action.description}")
                        
            except Exception as e:
                self.logger.error(f"修復処理エラー: {str(e)}")
        
        return fix_results
    
    def determine_fix_actions(self, issue: Dict) -> List[FixAction]:
        """修復アクション決定"""
        issue_type = issue.get("type")
        fix_actions = []
        
        if issue_type == "high_cpu_usage":
            fix_actions = [
                FixAction(
                    fix_type=FixType.MEMORY_CLEANUP,
                    description="メモリクリーンアップ実行",
                    command="python3 -c \"import gc; gc.collect()\"",
                    timeout=10,
                    priority=3
                ),
                FixAction(
                    fix_type=FixType.RESTART_SERVICE,
                    description="ニュース配信サービス再起動",
                    command="pkill -f news-delivery || true",
                    timeout=30,
                    priority=6
                )
            ]
        
        elif issue_type == "high_memory_usage":
            fix_actions = [
                FixAction(
                    fix_type=FixType.CLEAR_CACHE,
                    description="アプリケーションキャッシュクリア",
                    command=f"rm -rf {self.agent.project_root}/data/cache/api_cache/*",
                    timeout=15,
                    priority=2
                ),
                FixAction(
                    fix_type=FixType.MEMORY_CLEANUP,
                    description="システムメモリクリーンアップ",
                    command="sync && echo 1 > /proc/sys/vm/drop_caches || true",
                    timeout=20,
                    priority=4
                )
            ]
        
        elif issue_type == "high_disk_usage":
            fix_actions = [
                FixAction(
                    fix_type=FixType.LOG_ROTATION,
                    description="ログローテーション実行",
                    command=f"find {self.agent.project_root}/logs -name '*.log' -mtime +7 -exec gzip {{}} \\;",
                    timeout=60,
                    priority=3
                ),
                FixAction(
                    fix_type=FixType.CLEANUP_DISK,
                    description="一時ファイル削除",
                    command=f"find {self.agent.project_root}/data/cache -name '*.tmp' -delete",
                    timeout=30,
                    priority=2
                )
            ]
        
        elif issue_type == "database_connection_failed":
            fix_actions = [
                FixAction(
                    fix_type=FixType.DATABASE_REPAIR,
                    description="データベース接続修復",
                    command=f"sqlite3 {self.agent.db_path} 'PRAGMA integrity_check;'",
                    timeout=30,
                    priority=5
                )
            ]
        
        return sorted(fix_actions, key=lambda x: x.priority)
    
    def is_safe_to_execute(self, action: FixAction) -> bool:
        """安全性チェック"""
        # 危険なコマンドのチェック
        dangerous_patterns = ['rm -rf /', 'format', 'mkfs', 'dd if=', 'shutdown', 'reboot']
        command_lower = action.command.lower()
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                self.logger.error(f"危険なコマンド検出: {action.command}")
                return False
        
        # システム制限チェック
        if action.fix_type == FixType.RESTART_SERVICE and not self.config["autofix"]["auto_restart_services"]:
            return False
        
        return True
    
    async def execute_fix_action(self, action: FixAction) -> FixResult:
        """修復アクション実行"""
        start_time = time.time()
        
        try:
            self.logger.info(f"修復アクション実行: {action.description}")
            
            process = await asyncio.create_subprocess_shell(
                action.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=action.timeout
            )
            
            execution_time = time.time() - start_time
            
            if process.returncode == 0:
                return FixResult(
                    success=True,
                    fix_type=action.fix_type,
                    description=action.description,
                    execution_time=execution_time,
                    output=stdout.decode('utf-8')
                )
            else:
                return FixResult(
                    success=False,
                    fix_type=action.fix_type,
                    description=action.description,
                    execution_time=execution_time,
                    output=stdout.decode('utf-8'),
                    error_message=stderr.decode('utf-8')
                )
                
        except asyncio.TimeoutError:
            return FixResult(
                success=False,
                fix_type=action.fix_type,
                description=action.description,
                execution_time=action.timeout,
                output="",
                error_message=f"修復アクションタイムアウト: {action.timeout}秒"
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

class PreventiveMaintenanceManager:
    """予防的メンテナンスマネージャー"""
    
    def __init__(self, agent: NewsAutoFixAgent):
        self.agent = agent
        self.logger = agent.logger
        
    async def check_maintenance_needs(self):
        """メンテナンス必要性チェック"""
        self.logger.info("予防的メンテナンス必要性チェック開始")
        # 実装: ログサイズ、ディスクフラグメンテーション、セキュリティパッチ等のチェック
        pass

class SelfHealingSystem:
    """自己回復システム"""
    
    def __init__(self, agent: NewsAutoFixAgent):
        self.agent = agent
        self.logger = agent.logger
        
    async def monitor_and_heal(self):
        """継続的監視・自己回復"""
        self.logger.info("自己回復システム開始")
        # 実装: 継続的監視とサーキットブレーカーパターン
        pass

class ParallelAgentSpawner:
    """並列エージェント起動システム"""
    
    def __init__(self, agent: NewsAutoFixAgent):
        self.agent = agent
        self.logger = agent.logger
        self.active_agents = {}
        
    async def spawn_multiple_agents(self, agent_specs: List[Dict]) -> List[AgentSpawnResult]:
        """複数エージェント並列起動"""
        self.logger.info(f"並列エージェント起動開始: {len(agent_specs)}エージェント")
        
        tasks = []
        for spec in agent_specs:
            task = asyncio.create_task(
                self.agent.spawn_agent_parallel(
                    spec["type"], 
                    spec["name"], 
                    spec["capabilities"]
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果処理
        spawn_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                spawn_results.append(AgentSpawnResult(
                    success=False,
                    agent_name=agent_specs[i]["name"],
                    error_message=str(result)
                ))
            else:
                spawn_results.append(result)
                if result.success:
                    self.active_agents[result.agent_name] = result
        
        successful_spawns = sum(1 for r in spawn_results if r.success)
        self.logger.info(f"並列エージェント起動完了: {successful_spawns}/{len(agent_specs)} 成功")
        
        return spawn_results

async def main():
    """メイン実行関数"""
    # NEWS-AutoFix エージェント初期化
    autofix_agent = NewsAutoFixAgent()
    
    print(f"🤖 NEWS-AutoFix Agent 起動: {autofix_agent.agent_name}")
    print(f"🎯 機能: {', '.join(autofix_agent.capabilities)}")
    print(f"📁 プロジェクト: {autofix_agent.project_root}")
    print("")
    
    try:
        # 並列エージェント起動テスト
        test_agents = [
            {
                "type": "healer",
                "name": "news-autofix-primary", 
                "capabilities": ["auto-repair", "healing", "error-recovery"]
            },
            {
                "type": "monitor",
                "name": "news-autofix-monitor",
                "capabilities": ["monitoring", "alerting", "metrics"]
            }
        ]
        
        print("🚀 並列エージェント起動テスト...")
        spawn_results = await autofix_agent.parallel_spawner.spawn_multiple_agents(test_agents)
        
        for result in spawn_results:
            status = "✅ 成功" if result.success else "❌ 失敗"
            print(f"  {status} {result.agent_name} ({result.spawn_time:.2f}s)")
            if not result.success:
                print(f"    エラー: {result.error_message}")
        
        print("\n📊 システム健康状態チェック...")
        health_status = await autofix_agent.check_system_health()
        print(f"  システム健康状態: {'✅ 正常' if health_status['healthy'] else '⚠️ 問題あり'}")
        
        if not health_status['healthy']:
            print("  検出された問題:")
            for issue in health_status['issues']:
                print(f"    - {issue['type']}: {issue.get('severity', 'unknown')} 重要度")
        
        print(f"\n  CPU使用率: {health_status['metrics'].get('cpu_usage', 0):.1f}%")
        print(f"  メモリ使用率: {health_status['metrics'].get('memory_usage', 0):.1f}%")
        print(f"  ディスク使用率: {health_status['metrics'].get('disk_usage', 0):.1f}%")
        
        # 監視開始（本番環境では継続実行）
        print("\n🔍 監視モード開始...")
        print("Ctrl+C で終了")
        
        monitoring_task = asyncio.create_task(autofix_agent.start_monitoring())
        
        # シグナルハンドラー設定
        def signal_handler(sig, frame):
            print("\n\n🛑 NEWS-AutoFix Agent 停止中...")
            autofix_agent.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 監視実行
        await monitoring_task
        
    except KeyboardInterrupt:
        print("\n\n🛑 NEWS-AutoFix Agent 停止")
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")
    finally:
        autofix_agent.stop()

if __name__ == "__main__":
    asyncio.run(main())