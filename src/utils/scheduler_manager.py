#!/usr/bin/env python3
"""
Cross-platform Scheduler Manager
クロスプラットフォーム対応スケジューラ管理モジュール

Linux (cron) と Windows (Task Scheduler) の両方に対応
"""

import os
import sys
import platform
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, time
import logging

from .path_resolver import get_path_resolver
from .config import get_config


class SchedulerManager:
    """スケジュール管理クラス"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.is_windows = self.platform == 'windows'
        self.is_linux = self.platform in ['linux', 'darwin']
        
        self.path_resolver = get_path_resolver()
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # スケジュール設定の読み込み
        self.schedules = self._load_schedules()
        
    def _load_schedules(self) -> List[Dict]:
        """スケジュール設定を読み込み"""
        schedules = []
        
        # 定期配信スケジュール（CLAUDE.md仕様: 7:00, 12:00, 18:00）
        daily_times = self.config.get('delivery', 'schedule', 
                                     default=['07:00', '12:00', '18:00'])
        
        for time_str in daily_times:
            schedules.append({
                'name': f'news_delivery_{time_str.replace(":", "")}',
                'time': time_str,
                'type': 'daily',
                'command': self._get_execution_command(),
                'description': f'ニュース配信 - {time_str}'
            })
        
        # 緊急チェック（30分ごと）
        if self.config.get('delivery', 'urgent_notification', 'enabled', default=True):
            schedules.append({
                'name': 'news_emergency_check',
                'interval': 30,  # 分
                'type': 'interval',
                'command': self._get_execution_command('--emergency-only'),
                'description': '緊急ニュースチェック'
            })
        
        return schedules
    
    def _get_execution_command(self, *args) -> str:
        """実行コマンドを生成"""
        python_executable = sys.executable
        main_script = self.path_resolver.project_root / "src" / "main.py"
        
        command_parts = [python_executable, str(main_script)]
        command_parts.extend(args)
        
        return ' '.join(command_parts)
    
    def setup_schedules(self) -> bool:
        """スケジュールを設定"""
        if self.is_linux:
            return self._setup_cron()
        elif self.is_windows:
            return self._setup_task_scheduler()
        else:
            self.logger.error(f"Unsupported platform: {self.platform}")
            return False
    
    def _setup_cron(self) -> bool:
        """Linux用cron設定"""
        try:
            # 現在のcrontabを取得
            current_crontab = self._get_current_crontab()
            
            # 新しいcrontab内容を生成
            new_crontab = self._generate_crontab(current_crontab)
            
            # crontabを更新
            self._update_crontab(new_crontab)
            
            self.logger.info("Cron schedules have been set up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up cron: {e}")
            return False
    
    def _get_current_crontab(self) -> str:
        """現在のcrontabを取得"""
        try:
            result = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return result.stdout
            return ""
        except:
            return ""
    
    def _generate_crontab(self, current: str) -> str:
        """新しいcrontab内容を生成"""
        lines = current.strip().split('\n') if current else []
        
        # 既存のニュース配信関連エントリを削除
        filtered_lines = [
            line for line in lines 
            if not any(marker in line for marker in ['news_delivery', 'news_emergency'])
        ]
        
        # ヘッダーコメントを追加
        if not any('News Delivery System' in line for line in filtered_lines):
            filtered_lines.append("")
            filtered_lines.append("# ===== News Delivery System Schedules =====")
            filtered_lines.append(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 環境変数の設定
        env_vars = [
            f"NEWS_PROJECT_ROOT={self.path_resolver.project_root}",
            f"PYTHONPATH={self.path_resolver.project_root}/src:$PYTHONPATH",
        ]
        
        for env_var in env_vars:
            if env_var not in '\n'.join(filtered_lines):
                filtered_lines.append(env_var)
        
        # スケジュールエントリを追加
        for schedule in self.schedules:
            cron_entry = self._create_cron_entry(schedule)
            if cron_entry:
                filtered_lines.append(cron_entry)
        
        filtered_lines.append("# ===== End of News Delivery System =====")
        filtered_lines.append("")
        
        return '\n'.join(filtered_lines)
    
    def _create_cron_entry(self, schedule: Dict) -> Optional[str]:
        """cronエントリを作成"""
        if schedule['type'] == 'daily':
            # 時刻形式のパース (HH:MM)
            hour, minute = schedule['time'].split(':')
            
            # ログファイルパス
            log_file = self.path_resolver.get_log_path(
                f"cron_{schedule['name']}.log"
            )
            
            # cronフォーマット: 分 時 * * * コマンド
            entry = f"{minute} {hour} * * * {schedule['command']} >> {log_file} 2>&1"
            
            return f"{entry} # {schedule['description']}"
            
        elif schedule['type'] == 'interval':
            interval = schedule['interval']
            
            # ログファイルパス
            log_file = self.path_resolver.get_log_path(
                f"cron_{schedule['name']}.log"
            )
            
            # intervalをcron形式に変換
            if interval == 30:
                entry = f"*/30 * * * * {schedule['command']} >> {log_file} 2>&1"
            elif interval == 60:
                entry = f"0 * * * * {schedule['command']} >> {log_file} 2>&1"
            else:
                entry = f"*/{interval} * * * * {schedule['command']} >> {log_file} 2>&1"
            
            return f"{entry} # {schedule['description']}"
        
        return None
    
    def _update_crontab(self, content: str):
        """crontabを更新"""
        # 一時ファイルに書き込み
        temp_file = Path("/tmp/news_crontab_temp")
        temp_file.write_text(content)
        
        # crontabを更新
        result = subprocess.run(
            ['crontab', str(temp_file)],
            capture_output=True,
            text=True
        )
        
        # 一時ファイルを削除
        temp_file.unlink()
        
        if result.returncode != 0:
            raise Exception(f"Failed to update crontab: {result.stderr}")
    
    def _setup_task_scheduler(self) -> bool:
        """Windows用タスクスケジューラ設定"""
        try:
            for schedule in self.schedules:
                self._create_windows_task(schedule)
            
            self.logger.info("Windows Task Scheduler has been set up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up Windows Task Scheduler: {e}")
            return False
    
    def _create_windows_task(self, schedule: Dict):
        """Windowsタスクを作成"""
        task_name = f"NewsDeliverySystem_{schedule['name']}"
        
        # PowerShellスクリプトを生成
        ps_script = self._generate_powershell_script(schedule, task_name)
        
        # PowerShellスクリプトを実行
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to create task {task_name}: {result.stderr}")
    
    def _generate_powershell_script(self, schedule: Dict, task_name: str) -> str:
        """PowerShellスクリプトを生成"""
        if schedule['type'] == 'daily':
            time_str = schedule['time']
            trigger = f"New-ScheduledTaskTrigger -Daily -At {time_str}"
        elif schedule['type'] == 'interval':
            interval = schedule['interval']
            trigger = f"New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes {interval}) -RepetitionDuration ([System.TimeSpan]::MaxValue)"
        else:
            raise ValueError(f"Unknown schedule type: {schedule['type']}")
        
        python_exe = sys.executable.replace('\\', '\\\\')
        script_path = str(self.path_resolver.project_root / "src" / "main.py").replace('\\', '\\\\')
        
        ps_script = f"""
$taskName = "{task_name}"
$trigger = {trigger}
$action = New-ScheduledTaskAction -Execute "{python_exe}" -Argument '"{script_path}"'
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# Remove existing task if exists
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Register new task
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Principal $principal -Settings $settings -Description "{schedule['description']}"
"""
        return ps_script
    
    def remove_schedules(self) -> bool:
        """スケジュールを削除"""
        if self.is_linux:
            return self._remove_cron()
        elif self.is_windows:
            return self._remove_tasks()
        else:
            return False
    
    def _remove_cron(self) -> bool:
        """cron設定を削除"""
        try:
            current = self._get_current_crontab()
            lines = current.strip().split('\n') if current else []
            
            # ニュース配信関連のエントリを削除
            filtered = []
            in_news_section = False
            
            for line in lines:
                if '===== News Delivery System Schedules =====' in line:
                    in_news_section = True
                    continue
                elif '===== End of News Delivery System =====' in line:
                    in_news_section = False
                    continue
                elif not in_news_section:
                    filtered.append(line)
            
            self._update_crontab('\n'.join(filtered))
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove cron entries: {e}")
            return False
    
    def _remove_tasks(self) -> bool:
        """Windowsタスクを削除"""
        try:
            for schedule in self.schedules:
                task_name = f"NewsDeliverySystem_{schedule['name']}"
                subprocess.run(
                    ['schtasks', '/Delete', '/TN', task_name, '/F'],
                    capture_output=True,
                    check=False
                )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove Windows tasks: {e}")
            return False
    
    def list_schedules(self) -> List[Dict]:
        """現在のスケジュールを一覧表示"""
        if self.is_linux:
            return self._list_cron_schedules()
        elif self.is_windows:
            return self._list_windows_tasks()
        else:
            return []
    
    def _list_cron_schedules(self) -> List[Dict]:
        """cron設定を一覧表示"""
        schedules = []
        current = self._get_current_crontab()
        
        for line in current.split('\n'):
            if 'news_delivery' in line or 'news_emergency' in line:
                parts = line.split('#')
                if len(parts) == 2:
                    schedules.append({
                        'entry': parts[0].strip(),
                        'description': parts[1].strip()
                    })
        
        return schedules
    
    def _list_windows_tasks(self) -> List[Dict]:
        """Windowsタスクを一覧表示"""
        schedules = []
        
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/FO', 'CSV', '/V'],
                capture_output=True,
                text=True,
                check=True
            )
            
            lines = result.stdout.strip().split('\n')
            headers = lines[0].split(',')
            
            for line in lines[1:]:
                if 'NewsDeliverySystem' in line:
                    values = line.split(',')
                    task_info = dict(zip(headers, values))
                    schedules.append({
                        'name': task_info.get('TaskName', '').strip('"'),
                        'status': task_info.get('Status', '').strip('"'),
                        'next_run': task_info.get('Next Run Time', '').strip('"')
                    })
        except:
            pass
        
        return schedules
    
    def validate_schedules(self) -> Tuple[bool, List[str]]:
        """スケジュール設定を検証"""
        issues = []
        
        # Python実行可能ファイルの確認
        if not Path(sys.executable).exists():
            issues.append(f"Python executable not found: {sys.executable}")
        
        # メインスクリプトの確認
        main_script = self.path_resolver.project_root / "src" / "main.py"
        if not main_script.exists():
            issues.append(f"Main script not found: {main_script}")
        
        # ログディレクトリの書き込み権限確認
        log_dir = self.path_resolver.get_log_path()
        if not os.access(log_dir, os.W_OK):
            issues.append(f"No write permission for log directory: {log_dir}")
        
        # プラットフォーム固有の検証
        if self.is_linux:
            # crontabコマンドの存在確認
            try:
                subprocess.run(['which', 'crontab'], capture_output=True, check=True)
            except:
                issues.append("crontab command not found")
        
        elif self.is_windows:
            # schtasksコマンドの存在確認
            try:
                subprocess.run(['where', 'schtasks'], capture_output=True, check=True)
            except:
                issues.append("schtasks command not found")
        
        return len(issues) == 0, issues


def main():
    """CLIエントリポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Delivery System Scheduler Manager')
    parser.add_argument('action', choices=['setup', 'remove', 'list', 'validate'],
                       help='Action to perform')
    
    args = parser.parse_args()
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = SchedulerManager()
    
    if args.action == 'setup':
        success = manager.setup_schedules()
        if success:
            print("✅ Schedules have been set up successfully")
            print("\nConfigured schedules:")
            for schedule in manager.list_schedules():
                print(f"  - {schedule}")
        else:
            print("❌ Failed to set up schedules")
            sys.exit(1)
    
    elif args.action == 'remove':
        success = manager.remove_schedules()
        if success:
            print("✅ Schedules have been removed successfully")
        else:
            print("❌ Failed to remove schedules")
            sys.exit(1)
    
    elif args.action == 'list':
        schedules = manager.list_schedules()
        if schedules:
            print("Current schedules:")
            for schedule in schedules:
                print(f"  - {schedule}")
        else:
            print("No schedules found")
    
    elif args.action == 'validate':
        valid, issues = manager.validate_schedules()
        if valid:
            print("✅ Schedule configuration is valid")
        else:
            print("❌ Schedule configuration has issues:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)


if __name__ == '__main__':
    main()