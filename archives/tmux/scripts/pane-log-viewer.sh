#!/bin/bash

# Pane Log Viewer - Real-time log monitoring for tmux panes
# ペインログビューワー - リアルタイムログ監視

# 設定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$TMUX_DIR/logs"
SESSION_NAME="news-dev-team"

# 色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ログファイルパターン
LAYOUT_LOGS="$LOG_DIR/pane-layout-*.log"
SYSTEM_LOGS="$LOG_DIR/*.log"

# リアルタイムログ表示
show_realtime_logs() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    Real-time Log Viewer                     ║${NC}"
    echo -e "${CYAN}║              リアルタイムログビューワー                      ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Monitoring logs... Press Ctrl+C to exit${NC}"
    echo ""
    
    # 最新のログファイルを取得
    local latest_layout_log=$(ls -t $LAYOUT_LOGS 2>/dev/null | head -1)
    
    if [ -n "$latest_layout_log" ]; then
        echo -e "${GREEN}Following: $latest_layout_log${NC}"
        echo "=================================="
        tail -f "$latest_layout_log"
    else
        echo -e "${RED}No layout log files found${NC}"
        return 1
    fi
}

# ログサマリー表示
show_log_summary() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                      Log Summary                             ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # ログファイル一覧
    echo -e "${YELLOW}Available Log Files:${NC}"
    if ls $LAYOUT_LOGS &>/dev/null; then
        ls -la $LAYOUT_LOGS | while read line; do
            echo "  $line"
        done
    else
        echo "  No layout log files found"
    fi
    echo ""
    
    # 最新ログの概要
    local latest_log=$(ls -t $LAYOUT_LOGS 2>/dev/null | head -1)
    if [ -n "$latest_log" ]; then
        echo -e "${YELLOW}Latest Log Summary ($latest_log):${NC}"
        echo "  Total entries: $(wc -l < "$latest_log")"
        echo "  Actions: $(grep -c '\[ACTION\]' "$latest_log" 2>/dev/null || echo 0)"
        echo "  Errors: $(grep -c '\[ERROR\]' "$latest_log" 2>/dev/null || echo 0)"
        echo "  Status updates: $(grep -c '\[STATUS\]' "$latest_log" 2>/dev/null || echo 0)"
        echo ""
        echo -e "${YELLOW}Recent entries:${NC}"
        tail -10 "$latest_log" | sed 's/^/  /'
    fi
}

# ペイン状態監視
monitor_pane_status() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                   Pane Status Monitor                       ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${RED}Session '$SESSION_NAME' not found${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Monitoring pane status... Press Ctrl+C to exit${NC}"
    echo ""
    
    while true; do
        clear
        echo -e "${CYAN}=== Pane Status Monitor - $(date) ===${NC}"
        echo ""
        
        # セッション情報
        echo -e "${GREEN}Session Information:${NC}"
        tmux list-sessions | grep "$SESSION_NAME" || echo "Session not found"
        echo ""
        
        # ペイン情報
        echo -e "${GREEN}Pane Information:${NC}"
        tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}: #{pane_title} - #{pane_width}x#{pane_height} [#{pane_active}#{?pane_active, ACTIVE,}]' 2>/dev/null || echo "No panes found"
        echo ""
        
        # ウィンドウ情報
        echo -e "${GREEN}Window Information:${NC}"
        tmux list-windows -t "$SESSION_NAME" -F '#{window_index}: #{window_name} (#{window_panes} panes)' 2>/dev/null || echo "No windows found"
        echo ""
        
        sleep 2
    done
}

# ログ検索
search_logs() {
    local search_term="$1"
    
    if [ -z "$search_term" ]; then
        read -p "Enter search term: " search_term
    fi
    
    if [ -z "$search_term" ]; then
        echo -e "${RED}No search term provided${NC}"
        return 1
    fi
    
    echo -e "${CYAN}Searching for: '$search_term'${NC}"
    echo "=================================="
    
    # 全ログファイルを検索
    if ls $LAYOUT_LOGS &>/dev/null; then
        grep -n --color=always "$search_term" $LAYOUT_LOGS 2>/dev/null || echo "No matches found"
    else
        echo "No log files to search"
    fi
}

# ログ統計
show_log_statistics() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                     Log Statistics                          ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if ! ls $LAYOUT_LOGS &>/dev/null; then
        echo -e "${RED}No log files found${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Log File Statistics:${NC}"
    echo ""
    
    for log_file in $LAYOUT_LOGS; do
        if [ -f "$log_file" ]; then
            local filename=$(basename "$log_file")
            echo -e "${GREEN}File: $filename${NC}"
            echo "  Total lines: $(wc -l < "$log_file")"
            echo "  Size: $(du -h "$log_file" | cut -f1)"
            echo "  Created: $(stat -c %y "$log_file" | cut -d. -f1)"
            echo "  Actions: $(grep -c '\[ACTION\]' "$log_file" 2>/dev/null || echo 0)"
            echo "  Errors: $(grep -c '\[ERROR\]' "$log_file" 2>/dev/null || echo 0)"
            echo "  Status: $(grep -c '\[STATUS\]' "$log_file" 2>/dev/null || echo 0)"
            echo "  Log entries: $(grep -c '\[LOG\]' "$log_file" 2>/dev/null || echo 0)"
            echo ""
        fi
    done
    
    # 総計
    echo -e "${YELLOW}Total Statistics:${NC}"
    local total_files=$(ls $LAYOUT_LOGS 2>/dev/null | wc -l)
    local total_lines=$(cat $LAYOUT_LOGS 2>/dev/null | wc -l)
    local total_actions=$(grep -c '\[ACTION\]' $LAYOUT_LOGS 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
    local total_errors=$(grep -c '\[ERROR\]' $LAYOUT_LOGS 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
    
    echo "  Total log files: $total_files"
    echo "  Total log entries: $total_lines"
    echo "  Total actions: $total_actions"
    echo "  Total errors: $total_errors"
}

# メニュー表示
show_menu() {
    while true; do
        clear
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║                    Pane Log Viewer Menu                     ║${NC}"
        echo -e "${CYAN}║                ペインログビューワーメニュー                  ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "1. Show real-time logs (リアルタイムログ表示)"
        echo "2. Show log summary (ログサマリー表示)"
        echo "3. Monitor pane status (ペイン状態監視)"
        echo "4. Search logs (ログ検索)"
        echo "5. Show log statistics (ログ統計表示)"
        echo "6. Clean old logs (古いログ削除)"
        echo "q. Quit (終了)"
        echo ""
        read -p "Select option: " choice
        
        case $choice in
            1)
                show_realtime_logs
                ;;
            2)
                show_log_summary
                read -p "Press Enter to continue..."
                ;;
            3)
                monitor_pane_status
                ;;
            4)
                read -p "Enter search term: " search_term
                search_logs "$search_term"
                read -p "Press Enter to continue..."
                ;;
            5)
                show_log_statistics
                read -p "Press Enter to continue..."
                ;;
            6)
                echo ""
                echo -e "${YELLOW}Cleaning logs older than 7 days...${NC}"
                find "$LOG_DIR" -name "pane-layout-*.log" -mtime +7 -delete 2>/dev/null
                echo -e "${GREEN}Old logs cleaned${NC}"
                read -p "Press Enter to continue..."
                ;;
            q|Q)
                echo -e "${GREEN}Exiting Log Viewer${NC}"
                break
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# メイン処理
main() {
    # ログディレクトリ作成
    mkdir -p "$LOG_DIR"
    
    case "${1:-}" in
        "realtime"|"rt")
            show_realtime_logs
            ;;
        "summary"|"s")
            show_log_summary
            ;;
        "monitor"|"m")
            monitor_pane_status
            ;;
        "search")
            search_logs "$2"
            ;;
        "stats")
            show_log_statistics
            ;;
        "help"|"-h"|"--help")
            echo "Pane Log Viewer - Usage:"
            echo "  $0 [menu]     - Open interactive menu"
            echo "  $0 realtime   - Show real-time logs"
            echo "  $0 summary    - Show log summary"
            echo "  $0 monitor    - Monitor pane status"
            echo "  $0 search     - Search logs"
            echo "  $0 stats      - Show statistics"
            ;;
        *)
            show_menu
            ;;
    esac
}

# スクリプト実行
main "$@"