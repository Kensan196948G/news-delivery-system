#!/usr/bin/env python3
"""
Scheduler Management CLI Tool
スケジューラー管理ツール
"""

import asyncio
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Change to parent directory and add src to path
root_dir = Path(__file__).parent.parent
os.chdir(root_dir)
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / 'src'))

from src.services.scheduler import NewsDeliveryScheduler
from src.utils.logger import setup_logger


class SchedulerManager:
    """Scheduler management interface"""
    
    def __init__(self):
        self.scheduler = NewsDeliveryScheduler()
        self.logger = setup_logger('scheduler_manager')
    
    def status(self):
        """Show scheduler status"""
        status = self.scheduler.get_status()
        
        print("=" * 70)
        print("📊 Scheduler Status")
        print("=" * 70)
        print(f"🏃 Running: {'Yes' if status['running'] else 'No'}")
        print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        print("📋 Tasks:")
        print("-" * 50)
        
        for task_name, task_info in status['tasks'].items():
            status_icon = "✅" if task_info['enabled'] else "❌"
            print(f"{status_icon} {task_name.replace('_', ' ').title()}")
            print(f"   📝 {task_info['description']}")
            print(f"   ⏰ Schedule: {task_info['schedule_type']} at {task_info['schedule_time']}")
            
            if task_info['last_run']:
                last_run = datetime.fromisoformat(task_info['last_run'])
                print(f"   📊 Last run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"   📊 Last run: Never")
                
            if task_info['next_run']:
                next_run = datetime.fromisoformat(task_info['next_run'])
                print(f"   ⏭️  Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print(f"   📈 Completed: {task_info['run_count']}, Errors: {task_info['error_count']}")
            print()
        
        print("=" * 70)
    
    def enable_task(self, task_name: str):
        """Enable a task"""
        try:
            self.scheduler.enable_task(task_name)
            print(f"✅ Enabled task: {task_name}")
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    def disable_task(self, task_name: str):
        """Disable a task"""
        try:
            self.scheduler.disable_task(task_name)
            print(f"❌ Disabled task: {task_name}")
        except ValueError as e:
            print(f"❌ Error: {e}")
    
    async def run_task(self, task_name: str):
        """Run a task immediately"""
        try:
            print(f"🏃 Running task: {task_name}")
            await self.scheduler.run_task_now(task_name)
            print(f"✅ Task completed: {task_name}")
        except ValueError as e:
            print(f"❌ Error: {e}")
        except Exception as e:
            print(f"❌ Task failed: {e}")
    
    def list_tasks(self):
        """List all available tasks"""
        status = self.scheduler.get_status()
        
        print("📋 Available Tasks:")
        print("-" * 30)
        for task_name, task_info in status['tasks'].items():
            status_icon = "✅" if task_info['enabled'] else "❌"
            print(f"{status_icon} {task_name}")
        print()
    
    def export_config(self, output_file: str):
        """Export scheduler configuration"""
        try:
            config_file = Path('schedule_config.json')
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                with open(output_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"✅ Configuration exported to: {output_file}")
            else:
                print("❌ Configuration file not found")
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def import_config(self, input_file: str):
        """Import scheduler configuration"""
        try:
            with open(input_file, 'r') as f:
                config = json.load(f)
            
            config_file = Path('schedule_config.json')
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Configuration imported from: {input_file}")
            print("⚠️  Restart scheduler to apply changes")
        except Exception as e:
            print(f"❌ Import failed: {e}")


def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(description="News Delivery Scheduler Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show scheduler status')
    
    # List tasks command
    subparsers.add_parser('list', help='List all tasks')
    
    # Enable task command
    enable_parser = subparsers.add_parser('enable', help='Enable a task')
    enable_parser.add_argument('task_name', help='Name of task to enable')
    
    # Disable task command
    disable_parser = subparsers.add_parser('disable', help='Disable a task')
    disable_parser.add_argument('task_name', help='Name of task to disable')
    
    # Run task command
    run_parser = subparsers.add_parser('run', help='Run a task immediately')
    run_parser.add_argument('task_name', help='Name of task to run')
    
    # Export config command
    export_parser = subparsers.add_parser('export', help='Export configuration')
    export_parser.add_argument('output_file', help='Output file path')
    
    # Import config command
    import_parser = subparsers.add_parser('import', help='Import configuration')
    import_parser.add_argument('input_file', help='Input file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize manager
    manager = SchedulerManager()
    
    # Execute command
    if args.command == 'status':
        manager.status()
    elif args.command == 'list':
        manager.list_tasks()
    elif args.command == 'enable':
        manager.enable_task(args.task_name)
    elif args.command == 'disable':
        manager.disable_task(args.task_name)
    elif args.command == 'run':
        asyncio.run(manager.run_task(args.task_name))
    elif args.command == 'export':
        manager.export_config(args.output_file)
    elif args.command == 'import':
        manager.import_config(args.input_file)
    
    return 0


if __name__ == "__main__":
    exit(main())