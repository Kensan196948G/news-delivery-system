#!/usr/bin/env python3
"""
Advanced Health Monitoring and Self-Healing System
高度なヘルスモニタリングと自動修復システム

システムの健全性を監視し、問題を自動的に検出・修復
"""

import asyncio
import json
import logging
import os
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
import sqlite3

from ..utils.path_resolver import get_path_resolver
from ..utils.config import get_config
from ..utils.logger import setup_logger


class HealthMonitor:
    """システムヘルスモニタリングクラス"""
    
    def __init__(self):
        self.path_resolver = get_path_resolver()
        self.config = get_config()
        self.logger = setup_logger(__name__)
        
        # モニタリング設定
        self.check_interval = 300  # 5分ごとにチェック
        self.metrics_history = []
        self.max_history_size = 288  # 24時間分（5分間隔）
        
        # しきい値設定
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'api_response_time': 5.0,  # 秒
            'error_rate': 0.1,  # 10%
            'database_size_mb': 1000,  # 1GB
        }
        
        # 自動修復アクション
        self.healing_actions = {
            'high_memory': self._heal_high_memory,
            'high_disk': self._heal_high_disk,
            'api_failure': self._heal_api_failure,
            'database_large': self._heal_database_size,
            'cache_overflow': self._heal_cache_overflow,
        }
        
        # アラート状態
        self.alert_states = {}
        self.alert_cooldown = 3600  # 1時間のクールダウン
        
    async def start_monitoring(self):
        """モニタリングを開始"""
        self.logger.info("Starting health monitoring system")
        
        while True:
            try:
                # ヘルスチェック実行
                health_status = await self.perform_health_check()
                
                # メトリクスを記録
                self._record_metrics(health_status)
                
                # 問題を検出して修復
                await self._detect_and_heal(health_status)
                
                # レポート生成
                self._generate_report(health_status)
                
                # 次のチェックまで待機
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)  # エラー時は1分後に再試行
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """包括的なヘルスチェックを実行"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'system': await self._check_system_resources(),
            'apis': await self._check_api_health(),
            'database': await self._check_database_health(),
            'cache': await self._check_cache_health(),
            'processes': await self._check_process_health(),
            'storage': await self._check_storage_health(),
            'network': await self._check_network_health(),
            'overall_health': 'healthy',
            'issues': [],
            'recommendations': []
        }
        
        # 全体的な健全性を評価
        health_status['overall_health'] = self._evaluate_overall_health(health_status)
        
        return health_status
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """システムリソースをチェック"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(str(self.path_resolver.data_root))
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'status': 'healthy' if cpu_percent < self.thresholds['cpu_percent'] else 'warning',
                    'cores': psutil.cpu_count()
                },
                'memory': {
                    'percent': memory.percent,
                    'used_gb': memory.used / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'status': 'healthy' if memory.percent < self.thresholds['memory_percent'] else 'warning'
                },
                'disk': {
                    'percent': disk.percent,
                    'used_gb': disk.used / (1024**3),
                    'free_gb': disk.free / (1024**3),
                    'status': 'healthy' if disk.percent < self.thresholds['disk_percent'] else 'critical'
                }
            }
        except Exception as e:
            self.logger.error(f"System resource check failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _check_api_health(self) -> Dict[str, Any]:
        """API健全性をチェック"""
        api_status = {}
        
        # NewsAPI
        if self.config.is_service_enabled('newsapi'):
            api_status['newsapi'] = await self._check_single_api(
                'https://newsapi.org/v2/top-headlines',
                params={'country': 'jp', 'pageSize': 1},
                headers={'X-Api-Key': self.config.get_api_key('newsapi')}
            )
        
        # DeepL API
        if self.config.is_service_enabled('deepl'):
            api_status['deepl'] = await self._check_single_api(
                'https://api-free.deepl.com/v2/usage',
                headers={'Authorization': f'DeepL-Auth-Key {self.config.get_api_key("deepl")}'}
            )
        
        # Claude API
        if self.config.is_service_enabled('claude'):
            api_status['claude'] = {
                'status': 'healthy',  # Claude APIは別途チェック
                'response_time': 0.0
            }
        
        return api_status
    
    async def _check_single_api(self, url: str, params: Dict = None, headers: Dict = None) -> Dict:
        """単一APIをチェック"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    response_time = time.time() - start_time
                    
                    return {
                        'status': 'healthy' if response.status == 200 else 'degraded',
                        'response_time': response_time,
                        'status_code': response.status
                    }
        except asyncio.TimeoutError:
            return {
                'status': 'timeout',
                'response_time': time.time() - start_time,
                'error': 'Request timeout'
            }
        except Exception as e:
            return {
                'status': 'error',
                'response_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """データベース健全性をチェック"""
        try:
            db_path = self.path_resolver.get_database_path()
            
            if not db_path.exists():
                return {'status': 'not_initialized', 'message': 'Database not found'}
            
            # ファイルサイズチェック
            size_mb = db_path.stat().st_size / (1024 * 1024)
            
            # 接続テスト
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # テーブル数を取得
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # 記事数を取得
            try:
                cursor.execute("SELECT COUNT(*) FROM articles")
                article_count = cursor.fetchone()[0]
            except:
                article_count = 0
            
            conn.close()
            
            return {
                'status': 'healthy' if size_mb < self.thresholds['database_size_mb'] else 'warning',
                'size_mb': size_mb,
                'table_count': table_count,
                'article_count': article_count
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def _check_cache_health(self) -> Dict[str, Any]:
        """キャッシュ健全性をチェック"""
        try:
            cache_dir = self.path_resolver.get_cache_path()
            
            # キャッシュディレクトリのサイズを計算
            total_size = 0
            file_count = 0
            
            for path in cache_dir.rglob('*'):
                if path.is_file():
                    total_size += path.stat().st_size
                    file_count += 1
            
            size_mb = total_size / (1024 * 1024)
            
            return {
                'status': 'healthy' if size_mb < 500 else 'warning',  # 500MB制限
                'size_mb': size_mb,
                'file_count': file_count
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def _check_process_health(self) -> Dict[str, Any]:
        """プロセス健全性をチェック"""
        try:
            current_process = psutil.Process()
            
            # プロセス情報
            process_info = {
                'pid': current_process.pid,
                'cpu_percent': current_process.cpu_percent(),
                'memory_mb': current_process.memory_info().rss / (1024 * 1024),
                'threads': current_process.num_threads(),
                'open_files': len(current_process.open_files()),
                'status': 'healthy'
            }
            
            # しきい値チェック
            if process_info['memory_mb'] > 500:  # 500MB制限
                process_info['status'] = 'warning'
            
            return process_info
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def _check_storage_health(self) -> Dict[str, Any]:
        """ストレージ健全性をチェック"""
        try:
            storage_info = {}
            
            # 各ストレージパスをチェック
            paths_to_check = {
                'reports': self.path_resolver.get_report_path(),
                'articles': self.path_resolver.get_article_path(),
                'logs': self.path_resolver.get_log_path(),
                'backup': self.path_resolver.get_backup_path()
            }
            
            for name, path in paths_to_check.items():
                if path.exists():
                    # ディレクトリサイズを計算
                    total_size = sum(
                        f.stat().st_size for f in path.rglob('*') if f.is_file()
                    )
                    storage_info[name] = {
                        'size_mb': total_size / (1024 * 1024),
                        'exists': True
                    }
                else:
                    storage_info[name] = {
                        'size_mb': 0,
                        'exists': False
                    }
            
            return storage_info
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def _check_network_health(self) -> Dict[str, Any]:
        """ネットワーク健全性をチェック"""
        try:
            # 基本的な接続性チェック
            test_urls = [
                ('google', 'https://www.google.com'),
                ('cloudflare', 'https://1.1.1.1')
            ]
            
            network_status = {}
            
            for name, url in test_urls:
                start_time = time.time()
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=5) as response:
                            network_status[name] = {
                                'reachable': response.status == 200,
                                'response_time': time.time() - start_time
                            }
                except:
                    network_status[name] = {
                        'reachable': False,
                        'response_time': time.time() - start_time
                    }
            
            return network_status
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _evaluate_overall_health(self, health_status: Dict) -> str:
        """全体的な健全性を評価"""
        issues = []
        
        # システムリソース評価
        if isinstance(health_status.get('system'), dict):
            if health_status['system'].get('cpu', {}).get('status') == 'warning':
                issues.append('high_cpu')
            if health_status['system'].get('memory', {}).get('status') == 'warning':
                issues.append('high_memory')
            if health_status['system'].get('disk', {}).get('status') in ['warning', 'critical']:
                issues.append('high_disk')
        
        # API評価
        if isinstance(health_status.get('apis'), dict):
            for api_name, api_status in health_status['apis'].items():
                if api_status.get('status') in ['error', 'timeout']:
                    issues.append(f'api_{api_name}_down')
        
        # データベース評価
        if health_status.get('database', {}).get('status') == 'warning':
            issues.append('database_large')
        
        health_status['issues'] = issues
        
        # 全体評価
        if not issues:
            return 'healthy'
        elif len(issues) <= 2:
            return 'degraded'
        else:
            return 'critical'
    
    async def _detect_and_heal(self, health_status: Dict):
        """問題を検出して自動修復"""
        issues = health_status.get('issues', [])
        
        for issue in issues:
            # クールダウンチェック
            if self._is_in_cooldown(issue):
                continue
            
            # 修復アクションマッピング
            action_map = {
                'high_memory': 'high_memory',
                'high_disk': 'high_disk',
                'api_newsapi_down': 'api_failure',
                'api_deepl_down': 'api_failure',
                'database_large': 'database_large'
            }
            
            action_key = action_map.get(issue)
            if action_key and action_key in self.healing_actions:
                self.logger.info(f"Executing healing action for: {issue}")
                
                try:
                    success = await self.healing_actions[action_key](health_status)
                    
                    if success:
                        self.logger.info(f"Successfully healed: {issue}")
                        self._set_cooldown(issue)
                    else:
                        self.logger.warning(f"Failed to heal: {issue}")
                        
                except Exception as e:
                    self.logger.error(f"Healing action failed for {issue}: {e}")
    
    async def _heal_high_memory(self, health_status: Dict) -> bool:
        """高メモリ使用率を修復"""
        try:
            # ガベージコレクション強制実行
            import gc
            gc.collect()
            
            # キャッシュクリア
            cache_dir = self.path_resolver.get_cache_path()
            old_threshold = datetime.now() - timedelta(hours=24)
            
            for cache_file in cache_dir.rglob('*'):
                if cache_file.is_file():
                    if datetime.fromtimestamp(cache_file.stat().st_mtime) < old_threshold:
                        cache_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Memory healing failed: {e}")
            return False
    
    async def _heal_high_disk(self, health_status: Dict) -> bool:
        """高ディスク使用率を修復"""
        try:
            # 古いログファイルを削除
            log_dir = self.path_resolver.get_log_path()
            old_threshold = datetime.now() - timedelta(days=7)
            
            for log_file in log_dir.glob('*.log'):
                if datetime.fromtimestamp(log_file.stat().st_mtime) < old_threshold:
                    log_file.unlink()
            
            # 古いレポートを削除
            report_dir = self.path_resolver.get_report_path()
            old_report_threshold = datetime.now() - timedelta(days=30)
            
            for report_file in report_dir.rglob('*.html'):
                if datetime.fromtimestamp(report_file.stat().st_mtime) < old_report_threshold:
                    report_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Disk healing failed: {e}")
            return False
    
    async def _heal_api_failure(self, health_status: Dict) -> bool:
        """API障害を修復"""
        try:
            # APIキーローテーション（環境変数から代替キーを取得）
            # ここでは単純にキャッシュをクリアして再接続を促す
            
            cache_dir = self.path_resolver.get_cache_path() / 'api_cache'
            if cache_dir.exists():
                for cache_file in cache_dir.glob('*'):
                    cache_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error(f"API healing failed: {e}")
            return False
    
    async def _heal_database_size(self, health_status: Dict) -> bool:
        """データベースサイズを修復"""
        try:
            db_path = self.path_resolver.get_database_path()
            
            # SQLiteのVACUUMコマンドを実行
            conn = sqlite3.connect(str(db_path))
            conn.execute("VACUUM")
            conn.close()
            
            # 古い記事を削除（90日以上前）
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            old_date = (datetime.now() - timedelta(days=90)).isoformat()
            cursor.execute("DELETE FROM articles WHERE collected_at < ?", (old_date,))
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database healing failed: {e}")
            return False
    
    async def _heal_cache_overflow(self, health_status: Dict) -> bool:
        """キャッシュオーバーフローを修復"""
        try:
            cache_dir = self.path_resolver.get_cache_path()
            
            # サイズでソートして古いものから削除
            cache_files = []
            for cache_file in cache_dir.rglob('*'):
                if cache_file.is_file():
                    cache_files.append((cache_file, cache_file.stat().st_mtime))
            
            # 古い順にソート
            cache_files.sort(key=lambda x: x[1])
            
            # 50%のファイルを削除
            to_delete = len(cache_files) // 2
            for cache_file, _ in cache_files[:to_delete]:
                cache_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Cache healing failed: {e}")
            return False
    
    def _is_in_cooldown(self, issue: str) -> bool:
        """クールダウン中かチェック"""
        if issue not in self.alert_states:
            return False
        
        last_alert = self.alert_states[issue]
        return (datetime.now() - last_alert).total_seconds() < self.alert_cooldown
    
    def _set_cooldown(self, issue: str):
        """クールダウンを設定"""
        self.alert_states[issue] = datetime.now()
    
    def _record_metrics(self, health_status: Dict):
        """メトリクスを記録"""
        self.metrics_history.append(health_status)
        
        # 履歴サイズを制限
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
    
    def _generate_report(self, health_status: Dict):
        """ヘルスレポートを生成"""
        report_path = self.path_resolver.get_data_path(
            'monitoring',
            f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(health_status, f, indent=2, ensure_ascii=False)
    
    def get_current_status(self) -> Dict:
        """現在のステータスを取得"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return {'status': 'no_data'}
    
    def get_metrics_summary(self, hours: int = 24) -> Dict:
        """メトリクスサマリーを取得"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        # 指定時間内のメトリクスを抽出
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m['timestamp']) > cutoff
        ]
        
        if not recent_metrics:
            return {'status': 'no_recent_data'}
        
        # サマリー計算
        summary = {
            'period_hours': hours,
            'total_checks': len(recent_metrics),
            'health_distribution': {},
            'average_metrics': {},
            'issues_encountered': set()
        }
        
        # 健全性分布
        for metric in recent_metrics:
            health = metric.get('overall_health', 'unknown')
            summary['health_distribution'][health] = \
                summary['health_distribution'].get(health, 0) + 1
            
            # 問題収集
            for issue in metric.get('issues', []):
                summary['issues_encountered'].add(issue)
        
        # 問題リストを通常のリストに変換
        summary['issues_encountered'] = list(summary['issues_encountered'])
        
        return summary


async def main():
    """メインエントリポイント"""
    monitor = HealthMonitor()
    await monitor.start_monitoring()


if __name__ == '__main__':
    asyncio.run(main())