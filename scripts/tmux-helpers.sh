#!/bin/bash
# News Delivery System - tmux ヘルパー関数とエイリアス
# 各ウィンドウで使用する便利なコマンドとエイリアス

# 基本設定
export NEWS_BASE_DIR="/mnt/e/news-delivery-system"
export NEWS_LOGS_DIR="$NEWS_BASE_DIR/data/logs"
export NEWS_CONFIG_DIR="$NEWS_BASE_DIR/config"
export NEWS_DATA_DIR="$NEWS_BASE_DIR/data"

# 色付きメッセージ関数
news_info() {
    echo -e "\033[0;32m[NEWS-INFO]\033[0m $1"
}

news_warning() {
    echo -e "\033[0;33m[NEWS-WARNING]\033[0m $1"
}

news_error() {
    echo -e "\033[0;31m[NEWS-ERROR]\033[0m $1"
}

# システム監視関連
alias news-logs='tail -f $NEWS_LOGS_DIR/*.log'
alias news-logs-error='tail -f $NEWS_LOGS_DIR/*error*.log'
alias news-logs-system='tail -f $NEWS_LOGS_DIR/news_system.log'
alias news-logs-scheduler='tail -f $NEWS_LOGS_DIR/scheduler.log'

# プロセス監視
news_status() {
    echo "=== News Delivery System Status ==="
    echo ""
    echo "📊 Running Processes:"
    ps aux | grep -E "(python.*main\.py|python.*scheduler\.py)" | grep -v grep
    echo ""
    echo "📁 Disk Usage:"
    du -sh "$NEWS_DATA_DIR"/* 2>/dev/null | sort -hr
    echo ""
    echo "📝 Recent Log Activity:"
    find "$NEWS_LOGS_DIR" -name "*.log" -mmin -60 -exec ls -lh {} \; 2>/dev/null | head -5
}

# システム実行関連
alias news-daily='cd $NEWS_BASE_DIR && python main.py daily --verbose'
alias news-urgent='cd $NEWS_BASE_DIR && python main.py urgent --verbose'
alias news-check='cd $NEWS_BASE_DIR && python main.py check'
alias news-status-cmd='cd $NEWS_BASE_DIR && python main.py status'

# スケジューラー関連
alias news-scheduler='cd $NEWS_BASE_DIR && python scheduler.py'
alias news-schedule='cd $NEWS_BASE_DIR && python scheduler.py --show-schedule'
alias news-run-once='cd $NEWS_BASE_DIR && python scheduler.py --run-once'

# 設定関連
alias news-config='cd $NEWS_CONFIG_DIR && ls -la'
alias news-env='cd $NEWS_BASE_DIR && ls -la .env*'
alias news-edit-config='cd $NEWS_CONFIG_DIR && nano config.json'
alias news-edit-env='cd $NEWS_BASE_DIR && nano .env'

# ログ分析
news_log_analysis() {
    echo "=== News Delivery System Log Analysis ==="
    echo ""
    echo "🔍 Error Count (last 24 hours):"
    find "$NEWS_LOGS_DIR" -name "*.log" -mtime -1 -exec grep -c "ERROR" {} \; 2>/dev/null | awk '{sum+=$1} END {print "Total Errors: " sum}'
    echo ""
    echo "📈 Recent Activity:"
    find "$NEWS_LOGS_DIR" -name "*.log" -mtime -1 -exec grep -h "INFO.*completed" {} \; 2>/dev/null | tail -5
    echo ""
    echo "⚠️  Recent Warnings:"
    find "$NEWS_LOGS_DIR" -name "*.log" -mtime -1 -exec grep -h "WARNING" {} \; 2>/dev/null | tail -3
}

# データ管理
news_cleanup() {
    echo "=== News Delivery System Cleanup ==="
    cd "$NEWS_BASE_DIR"
    
    echo "🧹 Cleaning old logs..."
    find "$NEWS_LOGS_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null
    
    echo "🧹 Cleaning cache..."
    find "$NEWS_DATA_DIR/cache" -type f -mtime +7 -delete 2>/dev/null
    
    echo "🧹 Cleaning old reports..."
    find "$NEWS_DATA_DIR/reports" -name "*.html" -mtime +7 -delete 2>/dev/null
    find "$NEWS_DATA_DIR/reports" -name "*.pdf" -mtime +7 -delete 2>/dev/null
    
    echo "✅ Cleanup completed"
    news_status
}

# 緊急時のシステム停止
news_emergency_stop() {
    echo "🚨 Emergency Stop - Stopping all News Delivery processes..."
    pkill -f "python.*scheduler\.py" 2>/dev/null
    pkill -f "python.*main\.py" 2>/dev/null
    news_warning "All News Delivery processes have been stopped"
    echo "Use 'news-scheduler' to restart the scheduler"
}

# システム健全性チェック
news_health_check() {
    echo "=== News Delivery System Health Check ==="
    echo ""
    
    # ディスク容量チェック
    echo "💾 Disk Space:"
    df -h "$NEWS_BASE_DIR" | tail -1 | awk '{print "  Available: " $4 " (" $5 " used)"}'
    
    # API設定チェック
    echo ""
    echo "🔑 API Configuration:"
    cd "$NEWS_BASE_DIR"
    python -c "
import os
apis = ['NEWSAPI_KEY', 'DEEPL_API_KEY', 'ANTHROPIC_API_KEY', 'GMAIL_CLIENT_ID']
for api in apis:
    status = '✅' if os.getenv(api) else '❌'
    print(f'  {status} {api}')
" 2>/dev/null || echo "  ❌ Cannot check API configuration"
    
    # ディレクトリ構造チェック
    echo ""
    echo "📁 Directory Structure:"
    for dir in "data/logs" "data/cache" "data/reports" "config"; do
        if [[ -d "$NEWS_BASE_DIR/$dir" ]]; then
            echo "  ✅ $dir"
        else
            echo "  ❌ $dir (missing)"
        fi
    done
    
    echo ""
    python main.py check 2>/dev/null || echo "❌ System check failed"
}

# tmux専用関数
news_tmux_info() {
    echo "=== News Delivery tmux Information ==="
    echo ""
    echo "📺 Current Session: $(tmux display-message -p '#S')"
    echo "📺 Current Window: $(tmux display-message -p '#W')"
    echo "📺 Current Pane: $(tmux display-message -p '#P')"
    echo ""
    echo "⌨️  Key Bindings:"
    echo "  Prefix + 0-4  : Switch to pane"
    echo "  Prefix + q    : Show pane numbers"
    echo "  Prefix + r    : Reload tmux config"
    echo "  Prefix + A    : Apply Pattern A layout"
    echo ""
    echo "🚀 Quick Commands:"
    echo "  news-status   : System status"
    echo "  news-logs     : View all logs"
    echo "  news-daily    : Run daily collection"
    echo "  news-check    : Health check"
}

# ウィンドウ別初期化関数
init_monitor_pane() {
    echo "🖥️  システム監視ペイン初期化中..."
    news_tmux_info
    echo ""
    echo "利用可能なコマンド:"
    echo "  news-logs      # 全ログ監視"
    echo "  news-status    # システム状況"
    echo "  news-health-check # 健全性チェック"
    echo ""
    news_status
}

init_scheduler_pane() {
    echo "⏰ スケジューラーペイン初期化中..."
    echo ""
    echo "利用可能なコマンド:"
    echo "  news-scheduler # スケジューラー開始"
    echo "  news-schedule  # スケジュール表示"
    echo "  news-run-once daily # 単発実行"
    echo ""
    cd "$NEWS_BASE_DIR"
    echo "Ready to start scheduler..."
}

init_manual_pane() {
    echo "🔧 手動実行ペイン初期化中..."
    echo ""
    echo "利用可能なコマンド:"
    echo "  news-daily     # 日次収集実行"
    echo "  news-urgent    # 緊急チェック"
    echo "  news-check     # システムチェック"
    echo "  news-cleanup   # システムクリーンアップ"
    echo ""
    cd "$NEWS_BASE_DIR"
    echo "Ready for manual execution..."
}

init_config_pane() {
    echo "⚙️  設定編集ペイン初期化中..."
    echo ""
    echo "設定ファイル:"
    echo "  news-config    # 設定ディレクトリ表示"
    echo "  news-edit-config # config.json編集"
    echo "  news-edit-env  # .env編集"
    echo ""
    cd "$NEWS_CONFIG_DIR"
    ls -la
}

init_claude_pane() {
    echo "🤖 Claude Code指示用ペイン初期化中..."
    echo ""
    echo "Claude Code セッション開始: claude-code"
    echo ""
    echo "このペインで以下を実行できます:"
    echo "  - システム分析・診断"
    echo "  - コード修正・改善"
    echo "  - 設定ファイル調整"
    echo "  - トラブルシューティング"
    echo ""
    cd "$NEWS_BASE_DIR"
    echo "Ready for Claude Code session..."
}

# ペイン間指示コマンドの簡易実行関数
alias cmd="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh"
alias send-to="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh send-to-pane"
alias send-monitor="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh send-to-monitor"
alias send-manual="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh send-to-manual"
alias send-scheduler="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh send-to-scheduler"
alias send-config="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh send-to-config"

# クイック実行コマンド
alias quick-daily="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh quick-daily"
alias quick-urgent="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh quick-urgent"
alias quick-logs="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh quick-logs"
alias quick-scheduler="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh quick-scheduler-start"
alias quick-health="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh quick-health-check"
alias quick-clear="$NEWS_BASE_DIR/scripts/tmux-pane-commander.sh clear-all"

# ペイン操作関数
switch_to_pane() {
    local pane_num="$1"
    if [[ "$pane_num" =~ ^[0-4]$ ]]; then
        tmux select-pane -t "news-main:0.$pane_num"
        echo "ペイン $pane_num に切り替えました"
    else
        echo "エラー: ペイン番号は 0-4 を指定してください"
    fi
}

alias pane="switch_to_pane"

# ペイン情報表示
show_current_pane() {
    local current=$(tmux display-message -p '#P')
    local title=$(tmux display-message -p '#T')
    echo "現在のペイン: $current ($title)"
}

alias current-pane="show_current_pane"

# ヘルプ表示
news_help() {
    echo "=== News Delivery System tmux Helper Commands ==="
    echo ""
    echo "📊 Status & Monitoring:"
    echo "  news-status        # システム状況表示"
    echo "  news-health-check  # 健全性チェック"
    echo "  news-log-analysis  # ログ分析"
    echo ""
    echo "📝 Log Monitoring:"
    echo "  news-logs          # 全ログ監視"
    echo "  news-logs-error    # エラーログのみ"
    echo "  news-logs-system   # システムログのみ"
    echo ""
    echo "🚀 System Execution:"
    echo "  news-daily         # 日次収集実行"
    echo "  news-urgent        # 緊急チェック"
    echo "  news-check         # システムチェック"
    echo ""
    echo "⏰ Scheduler:"
    echo "  news-scheduler     # スケジューラー開始"
    echo "  news-schedule      # スケジュール表示"
    echo "  news-run-once TYPE # 単発実行"
    echo ""
    echo "⚙️  Configuration:"
    echo "  news-config        # 設定ファイル一覧"
    echo "  news-edit-config   # config.json編集"
    echo "  news-edit-env      # .env編集"
    echo ""
    echo "🧹 Maintenance:"
    echo "  news-cleanup       # システムクリーンアップ"
    echo "  news-emergency-stop # 緊急停止"
    echo ""
    echo "📺 tmux:"
    echo "  news-tmux-info     # tmux情報表示"
    echo "  news-help          # このヘルプ"
    echo ""
    echo "🎯 ペイン間指示コマンド (NEW!):"
    echo "  cmd help           # 指示コマンドヘルプ"
    echo "  send-to <番号> <コマンド>  # 指定ペインに送信"
    echo "  send-monitor <コマンド>    # 監視ペインに送信"
    echo "  send-manual <コマンド>     # 手動ペインに送信"
    echo "  send-scheduler <コマンド>  # スケジューラーペインに送信"
    echo "  send-config <コマンド>     # 設定ペインに送信"
    echo ""
    echo "⚡ クイック実行:"
    echo "  quick-daily        # 日次収集実行"
    echo "  quick-urgent       # 緊急チェック"
    echo "  quick-logs         # ログ監視開始"
    echo "  quick-scheduler    # スケジューラー開始"
    echo "  quick-health       # 全ペイン健全性チェック"
    echo "  quick-clear        # 全ペインクリア"
    echo ""
    echo "🔀 ペイン操作:"
    echo "  pane <番号>        # 指定ペインに切り替え (0-4)"
    echo "  current-pane       # 現在のペイン情報表示"
}

# 初期化メッセージ
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "News Delivery System tmux helpers loaded!"
    echo "Type 'news-help' for available commands."
fi