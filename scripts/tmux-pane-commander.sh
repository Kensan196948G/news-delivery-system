#!/bin/bash
# News Delivery System - tmux ペイン間指示コマンドシステム
# ペイン4（Claude指示用）から他のペインに正確な指示を送るためのコマンド

set -e

# 設定
SESSION_NAME="news-main"
WINDOW_ID="0"
BASE_DIR="/mnt/e/news-delivery-system"

# 色付きメッセージ関数
print_info() {
    echo -e "\033[0;32m[COMMANDER]\033[0m $1"
}

print_warning() {
    echo -e "\033[0;33m[COMMANDER]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[COMMANDER]\033[0m $1"
}

# ペイン存在確認
check_pane() {
    local pane_id="$1"
    if ! tmux list-panes -t "$SESSION_NAME:$WINDOW_ID" | grep -q "^$pane_id:"; then
        print_error "ペイン $pane_id が見つかりません"
        return 1
    fi
    return 0
}

# セッション存在確認
check_session() {
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        print_error "セッション '$SESSION_NAME' が見つかりません"
        print_info "まず ./scripts/news-tmux-setup.sh を実行してください"
        return 1
    fi
    return 0
}

# 単一ペインに指示送信
send_to_pane() {
    local pane_id="$1"
    local command="$2"
    
    if ! check_session || ! check_pane "$pane_id"; then
        return 1
    fi
    
    print_info "ペイン $pane_id に指示送信: $command"
    tmux send-keys -t "$SESSION_NAME:$WINDOW_ID.$pane_id" "$command" C-m
    
    # コマンド履歴に記録
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Pane $pane_id: $command" >> "$BASE_DIR/data/logs/tmux_commands.log"
}

# 複数ペインに同時送信
send_to_multiple() {
    local panes="$1"
    local command="$2"
    
    if ! check_session; then
        return 1
    fi
    
    print_info "複数ペイン ($panes) に同時送信: $command"
    
    for pane in ${panes//,/ }; do
        if check_pane "$pane"; then
            tmux send-keys -t "$SESSION_NAME:$WINDOW_ID.$pane" "$command" C-m
            sleep 0.1  # わずかな遅延で同期を取る
        fi
    done
}

# 特定の役割ペインに送信
send_to_monitor() {
    send_to_pane 0 "$1"
}

send_to_manual() {
    send_to_pane 1 "$1"
}

send_to_scheduler() {
    send_to_pane 2 "$1"
}

send_to_config() {
    send_to_pane 3 "$1"
}

# よく使用するコマンドの簡易実行
quick_daily() {
    print_info "日次収集を手動実行ペインで開始"
    send_to_manual "clear"
    send_to_manual "echo '🚀 日次ニュース収集を開始します...'"
    send_to_manual "cd $BASE_DIR && python main.py daily --verbose"
}

quick_urgent() {
    print_info "緊急チェックを手動実行ペインで開始"
    send_to_manual "clear"
    send_to_manual "echo '⚡ 緊急ニュースチェックを開始します...'"
    send_to_manual "cd $BASE_DIR && python main.py urgent --verbose"
}

quick_logs() {
    print_info "ログ監視をシステム監視ペインで開始"
    send_to_monitor "clear"
    send_to_monitor "echo '📊 システムログ監視を開始します...'"
    send_to_monitor "cd $BASE_DIR && tail -f data/logs/*.log"
}

quick_scheduler_start() {
    print_info "スケジューラーをスケジューラーペインで開始"
    send_to_scheduler "clear"
    send_to_scheduler "echo '⏰ スケジューラーを開始します...'"
    send_to_scheduler "cd $BASE_DIR && python scheduler.py"
}

quick_health_check() {
    print_info "全ペインでシステム健全性チェック実行"
    send_to_multiple "0,1,2,3" "clear"
    send_to_monitor "echo '🏥 システム監視ペイン: ヘルスチェック実行中...'"
    send_to_monitor "cd $BASE_DIR && python main.py check"
    
    send_to_manual "echo '🔧 手動実行ペイン: システム状況確認中...'"
    send_to_manual "cd $BASE_DIR && python main.py status"
    
    send_to_scheduler "echo '⏰ スケジューラーペイン: スケジュール確認中...'"
    send_to_scheduler "cd $BASE_DIR && python scheduler.py --show-schedule"
    
    send_to_config "echo '⚙️ 設定ペイン: 設定ファイル確認中...'"
    send_to_config "cd $BASE_DIR/config && ls -la"
}

# 全ペインクリア
clear_all() {
    print_info "全ペインをクリア"
    send_to_multiple "0,1,2,3" "clear"
}

# ペイン情報表示
show_panes() {
    if ! check_session; then
        return 1
    fi
    
    print_info "現在のペイン構成:"
    echo ""
    echo "  ┌─────────────────┬─────────────────┐"
    echo "  │ 0: 🖥️ システム監視 │ 2: ⏰ スケジューラー │"
    echo "  ├─────────────────┼─────────────────┤"
    echo "  │ 1: 🔧 手動実行    │ 3: ⚙️ 設定編集     │"
    echo "  ├─────────────────┴─────────────────┤"
    echo "  │ 4: 🤖 Claude指示用ペイン          │"
    echo "  └───────────────────────────────────┘"
    echo ""
    
    # アクティブなペインを表示
    current_pane=$(tmux display-message -p '#P')
    print_info "現在のアクティブペイン: $current_pane"
    
    # 各ペインの状態確認
    echo ""
    echo "ペイン状態:"
    for pane in 0 1 2 3 4; do
        if check_pane "$pane" 2>/dev/null; then
            title=$(tmux display-message -t "$SESSION_NAME:$WINDOW_ID.$pane" -p '#T' 2>/dev/null || echo "未設定")
            echo "  ✅ ペイン $pane: $title"
        else
            echo "  ❌ ペイン $pane: 存在しません"
        fi
    done
}

# コマンド履歴表示
show_history() {
    local log_file="$BASE_DIR/data/logs/tmux_commands.log"
    
    if [[ -f "$log_file" ]]; then
        print_info "最近のコマンド履歴 (最新10件):"
        tail -10 "$log_file"
    else
        print_warning "コマンド履歴ファイルが見つかりません"
    fi
}

# ヘルプ表示
show_help() {
    echo "=== News Delivery System - tmux ペイン指示コマンド ==="
    echo ""
    echo "📤 基本的な指示送信:"
    echo "  send-to-pane <ペイン番号> <コマンド>    # 指定ペインにコマンド送信"
    echo "  send-to-multiple <ペイン番号> <コマンド> # 複数ペインに同時送信 (例: 0,1,2)"
    echo ""
    echo "🎯 役割別指示:"
    echo "  send-to-monitor <コマンド>      # システム監視ペイン(0)に送信"
    echo "  send-to-manual <コマンド>       # 手動実行ペイン(1)に送信" 
    echo "  send-to-scheduler <コマンド>    # スケジューラーペイン(2)に送信"
    echo "  send-to-config <コマンド>       # 設定編集ペイン(3)に送信"
    echo ""
    echo "⚡ クイック実行:"
    echo "  quick-daily            # 日次収集実行"
    echo "  quick-urgent           # 緊急チェック実行"
    echo "  quick-logs             # ログ監視開始"
    echo "  quick-scheduler-start  # スケジューラー開始"
    echo "  quick-health-check     # 全ペイン健全性チェック"
    echo ""
    echo "🛠️ ユーティリティ:"
    echo "  clear-all      # 全ペインクリア"
    echo "  show-panes     # ペイン構成表示"
    echo "  show-history   # コマンド履歴表示"
    echo "  show-help      # このヘルプ表示"
    echo ""
    echo "📝 使用例:"
    echo "  $0 send-to-manual 'news-daily'"
    echo "  $0 send-to-multiple '0,1' 'clear'"
    echo "  $0 quick-health-check"
}

# メイン処理
main() {
    # ログディレクトリ作成
    mkdir -p "$BASE_DIR/data/logs"
    
    case "${1:-help}" in
        "send-to-pane")
            if [[ $# -lt 3 ]]; then
                print_error "使用方法: $0 send-to-pane <ペイン番号> <コマンド>"
                exit 1
            fi
            send_to_pane "$2" "$3"
            ;;
        "send-to-multiple")
            if [[ $# -lt 3 ]]; then
                print_error "使用方法: $0 send-to-multiple <ペイン番号> <コマンド>"
                exit 1
            fi
            send_to_multiple "$2" "$3"
            ;;
        "send-to-monitor")
            if [[ $# -lt 2 ]]; then
                print_error "使用方法: $0 send-to-monitor <コマンド>"
                exit 1
            fi
            send_to_monitor "$2"
            ;;
        "send-to-manual")
            if [[ $# -lt 2 ]]; then
                print_error "使用方法: $0 send-to-manual <コマンド>"
                exit 1
            fi
            send_to_manual "$2"
            ;;
        "send-to-scheduler")
            if [[ $# -lt 2 ]]; then
                print_error "使用方法: $0 send-to-scheduler <コマンド>"
                exit 1
            fi
            send_to_scheduler "$2"
            ;;
        "send-to-config")
            if [[ $# -lt 2 ]]; then
                print_error "使用方法: $0 send-to-config <コマンド>"
                exit 1
            fi
            send_to_config "$2"
            ;;
        "quick-daily")
            quick_daily
            ;;
        "quick-urgent")
            quick_urgent
            ;;
        "quick-logs")
            quick_logs
            ;;
        "quick-scheduler-start")
            quick_scheduler_start
            ;;
        "quick-health-check")
            quick_health_check
            ;;
        "clear-all")
            clear_all
            ;;
        "show-panes")
            show_panes
            ;;
        "show-history")
            show_history
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            print_error "不明なコマンド: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"