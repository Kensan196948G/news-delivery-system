"""
Automated Scheduling Service for News Delivery System
定期実行スケジュール管理サービス
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json

from utils.config import get_config
from utils.logger import setup_logger
from .news_collector import NewsCollector
from .report_generator import ReportGenerator
from .email_delivery import GmailDeliveryService


logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Schedule type enumeration"""
    DAILY = "daily"
    HOURLY = "hourly"
    WEEKLY = "weekly"
    INTERVAL = "interval"


@dataclass
class ScheduledTask:
    """Scheduled task definition"""
    name: str
    task_func: Callable
    schedule_type: ScheduleType
    schedule_time: str  # Format: "HH:MM" for daily, "MM" for hourly, seconds for interval
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    max_errors: int = 5
    description: str = ""
    
    def calculate_next_run(self, base_time: datetime = None) -> datetime:
        """Calculate next run time based on schedule type"""
        if base_time is None:
            base_time = datetime.now()
            
        if self.schedule_type == ScheduleType.DAILY:
            # Parse time string (HH:MM)
            hour, minute = map(int, self.schedule_time.split(':'))
            next_run = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if next_run <= base_time:
                next_run += timedelta(days=1)
                
        elif self.schedule_type == ScheduleType.HOURLY:
            # Parse minute string
            minute = int(self.schedule_time)
            next_run = base_time.replace(minute=minute, second=0, microsecond=0)
            
            # If minute has passed this hour, schedule for next hour
            if next_run <= base_time:
                next_run += timedelta(hours=1)
                
        elif self.schedule_type == ScheduleType.WEEKLY:
            # Parse day and time (format: "MON:09:00")
            day_name, time_str = self.schedule_time.split(':')
            hour, minute = map(int, time_str.split(':'))
            
            days = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
            target_weekday = days[day_name.upper()]
            
            # Calculate days until target weekday
            days_ahead = target_weekday - base_time.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
                
            next_run = base_time + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
        elif self.schedule_type == ScheduleType.INTERVAL:
            # Parse interval in seconds
            interval_seconds = int(self.schedule_time)
            next_run = base_time + timedelta(seconds=interval_seconds)
            
        else:
            raise ValueError(f"Unknown schedule type: {self.schedule_type}")
            
        return next_run
    
    def should_run(self, current_time: datetime = None) -> bool:
        """Check if task should run now"""
        if not self.enabled:
            return False
            
        if self.error_count >= self.max_errors:
            logger.warning(f"Task {self.name} disabled due to too many errors ({self.error_count})")
            return False
            
        if current_time is None:
            current_time = datetime.now()
            
        if self.next_run is None:
            self.next_run = self.calculate_next_run(current_time)
            
        return current_time >= self.next_run


class NewsDeliveryScheduler:
    """Main scheduler for news delivery system"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        self.running = False
        self.tasks: Dict[str, ScheduledTask] = {}
        
        # Initialize services
        self.news_collector = NewsCollector(self.config)
        self.report_generator = ReportGenerator(self.config)
        self.email_service = GmailDeliveryService(self.config)
        
        # Schedule configuration
        self.schedule_file = Path('system/schedule_config.json')
        self.state_file = Path('scheduler_state.json')
        
        # Load configuration
        self._load_schedule_config()
        self._load_scheduler_state()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down scheduler...")
        self.stop()
        sys.exit(0)
    
    def _load_schedule_config(self):
        """Load schedule configuration from file"""
        default_config = {
            "daily_news_collection": {
                "schedule_type": "daily",
                "schedule_time": "07:00",
                "enabled": True,
                "description": "Daily news collection and delivery"
            },
            "urgent_news_check": {
                "schedule_type": "interval", 
                "schedule_time": "3600",  # Every hour
                "enabled": True,
                "description": "Check for urgent/breaking news"
            },
            "system_health_check": {
                "schedule_type": "daily",
                "schedule_time": "23:00",
                "enabled": True,
                "description": "Daily system health and status check"
            },
            "weekly_summary": {
                "schedule_type": "weekly",
                "schedule_time": "SUN:18:00",
                "enabled": False,
                "description": "Weekly news summary report"
            }
        }
        
        if self.schedule_file.exists():
            try:
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.logger.info("Loaded schedule configuration from file")
            except Exception as e:
                self.logger.error(f"Failed to load schedule config: {e}")
                config = default_config
        else:
            config = default_config
            self._save_schedule_config(config)
            self.logger.info("Created default schedule configuration")
        
        # Create scheduled tasks
        task_mapping = {
            "daily_news_collection": self._daily_news_collection,
            "urgent_news_check": self._urgent_news_check,
            "system_health_check": self._system_health_check,
            "weekly_summary": self._weekly_summary
        }
        
        for task_name, task_config in config.items():
            if task_name in task_mapping:
                self.tasks[task_name] = ScheduledTask(
                    name=task_name,
                    task_func=task_mapping[task_name],
                    schedule_type=ScheduleType(task_config["schedule_type"]),
                    schedule_time=task_config["schedule_time"],
                    enabled=task_config.get("enabled", True),
                    description=task_config.get("description", "")
                )
    
    def _save_schedule_config(self, config: Dict[str, Any]):
        """Save schedule configuration to file"""
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save schedule config: {e}")
    
    def _load_scheduler_state(self):
        """Load scheduler state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                for task_name, task_state in state.items():
                    if task_name in self.tasks:
                        task = self.tasks[task_name]
                        task.last_run = datetime.fromisoformat(task_state["last_run"]) if task_state.get("last_run") else None
                        task.run_count = task_state.get("run_count", 0)
                        task.error_count = task_state.get("error_count", 0)
                        
                self.logger.info("Loaded scheduler state from file")
            except Exception as e:
                self.logger.error(f"Failed to load scheduler state: {e}")
    
    def _save_scheduler_state(self):
        """Save scheduler state to file"""
        try:
            state = {}
            for task_name, task in self.tasks.items():
                state[task_name] = {
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "run_count": task.run_count,
                    "error_count": task.error_count
                }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save scheduler state: {e}")
    
    async def _daily_news_collection(self):
        """Daily news collection and delivery task"""
        self.logger.info("Starting daily news collection...")
        
        try:
            # Collect news from all sources
            articles = await self.news_collector.collect_all_news()
            
            if not articles:
                self.logger.warning("No articles collected")
                return
            
            # Generate reports
            report_files = await self.report_generator.generate_daily_report(articles)
            
            # Count urgent articles
            urgent_count = sum(1 for article in articles if getattr(article, 'is_urgent', False))
            
            # Send email delivery
            delivery_record = await self.email_service.send_daily_report(
                report_files, len(articles), urgent_count
            )
            
            self.logger.info(f"Daily news delivery completed: {len(articles)} articles, {urgent_count} urgent")
            
        except Exception as e:
            self.logger.error(f"Daily news collection failed: {e}")
            raise
    
    async def _urgent_news_check(self):
        """Check for urgent/breaking news"""
        self.logger.info("Checking for urgent news...")
        
        try:
            # Collect emergency news
            urgent_articles = await self.news_collector.collect_emergency_news()
            
            if urgent_articles:
                # Generate urgent report
                report_files = await self.report_generator.generate_urgent_report(urgent_articles)
                
                # Send urgent alert
                delivery_record = await self.email_service.send_urgent_alert(
                    report_files, len(urgent_articles)
                )
                
                self.logger.info(f"Urgent news alert sent: {len(urgent_articles)} articles")
            else:
                self.logger.debug("No urgent news found")
                
        except Exception as e:
            self.logger.error(f"Urgent news check failed: {e}")
            raise
    
    async def _system_health_check(self):
        """System health and status check"""
        self.logger.info("Running system health check...")
        
        try:
            # Check API status
            health_status = {
                "timestamp": datetime.now().isoformat(),
                "apis": {},
                "system": {}
            }
            
            # Test API connections
            from ..check_api_keys import check_newsapi_key, check_deepl_key, check_nvd_api
            
            health_status["apis"]["newsapi"] = await check_newsapi_key()
            health_status["apis"]["deepl"] = check_deepl_key()
            health_status["apis"]["nvd"] = await check_nvd_api()
            health_status["apis"]["gmail"] = self.email_service.test_email_connection()
            
            # System status
            health_status["system"]["scheduler_running"] = self.running
            health_status["system"]["active_tasks"] = len([t for t in self.tasks.values() if t.enabled])
            
            # Log health status
            working_apis = sum(1 for status in health_status["apis"].values() if status)
            total_apis = len(health_status["apis"])
            
            self.logger.info(f"System health check: {working_apis}/{total_apis} APIs working")
            
            # Save health report
            health_file = Path('logs/system_health.json')
            health_file.parent.mkdir(exist_ok=True)
            
            with open(health_file, 'w', encoding='utf-8') as f:
                json.dump(health_status, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"System health check failed: {e}")
            raise
    
    async def _weekly_summary(self):
        """Weekly summary report"""
        self.logger.info("Generating weekly summary...")
        
        try:
            # Generate weekly summary report
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # This would typically query the database for articles from the past week
            # For now, we'll create a simple summary
            
            summary_data = {
                "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "generated_at": datetime.now().isoformat(),
                "total_articles": 0,  # Would be calculated from database
                "urgent_alerts": 0,   # Would be calculated from database
                "delivery_success_rate": 100.0  # Would be calculated from delivery records
            }
            
            # Save weekly summary
            summary_file = Path(f'reports/weekly_summary_{end_date.strftime("%Y%m%d")}.json')
            summary_file.parent.mkdir(exist_ok=True)
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Weekly summary generated")
            
        except Exception as e:
            self.logger.error(f"Weekly summary generation failed: {e}")
            raise
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.logger.info("Starting News Delivery Scheduler...")
        
        # Calculate next run times for all tasks
        current_time = datetime.now()
        for task in self.tasks.values():
            if task.enabled:
                task.next_run = task.calculate_next_run(current_time)
                self.logger.info(f"Task '{task.name}' scheduled for {task.next_run}")
        
        # Start the main loop
        asyncio.create_task(self._scheduler_loop())
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        self._save_scheduler_state()
        self.logger.info("News Delivery Scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        self.logger.info("Scheduler loop started")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check each task
                for task_name, task in self.tasks.items():
                    if task.should_run(current_time):
                        self.logger.info(f"Running task: {task.name}")
                        
                        try:
                            # Run the task
                            await task.task_func()
                            
                            # Update task state
                            task.last_run = current_time
                            task.run_count += 1
                            task.next_run = task.calculate_next_run(current_time)
                            
                            self.logger.info(f"Task '{task.name}' completed successfully. Next run: {task.next_run}")
                            
                        except Exception as e:
                            task.error_count += 1
                            self.logger.error(f"Task '{task.name}' failed: {e}")
                            
                            # Reschedule even if failed
                            task.next_run = task.calculate_next_run(current_time)
                
                # Save state periodically
                self._save_scheduler_state()
                
                # Sleep for a minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
        
        self.logger.info("Scheduler loop ended")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "running": self.running,
            "tasks": {
                name: {
                    "enabled": task.enabled,
                    "schedule_type": task.schedule_type.value,
                    "schedule_time": task.schedule_time,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "run_count": task.run_count,
                    "error_count": task.error_count,
                    "description": task.description
                }
                for name, task in self.tasks.items()
            }
        }
    
    def enable_task(self, task_name: str):
        """Enable a specific task"""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = True
            self.tasks[task_name].next_run = self.tasks[task_name].calculate_next_run()
            self.logger.info(f"Enabled task: {task_name}")
        else:
            raise ValueError(f"Task not found: {task_name}")
    
    def disable_task(self, task_name: str):
        """Disable a specific task"""
        if task_name in self.tasks:
            self.tasks[task_name].enabled = False
            self.logger.info(f"Disabled task: {task_name}")
        else:
            raise ValueError(f"Task not found: {task_name}")
    
    async def run_task_now(self, task_name: str):
        """Run a specific task immediately"""
        if task_name not in self.tasks:
            raise ValueError(f"Task not found: {task_name}")
        
        task = self.tasks[task_name]
        self.logger.info(f"Running task '{task_name}' manually...")
        
        try:
            await task.task_func()
            task.last_run = datetime.now()
            task.run_count += 1
            self.logger.info(f"Task '{task_name}' completed successfully")
        except Exception as e:
            task.error_count += 1
            self.logger.error(f"Task '{task_name}' failed: {e}")
            raise


async def main():
    """Main scheduler entry point"""
    
    # Initialize scheduler
    scheduler = NewsDeliveryScheduler()
    
    # Start scheduler
    scheduler.start()
    
    try:
        # Run indefinitely
        while scheduler.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        scheduler.logger.info("Received interrupt signal")
    finally:
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())