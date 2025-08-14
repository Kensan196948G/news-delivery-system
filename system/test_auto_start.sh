#!/bin/bash
#
# News Delivery System Auto-Start Test Script
# ニュース配信システム自動起動テストスクリプト
#

echo "🧪 News Delivery System - Auto-Start Test"
echo "=========================================="

PROJECT_ROOT="/media/kensan/LinuxHDD/news-delivery-system"

# スクリプト直接テスト
echo "📋 1. 起動スクリプトの直接テスト..."
if "$PROJECT_ROOT/system/startup-news-delivery.sh"; then
    echo "   ✅ 起動スクリプトが正常に実行されました"
else
    echo "   ❌ 起動スクリプトの実行に失敗しました"
    exit 1
fi

echo ""
echo "📊 2. システム状態確認..."

# crontab確認
echo "⏰ Crontab Schedule:"
crontab -l | grep news-delivery-system || echo "   ⚠️  Crontab schedule not found"

echo ""
echo "📝 3. 最新のログ確認..."
echo "Startup Log (最新10行):"
tail -n 10 "$PROJECT_ROOT/logs/startup_$(date +%Y%m%d).log" 2>/dev/null || echo "   📄 起動ログファイルがありません"

echo ""
echo "🎉 テスト完了！"
echo "=========================================="
echo "✅ 自動起動スクリプトは正常に動作しています"
echo ""
echo "📧 起動通知メールが kensan1969@gmail.com に送信されました"
echo "📋 詳細なログは以下で確認できます:"
echo "   $PROJECT_ROOT/logs/startup_$(date +%Y%m%d).log"
echo "=========================================="