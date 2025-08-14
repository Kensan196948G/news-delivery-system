#!/usr/bin/env python3
"""
Simple News Monitor Agent
シンプルニュース監視エージェント - 独立実行可能
"""

import asyncio
import logging
import sys
import os
import psutil
import json
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/simple-news-monitor.log')
    ]
)
logger = logging.getLogger(__name__)


class SimpleNewsMonitorAgent:
    """シンプルニュース監視エージェント"""
    
    def __init__(self):
        self.agent_id = f"news-monitor-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.running = False
        self.status = "initialized"
        self.start_time = datetime.now()
        
        # 監視統計
        self.metrics = {
            'checks_performed': 0,
            'alerts_generated': 0,
            'system_status': 'unknown',
            'last_check': None
        }
        
        # 監視対象プロセス
        self.target_processes = [
            'python',
            'main.py',
            'news_system',
            'collector'
        ]
        
        logger.info(f"Simple News Monitor Agent initialized: {self.agent_id}")
    
    async def start_monitoring(self):
        """監視開始"""
        logger.info(f"Starting monitoring agent: {self.agent_id}")
        self.running = True
        self.status = "running"
        
        # 並列監視タスク
        await asyncio.gather(
            self._monitor_system_resources(),
            self._monitor_news_processes(),
            self._monitor_log_files(),
            self._generate_status_reports(),
            return_exceptions=True
        )
    
    async def _monitor_system_resources(self):
        """システムリソース監視"""
        while self.running:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # メモリ使用率
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                # ディスク使用率
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                
                # アラートチェック
                if cpu_percent > 80:
                    await self._generate_alert("HIGH_CPU", f"CPU usage: {cpu_percent:.1f}%")
                
                if memory_percent > 85:
                    await self._generate_alert("HIGH_MEMORY", f"Memory usage: {memory_percent:.1f}%")
                
                if disk_percent > 90:
                    await self._generate_alert("HIGH_DISK", f"Disk usage: {disk_percent:.1f}%")
                
                logger.debug(f"System metrics - CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%, Disk: {disk_percent:.1f}%")
                
                self.metrics['system_status'] = 'healthy' if cpu_percent < 80 and memory_percent < 85 else 'warning'
                self.metrics['checks_performed'] += 1
                self.metrics['last_check'] = datetime.now().isoformat()
                
                await asyncio.sleep(60)  # 1分間隔
                
            except Exception as e:
                logger.error(f"System resource monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_news_processes(self):
        """ニュース関連プロセス監視"""
        while self.running:
            try:
                news_processes = []
                
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                    try:
                        proc_info = proc.info
                        cmdline = ' '.join(proc_info['cmdline'] or [])
                        
                        # ニュース関連プロセスをチェック
                        if any(target in cmdline.lower() for target in ['news', 'main.py', 'collector']):
                            news_processes.append({
                                'pid': proc_info['pid'],
                                'name': proc_info['name'],
                                'cmdline': cmdline,
                                'cpu_percent': proc_info['cpu_percent'],
                                'memory_percent': proc_info['memory_percent']
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                logger.info(f"Found {len(news_processes)} news-related processes")
                
                if not news_processes:
                    await self._generate_alert("NO_NEWS_PROCESSES", "No news-related processes found")
                
                await asyncio.sleep(300)  # 5分間隔
                
            except Exception as e:
                logger.error(f"Process monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_log_files(self):
        """ログファイル監視"""
        while self.running:
            try:
                log_directories = [
                    'logs/',
                    'data/logs/',
                    'E:/NewsDeliverySystem/logs/' if os.path.exists('E:/NewsDeliverySystem/logs/') else None
                ]
                
                error_patterns = ['ERROR', 'CRITICAL', 'FAILED', 'Exception', 'Traceback']
                recent_errors = []
                
                for log_dir in filter(None, log_directories):
                    if os.path.exists(log_dir):
                        for log_file in Path(log_dir).glob('*.log'):
                            try:
                                # 最新のログエントリをチェック
                                with open(log_file, 'r', encoding='utf-8') as f:
                                    lines = f.readlines()
                                    
                                # 直近50行をチェック
                                for line in lines[-50:]:
                                    if any(pattern in line for pattern in error_patterns):
                                        recent_errors.append({
                                            'file': str(log_file),
                                            'line': line.strip(),
                                            'timestamp': datetime.now().isoformat()
                                        })
                                        
                            except Exception as e:
                                logger.debug(f"Could not read log file {log_file}: {e}")
                
                if recent_errors:
                    logger.warning(f"Found {len(recent_errors)} recent errors in log files")
                    for error in recent_errors[:5]:  # 最大5件表示
                        logger.warning(f"Log error in {error['file']}: {error['line']}")
                
                await asyncio.sleep(600)  # 10分間隔
                
            except Exception as e:
                logger.error(f"Log monitoring error: {e}")
                await asyncio.sleep(120)
    
    async def _generate_status_reports(self):
        """ステータスレポート生成"""
        while self.running:
            try:
                await asyncio.sleep(1800)  # 30分間隔
                
                uptime = datetime.now() - self.start_time
                status_report = {
                    'agent_id': self.agent_id,
                    'status': self.status,
                    'uptime_seconds': uptime.total_seconds(),
                    'uptime_formatted': str(uptime),
                    'metrics': self.metrics,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"Status Report: {json.dumps(status_report, indent=2)}")
                
                # レポートファイル保存
                os.makedirs('reports', exist_ok=True)
                report_file = f"reports/monitor-status-{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                with open(report_file, 'w') as f:
                    json.dump(status_report, f, indent=2)
                
            except Exception as e:
                logger.error(f"Status report generation error: {e}")
                await asyncio.sleep(300)
    
    async def _generate_alert(self, alert_type: str, message: str):
        """アラート生成"""
        alert = {
            'alert_id': f"{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'agent_id': self.agent_id
        }
        
        logger.warning(f"ALERT: {alert_type} - {message}")
        self.metrics['alerts_generated'] += 1
        
        # アラートファイル保存
        os.makedirs('alerts', exist_ok=True)
        alert_file = f"alerts/alert-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(alert_file, 'w') as f:
            json.dump(alert, f, indent=2)
    
    def get_status(self) -> dict:
        """エージェント状態取得"""
        uptime = datetime.now() - self.start_time
        return {
            'agent_id': self.agent_id,
            'status': self.status,
            'running': self.running,
            'uptime_seconds': uptime.total_seconds(),
            'start_time': self.start_time.isoformat(),
            'metrics': self.metrics
        }
    
    async def stop_monitoring(self):
        """監視停止"""
        logger.info(f"Stopping monitoring agent: {self.agent_id}")
        self.running = False
        self.status = "stopped"


async def main():
    """メイン実行"""
    # ログディレクトリ作成
    for directory in ['logs', 'reports', 'alerts']:
        os.makedirs(directory, exist_ok=True)
    
    logger.info("Starting Simple News Monitor Agent...")
    
    agent = SimpleNewsMonitorAgent()
    
    # 状態表示
    print("\n" + "="*50)
    print("NEWS MONITOR AGENT - PARALLEL EXECUTION")
    print("="*50)
    print(f"Agent ID: {agent.agent_id}")
    print(f"Status: {agent.status}")
    print(f"Capabilities: monitoring, alerting, metrics")
    print(f"Start Time: {agent.start_time}")
    print("="*50)
    
    try:
        await agent.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        await agent.stop_monitoring()
    except Exception as e:
        logger.error(f"Agent error: {e}")
        await agent.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())