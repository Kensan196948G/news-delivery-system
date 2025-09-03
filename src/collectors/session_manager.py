"""
Advanced Session Manager for API Clients
高度なAPIクライアントセッション管理
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionPool:
    """セッションプール管理クラス"""
    
    def __init__(self, max_sessions: int = 10, max_per_host: int = 5):
        self.max_sessions = max_sessions
        self.max_per_host = max_per_host
        self.sessions: Dict[str, List[aiohttp.ClientSession]] = {}
        self.session_stats: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()
        
        # コネクタ設定
        self.connector_config = {
            'limit': 100,  # 総接続数制限
            'limit_per_host': 30,  # ホストごとの接続数制限
            'ttl_dns_cache': 300,  # DNSキャッシュTTL（秒）
            'enable_cleanup_closed': True,  # 閉じた接続の自動クリーンアップ
        }
        
        # タイムアウト設定
        self.timeout_config = {
            'total': 30,  # 総タイムアウト
            'connect': 10,  # 接続タイムアウト
            'sock_connect': 10,  # ソケット接続タイムアウト
            'sock_read': 10,  # ソケット読み取りタイムアウト
        }
        
        # セッション設定
        self.session_config = {
            'headers': {
                'User-Agent': 'NewsDeliverySystem/1.0',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
            },
            'trust_env': True,  # プロキシ環境変数を信頼
            'trace_configs': [],  # トレース設定
        }
        
        # パフォーマンス統計
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'connections_created': 0,
            'connections_reused': 0,
            'connections_closed': 0,
        }
        
        # セッションの自動クリーンアップ設定
        self.cleanup_interval = 300  # 5分ごと
        self.session_idle_timeout = 600  # 10分アイドルでクローズ
        
    async def initialize(self):
        """セッションプール初期化"""
        # トレース設定の初期化
        trace_config = aiohttp.TraceConfig()
        trace_config.on_request_start.append(self._on_request_start)
        trace_config.on_request_end.append(self._on_request_end)
        trace_config.on_request_exception.append(self._on_request_exception)
        self.session_config['trace_configs'] = [trace_config]
        
        # クリーンアップタスク開始
        asyncio.create_task(self._cleanup_sessions())
        
        logger.info("Session pool initialized")
    
    @asynccontextmanager
    async def get_session(self, service_name: str, base_url: str = None, timeout: float = 30.0) -> aiohttp.ClientSession:
        """セッション取得（コンテキストマネージャー・タイムアウト付き）"""
        try:
            # タイムアウト付きでセッション取得
            session = await asyncio.wait_for(
                self._acquire_session(service_name, base_url), 
                timeout=timeout
            )
            try:
                yield session
            finally:
                await self._release_session(service_name, session)
        except asyncio.TimeoutError:
            logger.error(f"Session acquisition timeout for {service_name} after {timeout}s")
            raise RuntimeError(f"Session acquisition timeout for {service_name}")
    
    async def _acquire_session(self, service_name: str, base_url: str = None) -> aiohttp.ClientSession:
        """セッション取得（タイムアウト付き）"""
        max_wait_time = 30.0  # 最大30秒待機
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait_time:
            async with self.lock:
                # サービス用セッションリスト初期化
                if service_name not in self.sessions:
                    self.sessions[service_name] = []
                    self.session_stats[service_name] = {
                        'created_at': datetime.now().isoformat(),
                        'last_used': datetime.now().isoformat(),
                        'request_count': 0,
                        'error_count': 0,
                        'total_response_time': 0.0,
                    }
                
                # 既存セッションの再利用
                for session in self.sessions[service_name]:
                    if not session.closed:
                        self.session_stats[service_name]['last_used'] = datetime.now().isoformat()
                        self.performance_stats['connections_reused'] += 1
                        logger.debug(f"Reusing session for {service_name}")
                        return session
                
                # 新規セッション作成
                if len(self.sessions[service_name]) < self.max_per_host:
                    try:
                        session = await self._create_session(service_name, base_url)
                        self.sessions[service_name].append(session)
                        self.performance_stats['connections_created'] += 1
                        logger.debug(f"Created new session for {service_name}")
                        return session
                    except Exception as e:
                        logger.error(f"Failed to create session for {service_name}: {e}")
                        # セッション作成に失敗した場合もリトライする
                
                # セッション数制限に達した場合
                logger.debug(f"Session limit reached for {service_name}, waiting for available session")
            
            # ロック外で待機（デッドロック防止）
            await asyncio.sleep(0.1)
        
        # タイムアウトした場合
        logger.error(f"Session acquisition timeout for {service_name} after {max_wait_time}s")
        
        # 最後の手段として既存セッションを強制的に返す
        async with self.lock:
            if service_name in self.sessions and self.sessions[service_name]:
                # 最初のセッションを返す（閉じていても）
                session = self.sessions[service_name][0]
                if session.closed:
                    logger.warning(f"Returning closed session for {service_name} due to timeout")
                return session
        
        # それでもセッションが無い場合は例外
        raise RuntimeError(f"Unable to acquire session for {service_name} within {max_wait_time}s")
    
    async def _create_session(self, service_name: str, base_url: str = None) -> aiohttp.ClientSession:
        """新規セッション作成"""
        # コネクタ作成
        connector = aiohttp.TCPConnector(
            limit=self.connector_config['limit'],
            limit_per_host=self.connector_config['limit_per_host'],
            ttl_dns_cache=self.connector_config['ttl_dns_cache'],
            enable_cleanup_closed=self.connector_config['enable_cleanup_closed'],
            force_close=False,  # Keep-Alive有効
            keepalive_timeout=30,  # Keep-Aliveタイムアウト
        )
        
        # タイムアウト設定
        timeout = aiohttp.ClientTimeout(
            total=self.timeout_config['total'],
            connect=self.timeout_config['connect'],
            sock_connect=self.timeout_config['sock_connect'],
            sock_read=self.timeout_config['sock_read'],
        )
        
        # セッション作成
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.session_config['headers'].copy(),
            trust_env=self.session_config['trust_env'],
            trace_configs=self.session_config['trace_configs'],
            json_serialize=json.dumps,
        )
        
        # ベースURL設定
        if base_url:
            session._base_url = base_url
        
        return session
    
    async def _release_session(self, service_name: str, session: aiohttp.ClientSession):
        """セッション解放"""
        # セッションは自動的にプールに戻される
        self.session_stats[service_name]['last_used'] = datetime.now().isoformat()
    
    async def close_session(self, service_name: str, session: aiohttp.ClientSession):
        """特定セッションクローズ"""
        async with self.lock:
            if service_name in self.sessions and session in self.sessions[service_name]:
                await session.close()
                self.sessions[service_name].remove(session)
                self.performance_stats['connections_closed'] += 1
                logger.debug(f"Closed session for {service_name}")
    
    async def close_all_sessions(self, service_name: str = None):
        """全セッションクローズ"""
        async with self.lock:
            if service_name:
                # 特定サービスのセッションのみクローズ
                if service_name in self.sessions:
                    for session in self.sessions[service_name]:
                        if not session.closed:
                            await session.close()
                            self.performance_stats['connections_closed'] += 1
                    self.sessions[service_name] = []
                    logger.info(f"Closed all sessions for {service_name}")
            else:
                # 全サービスのセッションをクローズ
                for service, sessions in self.sessions.items():
                    for session in sessions:
                        if not session.closed:
                            await session.close()
                            self.performance_stats['connections_closed'] += 1
                    self.sessions[service] = []
                logger.info("Closed all sessions")
    
    async def _cleanup_sessions(self):
        """定期的なセッションクリーンアップ（改善版）"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # タイムアウト付きでロック取得
                try:
                    async with asyncio.wait_for(self.lock.acquire(), timeout=5.0):
                        for service_name, sessions in list(self.sessions.items()):
                            try:
                                # アイドルセッションのクローズ
                                if service_name in self.session_stats:
                                    last_used = datetime.fromisoformat(self.session_stats[service_name]['last_used'])
                                    idle_time = (datetime.now() - last_used).total_seconds()
                                    
                                    if idle_time > self.session_idle_timeout:
                                        for session in sessions[:]:  # コピーを作成してイテレート
                                            if not session.closed:
                                                try:
                                                    await asyncio.wait_for(session.close(), timeout=2.0)
                                                    self.performance_stats['connections_closed'] += 1
                                                except asyncio.TimeoutError:
                                                    logger.warning(f"Session close timeout for {service_name}")
                                                except Exception as close_error:
                                                    logger.warning(f"Session close error for {service_name}: {close_error}")
                                        self.sessions[service_name] = []
                                        logger.info(f"Cleaned up idle sessions for {service_name}")
                                
                                # 閉じたセッションの削除
                                active_sessions = []
                                for session in sessions:
                                    if not session.closed:
                                        active_sessions.append(session)
                                
                                if len(active_sessions) < len(sessions):
                                    removed = len(sessions) - len(active_sessions)
                                    self.sessions[service_name] = active_sessions
                                    logger.debug(f"Removed {removed} closed sessions for {service_name}")
                                    
                            except Exception as service_error:
                                logger.error(f"Cleanup error for service {service_name}: {service_error}")
                        
                        self.lock.release()
                        
                except asyncio.TimeoutError:
                    logger.warning("Session cleanup skipped due to lock timeout")
                
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
    
    async def _on_request_start(self, session, trace_config_ctx, params):
        """リクエスト開始トレース"""
        trace_config_ctx.start = time.time()
        self.performance_stats['total_requests'] += 1
    
    async def _on_request_end(self, session, trace_config_ctx, params):
        """リクエスト終了トレース"""
        elapsed = time.time() - trace_config_ctx.start
        self.performance_stats['successful_requests'] += 1
        self.performance_stats['total_response_time'] += elapsed
        
        # サービス別統計更新
        service_name = getattr(trace_config_ctx, 'service_name', 'unknown')
        if service_name in self.session_stats:
            self.session_stats[service_name]['request_count'] += 1
            self.session_stats[service_name]['total_response_time'] += elapsed
    
    async def _on_request_exception(self, session, trace_config_ctx, params):
        """リクエスト例外トレース"""
        self.performance_stats['failed_requests'] += 1
        
        service_name = getattr(trace_config_ctx, 'service_name', 'unknown')
        if service_name in self.session_stats:
            self.session_stats[service_name]['error_count'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        stats = self.performance_stats.copy()
        
        # 成功率計算
        if stats['total_requests'] > 0:
            stats['success_rate'] = (stats['successful_requests'] / stats['total_requests']) * 100
            stats['average_response_time'] = stats['total_response_time'] / stats['successful_requests'] if stats['successful_requests'] > 0 else 0
        else:
            stats['success_rate'] = 0
            stats['average_response_time'] = 0
        
        # セッション統計
        stats['sessions'] = {}
        for service_name, sessions in self.sessions.items():
            active_count = sum(1 for s in sessions if not s.closed)
            stats['sessions'][service_name] = {
                'active': active_count,
                'total': len(sessions),
                'stats': self.session_stats.get(service_name, {}),
            }
        
        # 接続効率
        total_connections = stats['connections_created'] + stats['connections_reused']
        if total_connections > 0:
            stats['reuse_rate'] = (stats['connections_reused'] / total_connections) * 100
        else:
            stats['reuse_rate'] = 0
        
        return stats
    
    def save_statistics(self, filepath: Path):
        """統計情報保存"""
        try:
            stats = self.get_statistics()
            stats['timestamp'] = datetime.now().isoformat()
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            
            logger.info(f"Statistics saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save statistics: {e}")


class OptimizedAPIClient:
    """最適化されたAPIクライアント"""
    
    def __init__(self, session_pool: SessionPool):
        self.session_pool = session_pool
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # リトライ設定
        self.max_retries = 3
        self.base_retry_delay = 1
        self.max_retry_delay = 60
        
        # レート制限
        self.rate_limits: Dict[str, Dict] = {}
        
    async def request(self, service_name: str, method: str, url: str, 
                      **kwargs) -> Optional[Dict]:
        """最適化されたHTTPリクエスト"""
        
        # レート制限チェック
        if not await self._check_rate_limit(service_name):
            self.logger.warning(f"Rate limit exceeded for {service_name}")
            return None
        
        # リトライロジック
        for attempt in range(self.max_retries):
            try:
                async with self.session_pool.get_session(service_name) as session:
                    # トレースコンテキスト設定
                    if hasattr(session, '_trace_configs'):
                        for trace_config in session._trace_configs:
                            trace_config.ctx.service_name = service_name
                    
                    # リクエスト実行
                    start_time = time.time()
                    
                    async with session.request(method, url, **kwargs) as response:
                        elapsed = time.time() - start_time
                        
                        # レート制限ヘッダー更新
                        self._update_rate_limits(service_name, response.headers)
                        
                        if response.status == 200:
                            data = await response.json()
                            self.logger.debug(
                                f"{service_name} request successful: {response.status} in {elapsed:.2f}s"
                            )
                            return data
                        
                        elif response.status == 429:  # Too Many Requests
                            retry_after = response.headers.get('Retry-After', '60')
                            wait_time = min(int(retry_after), self.max_retry_delay)
                            
                            self.logger.warning(
                                f"Rate limit for {service_name}: waiting {wait_time}s"
                            )
                            
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(wait_time)
                                continue
                        
                        elif response.status >= 500:  # Server Error
                            wait_time = min(
                                self.base_retry_delay * (2 ** attempt), 
                                self.max_retry_delay
                            )
                            
                            self.logger.warning(
                                f"Server error for {service_name}: {response.status}, "
                                f"retrying in {wait_time}s"
                            )
                            
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(wait_time)
                                continue
                        
                        else:
                            self.logger.error(
                                f"{service_name} request failed: {response.status}"
                            )
                            return None
            
            except asyncio.TimeoutError:
                wait_time = min(
                    self.base_retry_delay * (2 ** attempt), 
                    self.max_retry_delay
                )
                
                self.logger.warning(
                    f"Timeout for {service_name}, retrying in {wait_time}s"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
            
            except Exception as e:
                self.logger.error(f"Request error for {service_name}: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_retry_delay)
                    continue
        
        self.logger.error(f"All retries failed for {service_name}")
        return None
    
    async def _check_rate_limit(self, service_name: str) -> bool:
        """レート制限チェック"""
        if service_name not in self.rate_limits:
            return True
        
        limits = self.rate_limits[service_name]
        
        # リクエスト残数チェック
        if 'remaining' in limits and limits['remaining'] <= 0:
            # リセット時間チェック
            if 'reset' in limits:
                reset_time = datetime.fromtimestamp(limits['reset'])
                if datetime.now() < reset_time:
                    return False
        
        return True
    
    def _update_rate_limits(self, service_name: str, headers: Dict):
        """レート制限情報更新"""
        rate_limit_headers = {
            'X-RateLimit-Limit': 'limit',
            'X-RateLimit-Remaining': 'remaining',
            'X-RateLimit-Reset': 'reset',
            'X-Rate-Limit-Limit': 'limit',
            'X-Rate-Limit-Remaining': 'remaining',
            'X-Rate-Limit-Reset': 'reset',
        }
        
        if service_name not in self.rate_limits:
            self.rate_limits[service_name] = {}
        
        for header_name, key in rate_limit_headers.items():
            if header_name in headers:
                try:
                    value = headers[header_name]
                    if key == 'reset':
                        self.rate_limits[service_name][key] = int(value)
                    else:
                        self.rate_limits[service_name][key] = int(value)
                except (ValueError, TypeError):
                    pass
    
    async def batch_request(self, service_name: str, requests: List[Dict]) -> List[Optional[Dict]]:
        """バッチリクエスト処理"""
        tasks = []
        
        for req in requests:
            task = self.request(
                service_name,
                req.get('method', 'GET'),
                req['url'],
                **req.get('kwargs', {})
            )
            tasks.append(task)
        
        # 並行実行（最大10並行）
        results = []
        for i in range(0, len(tasks), 10):
            batch = tasks[i:i+10]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
        
        return results


# グローバルインスタンス
_session_pool: Optional[SessionPool] = None
_api_client: Optional[OptimizedAPIClient] = None


async def get_session_pool() -> SessionPool:
    """セッションプール取得"""
    global _session_pool
    if _session_pool is None:
        _session_pool = SessionPool()
        await _session_pool.initialize()
    return _session_pool


async def get_api_client() -> OptimizedAPIClient:
    """APIクライアント取得"""
    global _api_client
    if _api_client is None:
        session_pool = await get_session_pool()
        _api_client = OptimizedAPIClient(session_pool)
    return _api_client