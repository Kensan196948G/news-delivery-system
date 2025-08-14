#!/usr/bin/env python3
"""
News Delivery System Scheduler Runner
スケジューラー起動スクリプト
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Change to parent directory and add src to path
root_dir = Path(__file__).parent.parent
os.chdir(root_dir)
sys.path.insert(0, str(root_dir / 'src'))

from src.services.scheduler import NewsDeliveryScheduler
from src.utils.logger import setup_logger


def main():
    """Main entry point for scheduler"""
    
    print("=" * 70)
    print("📅 News Delivery System - Automated Scheduler")
    print("=" * 70)
    print(f"🕐 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Setup logging
    logger = setup_logger('scheduler_runner')
    
    try:
        # Initialize scheduler
        logger.info("Initializing News Delivery Scheduler...")
        scheduler = NewsDeliveryScheduler()
        
        # Display schedule information
        status = scheduler.get_status()
        
        print("📋 Scheduled Tasks:")
        print("-" * 50)
        for task_name, task_info in status['tasks'].items():
            status_icon = "✅" if task_info['enabled'] else "❌"
            print(f"{status_icon} {task_name}")
            print(f"   📝 {task_info['description']}")
            print(f"   ⏰ Schedule: {task_info['schedule_type']} at {task_info['schedule_time']}")
            if task_info['next_run']:
                print(f"   ⏭️  Next run: {task_info['next_run']}")
            print(f"   📊 Runs: {task_info['run_count']}, Errors: {task_info['error_count']}")
            print()
        
        print("=" * 70)
        print("🚀 Starting scheduler... (Press Ctrl+C to stop)")
        print("=" * 70)
        
        # Start scheduler
        scheduler.start()
        
        # Keep running
        try:
            while scheduler.running:
                asyncio.run(asyncio.sleep(1))
        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received...")
            logger.info("Received interrupt signal")
        
    except Exception as e:
        logger.error(f"Scheduler startup failed: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    finally:
        try:
            scheduler.stop()
            print("✅ Scheduler stopped successfully")
        except:
            pass
    
    return 0


if __name__ == "__main__":
    exit(main())