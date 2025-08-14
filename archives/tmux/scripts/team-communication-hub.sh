#!/bin/bash

# Team Communication Hub - Real-time Instruction & Reporting System
# チームコミュニケーションハブ - リアルタイム指示・報告システム

# 設定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TMUX_DIR")"
SESSION_NAME="news-dev-team"

# ログ設定
LOG_DIR="$TMUX_DIR/logs"
COMM_LOG="$LOG_DIR/team-communication-$(date +%Y%m%d).log"
INSTRUCTION_LOG="$LOG_DIR/instructions-$(date +%Y%m%d).log"
REPORT_LOG="$LOG_DIR/reports-$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

# 色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# アイコン定義
ICON_INSTRUCTION="📨"
ICON_REPORT="📊"
ICON_URGENT="🚨"
ICON_SUCCESS="✅"
ICON_WARNING="⚠️"
ICON_ERROR="❌"

# ロール・ペイン対応表
declare -A ROLE_TO_PANE=(
    ["manager"]="0.0"
    ["MANAGER"]="0.0"
    ["cto"]="0.1"
    ["CTO"]="0.1"
    ["dev0"]="0.2"
    ["DEV0"]="0.2"
    ["dev1"]="0.3"
    ["DEV1"]="0.3"
    ["dev2"]="0.4"
    ["DEV2"]="0.4"
    ["dev3"]="0.5"
    ["DEV3"]="0.5"
    ["dev4"]="0.6"
    ["DEV4"]="0.6"
    ["dev5"]="0.7"
    ["DEV5"]="0.7"
)

declare -A ROLE_NAMES=(
    ["cto"]="CTO"
    ["manager"]="Manager"
    ["dev0"]="Dev0"
    ["dev1"]="Dev1"
    ["dev2"]="Dev2"
    ["dev3"]="Dev3"
    ["dev4"]="Dev4"
    ["dev5"]="Dev5"
)

# ログ関数
log_communication() {
    local type="$1"
    local from="$2"
    local to="$3"
    local message="$4"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] $type: $from → $to: $message" >> "$COMM_LOG"
}

log_instruction() {
    local from="$1"
    local to="$2"
    local instruction="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] INSTRUCTION: $from → $to: $instruction" >> "$INSTRUCTION_LOG"
    log_communication "INSTRUCTION" "$from" "$to" "$instruction"
}

log_report() {
    local from="$1"
    local to="$2"
    local report="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] REPORT: $from → $to: $report" >> "$REPORT_LOG"
    log_communication "REPORT" "$from" "$to" "$report"
}

# 指示送信システム
send_instruction() {
    local from_role="$1"
    local to_role="$2"
    local instruction="$3"
    local priority="${4:-normal}"
    
    # ペイン特定
    local target_pane="${ROLE_TO_PANE[$to_role]}"
    if [ -z "$target_pane" ]; then
        echo -e "${RED}Error: Unknown target role: $to_role${NC}"
        return 1
    fi
    
    # セッション存在確認
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${RED}Error: Team session not found${NC}"
        return 1
    fi
    
    # 優先度アイコン
    local priority_icon="$ICON_INSTRUCTION"
    case "$priority" in
        "urgent") priority_icon="$ICON_URGENT" ;;
        "high") priority_icon="$ICON_WARNING" ;;
    esac
    
    # 指示メッセージ作成
    local timestamp=$(date '+%H:%M:%S')
    local formatted_message="$priority_icon [$timestamp] 指示 from ${ROLE_NAMES[$from_role]}: $instruction"
    
    # ペインに送信
    tmux send-keys -t "$SESSION_NAME:$target_pane" "echo '$formatted_message'" C-m
    
    # ログ記録
    log_instruction "${ROLE_NAMES[$from_role]}" "${ROLE_NAMES[$to_role]}" "$instruction"
    
    echo -e "${GREEN}Instruction sent: ${ROLE_NAMES[$from_role]} → ${ROLE_NAMES[$to_role]}${NC}"
    echo -e "${CYAN}Message: $instruction${NC}"
    
    # 管理者ペインにも通知（ManagerとCTO）
    if [ "$to_role" != "cto" ] && [ "$to_role" != "manager" ]; then
        tmux send-keys -t "$SESSION_NAME:0.0" "echo '📋 指示送信: ${ROLE_NAMES[$from_role]} → ${ROLE_NAMES[$to_role]}'" C-m
        tmux send-keys -t "$SESSION_NAME:0.1" "echo '📋 指示送信: ${ROLE_NAMES[$from_role]} → ${ROLE_NAMES[$to_role]}'" C-m
    fi
    
    return 0
}

# 報告受信システム
receive_report() {
    local from_role="$1"
    local to_role="$2"
    local report="$3"
    local status="${4:-info}"
    
    # ペイン特定
    local target_pane="${ROLE_TO_PANE[$to_role]}"
    if [ -z "$target_pane" ]; then
        echo -e "${RED}Error: Unknown target role: $to_role${NC}"
        return 1
    fi
    
    # セッション存在確認
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${RED}Error: Team session not found${NC}"
        return 1
    fi
    
    # ステータスアイコン
    local status_icon="$ICON_REPORT"
    case "$status" in
        "success") status_icon="$ICON_SUCCESS" ;;
        "warning") status_icon="$ICON_WARNING" ;;
        "error") status_icon="$ICON_ERROR" ;;
    esac
    
    # 報告メッセージ作成
    local timestamp=$(date '+%H:%M:%S')
    local formatted_message="$status_icon [$timestamp] 報告 from ${ROLE_NAMES[$from_role]}: $report"
    
    # ペインに送信
    tmux send-keys -t "$SESSION_NAME:$target_pane" "echo '$formatted_message'" C-m
    
    # ログ記録
    log_report "${ROLE_NAMES[$from_role]}" "${ROLE_NAMES[$to_role]}" "$report"
    
    echo -e "${GREEN}Report received: ${ROLE_NAMES[$from_role]} → ${ROLE_NAMES[$to_role]}${NC}"
    echo -e "${CYAN}Report: $report${NC}"
    
    # 管理者ペインにも通知
    if [ "$from_role" != "cto" ] && [ "$from_role" != "manager" ]; then
        tmux send-keys -t "$SESSION_NAME:0.0" "echo '📊 報告受信: ${ROLE_NAMES[$from_role]} → ${ROLE_NAMES[$to_role]}'" C-m
        tmux send-keys -t "$SESSION_NAME:0.1" "echo '📊 報告受信: ${ROLE_NAMES[$from_role]} → ${ROLE_NAMES[$to_role]}'" C-m
    fi
    
    return 0
}

# 一斉指示システム
broadcast_instruction() {
    local from_role="$1"
    local instruction="$2"
    local target_group="${3:-all}"
    
    echo -e "${YELLOW}Broadcasting instruction from ${ROLE_NAMES[$from_role]}...${NC}"
    
    local targets=()
    case "$target_group" in
        "all")
            targets=("manager" "cto" "dev0" "dev1" "dev2" "dev3" "dev4" "dev5")
            ;;
        "devs")
            targets=("dev0" "dev1" "dev2" "dev3" "dev4" "dev5")
            ;;
        "management")
            targets=("cto" "manager")
            ;;
        *)
            echo -e "${RED}Unknown target group: $target_group${NC}"
            return 1
            ;;
    esac
    
    for target in "${targets[@]}"; do
        if [ "$target" != "$from_role" ] && [ -n "${ROLE_TO_PANE[$target]}" ]; then
            if tmux list-panes -t "$SESSION_NAME:${ROLE_TO_PANE[$target]}" 2>/dev/null; then
                send_instruction "$from_role" "$target" "$instruction" "urgent"
                sleep 0.5
            fi
        fi
    done
    
    echo -e "${GREEN}Broadcast completed to $target_group group${NC}"
}

# チーム状態監視
monitor_team_status() {
    echo -e "${CYAN}=== Team Status Monitor ===${NC}"
    echo ""
    
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${RED}No active team session${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Active Panes:${NC}"
    tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}: #{pane_title} (#{pane_width}x#{pane_height})' | while read line; do
        echo "  $line"
    done
    
    echo ""
    echo -e "${YELLOW}Recent Communication (last 10):${NC}"
    if [ -f "$COMM_LOG" ]; then
        tail -10 "$COMM_LOG" | while read line; do
            echo "  $line"
        done
    else
        echo "  No communication logs"
    fi
}

# 通信履歴表示
show_communication_history() {
    local filter="$1"
    local count="${2:-20}"
    
    echo -e "${CYAN}=== Communication History ===${NC}"
    echo ""
    
    case "$filter" in
        "instructions")
            if [ -f "$INSTRUCTION_LOG" ]; then
                echo -e "${YELLOW}Recent Instructions (last $count):${NC}"
                tail -$count "$INSTRUCTION_LOG"
            else
                echo "No instruction logs"
            fi
            ;;
        "reports")
            if [ -f "$REPORT_LOG" ]; then
                echo -e "${YELLOW}Recent Reports (last $count):${NC}"
                tail -$count "$REPORT_LOG"
            else
                echo "No report logs"
            fi
            ;;
        *)
            if [ -f "$COMM_LOG" ]; then
                echo -e "${YELLOW}All Communication (last $count):${NC}"
                tail -$count "$COMM_LOG"
            else
                echo "No communication logs"
            fi
            ;;
    esac
}

# 緊急通知システム
send_urgent_notification() {
    local message="$1"
    local timestamp=$(date '+%H:%M:%S')
    
    echo -e "${RED}🚨 URGENT NOTIFICATION 🚨${NC}"
    echo -e "${YELLOW}Message: $message${NC}"
    
    # 全ペインに緊急通知
    for pane in "${ROLE_TO_PANE[@]}"; do
        if tmux list-panes -t "$SESSION_NAME:$pane" 2>/dev/null; then
            tmux send-keys -t "$SESSION_NAME:$pane" "echo '🚨 [$timestamp] URGENT: $message'" C-m
        fi
    done
    
    # ログ記録
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] URGENT: $message" >> "$COMM_LOG"
}

# インタラクティブコミュニケーションメニュー
show_communication_menu() {
    while true; do
        clear
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║              Team Communication Hub                         ║${NC}"
        echo -e "${CYAN}║            チームコミュニケーションハブ                      ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "1. Send Instruction (指示送信)"
        echo "2. Send Report (報告送信)"
        echo "3. Broadcast to Team (チーム一斉指示)"
        echo "4. Send Urgent Notification (緊急通知)"
        echo "5. Monitor Team Status (チーム状態監視)"
        echo "6. View Communication History (通信履歴)"
        echo "7. Quick Commands (クイックコマンド)"
        echo "8. Communication Templates (テンプレート)"
        echo "q. Quit (終了)"
        echo ""
        read -p "Select option: " choice
        
        case $choice in
            1)
                echo ""
                echo -e "${YELLOW}Available roles:${NC} manager, cto, dev0, dev1, dev2, dev3, dev4, dev5"
                read -p "From role: " from_role
                read -p "To role: " to_role
                read -p "Instruction: " instruction
                read -p "Priority (normal/high/urgent): " priority
                
                send_instruction "$from_role" "$to_role" "$instruction" "${priority:-normal}"
                read -p "Press Enter to continue..."
                ;;
            2)
                echo ""
                echo -e "${YELLOW}Available roles:${NC} manager, cto, dev0, dev1, dev2, dev3, dev4, dev5"
                read -p "From role: " from_role
                read -p "To role: " to_role
                read -p "Report: " report
                read -p "Status (info/success/warning/error): " status
                
                receive_report "$from_role" "$to_role" "$report" "${status:-info}"
                read -p "Press Enter to continue..."
                ;;
            3)
                echo ""
                echo -e "${YELLOW}Available groups:${NC} all, devs, management"
                read -p "From role: " from_role
                read -p "Target group: " target_group
                read -p "Instruction: " instruction
                
                broadcast_instruction "$from_role" "$instruction" "$target_group"
                read -p "Press Enter to continue..."
                ;;
            4)
                echo ""
                read -p "Urgent message: " urgent_msg
                send_urgent_notification "$urgent_msg"
                read -p "Press Enter to continue..."
                ;;
            5)
                echo ""
                monitor_team_status
                read -p "Press Enter to continue..."
                ;;
            6)
                echo ""
                echo -e "${YELLOW}Filter options:${NC} all, instructions, reports"
                read -p "Filter (default: all): " filter
                read -p "Count (default: 20): " count
                show_communication_history "${filter:-all}" "${count:-20}"
                read -p "Press Enter to continue..."
                ;;
            7)
                show_quick_commands
                read -p "Press Enter to continue..."
                ;;
            8)
                show_templates
                read -p "Press Enter to continue..."
                ;;
            q|Q)
                echo -e "${GREEN}Exiting Communication Hub${NC}"
                break
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# クイックコマンド表示
show_quick_commands() {
    echo ""
    echo -e "${CYAN}=== Quick Commands ===${NC}"
    echo ""
    echo -e "${YELLOW}Command Line Usage:${NC}"
    echo "  $0 send [from] [to] [message]              # 指示送信"
    echo "  $0 report [from] [to] [report]             # 報告送信"
    echo "  $0 broadcast [from] [group] [message]      # 一斉指示"
    echo "  $0 urgent [message]                        # 緊急通知"
    echo "  $0 status                                  # チーム状態"
    echo "  $0 history [filter] [count]                # 通信履歴"
    echo ""
    echo -e "${YELLOW}Example Commands:${NC}"
    echo "  $0 send cto manager 'Start development phase'"
    echo "  $0 report dev0 manager 'Frontend completed'"
    echo "  $0 broadcast manager devs 'Daily standup in 5 min'"
    echo "  $0 urgent 'System emergency - all hands on deck'"
}

# テンプレート表示
show_templates() {
    echo ""
    echo -e "${CYAN}=== Communication Templates ===${NC}"
    echo ""
    echo -e "${YELLOW}CTO → Manager Templates:${NC}"
    echo "  'Phase 1 development start - implement user authentication'"
    echo "  'Architecture review needed for scalability'"
    echo "  'Security audit required before production'"
    echo ""
    echo -e "${YELLOW}Manager → Dev Templates:${NC}"
    echo "  'Implement React frontend for user dashboard'"
    echo "  'Create REST API endpoints for data management'"
    echo "  'Set up CI/CD pipeline with testing automation'"
    echo ""
    echo -e "${YELLOW}Dev → Manager Templates:${NC}"
    echo "  'Frontend development completed - ready for testing'"
    echo "  'API implementation done - documentation updated'"
    echo "  'Deployment pipeline configured - staging environment ready'"
    echo ""
    echo -e "${YELLOW}Emergency Templates:${NC}"
    echo "  'Production issue detected - immediate attention required'"
    echo "  'Security vulnerability found - patch needed urgently'"
    echo "  'Performance degradation - optimization required'"
}

# メイン処理
main() {
    case "${1:-}" in
        "send")
            if [ $# -ge 4 ]; then
                send_instruction "$2" "$3" "$4" "${5:-normal}"
            else
                echo "Usage: $0 send [from] [to] [message] [priority]"
                exit 1
            fi
            ;;
        "report")
            if [ $# -ge 4 ]; then
                receive_report "$2" "$3" "$4" "${5:-info}"
            else
                echo "Usage: $0 report [from] [to] [report] [status]"
                exit 1
            fi
            ;;
        "broadcast")
            if [ $# -ge 4 ]; then
                broadcast_instruction "$2" "$4" "$3"
            else
                echo "Usage: $0 broadcast [from] [group] [message]"
                exit 1
            fi
            ;;
        "urgent")
            if [ $# -ge 2 ]; then
                send_urgent_notification "$2"
            else
                echo "Usage: $0 urgent [message]"
                exit 1
            fi
            ;;
        "status")
            monitor_team_status
            ;;
        "history")
            show_communication_history "$2" "$3"
            ;;
        "help"|"-h"|"--help")
            echo "Team Communication Hub - Usage:"
            echo ""
            show_quick_commands
            ;;
        *)
            show_communication_menu
            ;;
    esac
}

# スクリプト実行
main "$@"