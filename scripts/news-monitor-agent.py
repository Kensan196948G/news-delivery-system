#!/usr/bin/env python3
"""
News Monitor Agent - Parallel Monitoring System
ニュース監視エージェント - 並列監視システム
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.monitoring_system import get_monitoring_system
from src.utils.performance_monitor import get_performance_monitor
from src.utils.config import get_config
# Configure logging directly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsMonitorAgent:
    """ニュース監視エージェント"""
    
    def __init__(self):
        self.config = get_config()
        self.monitoring_system = get_monitoring_system()
        self.performance_monitor = get_performance_monitor()
        self.agent_id = f"news-monitor-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.running = False
        
        # 監視設定
        self.monitoring_capabilities = [
            "monitoring",
            "alerting", 
            "metrics",
            "performance_analysis",
            "system_health"
        ]
        
        # エージェント状態
        self.status = "initializing"
        self.last_health_check = None
        self.alerts_generated = 0
        self.metrics_collected = 0
        
        logger.info(f"News Monitor Agent initialized: {self.agent_id}")
        logger.info(f"Capabilities: {', '.join(self.monitoring_capabilities)}")
    
    async def start_agent(self):
        """エージェント開始"""
        try:
            logger.info(f"Starting News Monitor Agent: {self.agent_id}")
            
            # 統合監視システム開始
            await self.monitoring_system.start_monitoring()
            
            # パフォーマンス監視開始
            self.performance_monitor.start_background_monitoring()
            
            self.running = True
            self.status = "running"
            
            logger.info("News Monitor Agent started successfully")
            
            # 並列監視タスク開始
            await asyncio.gather(
                self._monitor_news_collection(),
                self._monitor_system_health(),
                self._monitor_api_usage(),
                self._monitor_performance_metrics(),
                self._generate_periodic_reports()
            )
            
        except Exception as e:
            logger.error(f"Failed to start News Monitor Agent: {e}")
            self.status = "error"
            raise
    
    async def stop_agent(self):
        """エージェント停止"""
        logger.info(f"Stopping News Monitor Agent: {self.agent_id}")
        
        self.running = False
        self.status = "stopping"
        
        # 監視システム停止
        await self.monitoring_system.stop_monitoring()
        self.performance_monitor.stop_background_monitoring()
        
        self.status = "stopped"
        logger.info("News Monitor Agent stopped")
    
    async def _monitor_news_collection(self):
        """ニュース収集監視"""
        while self.running:
            try:
                # ニュース収集プロセスの監視
                collection_status = await self._check_news_collection_status()
                
                if collection_status.get('issues'):
                    logger.warning(f"News collection issues detected: {collection_status['issues']}")
                    self.alerts_generated += len(collection_status['issues'])
                
                self.metrics_collected += 1
                await asyncio.sleep(300)  # 5分間隔
                
            except Exception as e:
                logger.error(f"News collection monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_system_health(self):
        """システムヘルス監視"""
        while self.running:
            try:
                # システムヘルス状態取得
                health_status = self.monitoring_system.get_health_status()
                
                if health_status['status'] in ['critical', 'degraded']:
                    logger.warning(f"System health degraded: {health_status}")
                    self.alerts_generated += 1
                
                self.last_health_check = datetime.now()
                await asyncio.sleep(60)  # 1分間隔
                
            except Exception as e:
                logger.error(f"System health monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_api_usage(self):
        """API使用量監視"""
        while self.running:
            try:
                # 監視ダッシュボードからAPI使用状況取得
                dashboard = self.monitoring_system.get_monitoring_dashboard()
                api_usage = dashboard.get('api_usage', {})
                
                # 使用量警告チェック
                for service, metrics in api_usage.items():
                    usage_percent = metrics.get('usage_percentage', 0)
                    
                    if usage_percent > 80:
                        logger.warning(f"High API usage detected for {service}: {usage_percent:.1f}%")
                        self.alerts_generated += 1
                
                await asyncio.sleep(600)  # 10分間隔
                
            except Exception as e:
                logger.error(f"API usage monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_performance_metrics(self):
        """パフォーマンスメトリクス監視"""
        while self.running:
            try:
                # パフォーマンスメトリクス収集
                current_metrics = self.performance_monitor.get_current_status()
                
                # 異常値チェック
                cpu_usage = current_metrics.get('cpu_usage_percent', 0)
                memory_usage = current_metrics.get('memory_usage_percent', 0)
                
                if cpu_usage > 85:
                    logger.warning(f"High CPU usage: {cpu_usage:.1f}%")
                    self.alerts_generated += 1
                
                if memory_usage > 90:
                    logger.warning(f"High memory usage: {memory_usage:.1f}%")
                    self.alerts_generated += 1
                
                self.metrics_collected += 1
                await asyncio.sleep(120)  # 2分間隔
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _generate_periodic_reports(self):
        """定期レポート生成"""
        while self.running:
            try:
                await asyncio.sleep(1800)  # 30分間隔
                
                report = await self._generate_monitoring_report()
                logger.info(f"Monitoring report generated: {report['summary']}")
                
            except Exception as e:
                logger.error(f"Report generation error: {e}")
                await asyncio.sleep(300)
    
    async def _check_news_collection_status(self) -> dict:
        """ニュース収集状況チェック"""
        try:
            from src.services.news_collector import NewsCollector
            
            collector = NewsCollector(self.config)
            status = collector.get_collector_status()
            
            issues = []
            
            # コレクター別チェック
            for collector_name, collector_info in status.get('collectors', {}).items():
                if collector_info.get('status') == 'error':
                    issues.append(f"{collector_name}: {collector_info.get('error')}")
                elif collector_info.get('last_success'):
                    last_success = datetime.fromisoformat(collector_info['last_success'])
                    if (datetime.now() - last_success).total_seconds() > 3600:  # 1時間以上
                        issues.append(f"{collector_name}: No successful collection for over 1 hour")
            
            return {
                'status': 'healthy' if not issues else 'issues_detected',
                'issues': issues,
                'collectors': status.get('collectors', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to check news collection status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _generate_monitoring_report(self) -> dict:
        """監視レポート生成"""
        try:
            dashboard = self.monitoring_system.get_monitoring_dashboard()
            
            summary = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat(),
                'status': self.status,
                'uptime_seconds': (datetime.now() - self.last_health_check).total_seconds() if self.last_health_check else 0,
                'metrics_collected': self.metrics_collected,
                'alerts_generated': self.alerts_generated,
                'system_status': dashboard.get('system_status', 'unknown'),
                'active_alerts': dashboard.get('alert_count', 0),
                'api_usage_summary': self._summarize_api_usage(dashboard.get('api_usage', {}))
            }
            
            return {'summary': summary, 'full_dashboard': dashboard}
            
        except Exception as e:
            logger.error(f"Failed to generate monitoring report: {e}")
            return {'error': str(e)}
    
    def _summarize_api_usage(self, api_usage: dict) -> dict:
        """API使用量要約"""
        summary = {}
        for service, metrics in api_usage.items():
            summary[service] = {
                'usage_percent': metrics.get('usage_percentage', 0),
                'success_rate': metrics.get('success_rate', 0),
                'avg_response_time': metrics.get('avg_response_time', 0)
            }
        return summary
    
    def get_agent_status(self) -> dict:
        """エージェント状態取得"""
        return {
            'agent_id': self.agent_id,
            'status': self.status,
            'capabilities': self.monitoring_capabilities,
            'running': self.running,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'metrics_collected': self.metrics_collected,
            'alerts_generated': self.alerts_generated,
            'uptime': (datetime.now() - self.last_health_check).total_seconds() if self.last_health_check else 0
        }


async def main():
    """メイン実行関数"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        logger.info("Starting News Monitor Agent in parallel mode...")
        
        # エージェント初期化・開始
        agent = NewsMonitorAgent()
        
        # 状態表示
        print(f"News Monitor Agent Status:")
        print(f"Agent ID: {agent.agent_id}")
        print(f"Capabilities: {', '.join(agent.monitoring_capabilities)}")
        print(f"Status: {agent.status}")
        
        # 並列監視開始
        await agent.start_agent()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        if 'agent' in locals():
            await agent.stop_agent()
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())