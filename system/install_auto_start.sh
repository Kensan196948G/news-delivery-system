#!/bin/bash
#
# News Delivery System Auto-Start Installation Script
# ニュース配信システム自動起動インストールスクリプト
#
# 使用方法: sudo ./install_auto_start.sh
#

echo "🚀 News Delivery System - Auto-Start Installation"
echo "================================================"

# Root権限チェック
if [ "$EUID" -ne 0 ]; then
    echo "❌ このスクリプトはroot権限で実行してください:"
    echo "   sudo ./install_auto_start.sh"
    exit 1
fi

PROJECT_ROOT="/media/kensan/LinuxHDD/news-delivery-system"
SERVICE_FILE="news-delivery-startup.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE"

echo "📁 プロジェクトパス: $PROJECT_ROOT"

# 1. サービスファイルのコピー
echo "📋 1. systemdサービスファイルをインストール中..."
if cp "$PROJECT_ROOT/system/$SERVICE_FILE" "$SERVICE_PATH"; then
    echo "   ✅ サービスファイルをコピーしました"
else
    echo "   ❌ サービスファイルのコピーに失敗しました"
    exit 1
fi

# 2. サービスファイルの権限設定
echo "🔐 2. サービスファイルの権限を設定中..."
chmod 644 "$SERVICE_PATH"
echo "   ✅ 権限を設定しました"

# 3. systemd設定をリロード
echo "🔄 3. systemd設定をリロード中..."
systemctl daemon-reload
echo "   ✅ systemd設定をリロードしました"

# 4. サービスを有効化（自動起動設定）
echo "⚡ 4. 自動起動サービスを有効化中..."
if systemctl enable $SERVICE_FILE; then
    echo "   ✅ 自動起動サービスを有効化しました"
else
    echo "   ❌ 自動起動サービスの有効化に失敗しました"
    exit 1
fi

# 5. サービス状態確認
echo "📊 5. サービス状態を確認中..."
systemctl status news-delivery-startup.service --no-pager -l

echo ""
echo "🎉 インストール完了！"
echo "================================================"
echo "✅ ニュース配信システムの自動起動が設定されました"
echo ""
echo "📝 次回のPC起動・再起動時に自動的に以下が実行されます:"
echo "   • システム初期化テスト"
echo "   • 配信スケジュール確認"
echo "   • 起動通知メール送信"
echo ""
echo "🔧 手動テスト実行:"
echo "   sudo systemctl start news-delivery-startup.service"
echo ""
echo "📋 ログ確認:"
echo "   journalctl -u news-delivery-startup.service -f"
echo "   tail -f $PROJECT_ROOT/logs/startup_\$(date +%Y%m%d).log"
echo ""
echo "🚫 自動起動を無効化する場合:"
echo "   sudo systemctl disable news-delivery-startup.service"
echo "================================================"