"""
Base Collector Class
ニュース収集の基底クラス - 強化版
"""

import asyncio
import aiohttp
import time
import hashlib
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_manager import CacheManager
from utils.rate_limiter import RateLimiter
from models.article import Article


class CollectionError(Exception):
    """収集関連のエラー"""
    pass


class APIError(CollectionError):
    """API関連のエラー"""
    pass


class ValidationError(CollectionError):
    """データ検証関連のエラー"""
    pass


class BaseCollector(ABC):
    """ニュース収集の基底クラス"""
    
    def __init__(self, config, logger, service_name: str):
        self.config = config
        self.logger = logger
        self.service_name = service_name
        self.cache = CacheManager()
        self.rate_limiter = RateLimiter()
        self.session = None
        
        # API設定
        self.api_key = config.get_api_key(service_name) if hasattr(config, 'get_api_key') else None
        self.timeout = aiohttp.ClientTimeout(total=30)
        
        # リトライ設定
        self.max_retries = 3
        self.base_retry_delay = 1
        self.max_retry_delay = 60
        
        # 統計・パフォーマンス追跡
        self.collection_stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'articles_collected': 0,
            'articles_filtered': 0,
            'total_processing_time': 0.0,
            'average_response_time': 0.0,
            'last_collection_time': None,
            'errors': [],
            'rate_limit_hits': 0
        }
        
        # バリデーション設定
        self.validation_rules = {
            'min_title_length': 10,
            'max_title_length': 500,
            'min_content_length': 50,
            'max_content_length': 50000,
            'required_fields': ['title', 'url'],
            'forbidden_domains': [],
            'forbidden_keywords': ['[removed]', 'advertisement', 'sponsored', 'ad:', 'promo:']
        }
    
    async def __aenter__(self):
        """非同期コンテキストマネージャー入口"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー出口"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def collect(self, **kwargs) -> List[Article]:
        """ニュース収集の実装（サブクラスで実装）"""
        pass
    
    async def fetch_with_cache(self, url: str, params: Dict[str, Any], 
                              cache_ttl: int = 3600) -> Optional[Dict[str, Any]]:
        """キャッシュ付きHTTPリクエスト（レート制限・リトライ機能付き）"""
        
        # キャッシュキー生成
        cache_key = f"{url}:{str(sorted(params.items()))}"
        
        # キャッシュチェック
        cached_response = self.cache.get_api_cache(url, params)
        if cached_response:
            self.logger.debug(f"Cache hit for {self.service_name}: {url}")
            return cached_response
        
        # レート制限チェック
        await self.rate_limiter.wait_if_needed(self.service_name)
        
        # リトライロジック付きHTTPリクエスト
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                async with self.session.get(url, params=params) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    # レート制限記録
                    self.rate_limiter.record_request(self.service_name)
                    
                    # API使用量ログ
                    if hasattr(self.config, 'log_api_usage'):
                        self.config.log_api_usage(
                            self.service_name, 'GET', response.status, response_time
                        )
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # キャッシュに保存
                        self.cache.set_api_cache(url, params, data, cache_ttl)
                        
                        self.logger.debug(
                            f"HTTP request successful for {self.service_name}: "
                            f"{response.status} in {response_time:.1f}ms"
                        )
                        
                        return data
                    
                    elif response.status == 429:  # Too Many Requests
                        retry_after = response.headers.get('Retry-After', '60')
                        wait_time = min(int(retry_after), self.max_retry_delay)
                        
                        self.logger.warning(
                            f"Rate limit exceeded for {self.service_name}. "
                            f"Waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(wait_time)
                            continue
                    
                    elif response.status in [401, 403]:  # Unauthorized/Forbidden
                        self.logger.error(
                            f"Authentication error for {self.service_name}: {response.status}"
                        )
                        return None
                    
                    elif response.status >= 500:  # Server Error
                        wait_time = min(self.base_retry_delay * (2 ** attempt), self.max_retry_delay)
                        
                        self.logger.warning(
                            f"Server error for {self.service_name}: {response.status}. "
                            f"Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(wait_time)
                            continue
                    
                    else:
                        self.logger.error(
                            f"HTTP error for {self.service_name}: {response.status}"
                        )
                        return None
            
            except asyncio.TimeoutError:
                wait_time = min(self.base_retry_delay * (2 ** attempt), self.max_retry_delay)
                
                self.logger.warning(
                    f"Timeout for {self.service_name}. "
                    f"Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
            
            except Exception as e:
                wait_time = min(self.base_retry_delay * (2 ** attempt), self.max_retry_delay)
                
                self.logger.error(
                    f"Request error for {self.service_name}: {e}. "
                    f"Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
        
        self.logger.error(
            f"All {self.max_retries} attempts failed for {self.service_name}: {url}"
        )
        return None
    
    def parse_date(self, date_str: str) -> str:
        """日付文字列のパース"""
        try:
            if date_str:
                # ISO 8601形式の処理
                if date_str.endswith('Z'):
                    date_str = date_str.replace('Z', '+00:00')
                
                dt = datetime.fromisoformat(date_str)
                return dt.isoformat()
            
            return datetime.now().isoformat()
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Date parsing failed for '{date_str}': {e}")
            return datetime.now().isoformat()
    
    def validate_article_data(self, article_data: Dict[str, Any]) -> bool:
        """記事データの基本検証"""
        required_fields = ['title', 'url']
        
        for field in required_fields:
            if not article_data.get(field):
                return False
        
        # 除外条件
        title = article_data.get('title', '').lower()
        excluded_keywords = ['[removed]', 'advertisement', 'sponsored']
        
        for keyword in excluded_keywords:
            if keyword in title:
                return False
        
        return True
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """レート制限状況を取得"""
        return self.rate_limiter.get_status().get(self.service_name, {})
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        return self.cache.get_stats()
    
    def create_content_hash(self, content: str) -> str:
        """コンテンツのハッシュ値を生成（重複チェック用）"""
        normalized_content = content.lower().strip()
        return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()
    
    def enhanced_validate_article_data(self, article_data: Dict[str, Any]) -> Dict[str, Union[bool, str]]:
        """強化された記事データ検証"""
        validation_result = {
            'is_valid': True,
            'reason': '',
            'warnings': []
        }
        
        try:
            # 必須フィールドチェック
            for field in self.validation_rules['required_fields']:
                if not article_data.get(field):
                    validation_result.update({
                        'is_valid': False,
                        'reason': f'Missing required field: {field}'
                    })
                    return validation_result
            
            # タイトル検証
            title = article_data.get('title', '').strip()
            if len(title) < self.validation_rules['min_title_length']:
                validation_result.update({
                    'is_valid': False,
                    'reason': f'Title too short: {len(title)} < {self.validation_rules["min_title_length"]}'
                })
                return validation_result
            
            if len(title) > self.validation_rules['max_title_length']:
                validation_result['warnings'].append(f'Title very long: {len(title)} characters')
                # 長すぎる場合は切り詰めるが有効とする
            
            # コンテンツ検証
            content = article_data.get('content', '') or article_data.get('description', '')
            if content and len(content) < self.validation_rules['min_content_length']:
                validation_result['warnings'].append(f'Content short: {len(content)} characters')
            
            # 禁止キーワードチェック
            title_lower = title.lower()
            for keyword in self.validation_rules['forbidden_keywords']:
                if keyword in title_lower:
                    validation_result.update({
                        'is_valid': False,
                        'reason': f'Contains forbidden keyword: {keyword}'
                    })
                    return validation_result
            
            # URLドメインチェック
            url = article_data.get('url', '')
            for forbidden_domain in self.validation_rules['forbidden_domains']:
                if forbidden_domain in url:
                    validation_result.update({
                        'is_valid': False,
                        'reason': f'URL from forbidden domain: {forbidden_domain}'
                    })
                    return validation_result
            
            # 重複コンテンツチェック
            if hasattr(self, '_collected_hashes'):
                content_hash = self.create_content_hash(title + content)
                if content_hash in self._collected_hashes:
                    validation_result.update({
                        'is_valid': False,
                        'reason': 'Duplicate content detected'
                    })
                    return validation_result
                else:
                    self._collected_hashes.add(content_hash)
            
            return validation_result
            
        except Exception as e:
            validation_result.update({
                'is_valid': False,
                'reason': f'Validation error: {str(e)}'
            })
            return validation_result
    
    def update_collection_stats(self, operation: str, **kwargs):
        """収集統計の更新"""
        try:
            if operation == 'request_made':
                self.collection_stats['requests_made'] += 1
                
            elif operation == 'request_success':
                self.collection_stats['successful_requests'] += 1
                response_time = kwargs.get('response_time', 0)
                self.collection_stats['total_processing_time'] += response_time
                
                # 平均レスポンス時間の更新
                total_requests = self.collection_stats['successful_requests']
                if total_requests > 0:
                    self.collection_stats['average_response_time'] = (
                        self.collection_stats['total_processing_time'] / total_requests
                    )
                    
            elif operation == 'request_failed':
                self.collection_stats['failed_requests'] += 1
                error = kwargs.get('error', 'Unknown error')
                self.collection_stats['errors'].append({
                    'timestamp': datetime.now().isoformat(),
                    'error': str(error)
                })
                
            elif operation == 'cache_hit':
                self.collection_stats['cache_hits'] += 1
                
            elif operation == 'cache_miss':
                self.collection_stats['cache_misses'] += 1
                
            elif operation == 'articles_collected':
                count = kwargs.get('count', 1)
                self.collection_stats['articles_collected'] += count
                
            elif operation == 'articles_filtered':
                count = kwargs.get('count', 1)
                self.collection_stats['articles_filtered'] += count
                
            elif operation == 'rate_limit_hit':
                self.collection_stats['rate_limit_hits'] += 1
                
            # 最新の収集時刻を更新
            self.collection_stats['last_collection_time'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Failed to update collection stats: {e}")
    
    def get_collection_statistics(self) -> Dict[str, Any]:
        """詳細な収集統計を取得"""
        stats = self.collection_stats.copy()
        
        # 成功率計算
        total_requests = stats['requests_made']
        if total_requests > 0:
            stats['success_rate'] = (stats['successful_requests'] / total_requests) * 100
            stats['failure_rate'] = (stats['failed_requests'] / total_requests) * 100
        else:
            stats['success_rate'] = 0
            stats['failure_rate'] = 0
        
        # キャッシュヒット率計算
        total_cache_requests = stats['cache_hits'] + stats['cache_misses']
        if total_cache_requests > 0:
            stats['cache_hit_rate'] = (stats['cache_hits'] / total_cache_requests) * 100
        else:
            stats['cache_hit_rate'] = 0
        
        # 効率性指標
        if stats['articles_collected'] > 0:
            stats['articles_per_request'] = stats['articles_collected'] / max(stats['successful_requests'], 1)
            stats['filter_rate'] = (stats['articles_filtered'] / stats['articles_collected']) * 100
        else:
            stats['articles_per_request'] = 0
            stats['filter_rate'] = 0
        
        # エラー統計
        stats['recent_errors'] = stats['errors'][-5:]  # 最新5件のエラー
        stats['error_count'] = len(stats['errors'])
        
        return stats
    
    def reset_session_stats(self):
        """セッション統計のリセット"""
        self.collection_stats.update({
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'articles_collected': 0,
            'articles_filtered': 0,
            'total_processing_time': 0.0,
            'average_response_time': 0.0,
            'errors': [],
            'rate_limit_hits': 0
        })
        
        # 重複チェック用ハッシュセットをリセット
        self._collected_hashes = set()
        
        self.logger.info(f"{self.service_name}: Session statistics reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """サービスヘルスチェック"""
        health_status = {
            'service': self.service_name,
            'status': 'unknown',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        try:
            # API Key チェック
            health_status['checks']['api_key'] = {
                'status': 'ok' if self.api_key else 'error',
                'message': 'API key configured' if self.api_key else 'API key missing'
            }
            
            # レート制限チェック
            rate_status = self.get_rate_limit_status()
            health_status['checks']['rate_limit'] = {
                'status': 'ok' if not rate_status.get('is_limited', False) else 'warning',
                'message': f"Rate limit: {rate_status}"
            }
            
            # キャッシュチェック
            try:
                cache_stats = self.get_cache_stats()
                health_status['checks']['cache'] = {
                    'status': 'ok',
                    'message': f"Cache operational: {cache_stats}"
                }
            except Exception as e:
                health_status['checks']['cache'] = {
                    'status': 'error',
                    'message': f"Cache error: {e}"
                }
            
            # 全体的なステータス判定
            check_statuses = [check['status'] for check in health_status['checks'].values()]
            if 'error' in check_statuses:
                health_status['status'] = 'error'
            elif 'warning' in check_statuses:
                health_status['status'] = 'warning'
            else:
                health_status['status'] = 'healthy'
                
        except Exception as e:
            health_status.update({
                'status': 'error',
                'error': str(e)
            })
        
        return health_status