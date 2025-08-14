#!/bin/bash

# Simple Auto Start Script
# ニュース自動配信システム起動スクリプト

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TMUX_DIR")"

echo "🚀 Starting News Delivery System..."

# Pythonスクリプトディレクトリへ移動
cd "$PROJECT_ROOT"

# 仮想環境の確認・アクティベート
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "Activating Python virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
elif [ -d "$PROJECT_ROOT/news-env" ]; then
    echo "Activating Python virtual environment..."
    source "$PROJECT_ROOT/news-env/bin/activate"
else
    echo "Python virtual environment not found"
fi

# メインシステムを起動（バックグラウンド）
echo "Starting News Delivery System..."
python main.py status &
MAIN_PID=$!

# 起動待機
echo "Waiting for system to initialize..."
sleep 5

# 状態確認
echo "Checking system status..."
echo "News Delivery System Status:"
python main.py status

echo ""
echo "✅ News Delivery System is running!"
echo "   System Status: Check logs in data/logs/"
echo "   Configuration: config/config.json"
echo "   Manual Commands:"
echo "     python main.py daily    - Run daily collection"
echo "     python main.py urgent   - Check urgent news"
echo "     python main.py check    - System health check"
echo ""
echo "Press Ctrl+C to stop system"

# 終了時処理
cleanup() {
    echo ""
    echo "Stopping News Delivery System..."
    kill $MAIN_PID 2>/dev/null
    echo "System stopped"
}

trap cleanup EXIT

# 待機
wait