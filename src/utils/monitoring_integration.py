"""
Monitoring System Integration
監視システムとcollectorsの統合モジュール
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from .monitoring_system import get_monitoring_system, ErrorCategory
from .error_notifier import ErrorSeverity


logger = logging.getLogger(__name__)


class MonitoredCollectorMixin:
    """コレクターに監視機能を追加するMixin"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitoring = get_monitoring_system()
        self._request_count = 0
        self._error_count = 0
        self._last_error_time = None
    
    @asynccontextmanager
    async def monitor_api_request(self, operation_name: str):
        """API リクエストの監視コンテキストマネージャー"""
        start_time = datetime.now()
        success = False
        error = None
        
        try:
            yield
            success = True
            
        except Exception as e:
            error = e
            self._error_count += 1
            self._last_error_time = datetime.now()
            
            # エラー分類とハンドリング
            await self.monitoring.handle_error_with_classification(
                e, f"{self.__class__.__name__}.{operation_name}"
            )
            raise
        
        finally:
            # API使用量トラッキング
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000  # ms
            
            self._request_count += 1
            await self.monitoring.track_api_usage(
                self.service_name if hasattr(self, 'service_name') else self.__class__.__name__,
                success,
                response_time
            )
    
    async def monitor_collection_process(self, collection_func, *args, **kwargs):
        """ニュース収集プロセス全体の監視"""
        operation_name = f"collect_{collection_func.__name__}"
        
        async with self.monitor_api_request(operation_name):
            return await collection_func(*args, **kwargs)
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """監視統計情報取得"""
        return {
            'request_count': self._request_count,
            'error_count': self._error_count,
            'error_rate': self._error_count / max(self._request_count, 1),
            'last_error_time': self._last_error_time.isoformat() if self._last_error_time else None,
            'monitoring_active': self.monitoring.monitoring_active
        }


class CollectorHealthChecker:
    """コレクターヘルスチェッカー"""
    
    def __init__(self):
        self.monitoring = get_monitoring_system()
        self.health_checks = {}
        self.last_check_times = {}
    
    async def register_collector(self, collector_name: str, collector_instance):
        """コレクターを監視対象に登録"""
        self.health_checks[collector_name] = collector_instance
        self.last_check_times[collector_name] = datetime.now()
        
        logger.info(f"Registered collector for health monitoring: {collector_name}")
    
    async def check_collector_health(self, collector_name: str) -> Dict[str, Any]:
        """個別コレクターのヘルスチェック"""
        if collector_name not in self.health_checks:
            return {'status': 'unknown', 'error': 'Collector not registered'}
        
        collector = self.health_checks[collector_name]
        health_status = {
            'status': 'healthy',
            'last_check': datetime.now().isoformat(),
            'issues': []
        }
        
        try:
            # サービス状況取得
            if hasattr(collector, 'get_service_status'):
                service_status = collector.get_service_status()
                
                # API制限チェック
                if 'remaining_requests' in service_status:
                    remaining = service_status['remaining_requests']
                    daily_limit = service_status.get('daily_limit', 1000)
                    
                    if remaining < daily_limit * 0.1:  # 10%以下
                        health_status['status'] = 'warning'
                        health_status['issues'].append(f"Low API quota: {remaining}/{daily_limit}")
                        
                        # アラート生成
                        await self.monitoring._create_alert(
                            f"low_api_quota_{collector_name}",
                            "api_quota",
                            ErrorSeverity.MEDIUM,
                            f"{collector_name} API quota low: {remaining}/{daily_limit}",
                            {'collector': collector_name, 'remaining': remaining, 'limit': daily_limit}
                        )
                
                # レート制限状況チェック
                if 'rate_limit_status' in service_status:
                    rate_status = service_status['rate_limit_status']
                    if rate_status.get('blocked', False):
                        health_status['status'] = 'degraded'
                        health_status['issues'].append("Rate limited")
            
            # 監視統計チェック（MonitoredCollectorMixin使用の場合）
            if hasattr(collector, 'get_monitoring_stats'):
                monitoring_stats = collector.get_monitoring_stats()
                error_rate = monitoring_stats.get('error_rate', 0)
                
                if error_rate > 0.3:  # 30%以上のエラー率
                    health_status['status'] = 'degraded'
                    health_status['issues'].append(f"High error rate: {error_rate:.1%}")
            
            # 最終チェック時刻更新
            self.last_check_times[collector_name] = datetime.now()
            
        except Exception as e:
            health_status['status'] = 'error'
            health_status['issues'].append(f"Health check failed: {str(e)}")
            
            # ヘルスチェック失敗をエラーとして報告
            await self.monitoring.handle_error_with_classification(
                e, f"health_check_{collector_name}"
            )
        
        return health_status
    
    async def check_all_collectors(self) -> Dict[str, Any]:
        """全コレクターのヘルスチェック"""
        overall_health = {
            'overall_status': 'healthy',
            'collectors': {},
            'summary': {
                'healthy': 0,
                'warning': 0,
                'degraded': 0,
                'error': 0
            }
        }
        
        for collector_name in self.health_checks.keys():
            collector_health = await self.check_collector_health(collector_name)
            overall_health['collectors'][collector_name] = collector_health
            
            # ステータス集計
            status = collector_health['status']
            if status in overall_health['summary']:
                overall_health['summary'][status] += 1
        
        # 全体ステータス決定
        if overall_health['summary']['error'] > 0:
            overall_health['overall_status'] = 'error'
        elif overall_health['summary']['degraded'] > 0:
            overall_health['overall_status'] = 'degraded'
        elif overall_health['summary']['warning'] > 0:
            overall_health['overall_status'] = 'warning'
        
        return overall_health


class NewsCollectionMonitor:
    """ニュース収集プロセス全体の監視"""
    
    def __init__(self):
        self.monitoring = get_monitoring_system()
        self.health_checker = CollectorHealthChecker()
        self.collection_metrics = {}
    
    async def monitor_collection_cycle(self, collection_func):
        """収集サイクル全体の監視デコレータ"""
        async def wrapper(*args, **kwargs):
            cycle_start = datetime.now()
            cycle_id = f"collection_cycle_{cycle_start.strftime('%Y%m%d_%H%M%S')}"
            
            try:
                # 収集前のヘルスチェック
                pre_health = await self.health_checker.check_all_collectors()
                
                # 収集実行
                with self.monitoring.performance_monitor.measure_operation("news_collection_cycle"):
                    result = await collection_func(*args, **kwargs)
                
                # 収集後のメトリクス記録
                cycle_end = datetime.now()
                collection_time = (cycle_end - cycle_start).total_seconds()
                
                self.collection_metrics[cycle_id] = {
                    'start_time': cycle_start.isoformat(),
                    'end_time': cycle_end.isoformat(),
                    'duration_seconds': collection_time,
                    'articles_collected': len(result) if hasattr(result, '__len__') else 0,
                    'pre_health_status': pre_health['overall_status'],
                    'success': True
                }
                
                # 収集後のヘルスチェック
                post_health = await self.health_checker.check_all_collectors()
                
                # システム状態アラート
                if post_health['overall_status'] != 'healthy':
                    await self.monitoring.error_notifier.send_system_status_alert(post_health)
                
                logger.info(f"Collection cycle completed: {len(result) if hasattr(result, '__len__') else 0} articles in {collection_time:.2f}s")
                
                return result
                
            except Exception as e:
                # 失敗時のメトリクス記録
                self.collection_metrics[cycle_id] = {
                    'start_time': cycle_start.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - cycle_start).total_seconds(),
                    'articles_collected': 0,
                    'success': False,
                    'error': str(e)
                }
                
                # エラーハンドリング
                await self.monitoring.handle_error_with_classification(e, "news_collection_cycle")
                raise
        
        return wrapper
    
    async def get_collection_summary(self, hours: int = 24) -> Dict[str, Any]:
        """収集サマリー取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = {
            cycle_id: metrics for cycle_id, metrics in self.collection_metrics.items()
            if datetime.fromisoformat(metrics['start_time']) >= cutoff_time
        }
        
        if not recent_metrics:
            return {'message': 'No collection data available'}
        
        # 統計計算
        successful_cycles = [m for m in recent_metrics.values() if m.get('success', False)]
        total_articles = sum(m.get('articles_collected', 0) for m in successful_cycles)
        avg_duration = sum(m.get('duration_seconds', 0) for m in successful_cycles) / max(len(successful_cycles), 1)
        success_rate = len(successful_cycles) / len(recent_metrics)
        
        return {
            'period_hours': hours,
            'total_cycles': len(recent_metrics),
            'successful_cycles': len(successful_cycles),
            'success_rate': success_rate,
            'total_articles_collected': total_articles,
            'avg_cycle_duration': avg_duration,
            'avg_articles_per_cycle': total_articles / max(len(successful_cycles), 1),
            'latest_cycle': max(recent_metrics.values(), key=lambda x: x['start_time']) if recent_metrics else None
        }


# グローバルインスタンス
_health_checker_instance = None
_collection_monitor_instance = None


def get_health_checker() -> CollectorHealthChecker:
    """グローバルヘルスチェッカーインスタンス取得"""
    global _health_checker_instance
    if _health_checker_instance is None:
        _health_checker_instance = CollectorHealthChecker()
    return _health_checker_instance


def get_collection_monitor() -> NewsCollectionMonitor:
    """グローバル収集監視インスタンス取得"""
    global _collection_monitor_instance
    if _collection_monitor_instance is None:
        _collection_monitor_instance = NewsCollectionMonitor()
    return _collection_monitor_instance


# 便利なデコレータ
def monitor_collection(func):
    """ニュース収集監視デコレータ"""
    monitor = get_collection_monitor()
    return monitor.monitor_collection_cycle(func)


async def setup_monitoring_integration():
    """監視統合の初期設定"""
    monitoring = get_monitoring_system()
    
    # 監視システム開始
    await monitoring.start_monitoring()
    
    # ヘルスチェッカー取得
    health_checker = get_health_checker()
    
    logger.info("Monitoring integration setup completed")
    
    return {
        'monitoring_system': monitoring,
        'health_checker': health_checker,
        'collection_monitor': get_collection_monitor()
    }


async def cleanup_monitoring_integration():
    """監視統合のクリーンアップ"""
    monitoring = get_monitoring_system()
    
    # 監視システム停止
    await monitoring.stop_monitoring()
    
    logger.info("Monitoring integration cleanup completed")