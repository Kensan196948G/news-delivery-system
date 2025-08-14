#!/bin/bash
"""
Linux Cron Setup for News Delivery System
ニュース配信システムのCron設定（Linux用）
"""

echo "🐧 Setting up Linux Cron for News Delivery System"
echo "=================================================="

# プロジェクトのパスを取得
# スクリプトの場所から相対パスで設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PATH="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_PATH=$(which python3)

echo "📍 Project Path: $PROJECT_PATH"
echo "🐍 Python Path: $PYTHON_PATH"

# Cronジョブの内容を作成
CRON_CONTENT="# News Delivery System - Automated News Collection
# 毎日 7:00, 12:00, 18:00 に実行

# 朝のニュース配信 (7:00)
0 7 * * * cd $PROJECT_PATH && $PYTHON_PATH src/main.py --mode daily >> logs/cron_morning.log 2>&1

# 昼のニュース配信 (12:00)  
0 12 * * * cd $PROJECT_PATH && $PYTHON_PATH src/main.py --mode daily >> logs/cron_noon.log 2>&1

# 夕方のニュース配信 (18:00)
0 18 * * * cd $PROJECT_PATH && $PYTHON_PATH src/main.py --mode daily >> logs/cron_evening.log 2>&1

# 週次バックアップ (日曜日 23:00)
0 23 * * 0 cd $PROJECT_PATH && $PYTHON_PATH scripts/backup_data.py >> logs/cron_backup.log 2>&1"

echo "📝 Cron configuration created:"
echo "$CRON_CONTENT"

# ログディレクトリを作成
mkdir -p "$PROJECT_PATH/logs"

# 現在のcrontabをバックアップ
echo "💾 Backing up current crontab..."
crontab -l > "$PROJECT_PATH/scripts/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || echo "No existing crontab found"

# 一時ファイルに新しいcrontabを作成
TEMP_CRON_FILE=$(mktemp)

# 既存のcrontabがあれば保持
crontab -l 2>/dev/null > "$TEMP_CRON_FILE" || touch "$TEMP_CRON_FILE"

# News Delivery System用の設定を追加
echo "" >> "$TEMP_CRON_FILE"
echo "$CRON_CONTENT" >> "$TEMP_CRON_FILE"

# 新しいcrontabをインストール
echo "⚙️  Installing new crontab..."
crontab "$TEMP_CRON_FILE"

# 一時ファイルを削除
rm "$TEMP_CRON_FILE"

echo "✅ Cron setup completed!"
echo ""
echo "📋 Scheduled jobs:"
echo "   🌅 Morning news: 07:00 daily"
echo "   🌞 Noon news:    12:00 daily" 
echo "   🌆 Evening news: 18:00 daily"
echo "   🗄️  Backup:       23:00 every Sunday"
echo ""
echo "🔍 To verify cron installation:"
echo "   crontab -l"
echo ""
echo "📊 To check cron logs:"
echo "   tail -f logs/cron_morning.log"
echo "   tail -f logs/cron_noon.log"
echo "   tail -f logs/cron_evening.log"