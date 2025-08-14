"""
Configuration Management Module
設定管理モジュール
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self, config_path: Optional[str] = None, env_path: Optional[str] = None):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = config_path or self.project_root / "config" / "config.json"
        self.env_path = env_path or self.project_root / ".env"
        
        # Load environment variables
        load_dotenv(self.env_path)
        
        # Load JSON configuration
        self.config = self._load_config()
        
        # Override with environment variables
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """JSON設定ファイルを読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def _apply_env_overrides(self):
        """環境変数による設定値のオーバーライド"""
        # API Keys
        api_keys = {
            'NEWSAPI_KEY': ['news_sources', 'newsapi', 'api_key'],
            'GNEWS_API_KEY': ['news_sources', 'gnews', 'api_key'],
            'NVD_API_KEY': ['news_sources', 'nvd', 'api_key'],
            'DEEPL_API_KEY': ['translation', 'deepl', 'api_key'],
            'ANTHROPIC_API_KEY': ['ai_analysis', 'claude', 'api_key'],
        }
        
        for env_key, config_path in api_keys.items():
            value = os.getenv(env_key)
            if value:
                self._set_nested_config(config_path, value)
        
        # Email configuration
        email_configs = {
            'GMAIL_CLIENT_ID': ['email', 'smtp', 'client_id'],
            'GMAIL_CLIENT_SECRET': ['email', 'smtp', 'client_secret'],
            'GMAIL_REFRESH_TOKEN': ['email', 'smtp', 'refresh_token'],
            'SENDER_EMAIL': ['email', 'delivery', 'sender'],
        }
        
        for env_key, config_path in email_configs.items():
            value = os.getenv(env_key)
            if value:
                self._set_nested_config(config_path, value)
        
        # Recipients (comma-separated)
        recipients = os.getenv('RECIPIENT_EMAILS')
        if recipients:
            recipient_list = [email.strip() for email in recipients.split(',')]
            self._set_nested_config(['email', 'delivery', 'recipients'], recipient_list)
        
        # Storage paths
        external_hdd = os.getenv('EXTERNAL_HDD_PATH')
        if external_hdd:
            self._set_nested_config(['storage', 'external_hdd_path'], external_hdd)
        
        # System settings
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        if debug:
            self._set_nested_config(['system', 'log_level'], 'DEBUG')
        
        log_level = os.getenv('LOG_LEVEL')
        if log_level:
            self._set_nested_config(['system', 'log_level'], log_level.upper())
    
    def _set_nested_config(self, path: list, value: Any):
        """ネストした設定値を設定"""
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, *path, default=None) -> Any:
        """設定値を取得"""
        current = self.config
        try:
            for key in path:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_api_key(self, service: str) -> str:
        """APIキーを取得"""
        key_mapping = {
            'newsapi': self.get('news_sources', 'newsapi', 'api_key'),
            'gnews': self.get('news_sources', 'gnews', 'api_key'),
            'nvd': self.get('news_sources', 'nvd', 'api_key'),
            'deepl': self.get('translation', 'deepl', 'api_key'),
            'claude': self.get('ai_analysis', 'claude', 'api_key'),
        }
        
        api_key = key_mapping.get(service)
        if not api_key:
            raise ValueError(f"API key not found for service: {service}")
        
        return api_key
    
    def get_storage_path(self, path_type: str) -> Path:
        """ストレージパスを取得"""
        base_path = Path(self.get('storage', 'external_hdd_path', default=str(self.project_root / 'data')))
        
        path_mapping = {
            'database': self.get('storage', 'database_path', default='news_system.db'),
            'cache': self.get('storage', 'cache_dir', default='cache'),
            'reports': self.get('storage', 'reports_dir', default='reports'),
            'logs': self.get('storage', 'logs_dir', default='logs'),
            'articles': 'articles',
            'backup': 'backup'
        }
        
        relative_path = path_mapping.get(path_type, path_type)
        full_path = base_path / relative_path
        
        # Create directory if it doesn't exist
        full_path.mkdir(parents=True, exist_ok=True)
        
        return full_path
    
    def is_service_enabled(self, service: str) -> bool:
        """サービスが有効かどうかチェック"""
        service_mapping = {
            'newsapi': self.get('news_sources', 'newsapi', 'enabled', default=True),
            'gnews': self.get('news_sources', 'gnews', 'enabled', default=True),
            'nvd': self.get('news_sources', 'nvd', 'enabled', default=True),
            'deepl': self.get('translation', 'deepl', 'enabled', default=True),
            'claude': self.get('ai_analysis', 'claude', 'enabled', default=True),
            'email': self.get('email', 'smtp', 'enabled', default=True),
        }
        
        return service_mapping.get(service, False)
    
    def get_email_config(self) -> Dict[str, Any]:
        """メール設定を取得"""
        return {
            'smtp': self.get('email', 'smtp', default={}),
            'delivery': self.get('email', 'delivery', default={}),
        }
    
    def get_schedule_config(self) -> Dict[str, Any]:
        """スケジュール設定を取得"""
        return {
            'daily_reports': self.get('scheduling', 'daily_reports', default={}),
            'emergency_check': self.get('scheduling', 'emergency_check', default={}),
        }
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """環境変数を取得"""
        return os.getenv(key, default)
    
    def validate_config(self) -> list:
        """設定の妥当性をチェック"""
        errors = []
        
        # Required API keys check
        required_services = ['newsapi', 'deepl', 'claude']
        for service in required_services:
            if self.is_service_enabled(service):
                try:
                    self.get_api_key(service)
                except ValueError:
                    errors.append(f"Missing API key for {service}")
        
        # Email configuration check
        if self.is_service_enabled('email'):
            email_config = self.get_email_config()
            required_email_fields = ['client_id', 'client_secret', 'refresh_token']
            for field in required_email_fields:
                if not email_config['smtp'].get(field):
                    errors.append(f"Missing email configuration: {field}")
            
            if not email_config['delivery'].get('recipients'):
                errors.append("No email recipients configured")
        
        # Storage path check
        try:
            storage_path = self.get_storage_path('database')
            if not storage_path.parent.exists():
                errors.append(f"Storage path does not exist: {storage_path.parent}")
        except Exception as e:
            errors.append(f"Storage path configuration error: {e}")
        
        return errors


# Global configuration instance
_config_instance = None

def load_config(config_path: Optional[str] = None, env_path: Optional[str] = None) -> ConfigManager:
    """設定を読み込み（シングルトンパターン）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager(config_path, env_path)
    return _config_instance

def get_config() -> ConfigManager:
    """現在の設定インスタンスを取得"""
    if _config_instance is None:
        return load_config()
    return _config_instance