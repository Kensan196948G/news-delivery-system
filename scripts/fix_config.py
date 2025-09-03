#!/usr/bin/env python3
"""
Auto-fix configuration issues
設定ファイルの自動修正
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

class ConfigFixer:
    """設定ファイルの自動修正クラス"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_path = project_root / "config" / "config.json"
        self.env_path = project_root / ".env"
        self.env_example_path = project_root / ".env.example"
        self.fixed_items = []
        self.errors = []
    
    def fix_all(self):
        """全ての設定問題を修正"""
        print("Fixing configuration issues...")
        
        # 1. config.jsonの修正
        self._fix_config_json()
        
        # 2. .envファイルの修正
        self._fix_env_file()
        
        # 3. .env.exampleの生成
        self._create_env_example()
        
        # 4. 設定の検証
        self._validate_config()
    
    def _fix_config_json(self):
        """config.jsonを修正"""
        # デフォルト設定（CLAUDE.md仕様準拠）
        default_config = {
            "system": {
                "version": "1.0.0",
                "timezone": "Asia/Tokyo",
                "language": "ja",
                "log_level": "INFO",
                "debug": False
            },
            "paths": {
                "data_root": "data",
                "templates": "src/templates",
                "logs": "data/logs"
            },
            "collection": {
                "categories": {
                    "domestic_social": {
                        "enabled": True,
                        "count": 10,
                        "priority": 1
                    },
                    "international_social": {
                        "enabled": True,
                        "count": 15,
                        "priority": 2,
                        "keywords": ["human rights", "social justice", "migration"]
                    },
                    "domestic_economy": {
                        "enabled": True,
                        "count": 8,
                        "priority": 3
                    },
                    "international_economy": {
                        "enabled": True,
                        "count": 15,
                        "priority": 4
                    },
                    "tech": {
                        "enabled": True,
                        "count": 20,
                        "priority": 5,
                        "keywords": ["AI", "machine learning", "cloud", "security"]
                    },
                    "security": {
                        "enabled": True,
                        "count": 20,
                        "priority": 6,
                        "alert_threshold": 9.0
                    }
                }
            },
            "news_sources": {
                "newsapi": {
                    "enabled": True,
                    "api_key": "",
                    "base_url": "https://newsapi.org/v2",
                    "rate_limit": 500,
                    "daily_limit": 1000
                },
                "gnews": {
                    "enabled": True,
                    "api_key": "",
                    "base_url": "https://gnews.io/api/v4",
                    "rate_limit": 100,
                    "daily_limit": 100
                },
                "nvd": {
                    "enabled": True,
                    "api_key": "",
                    "base_url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
                    "rate_limit": 50
                }
            },
            "translation": {
                "deepl": {
                    "enabled": True,
                    "api_key": "",
                    "api_url": "https://api-free.deepl.com/v2",
                    "target_language": "JA",
                    "monthly_limit": 500000,
                    "batch_size": 50
                }
            },
            "ai_analysis": {
                "claude": {
                    "enabled": True,
                    "api_key": "",
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "daily_limit": 1000,
                    "concurrent_requests": 5
                }
            },
            "email": {
                "smtp": {
                    "enabled": True,
                    "host": "smtp.gmail.com",
                    "port": 587,
                    "use_tls": True,
                    "client_id": "",
                    "client_secret": "",
                    "refresh_token": ""
                },
                "delivery": {
                    "sender": "",
                    "recipients": [],
                    "subject_prefix": "[ニュース配信]",
                    "send_html": True,
                    "attach_pdf": True
                }
            },
            "delivery": {
                "schedule": ["07:00", "12:00", "18:00"],
                "urgent_notification": {
                    "enabled": True,
                    "importance_threshold": 10,
                    "cvss_threshold": 9.0
                }
            },
            "storage": {
                "external_hdd_path": "",
                "database_path": "data/database/news_system.db",
                "cache_dir": "data/cache",
                "reports_dir": "data/reports",
                "logs_dir": "data/logs",
                "backup_dir": "data/backup"
            },
            "api_limits": {
                "newsapi": {
                    "daily_limit": 1000,
                    "rate_limit": 500
                },
                "deepl": {
                    "monthly_limit": 500000,
                    "batch_size": 50
                },
                "claude": {
                    "daily_limit": 1000,
                    "concurrent": 5
                }
            },
            "cache": {
                "api_cache_ttl": 3600,
                "article_cache_ttl": 86400,
                "analysis_cache_ttl": 604800
            },
            "monitoring": {
                "enabled": True,
                "check_interval": 300,
                "health_check_url": "",
                "alert_email": "",
                "metrics": {
                    "cpu_threshold": 80,
                    "memory_threshold": 85,
                    "disk_threshold": 90,
                    "error_rate_threshold": 0.1
                }
            },
            "scheduling": {
                "daily_reports": {
                    "enabled": True,
                    "times": ["07:00", "12:00", "18:00"]
                },
                "emergency_check": {
                    "enabled": True,
                    "interval_minutes": 30
                },
                "cleanup": {
                    "enabled": True,
                    "time": "03:00",
                    "retention_days": {
                        "logs": 7,
                        "reports": 30,
                        "articles": 90,
                        "cache": 1
                    }
                }
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "max_file_size": "10MB",
                "backup_count": 5,
                "console_output": True,
                "file_output": True
            }
        }
        
        # 既存の設定を読み込み
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            except json.JSONDecodeError:
                print("  ⚠️  Invalid JSON in config.json, using default")
                existing_config = {}
        else:
            existing_config = {}
        
        # デフォルト設定とマージ
        merged_config = self._deep_merge(default_config, existing_config)
        
        # 設定ファイルを作成/更新
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(merged_config, f, indent=2, ensure_ascii=False)
        
        self.fixed_items.append("config.json updated with complete configuration")
        print("  ✅ config.json fixed")
    
    def _deep_merge(self, default: Dict, override: Dict) -> Dict:
        """辞書を深くマージ"""
        result = default.copy()
        
        for key, value in override.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def _fix_env_file(self):
        """.envファイルを修正"""
        env_template = """# News Delivery System Environment Variables
# このファイルは自動生成されました

# API Keys
NEWSAPI_KEY=your_newsapi_key_here
DEEPL_API_KEY=your_deepl_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
GNEWS_API_KEY=your_gnews_api_key_here
NVD_API_KEY=your_nvd_api_key_here

# Gmail OAuth
GMAIL_CLIENT_ID=your_gmail_client_id_here
GMAIL_CLIENT_SECRET=your_gmail_client_secret_here
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token_here
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/gmail_token.json

# Email Settings
SENDER_EMAIL=your_email@gmail.com
RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com

# Storage Settings
EXTERNAL_STORAGE_PATH=
NEWS_PROJECT_ROOT={project_root}
DATA_ROOT=data

# Database
DB_PATH=data/database/news_system.db

# System Settings
DEBUG=False
LOG_LEVEL=INFO
PYTHONPATH={project_root}/src

# Monitoring
ENABLE_MONITORING=True
HEALTH_CHECK_INTERVAL=300
ALERT_EMAIL=admin@example.com

# Scheduler
ENABLE_SCHEDULER=True
TIMEZONE=Asia/Tokyo

# Security
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1

# Performance
MAX_WORKERS=4
REQUEST_TIMEOUT=30
CACHE_TTL=3600

# Feature Flags
ENABLE_TRANSLATION=True
ENABLE_AI_ANALYSIS=True
ENABLE_PDF_GENERATION=True
ENABLE_EMERGENCY_ALERTS=True

# Development
DEV_MODE=False
MOCK_API_CALLS=False
TEST_EMAIL_MODE=False
""".format(project_root=str(self.project_root))
        
        # 既存の.envファイルがある場合は値を保持
        existing_env = {}
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_env[key.strip()] = value.strip()
        
        # テンプレートに既存の値を適用
        lines = []
        for line in env_template.split('\n'):
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in existing_env and existing_env[key] not in ['', 'your_', 'None']:
                    lines.append(f"{key}={existing_env[key]}")
                else:
                    lines.append(line)
            else:
                lines.append(line)
        
        # .envファイルを作成/更新
        with open(self.env_path, 'w') as f:
            f.write('\n'.join(lines))
        
        self.fixed_items.append(".env file created/updated")
        print("  ✅ .env file fixed")
    
    def _create_env_example(self):
        """.env.exampleを生成"""
        example_content = """# News Delivery System Environment Variables Example
# Copy this file to .env and fill in your actual values

# API Keys (Required)
NEWSAPI_KEY=your_newsapi_key_here
DEEPL_API_KEY=your_deepl_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here

# Optional API Keys
GNEWS_API_KEY=your_gnews_api_key_here
NVD_API_KEY=your_nvd_api_key_here

# Gmail Configuration (Required for email delivery)
GMAIL_CLIENT_ID=your_gmail_client_id_here
GMAIL_CLIENT_SECRET=your_gmail_client_secret_here
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token_here
SENDER_EMAIL=your_email@gmail.com
RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com

# Storage (Optional - defaults will be used if not set)
EXTERNAL_STORAGE_PATH=/path/to/external/storage
DB_PATH=data/database/news_system.db

# System Settings (Optional)
DEBUG=False
LOG_LEVEL=INFO

# Monitoring (Optional)
ENABLE_MONITORING=True
ALERT_EMAIL=admin@example.com

# Security (Generate a strong secret key)
SECRET_KEY=generate_a_strong_secret_key_here
"""
        
        with open(self.env_example_path, 'w') as f:
            f.write(example_content)
        
        self.fixed_items.append(".env.example created")
        print("  ✅ .env.example created")
    
    def _validate_config(self):
        """設定を検証"""
        print("\nValidating configuration...")
        
        issues = []
        
        # config.jsonの検証
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 必須フィールドの確認
                required_fields = [
                    ['system', 'version'],
                    ['delivery', 'schedule'],
                    ['news_sources', 'newsapi', 'enabled'],
                    ['translation', 'deepl', 'enabled'],
                    ['ai_analysis', 'claude', 'enabled'],
                ]
                
                for field_path in required_fields:
                    current = config
                    for field in field_path:
                        if field not in current:
                            issues.append(f"Missing required field: {'.'.join(field_path)}")
                            break
                        current = current[field]
                
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON in config.json: {e}")
        else:
            issues.append("config.json not found")
        
        # .envファイルの検証
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                env_content = f.read()
            
            # 必須環境変数の確認
            required_env_vars = [
                'NEWSAPI_KEY',
                'DEEPL_API_KEY',
                'ANTHROPIC_API_KEY',
            ]
            
            for var in required_env_vars:
                if var not in env_content or f"{var}=your_" in env_content:
                    issues.append(f"Environment variable {var} not configured")
        else:
            issues.append(".env file not found")
        
        # 結果を報告
        if issues:
            print("  ⚠️  Configuration issues found:")
            for issue in issues:
                print(f"    - {issue}")
                self.errors.append(issue)
        else:
            print("  ✅ Configuration is valid")
    
    def report(self):
        """修正結果をレポート"""
        print(f"\nFixed {len(self.fixed_items)} configuration items")
        
        if self.fixed_items:
            print("\nFixed items:")
            for item in self.fixed_items:
                print(f"  - {item}")
        
        if self.errors:
            print(f"\n⚠️  {len(self.errors)} issues remain:")
            for error in self.errors:
                print(f"  - {error}")
            print("\nPlease update your .env file with actual API keys and settings")


def main():
    """メイン処理"""
    project_root = Path(__file__).parent.parent
    fixer = ConfigFixer(project_root)
    
    print("Fixing configuration...")
    fixer.fix_all()
    fixer.report()
    
    return 0 if not fixer.errors else 1


if __name__ == "__main__":
    sys.exit(main())