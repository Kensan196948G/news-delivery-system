"""
Windows Task Scheduler Integration for News Delivery System
Windowsタスクスケジューラ統合モジュール - CLAUDE.md仕様準拠
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import os
import sys

from utils.config import get_config
from utils.logger import setup_logger


logger = logging.getLogger(__name__)


class WindowsTaskScheduler:
    """Windows Task Scheduler integration for automated news delivery"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        
        # Task configuration - CLAUDE.md compliant schedule
        self.task_schedules = {
            'morning_delivery': {'time': '07:00', 'name': 'NewsDelivery_Morning'},
            'noon_delivery': {'time': '12:00', 'name': 'NewsDelivery_Noon'},
            'evening_delivery': {'time': '18:00', 'name': 'NewsDelivery_Evening'},
            'urgent_check': {'interval_minutes': 30, 'name': 'NewsDelivery_UrgentCheck'}
        }
        
        # Python executable and script paths
        self.python_executable = sys.executable
        self.main_script = Path(__file__).parent.parent / 'main.py'
        self.task_prefix = 'NewsDeliverySystem'
    
    def create_scheduled_tasks(self) -> Dict[str, bool]:
        """Create all scheduled tasks in Windows Task Scheduler"""
        results = {}
        
        try:
            # Create daily delivery tasks (7:00, 12:00, 18:00)
            for delivery_type in ['morning_delivery', 'noon_delivery', 'evening_delivery']:
                task_config = self.task_schedules[delivery_type]
                success = self._create_daily_task(
                    task_name=task_config['name'],
                    schedule_time=task_config['time'],
                    task_type='scheduled_delivery'
                )
                results[delivery_type] = success
            
            # Create urgent check task (every 30 minutes)
            success = self._create_interval_task(
                task_name=self.task_schedules['urgent_check']['name'],
                interval_minutes=self.task_schedules['urgent_check']['interval_minutes'],
                task_type='urgent_check'
            )
            results['urgent_check'] = success
            
            self.logger.info(f"Task creation results: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to create scheduled tasks: {e}")
            return {task: False for task in self.task_schedules.keys()}
    
    def _create_daily_task(self, task_name: str, schedule_time: str, task_type: str) -> bool:
        """Create daily scheduled task"""
        try:
            # Generate task XML definition
            task_xml = self._generate_daily_task_xml(
                task_name=task_name,
                schedule_time=schedule_time,
                task_type=task_type
            )
            
            # Save XML to temporary file
            temp_xml_file = Path(f'temp_{task_name}.xml')
            with open(temp_xml_file, 'w', encoding='utf-8') as f:
                f.write(task_xml)
            
            # Create task using schtasks command
            cmd = [
                'schtasks',
                '/create',
                '/tn', f'{self.task_prefix}\\{task_name}',
                '/xml', str(temp_xml_file),
                '/f'  # Force overwrite if exists
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Clean up temporary file
            temp_xml_file.unlink(missing_ok=True)
            
            self.logger.info(f"Successfully created daily task: {task_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create daily task {task_name}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error creating daily task {task_name}: {e}")
            return False
    
    def _create_interval_task(self, task_name: str, interval_minutes: int, task_type: str) -> bool:
        """Create interval-based scheduled task"""
        try:
            # Generate task XML definition for interval task
            task_xml = self._generate_interval_task_xml(
                task_name=task_name,
                interval_minutes=interval_minutes,
                task_type=task_type
            )
            
            # Save XML to temporary file
            temp_xml_file = Path(f'temp_{task_name}.xml')
            with open(temp_xml_file, 'w', encoding='utf-8') as f:
                f.write(task_xml)
            
            # Create task using schtasks command
            cmd = [
                'schtasks',
                '/create',
                '/tn', f'{self.task_prefix}\\{task_name}',
                '/xml', str(temp_xml_file),
                '/f'  # Force overwrite if exists
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Clean up temporary file
            temp_xml_file.unlink(missing_ok=True)
            
            self.logger.info(f"Successfully created interval task: {task_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create interval task {task_name}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error creating interval task {task_name}: {e}")
            return False
    
    def _generate_daily_task_xml(self, task_name: str, schedule_time: str, task_type: str) -> str:
        """Generate XML definition for daily scheduled task"""
        hour, minute = schedule_time.split(':')
        
        # Get current user
        username = os.getenv('USERNAME', 'User')
        
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
    <RegistrationInfo>
        <Date>{datetime.now().isoformat()}</Date>
        <Author>{username}</Author>
        <Description>News Delivery System - Daily scheduled delivery at {schedule_time}</Description>
        <URI>\\{self.task_prefix}\\{task_name}</URI>
    </RegistrationInfo>
    <Triggers>
        <CalendarTrigger>
            <StartBoundary>{datetime.now().strftime('%Y-%m-%d')}T{schedule_time}:00</StartBoundary>
            <Enabled>true</Enabled>
            <ScheduleByDay>
                <DaysInterval>1</DaysInterval>
            </ScheduleByDay>
        </CalendarTrigger>
    </Triggers>
    <Principals>
        <Principal id="Author">
            <UserId>{username}</UserId>
            <LogonType>InteractiveToken</LogonType>
            <RunLevel>LeastPrivilege</RunLevel>
        </Principal>
    </Principals>
    <Settings>
        <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
        <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
        <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
        <AllowHardTerminate>true</AllowHardTerminate>
        <StartWhenAvailable>true</StartWhenAvailable>
        <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
        <IdleSettings>
            <StopOnIdleEnd>false</StopOnIdleEnd>
            <RestartOnIdle>false</RestartOnIdle>
        </IdleSettings>
        <AllowStartOnDemand>true</AllowStartOnDemand>
        <Enabled>true</Enabled>
        <Hidden>false</Hidden>
        <RunOnlyIfIdle>false</RunOnlyIfIdle>
        <WakeToRun>true</WakeToRun>
        <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
        <Priority>6</Priority>
    </Settings>
    <Actions Context="Author">
        <Exec>
            <Command>{self.python_executable}</Command>
            <Arguments>"{self.main_script}" --mode={task_type} --schedule-time={schedule_time}</Arguments>
            <WorkingDirectory>{self.main_script.parent}</WorkingDirectory>
        </Exec>
    </Actions>
</Task>"""
        
        return task_xml
    
    def _generate_interval_task_xml(self, task_name: str, interval_minutes: int, task_type: str) -> str:
        """Generate XML definition for interval-based scheduled task"""
        username = os.getenv('USERNAME', 'User')
        
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
    <RegistrationInfo>
        <Date>{datetime.now().isoformat()}</Date>
        <Author>{username}</Author>
        <Description>News Delivery System - Urgent news check every {interval_minutes} minutes</Description>
        <URI>\\{self.task_prefix}\\{task_name}</URI>
    </RegistrationInfo>
    <Triggers>
        <TimeTrigger>
            <StartBoundary>{datetime.now().isoformat()}</StartBoundary>
            <Enabled>true</Enabled>
            <Repetition>
                <Interval>PT{interval_minutes}M</Interval>
            </Repetition>
        </TimeTrigger>
    </Triggers>
    <Principals>
        <Principal id="Author">
            <UserId>{username}</UserId>
            <LogonType>InteractiveToken</LogonType>
            <RunLevel>LeastPrivilege</RunLevel>
        </Principal>
    </Principals>
    <Settings>
        <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
        <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
        <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
        <AllowHardTerminate>true</AllowHardTerminate>
        <StartWhenAvailable>true</StartWhenAvailable>
        <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
        <IdleSettings>
            <StopOnIdleEnd>false</StopOnIdleEnd>
            <RestartOnIdle>false</RestartOnIdle>
        </IdleSettings>
        <AllowStartOnDemand>true</AllowStartOnDemand>
        <Enabled>true</Enabled>
        <Hidden>false</Hidden>
        <RunOnlyIfIdle>false</RunOnlyIfIdle>
        <WakeToRun>false</WakeToRun>
        <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
        <Priority>6</Priority>
    </Settings>
    <Actions Context="Author">
        <Exec>
            <Command>{self.python_executable}</Command>
            <Arguments>"{self.main_script}" --mode={task_type}</Arguments>
            <WorkingDirectory>{self.main_script.parent}</WorkingDirectory>
        </Exec>
    </Actions>
</Task>"""
        
        return task_xml
    
    def delete_all_tasks(self) -> Dict[str, bool]:
        """Delete all news delivery scheduled tasks"""
        results = {}
        
        try:
            for task_config in self.task_schedules.values():
                task_name = task_config['name']
                success = self._delete_task(task_name)
                results[task_name] = success
            
            self.logger.info(f"Task deletion results: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to delete scheduled tasks: {e}")
            return {task['name']: False for task in self.task_schedules.values()}
    
    def _delete_task(self, task_name: str) -> bool:
        """Delete specific scheduled task"""
        try:
            cmd = [
                'schtasks',
                '/delete',
                '/tn', f'{self.task_prefix}\\{task_name}',
                '/f'  # Force delete without confirmation
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Successfully deleted task: {task_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            if "cannot find the file specified" in e.stderr.lower():
                self.logger.info(f"Task {task_name} does not exist (already deleted)")
                return True
            else:
                self.logger.error(f"Failed to delete task {task_name}: {e.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting task {task_name}: {e}")
            return False
    
    def get_task_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all scheduled tasks"""
        status = {}
        
        try:
            for task_config in self.task_schedules.values():
                task_name = task_config['name']
                task_status = self._get_single_task_status(task_name)
                status[task_name] = task_status
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get task status: {e}")
            return {}
    
    def _get_single_task_status(self, task_name: str) -> Dict[str, Any]:
        """Get status of a single scheduled task"""
        try:
            cmd = [
                'schtasks',
                '/query',
                '/tn', f'{self.task_prefix}\\{task_name}',
                '/fo', 'csv',
                '/v'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse CSV output
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                headers = [h.strip('"') for h in lines[0].split(',')]
                values = [v.strip('"') for v in lines[1].split(',')]
                task_info = dict(zip(headers, values))
                
                return {
                    'exists': True,
                    'status': task_info.get('Status', 'Unknown'),
                    'last_run': task_info.get('Last Run Time', 'Never'),
                    'next_run': task_info.get('Next Run Time', 'Not scheduled'),
                    'last_result': task_info.get('Last Result', 'Unknown')
                }
            else:
                return {'exists': False}
                
        except subprocess.CalledProcessError:
            return {'exists': False}
        except Exception as e:
            self.logger.error(f"Error getting status for task {task_name}: {e}")
            return {'exists': False, 'error': str(e)}
    
    def enable_task(self, task_name: str) -> bool:
        """Enable a specific scheduled task"""
        try:
            cmd = [
                'schtasks',
                '/change',
                '/tn', f'{self.task_prefix}\\{task_name}',
                '/enable'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Successfully enabled task: {task_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to enable task {task_name}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error enabling task {task_name}: {e}")
            return False
    
    def disable_task(self, task_name: str) -> bool:
        """Disable a specific scheduled task"""
        try:
            cmd = [
                'schtasks',
                '/change',
                '/tn', f'{self.task_prefix}\\{task_name}',
                '/disable'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Successfully disabled task: {task_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to disable task {task_name}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error disabling task {task_name}: {e}")
            return False
    
    def run_task_immediately(self, task_name: str) -> bool:
        """Run a specific scheduled task immediately"""
        try:
            cmd = [
                'schtasks',
                '/run',
                '/tn', f'{self.task_prefix}\\{task_name}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Successfully triggered immediate run for task: {task_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to run task {task_name}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error running task {task_name}: {e}")
            return False
    
    def create_emergency_alert_task(self, cvss_threshold: float = 9.0, importance_threshold: int = 10) -> bool:
        """Create emergency alert task for critical security vulnerabilities"""
        try:
            task_name = f'{self.task_prefix}_EmergencyAlert'
            
            task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
    <RegistrationInfo>
        <Date>{datetime.now().isoformat()}</Date>
        <Author>{os.getenv('USERNAME', 'User')}</Author>
        <Description>Emergency alert for critical security vulnerabilities (CVSS >= {cvss_threshold})</Description>
        <URI>\\{task_name}</URI>
    </RegistrationInfo>
    <Triggers>
        <TimeTrigger>
            <StartBoundary>{datetime.now().isoformat()}</StartBoundary>
            <Enabled>true</Enabled>
            <Repetition>
                <Interval>PT10M</Interval>
            </Repetition>
        </TimeTrigger>
    </Triggers>
    <Principals>
        <Principal id="Author">
            <UserId>{os.getenv('USERNAME', 'User')}</UserId>
            <LogonType>InteractiveToken</LogonType>
            <RunLevel>LeastPrivilege</RunLevel>
        </Principal>
    </Principals>
    <Settings>
        <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
        <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
        <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
        <AllowHardTerminate>true</AllowHardTerminate>
        <StartWhenAvailable>true</StartWhenAvailable>
        <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
        <AllowStartOnDemand>true</AllowStartOnDemand>
        <Enabled>true</Enabled>
        <Hidden>false</Hidden>
        <RunOnlyIfIdle>false</RunOnlyIfIdle>
        <WakeToRun>true</WakeToRun>
        <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
        <Priority>4</Priority>
    </Settings>
    <Actions Context="Author">
        <Exec>
            <Command>{self.python_executable}</Command>
            <Arguments>"{self.main_script}" --mode=emergency_check --cvss-threshold={cvss_threshold} --importance-threshold={importance_threshold}</Arguments>
            <WorkingDirectory>{self.main_script.parent}</WorkingDirectory>
        </Exec>
    </Actions>
</Task>"""
            
            # Save XML to temporary file
            temp_xml_file = Path(f'temp_emergency_alert.xml')
            with open(temp_xml_file, 'w', encoding='utf-8') as f:
                f.write(task_xml)
            
            # Create task
            cmd = [
                'schtasks',
                '/create',
                '/tn', task_name,
                '/xml', str(temp_xml_file),
                '/f'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Clean up
            temp_xml_file.unlink(missing_ok=True)
            
            self.logger.info("Successfully created emergency alert task")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create emergency alert task: {e}")
            return False
    
    def setup_maintenance_tasks(self) -> Dict[str, bool]:
        """Setup system maintenance tasks"""
        results = {}
        
        # Weekly log cleanup task
        try:
            cleanup_task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
    <RegistrationInfo>
        <Date>{datetime.now().isoformat()}</Date>
        <Author>{os.getenv('USERNAME', 'User')}</Author>
        <Description>Weekly maintenance and log cleanup for News Delivery System</Description>
        <URI>\\{self.task_prefix}_Maintenance</URI>
    </RegistrationInfo>
    <Triggers>
        <CalendarTrigger>
            <StartBoundary>{datetime.now().strftime('%Y-%m-%d')}T02:00:00</StartBoundary>
            <Enabled>true</Enabled>
            <ScheduleByWeek>
                <WeeksInterval>1</WeeksInterval>
                <DaysOfWeek>
                    <Sunday />
                </DaysOfWeek>
            </ScheduleByWeek>
        </CalendarTrigger>
    </Triggers>
    <Principals>
        <Principal id="Author">
            <UserId>{os.getenv('USERNAME', 'User')}</UserId>
            <LogonType>InteractiveToken</LogonType>
            <RunLevel>LeastPrivilege</RunLevel>
        </Principal>
    </Principals>
    <Settings>
        <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
        <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
        <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
        <AllowHardTerminate>true</AllowHardTerminate>
        <StartWhenAvailable>true</StartWhenAvailable>
        <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
        <AllowStartOnDemand>true</AllowStartOnDemand>
        <Enabled>true</Enabled>
        <Hidden>false</Hidden>
        <RunOnlyIfIdle>false</RunOnlyIfIdle>
        <WakeToRun>false</WakeToRun>
        <ExecutionTimeLimit>PT15M</ExecutionTimeLimit>
        <Priority>6</Priority>
    </Settings>
    <Actions Context="Author">
        <Exec>
            <Command>{self.python_executable}</Command>
            <Arguments>"{self.main_script}" --mode=maintenance</Arguments>
            <WorkingDirectory>{self.main_script.parent}</WorkingDirectory>
        </Exec>
    </Actions>
</Task>"""
            
            # Save and create maintenance task
            temp_xml_file = Path('temp_maintenance.xml')
            with open(temp_xml_file, 'w', encoding='utf-8') as f:
                f.write(cleanup_task_xml)
            
            cmd = [
                'schtasks',
                '/create',
                '/tn', f'{self.task_prefix}_Maintenance',
                '/xml', str(temp_xml_file),
                '/f'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            temp_xml_file.unlink(missing_ok=True)
            
            results['maintenance'] = True
            self.logger.info("Successfully created maintenance task")
            
        except Exception as e:
            results['maintenance'] = False
            self.logger.error(f"Failed to create maintenance task: {e}")
        
        return results
    
    def export_task_configuration(self, output_file: str = 'task_configuration.json') -> bool:
        """Export current task configuration to JSON file"""
        try:
            config_data = {
                'task_schedules': self.task_schedules,
                'python_executable': str(self.python_executable),
                'main_script': str(self.main_script),
                'task_prefix': self.task_prefix,
                'export_timestamp': datetime.now().isoformat(),
                'task_status': self.get_task_status()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Task configuration exported to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export task configuration: {e}")
            return False
    
    def validate_windows_environment(self) -> Dict[str, Any]:
        """Validate Windows environment for task scheduler integration"""
        validation_results = {
            'is_windows': sys.platform.startswith('win'),
            'schtasks_available': False,
            'python_executable_exists': False,
            'main_script_exists': False,
            'user_has_permissions': False,
            'recommendations': []
        }
        
        try:
            # Check if schtasks command is available
            result = subprocess.run(['schtasks', '/?'], capture_output=True, text=True)
            validation_results['schtasks_available'] = result.returncode == 0
            
            # Check Python executable
            validation_results['python_executable_exists'] = Path(self.python_executable).exists()
            
            # Check main script
            validation_results['main_script_exists'] = self.main_script.exists()
            
            # Test user permissions by trying to query existing tasks
            try:
                result = subprocess.run(['schtasks', '/query'], capture_output=True, text=True, check=True)
                validation_results['user_has_permissions'] = True
            except subprocess.CalledProcessError:
                validation_results['user_has_permissions'] = False
                validation_results['recommendations'].append(
                    "Run as Administrator or ensure user has task scheduling permissions"
                )
            
            # Generate recommendations
            if not validation_results['is_windows']:
                validation_results['recommendations'].append(
                    "Windows Task Scheduler only available on Windows systems"
                )
            
            if not validation_results['schtasks_available']:
                validation_results['recommendations'].append(
                    "schtasks command not available - ensure Windows Task Scheduler service is running"
                )
            
            if not validation_results['python_executable_exists']:
                validation_results['recommendations'].append(
                    f"Python executable not found at: {self.python_executable}"
                )
            
            if not validation_results['main_script_exists']:
                validation_results['recommendations'].append(
                    f"Main script not found at: {self.main_script}"
                )
            
            validation_results['overall_ready'] = all([
                validation_results['is_windows'],
                validation_results['schtasks_available'],
                validation_results['python_executable_exists'],
                validation_results['main_script_exists'],
                validation_results['user_has_permissions']
            ])
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Environment validation failed: {e}")
            validation_results['error'] = str(e)
            return validation_results


def create_setup_script() -> str:
    """Create a PowerShell setup script for easy deployment"""
    setup_script = """
# News Delivery System - Windows Task Scheduler Setup
# PowerShell script for automated task creation

Write-Host "Setting up News Delivery System scheduled tasks..." -ForegroundColor Green

# Import the module and create scheduler instance
try {
    $pythonPath = (Get-Command python).Source
    $scriptPath = Split-Path -Parent $PSScriptRoot
    $mainScript = Join-Path $scriptPath "src\main.py"
    
    Write-Host "Python executable: $pythonPath" -ForegroundColor Yellow
    Write-Host "Main script: $mainScript" -ForegroundColor Yellow
    
    # Create the scheduled tasks using Python
    $createTasksCommand = "`"$pythonPath`" `"$mainScript`" --setup-tasks"
    
    Write-Host "Creating scheduled tasks..." -ForegroundColor Yellow
    Invoke-Expression $createTasksCommand
    
    Write-Host "Task setup completed successfully!" -ForegroundColor Green
    Write-Host "You can view the tasks in Windows Task Scheduler under 'NewsDeliverySystem' folder" -ForegroundColor Cyan
    
} catch {
    Write-Error "Failed to setup tasks: $_"
    Write-Host "Please ensure you are running as Administrator" -ForegroundColor Red
}

Read-Host "Press Enter to continue..."
"""
    
    return setup_script


# CLI interface for task management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Windows Task Scheduler Management for News Delivery System')
    parser.add_argument('--create', action='store_true', help='Create all scheduled tasks')
    parser.add_argument('--delete', action='store_true', help='Delete all scheduled tasks')
    parser.add_argument('--status', action='store_true', help='Show status of all tasks')
    parser.add_argument('--validate', action='store_true', help='Validate Windows environment')
    parser.add_argument('--export-config', type=str, help='Export task configuration to file')
    parser.add_argument('--enable', type=str, help='Enable specific task')
    parser.add_argument('--disable', type=str, help='Disable specific task')
    parser.add_argument('--run', type=str, help='Run specific task immediately')
    
    args = parser.parse_args()
    
    scheduler = WindowsTaskScheduler()
    
    if args.create:
        print("Creating scheduled tasks...")
        results = scheduler.create_scheduled_tasks()
        for task, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {task}")
    
    elif args.delete:
        print("Deleting scheduled tasks...")
        results = scheduler.delete_all_tasks()
        for task, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {task}")
    
    elif args.status:
        print("Task Status:")
        status = scheduler.get_task_status()
        for task_name, task_info in status.items():
            print(f"\n{task_name}:")
            for key, value in task_info.items():
                print(f"  {key}: {value}")
    
    elif args.validate:
        print("Validating Windows environment...")
        validation = scheduler.validate_windows_environment()
        print(f"Overall ready: {validation['overall_ready']}")
        for key, value in validation.items():
            if key != 'recommendations':
                print(f"{key}: {value}")
        if validation['recommendations']:
            print("\nRecommendations:")
            for rec in validation['recommendations']:
                print(f"- {rec}")
    
    elif args.export_config:
        scheduler.export_task_configuration(args.export_config)
        print(f"Configuration exported to: {args.export_config}")
    
    elif args.enable:
        success = scheduler.enable_task(args.enable)
        print(f"Enable {args.enable}: {'✓' if success else '✗'}")
    
    elif args.disable:
        success = scheduler.disable_task(args.disable)
        print(f"Disable {args.disable}: {'✓' if success else '✗'}")
    
    elif args.run:
        success = scheduler.run_task_immediately(args.run)
        print(f"Run {args.run}: {'✓' if success else '✗'}")
    
    else:
        parser.print_help()