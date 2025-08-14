#!/bin/bash

# Pane Layout Manager for News Delivery System
# ペイン構成管理ツール

# 設定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TMUX_DIR")"
SESSION_NAME="news-dev-team"

# ログ設定
LOG_DIR="$TMUX_DIR/logs"
LAYOUT_LOG="$LOG_DIR/pane-layout-$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

# 色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# リアルタイムログ関数
log_realtime() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_entry="[$timestamp] $message"
    
    echo -e "${CYAN}[LOG]${NC} $message" | tee -a "$LAYOUT_LOG"
}

log_action() {
    local action="$1"
    local detail="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo -e "${GREEN}[ACTION]${NC} $action${detail:+ - $detail}" | tee -a "$LAYOUT_LOG"
}

log_error() {
    local error="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo -e "${RED}[ERROR]${NC} $error" | tee -a "$LAYOUT_LOG"
}

log_status() {
    local status="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo -e "${YELLOW}[STATUS]${NC} $status" | tee -a "$LAYOUT_LOG"
}

# ヘッダー表示
show_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║               Pane Layout Manager for News System              ║${NC}"
    echo -e "${CYAN}║              ペイン構成管理ツール（チーム開発用）              ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_realtime "Pane Layout Manager Started"
}

# セッション存在確認
check_session_exists() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# セッション削除
kill_existing_session() {
    if check_session_exists; then
        log_action "Killing existing session" "$SESSION_NAME"
        tmux kill-session -t "$SESSION_NAME"
        log_status "Session $SESSION_NAME terminated"
    fi
}

# 基本セッション作成
create_base_session() {
    log_action "Creating base session" "$SESSION_NAME"
    
    # プロジェクトディレクトリでセッション作成
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT"
    
    if check_session_exists; then
        log_status "Base session created successfully"
        return 0
    else
        log_error "Failed to create base session"
        return 1
    fi
}

# 縦分割（左右）
create_vertical_split() {
    log_action "Creating vertical split" "左右分割"
    
    # 縦に分割（左右）
    tmux split-window -h -t "$SESSION_NAME" -c "$PROJECT_ROOT"
    log_status "Vertical split completed - Left and Right panes created"
}

# 左側分割（Manager + CTO）
create_left_management_panes() {
    log_action "Creating left management panes" "Manager + CTO"
    
    # 左側ペインを水平分割（上下）
    tmux split-window -v -t "$SESSION_NAME:0.0" -c "$PROJECT_ROOT"
    
    # ペインの設定
    tmux send-keys -t "$SESSION_NAME:0.0" 'clear && echo "=== MANAGER PANE ===" && echo "管理者用ペイン"' C-m
    tmux send-keys -t "$SESSION_NAME:0.1" 'clear && echo "=== CTO PANE ===" && echo "CTO用ペイン"' C-m
    
    log_status "Left management panes created - Manager (top), CTO (bottom)"
}

# 右側開発者ペイン作成
create_developer_panes() {
    local dev_count=$1
    log_action "Creating developer panes" "$dev_count developers"
    
    case $dev_count in
        2)
            create_2_dev_panes
            ;;
        4)
            create_4_dev_panes
            ;;
        6)
            create_6_dev_panes
            ;;
        *)
            log_error "Unsupported developer count: $dev_count"
            return 1
            ;;
    esac
}

# 2開発者構成（右側を上下分割）
create_2_dev_panes() {
    log_action "Setting up 2-developer layout" "右側を上下2分割"
    
    # 右側ペイン（ペイン2）を上下分割
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    
    # 開発者ペインの設定
    tmux send-keys -t "$SESSION_NAME:0.2" 'clear && echo "=== DEVELOPER 1 PANE ===" && echo "開発者1用ペイン"' C-m
    tmux send-keys -t "$SESSION_NAME:0.3" 'clear && echo "=== DEVELOPER 2 PANE ===" && echo "開発者2用ペイン"' C-m
    
    log_status "2-developer layout completed"
}

# 4開発者構成（右側を4分割）
create_4_dev_panes() {
    log_action "Setting up 4-developer layout" "右側を4分割"
    
    # 右側ペインを上下分割
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    
    # 上側をさらに上下分割
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    
    # 下側をさらに上下分割
    tmux split-window -v -t "$SESSION_NAME:0.4" -c "$PROJECT_ROOT"
    
    # 開発者ペインの設定
    tmux send-keys -t "$SESSION_NAME:0.2" 'clear && echo "=== DEVELOPER 1 PANE ===" && echo "開発者1用ペイン"' C-m
    tmux send-keys -t "$SESSION_NAME:0.3" 'clear && echo "=== DEVELOPER 2 PANE ===" && echo "開発者2用ペイン"' C-m
    tmux send-keys -t "$SESSION_NAME:0.4" 'clear && echo "=== DEVELOPER 3 PANE ===" && echo "開発者3用ペイン"' C-m
    tmux send-keys -t "$SESSION_NAME:0.5" 'clear && echo "=== DEVELOPER 4 PANE ===" && echo "開発者4用ペイン"' C-m
    
    log_status "4-developer layout completed"
}

# 6開発者構成（右側を6分割）
create_6_dev_panes() {
    log_action "Setting up 6-developer layout" "右側を6分割"
    
    # 右側ペインを上下分割
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    
    # 段階的に分割
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    tmux split-window -v -t "$SESSION_NAME:0.3" -c "$PROJECT_ROOT"
    tmux split-window -v -t "$SESSION_NAME:0.4" -c "$PROJECT_ROOT"
    tmux split-window -v -t "$SESSION_NAME:0.5" -c "$PROJECT_ROOT"
    
    # 開発者ペインの設定
    for i in {2..7}; do
        local dev_num=$((i-1))
        tmux send-keys -t "$SESSION_NAME:0.$i" "clear && echo \"=== DEVELOPER $dev_num PANE ===\" && echo \"開発者${dev_num}用ペイン\"" C-m
    done
    
    log_status "6-developer layout completed"
}

# ペインサイズ調整
adjust_pane_sizes() {
    local dev_count=$1
    log_action "Adjusting pane sizes" "Optimizing layout for $dev_count developers"
    
    # 左右の比率を50:50に調整
    tmux resize-pane -t "$SESSION_NAME:0.0" -x 50%
    
    # 左側の上下比率を50:50に調整
    tmux resize-pane -t "$SESSION_NAME:0.0" -y 50%
    
    # 右側の開発者ペインを均等分割
    case $dev_count in
        2)
            tmux resize-pane -t "$SESSION_NAME:0.2" -y 50%
            ;;
        4)
            # 4分割の場合は自動的に均等になる
            ;;
        6)
            # 6分割の場合は自動的に均等になる
            ;;
    esac
    
    log_status "Pane sizes adjusted"
}

# 開発環境初期化
initialize_development_environment() {
    log_action "Initializing development environment" "Setting up tools and environments"
    
    # Manager ペインでシステム監視
    tmux send-keys -t "$SESSION_NAME:0.0" 'cd "$PROJECT_ROOT" && python main.py status' C-m
    
    # CTO ペインでシステム概要
    tmux send-keys -t "$SESSION_NAME:0.1" 'cd "$PROJECT_ROOT" && echo "News Delivery System - CTO View" && ls -la' C-m
    
    log_status "Development environment initialized"
}

# ペインタイトル設定
set_pane_titles() {
    local dev_count=$1
    log_action "Setting pane titles" "Adding descriptive titles"
    
    # tmuxのpane-border-status機能を有効化
    tmux set -g pane-border-status top
    tmux set -g pane-border-format '#[fg=cyan]#{pane_title}'
    
    # 各ペインにタイトル設定
    tmux select-pane -t "$SESSION_NAME:0.0" -T "MANAGER"
    tmux select-pane -t "$SESSION_NAME:0.1" -T "CTO"
    
    # 開発者ペインのタイトル設定
    case $dev_count in
        2)
            tmux select-pane -t "$SESSION_NAME:0.2" -T "DEV-1"
            tmux select-pane -t "$SESSION_NAME:0.3" -T "DEV-2"
            ;;
        4)
            for i in {2..5}; do
                local dev_num=$((i-1))
                tmux select-pane -t "$SESSION_NAME:0.$i" -T "DEV-$dev_num"
            done
            ;;
        6)
            for i in {2..7}; do
                local dev_num=$((i-1))
                tmux select-pane -t "$SESSION_NAME:0.$i" -T "DEV-$dev_num"
            done
            ;;
    esac
    
    log_status "Pane titles configured"
}

# レイアウト情報表示
show_layout_info() {
    local dev_count=$1
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           Layout Information             ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo -e "${GREEN}Session Name:${NC} $SESSION_NAME"
    echo -e "${GREEN}Developers:${NC} $dev_count"
    echo -e "${GREEN}Layout:${NC} Left(Manager/CTO) | Right($dev_count Devs)"
    echo -e "${GREEN}Project Root:${NC} $PROJECT_ROOT"
    echo -e "${GREEN}Log File:${NC} $LAYOUT_LOG"
    echo ""
    echo -e "${YELLOW}Available tmux commands:${NC}"
    echo "  tmux attach -t $SESSION_NAME  # セッションにアタッチ"
    echo "  tmux list-panes -t $SESSION_NAME  # ペイン一覧表示"
    echo "  tmux kill-session -t $SESSION_NAME  # セッション終了"
    echo ""
}

# メインレイアウト作成関数
create_team_layout() {
    local dev_count=$1
    
    log_realtime "Starting team layout creation with $dev_count developers"
    
    # 既存セッション削除
    kill_existing_session
    sleep 1
    
    # 基本セッション作成
    if ! create_base_session; then
        log_error "Failed to create base session"
        return 1
    fi
    
    # 段階的レイアウト構築
    create_vertical_split
    sleep 0.5
    
    create_left_management_panes
    sleep 0.5
    
    create_developer_panes "$dev_count"
    sleep 0.5
    
    adjust_pane_sizes "$dev_count"
    sleep 0.5
    
    set_pane_titles "$dev_count"
    sleep 0.5
    
    initialize_development_environment
    
    log_realtime "Team layout creation completed successfully"
    show_layout_info "$dev_count"
    
    return 0
}

# インタラクティブメニュー
show_menu() {
    while true; do
        show_header
        echo -e "${CYAN}=== Pane Layout Manager Menu ===${NC}"
        echo ""
        echo "1. Create 2-Developer Layout (Manager/CTO + 2 Devs)"
        echo "2. Create 4-Developer Layout (Manager/CTO + 4 Devs)"
        echo "3. Create 6-Developer Layout (Manager/CTO + 6 Devs)"
        echo "4. Attach to existing session"
        echo "5. Show session status"
        echo "6. Kill session"
        echo "7. Show logs"
        echo "q. Quit"
        echo ""
        read -p "Select option: " choice
        
        case $choice in
            1)
                echo ""
                log_action "User selected" "2-Developer Layout"
                if create_team_layout 2; then
                    echo -e "${GREEN}✓ 2-Developer layout created successfully!${NC}"
                    echo "Attaching to session in 3 seconds..."
                    sleep 3
                    tmux attach -t "$SESSION_NAME"
                fi
                ;;
            2)
                echo ""
                log_action "User selected" "4-Developer Layout"
                if create_team_layout 4; then
                    echo -e "${GREEN}✓ 4-Developer layout created successfully!${NC}"
                    echo "Attaching to session in 3 seconds..."
                    sleep 3
                    tmux attach -t "$SESSION_NAME"
                fi
                ;;
            3)
                echo ""
                log_action "User selected" "6-Developer Layout"
                if create_team_layout 6; then
                    echo -e "${GREEN}✓ 6-Developer layout created successfully!${NC}"
                    echo "Attaching to session in 3 seconds..."
                    sleep 3
                    tmux attach -t "$SESSION_NAME"
                fi
                ;;
            4)
                if check_session_exists; then
                    log_action "Attaching to existing session" "$SESSION_NAME"
                    tmux attach -t "$SESSION_NAME"
                else
                    echo -e "${RED}No session exists. Create one first.${NC}"
                    read -p "Press Enter to continue..."
                fi
                ;;
            5)
                echo ""
                if check_session_exists; then
                    echo -e "${GREEN}Session Status:${NC}"
                    tmux list-sessions | grep "$SESSION_NAME"
                    echo ""
                    echo -e "${GREEN}Panes:${NC}"
                    tmux list-panes -t "$SESSION_NAME" -F '#I.#P: #{pane_title} (#{pane_width}x#{pane_height})'
                else
                    echo -e "${YELLOW}No session exists${NC}"
                fi
                echo ""
                read -p "Press Enter to continue..."
                ;;
            6)
                if check_session_exists; then
                    log_action "Killing session" "$SESSION_NAME"
                    kill_existing_session
                    echo -e "${GREEN}Session killed${NC}"
                else
                    echo -e "${YELLOW}No session to kill${NC}"
                fi
                read -p "Press Enter to continue..."
                ;;
            7)
                echo ""
                echo -e "${CYAN}=== Recent Logs ===${NC}"
                if [ -f "$LAYOUT_LOG" ]; then
                    tail -20 "$LAYOUT_LOG"
                else
                    echo "No log file found"
                fi
                echo ""
                read -p "Press Enter to continue..."
                ;;
            q|Q)
                log_realtime "Pane Layout Manager exiting"
                echo -e "${GREEN}Exiting Pane Layout Manager${NC}"
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
    # tmuxの存在確認
    if ! command -v tmux &> /dev/null; then
        echo -e "${RED}Error: tmux is not installed${NC}"
        exit 1
    fi
    
    case "${1:-}" in
        "2"|"dev2")
            create_team_layout 2
            tmux attach -t "$SESSION_NAME"
            ;;
        "4"|"dev4")
            create_team_layout 4
            tmux attach -t "$SESSION_NAME"
            ;;
        "6"|"dev6")
            create_team_layout 6
            tmux attach -t "$SESSION_NAME"
            ;;
        "status")
            if check_session_exists; then
                tmux list-panes -t "$SESSION_NAME" -F '#I.#P: #{pane_title}'
            else
                echo "No session exists"
            fi
            ;;
        "kill")
            kill_existing_session
            ;;
        "help"|"-h"|"--help")
            echo "Pane Layout Manager - Usage:"
            echo "  $0 [menu]    - Open interactive menu"
            echo "  $0 2         - Create 2-developer layout"
            echo "  $0 4         - Create 4-developer layout"
            echo "  $0 6         - Create 6-developer layout"
            echo "  $0 status    - Show session status"
            echo "  $0 kill      - Kill session"
            ;;
        *)
            show_menu
            ;;
    esac
}

# スクリプト実行
main "$@"