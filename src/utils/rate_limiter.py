"""
Enhanced Rate Limiting Utility for API calls
レート制限管理強化版 - DeepL文字数制限・Claude詳細制限対応
"""

import asyncio
import time
import json
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import logging

from .config import get_config
from .cache_manager import CacheManager


logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Enhanced rate limit configuration for a service"""
    max_requests: int
    time_window: int  # seconds
    requests_made: int = 0
    window_start: float = field(default_factory=time.time)
    last_request: float = 0
    # Enhanced fields for DeepL character limits
    max_characters: Optional[int] = None
    characters_used: int = 0
    # Burst protection
    burst_limit: Optional[int] = None
    burst_window: int = 60  # 1 minute
    burst_requests: int = 0
    burst_start: float = field(default_factory=time.time)
    
    def reset_if_needed(self):
        """Reset counter if time window has passed"""
        current_time = time.time()
        if current_time - self.window_start >= self.time_window:
            self.requests_made = 0
            self.characters_used = 0
            self.window_start = current_time
        
        # Reset burst counter
        if current_time - self.burst_start >= self.burst_window:
            self.burst_requests = 0
            self.burst_start = current_time
    
    def can_make_request(self, characters: int = 0) -> bool:
        """Check if request can be made within rate limit"""
        self.reset_if_needed()
        
        # Check basic request limit
        if self.requests_made >= self.max_requests:
            return False
        
        # Check character limit (for DeepL)
        if self.max_characters and (self.characters_used + characters) > self.max_characters:
            return False
        
        # Check burst limit
        if self.burst_limit and self.burst_requests >= self.burst_limit:
            return False
        
        return True
    
    def record_request(self, characters: int = 0):
        """Record that a request was made"""
        self.reset_if_needed()
        self.requests_made += 1
        self.characters_used += characters
        self.burst_requests += 1
        self.last_request = time.time()
    
    def time_until_next_request(self, characters: int = 0) -> float:
        """Calculate seconds to wait before next request"""
        if self.can_make_request(characters):
            return 0
        
        current_time = time.time()
        wait_times = []
        
        # Check main window reset
        if self.requests_made >= self.max_requests or \
           (self.max_characters and (self.characters_used + characters) > self.max_characters):
            time_until_reset = self.time_window - (current_time - self.window_start)
            wait_times.append(max(0, time_until_reset))
        
        # Check burst window reset
        if self.burst_limit and self.burst_requests >= self.burst_limit:
            burst_reset = self.burst_window - (current_time - self.burst_start)
            wait_times.append(max(0, burst_reset))
        
        return min(wait_times) if wait_times else 0
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        self.reset_if_needed()
        return {
            'requests_made': self.requests_made,
            'max_requests': self.max_requests,
            'remaining_requests': self.max_requests - self.requests_made,
            'characters_used': self.characters_used,
            'max_characters': self.max_characters,
            'remaining_characters': (self.max_characters - self.characters_used) if self.max_characters else None,
            'burst_requests': self.burst_requests,
            'burst_limit': self.burst_limit,
            'window_progress': (time.time() - self.window_start) / self.time_window,
            'last_request': self.last_request
        }


class EnhancedRateLimiter:
    """Enhanced rate limiter for multiple API services with character limits and burst protection"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache_manager = CacheManager()
        
        # CLAUDE.md仕様準拠のAPI制限設定
        self.limits: Dict[str, RateLimit] = {
            # NewsAPI: 1000 requests per day (CLAUDE.md仕様)
            'newsapi': RateLimit(
                max_requests=1000, 
                time_window=86400,
                burst_limit=50,  # 1分間に50リクエスト
                burst_window=60
            ),
            
            # GNews: 100 requests per day  
            'gnews': RateLimit(
                max_requests=100, 
                time_window=86400,
                burst_limit=10,
                burst_window=60
            ),
            
            # DeepL: 500,000 characters per month (CLAUDE.md仕様)
            'deepl': RateLimit(
                max_requests=2000,  # 日次リクエスト制限
                time_window=86400,
                max_characters=500000,  # 月間文字数制限
                burst_limit=50,
                burst_window=60
            ),
            
            # Claude API: 1000 requests per day (CLAUDE.md仕様)
            'claude': RateLimit(
                max_requests=1000, 
                time_window=86400,
                burst_limit=20,  # API安定性のため低めに設定
                burst_window=60
            ),
            
            # NVD API: Conservative limit
            'nvd': RateLimit(
                max_requests=100, 
                time_window=3600,
                burst_limit=10,
                burst_window=60
            ),
            
            # Gmail API: 250 quota units per day (CLAUDE.md仕様)
            'gmail': RateLimit(
                max_requests=250, 
                time_window=86400,
                burst_limit=10,
                burst_window=60
            )
        }
        
        # 使用統計保存用ファイル
        self.stats_file = self.config.get_storage_path('cache') / 'rate_limit_stats.json'
        self._load_usage_stats()
        
        # 警告閾値設定
        self.warning_thresholds = {
            'requests': 0.8,  # 80%
            'characters': 0.8,  # 80%
            'burst': 0.7      # 70%
        }
        
        logger.info("Enhanced Rate Limiter initialized with CLAUDE.md specifications")
    
    async def wait_if_needed(self, service: str, characters: int = 0) -> bool:
        """Wait if rate limit would be exceeded"""
        if service not in self.limits:
            logger.warning(f"No rate limit configured for service: {service}")
            return True
        
        rate_limit = self.limits[service]
        
        # Check if request can be made
        if rate_limit.can_make_request(characters):
            # Check for warning thresholds
            self._check_warning_thresholds(service)
            return True
        
        wait_time = rate_limit.time_until_next_request(characters)
        
        if wait_time > 0:
            logger.warning(f"Rate limit reached for {service}. Waiting {wait_time:.1f} seconds")
            
            # If wait time is too long, suggest alternatives
            if wait_time > 3600:  # More than 1 hour
                logger.error(f"Long wait time for {service}: {wait_time/3600:.1f} hours")
            
            await asyncio.sleep(min(wait_time, 300))  # Cap wait time at 5 minutes
        
        return True
    
    def record_request(self, service: str, characters: int = 0):
        """Record that a request was made to a service"""
        if service in self.limits:
            self.limits[service].record_request(characters)
            
            # Log usage with character information if applicable
            usage_info = f"Count: {self.limits[service].requests_made}"
            if characters > 0:
                usage_info += f", Characters: {characters} (Total: {self.limits[service].characters_used})"
            
            logger.debug(f"Recorded request for {service}. {usage_info}")
            
            # Periodically save usage stats
            if self.limits[service].requests_made % 10 == 0:
                self._save_usage_stats()
    
    def get_remaining_requests(self, service: str) -> Optional[int]:
        """Get remaining requests for a service"""
        if service not in self.limits:
            return None
        
        rate_limit = self.limits[service]
        rate_limit.reset_if_needed()
        return rate_limit.max_requests - rate_limit.requests_made
    
    def get_remaining_characters(self, service: str) -> Optional[int]:
        """Get remaining characters for a service (DeepL specific)"""
        if service not in self.limits:
            return None
        
        rate_limit = self.limits[service]
        rate_limit.reset_if_needed()
        
        if rate_limit.max_characters:
            return rate_limit.max_characters - rate_limit.characters_used
        return None
    
    def estimate_characters_needed(self, texts: list) -> int:
        """Estimate character count for translation"""
        return sum(len(text) for text in texts if text)
    
    def can_process_batch(self, service: str, texts: list) -> Tuple[bool, str]:
        """Check if a batch of texts can be processed"""
        if service not in self.limits:
            return False, f"No rate limit configured for service: {service}"
        
        characters_needed = self.estimate_characters_needed(texts)
        requests_needed = len(texts)
        
        rate_limit = self.limits[service]
        rate_limit.reset_if_needed()
        
        # Check request limit
        if rate_limit.requests_made + requests_needed > rate_limit.max_requests:
            remaining = rate_limit.max_requests - rate_limit.requests_made
            return False, f"Request limit exceeded. Need {requests_needed}, have {remaining}"
        
        # Check character limit (for DeepL)
        if rate_limit.max_characters:
            if rate_limit.characters_used + characters_needed > rate_limit.max_characters:
                remaining_chars = rate_limit.max_characters - rate_limit.characters_used
                return False, f"Character limit exceeded. Need {characters_needed}, have {remaining_chars}"
        
        # Check burst limit
        if rate_limit.burst_limit and rate_limit.burst_requests + requests_needed > rate_limit.burst_limit:
            remaining_burst = rate_limit.burst_limit - rate_limit.burst_requests
            return False, f"Burst limit exceeded. Need {requests_needed}, have {remaining_burst}"
        
        return True, "OK"
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive status of all rate limits"""
        status = {}
        
        for service, rate_limit in self.limits.items():
            rate_limit.reset_if_needed()
            
            # Basic status
            service_status = rate_limit.get_usage_stats()
            
            # Add computed fields
            service_status.update({
                'window_seconds': rate_limit.time_window,
                'time_until_reset': rate_limit.time_window - (time.time() - rate_limit.window_start),
                'can_make_request': rate_limit.can_make_request(),
                'usage_percentage': (rate_limit.requests_made / rate_limit.max_requests) * 100,
                'character_usage_percentage': (
                    (rate_limit.characters_used / rate_limit.max_characters) * 100
                    if rate_limit.max_characters else None
                ),
                'burst_usage_percentage': (
                    (rate_limit.burst_requests / rate_limit.burst_limit) * 100
                    if rate_limit.burst_limit else None
                ),
                'status': self._get_service_status(service)
            })
            
            status[service] = service_status
        
        return status
    
    def _check_warning_thresholds(self, service: str):
        """Check if usage is approaching limits and log warnings"""
        rate_limit = self.limits[service]
        
        # Check request threshold
        request_usage = rate_limit.requests_made / rate_limit.max_requests
        if request_usage >= self.warning_thresholds['requests']:
            logger.warning(f"{service} request usage at {request_usage:.1%}")
        
        # Check character threshold (DeepL)
        if rate_limit.max_characters:
            char_usage = rate_limit.characters_used / rate_limit.max_characters
            if char_usage >= self.warning_thresholds['characters']:
                logger.warning(f"{service} character usage at {char_usage:.1%}")
        
        # Check burst threshold
        if rate_limit.burst_limit:
            burst_usage = rate_limit.burst_requests / rate_limit.burst_limit
            if burst_usage >= self.warning_thresholds['burst']:
                logger.warning(f"{service} burst usage at {burst_usage:.1%}")
    
    def _get_service_status(self, service: str) -> str:
        """Get human-readable status for a service"""
        rate_limit = self.limits[service]
        
        if not rate_limit.can_make_request():
            return "RATE_LIMITED"
        
        request_usage = rate_limit.requests_made / rate_limit.max_requests
        
        if request_usage >= 0.9:
            return "CRITICAL"
        elif request_usage >= 0.8:
            return "WARNING"
        elif request_usage >= 0.5:
            return "MODERATE"
        else:
            return "OK"
    
    def _load_usage_stats(self):
        """Load saved usage statistics"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    saved_stats = json.load(f)
                
                # Load saved character usage for persistence across restarts
                for service, stats in saved_stats.items():
                    if service in self.limits:
                        # Only restore character usage, not request counts (reset daily)
                        saved_date = datetime.fromisoformat(stats.get('date', '2024-01-01'))
                        if saved_date.date() == datetime.now().date():
                            self.limits[service].characters_used = stats.get('characters_used', 0)
                
                logger.debug("Loaded rate limiter usage statistics")
        except Exception as e:
            logger.error(f"Failed to load usage stats: {e}")
    
    def _save_usage_stats(self):
        """Save current usage statistics"""
        try:
            stats = {}
            for service, rate_limit in self.limits.items():
                stats[service] = {
                    'requests_made': rate_limit.requests_made,
                    'characters_used': rate_limit.characters_used,
                    'date': datetime.now().isoformat(),
                    'last_request': rate_limit.last_request
                }
            
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save usage stats: {e}")
    
    async def reset_service_limits(self, service: str):
        """Manually reset limits for a service (emergency use)"""
        if service in self.limits:
            rate_limit = self.limits[service]
            rate_limit.requests_made = 0
            rate_limit.characters_used = 0
            rate_limit.burst_requests = 0
            rate_limit.window_start = time.time()
            rate_limit.burst_start = time.time()
            
            logger.warning(f"Manually reset rate limits for {service}")
            self._save_usage_stats()
    
    def get_daily_usage_report(self) -> Dict[str, Any]:
        """Generate daily usage report"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'services': {}
        }
        
        for service, rate_limit in self.limits.items():
            rate_limit.reset_if_needed()
            
            service_report = {
                'requests_used': rate_limit.requests_made,
                'requests_limit': rate_limit.max_requests,
                'requests_percentage': (rate_limit.requests_made / rate_limit.max_requests) * 100,
                'status': self._get_service_status(service)
            }
            
            if rate_limit.max_characters:
                service_report.update({
                    'characters_used': rate_limit.characters_used,
                    'characters_limit': rate_limit.max_characters,
                    'characters_percentage': (rate_limit.characters_used / rate_limit.max_characters) * 100
                })
            
            report['services'][service] = service_report
        
        return report


# Compatibility alias
RateLimiter = EnhancedRateLimiter


# グローバルレート制限インスタンス
_rate_limiter_instance = None


def get_rate_limiter() -> EnhancedRateLimiter:
    """グローバルレート制限インスタンス取得"""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = EnhancedRateLimiter()
    return _rate_limiter_instance