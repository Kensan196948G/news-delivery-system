"""
Logging System Module
ログシステムモジュール
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

from .config import get_config


class CustomFormatter(logging.Formatter):
    """カスタムログフォーマッター"""
    
    def __init__(self, include_color: bool = False):
        self.include_color = include_color
        
        # Color configuration for console output
        if include_color and HAS_COLORLOG:
            self.formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            # File output format (no color)
            self.formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
    
    def format(self, record):
        return self.formatter.format(record)


class NewsDeliveryLogger:
    """ニュース配信システム専用ロガー"""
    
    def __init__(self, name: str, config=None):
        self.name = name
        self.config = config or get_config()
        self.logger = logging.getLogger(name)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        """ロガーのセットアップ"""
        # Get log level from config
        log_level = self.config.get('system', 'log_level', default='INFO').upper()
        self.logger.setLevel(getattr(logging, log_level))
        
        # Console handler with color
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter(include_color=True))
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        self._setup_file_handler()
        
        # Error file handler
        self._setup_error_handler()
    
    def _setup_file_handler(self):
        """ファイルハンドラーのセットアップ（ローテーション付き）"""
        try:
            logs_dir = self.config.get_storage_path('logs')
            log_file = logs_dir / f"news_system_{datetime.now().strftime('%Y%m')}.log"
            
            # Rotating file handler (10MB per file, keep 5 files)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(CustomFormatter(include_color=False))
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            # If file logging fails, continue with console logging only
            self.logger.warning(f"Failed to setup file logging: {e}")
    
    def _setup_error_handler(self):
        """エラー専用ファイルハンドラー"""
        try:
            logs_dir = self.config.get_storage_path('logs')
            error_log_file = logs_dir / f"errors_{datetime.now().strftime('%Y%m')}.log"
            
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(CustomFormatter(include_color=False))
            self.logger.addHandler(error_handler)
            
        except Exception as e:
            self.logger.warning(f"Failed to setup error logging: {e}")
    
    def get_logger(self):
        """ロガーインスタンスを取得"""
        return self.logger


class PerformanceLogger:
    """パフォーマンス計測用ロガー"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(f"{logger_name}.performance")
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """タイマー開始"""
        self.start_times[operation] = datetime.now()
        self.logger.debug(f"Started: {operation}")
    
    def end_timer(self, operation: str):
        """タイマー終了"""
        if operation in self.start_times:
            duration = datetime.now() - self.start_times[operation]
            self.logger.info(f"Completed: {operation} - Duration: {duration.total_seconds():.2f}s")
            del self.start_times[operation]
        else:
            self.logger.warning(f"Timer not found for operation: {operation}")
    
    def log_api_call(self, service: str, endpoint: str, status_code: int, response_time: float):
        """API呼び出しログ"""
        self.logger.info(f"API Call - Service: {service}, Endpoint: {endpoint}, "
                        f"Status: {status_code}, Time: {response_time:.3f}s")
    
    def log_processing_stats(self, operation: str, items_processed: int, success_count: int, error_count: int):
        """処理統計ログ"""
        success_rate = (success_count / items_processed * 100) if items_processed > 0 else 0
        self.logger.info(f"Processing Stats - Operation: {operation}, "
                        f"Total: {items_processed}, Success: {success_count}, "
                        f"Errors: {error_count}, Success Rate: {success_rate:.1f}%")


class LogManager:
    """ログ管理クラス"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.loggers = {}
    
    def get_logger(self, name: str) -> logging.Logger:
        """ロガーを取得（キャッシュ付き）"""
        if name not in self.loggers:
            self.loggers[name] = NewsDeliveryLogger(name, self.config)
        return self.loggers[name].get_logger()
    
    def get_performance_logger(self, name: str) -> PerformanceLogger:
        """パフォーマンスロガーを取得"""
        return PerformanceLogger(name)
    
    def cleanup_old_logs(self):
        """古いログファイルのクリーンアップ"""
        try:
            logs_dir = self.config.get_storage_path('logs')
            retention_days = self.config.get('data_retention', 'logs_days', default=30)
            
            cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
            
            for log_file in logs_dir.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_date:
                    log_file.unlink()
                    print(f"Deleted old log file: {log_file}")
                    
        except Exception as e:
            print(f"Error cleaning up logs: {e}")
    
    def get_log_summary(self) -> dict:
        """ログサマリーを取得"""
        try:
            logs_dir = self.config.get_storage_path('logs')
            summary = {
                'total_files': 0,
                'total_size_mb': 0,
                'latest_file': None,
                'error_count_today': 0
            }
            
            for log_file in logs_dir.glob('*.log'):
                summary['total_files'] += 1
                summary['total_size_mb'] += log_file.stat().st_size / (1024 * 1024)
                
                if summary['latest_file'] is None or log_file.stat().st_mtime > summary['latest_file'][1]:
                    summary['latest_file'] = (str(log_file), log_file.stat().st_mtime)
            
            # Count today's errors
            today_str = datetime.now().strftime('%Y-%m-%d')
            error_log = logs_dir / f"errors_{datetime.now().strftime('%Y%m')}.log"
            if error_log.exists():
                with open(error_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        if today_str in line and 'ERROR' in line:
                            summary['error_count_today'] += 1
            
            summary['total_size_mb'] = round(summary['total_size_mb'], 2)
            return summary
            
        except Exception as e:
            return {'error': str(e)}


# Global log manager instance
_log_manager = None

def setup_logger(name: str, config=None) -> logging.Logger:
    """ロガーをセットアップ（メイン関数）"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager(config)
    return _log_manager.get_logger(name)

def get_performance_logger(name: str) -> PerformanceLogger:
    """パフォーマンスロガーを取得"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager.get_performance_logger(name)

def cleanup_logs():
    """ログクリーンアップ実行"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    _log_manager.cleanup_old_logs()

def get_log_status() -> dict:
    """ログステータス取得"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager.get_log_summary()