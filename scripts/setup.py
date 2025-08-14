#!/usr/bin/env python3
"""
News Delivery System Setup Script
ニュース配信システム セットアップスクリプト
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def print_banner():
    """バナー表示"""
    print("=" * 60)
    print("  News Delivery System - Setup Script")
    print("  ニュース自動配信システム - セットアップ")
    print("=" * 60)
    print()


def check_python_version():
    """Python バージョンチェック"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def create_directories():
    """必要なディレクトリ作成"""
    print("📁 Creating directories...")
    
    base_dir = Path.cwd()
    directories = [
        "data/articles/raw",
        "data/articles/processed", 
        "data/reports/daily",
        "data/reports/emergency",
        "data/reports/weekly",
        "data/database",
        "data/cache/api_cache",
        "data/cache/dedup_cache",
        "data/logs",
        "data/backup",
        "credentials"
    ]
    
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"   Created: {directory}")
    
    print("✅ Directories created")


def install_dependencies():
    """依存関係のインストール"""
    print("📦 Installing Python dependencies...")
    
    try:
        # pip のアップグレード
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        
        # requirements.txt からインストール
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        
        print("✅ Python dependencies installed")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)


def check_wkhtmltopdf():
    """wkhtmltopdf の存在確認"""
    print("🔍 Checking wkhtmltopdf...")
    
    try:
        # wkhtmltopdf が存在するかチェック
        result = subprocess.run(["wkhtmltopdf", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ wkhtmltopdf found")
            return True
    except FileNotFoundError:
        pass
    
    print("⚠️  wkhtmltopdf not found")
    print("   Please install wkhtmltopdf for PDF generation:")
    print("   - Windows: Download from https://wkhtmltopdf.org/downloads.html")
    print("   - Linux: sudo apt-get install wkhtmltopdf")
    print("   - macOS: brew install wkhtmltopdf")
    
    return False


def create_config_files():
    """設定ファイルの作成"""
    print("⚙️  Creating configuration files...")
    
    # .env ファイル作成
    env_file = Path(".env")
    if not env_file.exists():
        env_content = """# News Delivery System Environment Variables
# API Keys - APIキー設定
NEWSAPI_KEY=your_newsapi_key_here
DEEPL_API_KEY=your_deepl_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
GNEWS_API_KEY=your_gnews_api_key_here

# Gmail OAuth - Gmail認証設定
GMAIL_CREDENTIALS_PATH=credentials/credentials.json
GMAIL_TOKEN_PATH=credentials/token.json

# Database - データベース設定
DB_PATH=data/database/news.db

# System Settings - システム設定
DEBUG=False
LOG_LEVEL=INFO
SYSTEM_TIMEZONE=Asia/Tokyo

# Notification Settings - 通知設定
ADMIN_EMAIL=admin@example.com
RECIPIENT_EMAILS=user1@example.com,user2@example.com
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("   Created: .env")
    else:
        print("   .env file already exists")
    
    print("✅ Configuration files ready")


def display_next_steps():
    """次のステップ表示"""
    print()
    print("🎉 Setup completed successfully!")
    print()
    print("📋 Next Steps:")
    print("1. Edit .env file with your API keys:")
    print("   - NewsAPI: https://newsapi.org/")
    print("   - DeepL: https://www.deepl.com/pro-api")
    print("   - Claude (Anthropic): https://www.anthropic.com/")
    print()
    print("2. Set up Gmail OAuth credentials:")
    print("   - Go to Google Cloud Console")
    print("   - Enable Gmail API")
    print("   - Create OAuth 2.0 credentials")
    print("   - Download credentials.json to credentials/ folder")
    print()
    print("3. Configure recipients in .env file")
    print()
    print("4. Test the system:")
    print("   python src/main.py --mode test")
    print()
    print("5. Set up scheduled execution:")
    print("   - Windows: Use Task Scheduler")
    print("   - Linux: Use cron")
    print()
    print("📖 For detailed setup instructions, see:")
    print("   - README.md")
    print("   - CLAUDE.md")


def main():
    """メイン実行関数"""
    print_banner()
    
    try:
        check_python_version()
        create_directories()
        install_dependencies()
        check_wkhtmltopdf()
        create_config_files()
        display_next_steps()
        
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()