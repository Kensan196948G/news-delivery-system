#!/bin/bash

# Enhanced Pane Layout Manager with Claude Auto-Auth & Team Management
# 強化版ペイン構成管理ツール（Claude自動認証・チーム管理統合）

# 設定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TMUX_DIR")"
SESSION_NAME="news-dev-team"
INSTRUCTIONS_DIR="$TMUX_DIR/instructions"

# ログ設定
LOG_DIR="$TMUX_DIR/logs"
LAYOUT_LOG="$LOG_DIR/enhanced-pane-layout-$(date +%Y%m%d_%H%M%S).log"
CLAUDE_AUTH_LOG="$LOG_DIR/claude-auth-$(date +%Y%m%d_%H%M%S).log"
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
ICON_CTO="👔"
ICON_MANAGER="📋"
ICON_DEV="💻"
ICON_STATUS="⚡"
ICON_WORKING="🔄"
ICON_CLAUDE="🤖"

# 作業状態管理
declare -A PANE_STATUS
declare -A PANE_TASK
declare -A PANE_ROLE

# リアルタイムログ関数
log_realtime() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${CYAN}[LOG]${NC} $message" | tee -a "$LAYOUT_LOG"
}

log_action() {
    local action="$1"
    local detail="$2"
    echo -e "${GREEN}[ACTION]${NC} $action${detail:+ - $detail}" | tee -a "$LAYOUT_LOG"
}

log_claude() {
    local message="$1"
    echo -e "${MAGENTA}[CLAUDE]${NC} $message" | tee -a "$CLAUDE_AUTH_LOG"
}

# ヘッダー表示
show_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         Enhanced News Team Layout Manager + Claude            ║${NC}"
    echo -e "${CYAN}║       強化版ニュースチーム構成管理 + Claude自動認証           ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_realtime "Enhanced Pane Layout Manager Started"
}

# Claude自動認証システム（エラーハンドリング強化版）
setup_claude_auto_auth() {
    local pane_id="$1"
    local role="$2"
    local instructions_file="$3"
    
    log_claude "Setting up enhanced Claude auto-auth for $role (pane: $pane_id)"
    
    # Claude CLI存在確認
    if ! command -v claude &> /dev/null; then
        log_claude "ERROR: Claude CLI not found. Skipping setup for $role"
        return 1
    fi
    
    # 指示ファイルの内容を読み込み
    local instructions_content=""
    if [ -f "$INSTRUCTIONS_DIR/$instructions_file" ]; then
        instructions_content=$(cat "$INSTRUCTIONS_DIR/$instructions_file")
        log_claude "Loaded instructions from $instructions_file (${#instructions_content} chars)"
    else
        log_claude "WARNING: Instructions file not found: $instructions_file"
        instructions_content="# No specific instructions loaded for $role"
    fi
    
    # 強化版Claude認証&指示注入スクリプトを作成
    cat > "/tmp/claude_setup_$pane_id.sh" << EOF
#!/bin/bash

# 強化版Claude自動認証・指示注入スクリプト（エラーハンドリング付き）
echo "${ICON_CLAUDE} Starting enhanced Claude setup for $role..."

# Claude CLI 存在確認
if ! command -v claude &> /dev/null; then
    echo "❌ Claude CLI not found. Please install Claude CLI first."
    echo "Visit: https://claude.ai/download"
    read -p "Press Enter to continue without Claude..."
    exit 1
fi

# tmux環境検出とraw mode対応確認
check_tmux_compatibility() {
    if [ -n "\$TMUX" ]; then
        echo "${ICON_CLAUDE} tmux environment detected - using safe mode"
        return 0
    fi
    return 1
}

# 安全なClaude起動関数
safe_claude_launch() {
    local method="\$1"
    echo "${ICON_CLAUDE} Attempting Claude launch (method: \$method)..."
    
    case "\$method" in
        "interactive")
            # 対話モードで起動（最も安全）
            echo "${ICON_CLAUDE} Starting Claude in interactive mode..."
            claude 2>/dev/null || {
                echo "⚠️  Interactive mode failed, trying alternative..."
                return 1
            }
            ;;
        "skip-permissions")
            # 権限スキップモード（tmux環境で問題が出やすい）
            echo "${ICON_CLAUDE} Starting Claude with skip-permissions..."
            if check_tmux_compatibility; then
                # tmux環境では特別な処理
                echo "${ICON_CLAUDE} tmux detected - using stdin redirection"
                echo "" | claude --dangerously-skip-permissions 2>/dev/null || {
                    echo "⚠️  Skip-permissions mode failed in tmux"
                    return 1
                }
            else
                claude --dangerously-skip-permissions 2>/dev/null || {
                    echo "⚠️  Skip-permissions mode failed"
                    return 1
                }
            fi
            ;;
        "manual")
            # 手動起動の案内
            echo "${ICON_CLAUDE} Manual setup required"
            echo "📋 Please follow these steps:"
            echo "1. Open a new terminal"
            echo "2. Run: claude"
            echo "3. Complete authentication"
            echo "4. Return to this pane"
            read -p "Press Enter when ready to continue..."
            return 0
            ;;
    esac
}

# Step 1: Claude起動（複数方法で試行）
echo "${ICON_CLAUDE} Launching Claude with error handling..."

CLAUDE_SUCCESS=false

# 方法1: 対話モード（最も安全）
echo "${ICON_CLAUDE} Trying method 1: Interactive mode"
if safe_claude_launch "interactive"; then
    CLAUDE_SUCCESS=true
    echo "✅ Claude launched successfully (interactive mode)"
else
    echo "❌ Interactive mode failed"
    
    # 方法2: 権限スキップモード
    echo "${ICON_CLAUDE} Trying method 2: Skip-permissions mode"
    if safe_claude_launch "skip-permissions"; then
        CLAUDE_SUCCESS=true
        echo "✅ Claude launched successfully (skip-permissions mode)"
    else
        echo "❌ Skip-permissions mode failed"
        
        # 方法3: 手動起動案内
        echo "${ICON_CLAUDE} Fallback to method 3: Manual setup"
        safe_claude_launch "manual"
        CLAUDE_SUCCESS=true
    fi
fi

if [ "\$CLAUDE_SUCCESS" = "true" ]; then
    echo ""
    echo "${ICON_CLAUDE} $role Claude session ready!"
    echo "${ICON_STATUS} Role: $role"
    echo "${ICON_STATUS} Instructions loaded: \$(echo '$instructions_content' | wc -l) lines"
    echo ""
    
    # 指示ファイル内容を表示
    echo "${ICON_CLAUDE} Role-specific instructions:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat << 'INSTRUCTIONS_EOF'
$instructions_content
INSTRUCTIONS_EOF
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "${ICON_CLAUDE} You can now start working with Claude using the above instructions."
    echo "${ICON_STATUS} Type your questions or requests to Claude based on your role as $role."
else
    echo "❌ All Claude launch methods failed"
    echo "📋 Fallback options:"
    echo "1. Install Claude CLI: https://claude.ai/download"
    echo "2. Use manual authentication in browser"
    echo "3. Continue without Claude integration"
fi

# 継続的なターミナル使用のための待機
echo ""
echo "🔄 Terminal ready for $role operations..."
echo "💡 Tip: You can manually run 'claude' command if auto-launch failed"
bash
EOF

    chmod +x "/tmp/claude_setup_$pane_id.sh"
    log_claude "Created enhanced Claude setup script for $role"
}

# ペインタイトル設定（アイコン+作業名）
set_enhanced_pane_title() {
    local pane_index="$1"
    local role="$2"
    local icon="$3"
    local task="${4:-待機中}"
    
    # 作業状態を記録
    PANE_ROLE[$pane_index]="$role"
    PANE_STATUS[$pane_index]="準備中"
    PANE_TASK[$pane_index]="$task"
    
    # 拡張タイトル設定
    local title="$icon $role | $task"
    tmux select-pane -t "$SESSION_NAME:0.$pane_index" -T "$title"
    
    log_action "Set enhanced pane title" "Pane $pane_index: $title"
}

# ペイン作業状態更新
update_pane_status() {
    local pane_index="$1"
    local status="$2"
    local task="${3:-${PANE_TASK[$pane_index]}}"
    
    PANE_STATUS[$pane_index]="$status"
    PANE_TASK[$pane_index]="$task"
    
    local role="${PANE_ROLE[$pane_index]}"
    local icon
    case "$role" in
        "CTO") icon="$ICON_CTO" ;;
        "MANAGER") icon="$ICON_MANAGER" ;;
        *) icon="$ICON_DEV" ;;
    esac
    
    # ステータスアイコン追加
    case "$status" in
        "作業中") icon="$icon$ICON_WORKING" ;;
        "Claude起動中") icon="$icon$ICON_CLAUDE" ;;
        *) icon="$icon$ICON_STATUS" ;;
    esac
    
    local title="$icon $role | $task"
    tmux select-pane -t "$SESSION_NAME:0.$pane_index" -T "$title"
    
    log_action "Updated pane status" "Pane $pane_index: $status - $task"
}

# リアルタイム指示・報告システム
setup_communication_system() {
    log_action "Setting up communication system" "Real-time instruction and reporting"
    
    # 指示送信スクリプト作成
    cat > "$TMUX_DIR/send-instruction.sh" << 'EOF'
#!/bin/bash
TARGET_ROLE="$1"
INSTRUCTION="$2"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ターゲットペイン特定
case "$TARGET_ROLE" in
    "manager"|"MANAGER") TARGET_PANE="0.0" ;;
    "cto"|"CTO") TARGET_PANE="0.1" ;;
    "dev0"|"DEV0") TARGET_PANE="0.2" ;;
    "dev1"|"DEV1") TARGET_PANE="0.3" ;;
    "dev2"|"DEV2") TARGET_PANE="0.4" ;;
    "dev3"|"DEV3") TARGET_PANE="0.5" ;;
    "dev4"|"DEV4") TARGET_PANE="0.6" ;;
    "dev5"|"DEV5") TARGET_PANE="0.7" ;;
    *) echo "Unknown target role: $TARGET_ROLE"; exit 1 ;;
esac

# 指示をペインに送信
tmux send-keys -t "news-dev-team:$TARGET_PANE" "echo '【$TIMESTAMP】指示受信: $INSTRUCTION'" C-m

echo "Instruction sent to $TARGET_ROLE (pane $TARGET_PANE): $INSTRUCTION"
EOF

    chmod +x "$TMUX_DIR/send-instruction.sh"
    
    # 報告受信スクリプト作成
    cat > "$TMUX_DIR/receive-report.sh" << 'EOF'
#!/bin/bash
FROM_ROLE="$1"
REPORT="$2"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "【$TIMESTAMP】報告受信 from $FROM_ROLE: $REPORT" >> "$TMUX_DIR/logs/team-reports.log"

# 管理者ペインに通知
tmux send-keys -t "news-dev-team:0.0" "echo '【報告】$FROM_ROLE: $REPORT'" C-m
tmux send-keys -t "news-dev-team:0.1" "echo '【報告】$FROM_ROLE: $REPORT'" C-m

echo "Report received from $FROM_ROLE: $REPORT"
EOF

    chmod +x "$TMUX_DIR/receive-report.sh"
    
    log_action "Communication system ready" "send-instruction.sh and receive-report.sh created"
}

# 基本セッション作成
create_base_session() {
    log_action "Creating base session" "$SESSION_NAME"
    
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_action "Killing existing session" "$SESSION_NAME"
        tmux kill-session -t "$SESSION_NAME"
    fi
    
    # プロジェクトディレクトリでセッション作成
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT"
    
    # tmux設定を強化
    tmux set -g pane-border-status top
    tmux set -g pane-border-format '#[fg=cyan,bold]#{pane_title}'
    tmux set -g status-left-length 50
    tmux set -g status-right-length 50
    tmux set -g status-right "#{?window_bigger,[#{window_offset_x}#,#{window_offset_y}] ,}\"#{=21:pane_title}\" %H:%M %d-%b-%y"
    
    log_status "Base session created successfully"
    return 0
}

# 縦分割（左右）
create_vertical_split() {
    log_action "Creating vertical split" "左右分割"
    tmux split-window -h -t "$SESSION_NAME" -c "$PROJECT_ROOT"
    log_status "Vertical split completed - Left and Right panes created"
}

# 左側分割（Manager + CTO）均等スペース
create_left_management_panes() {
    log_action "Creating left management panes" "Manager + CTO (Equal Space)"
    
    # 左側ペインを水平分割（上下）
    tmux split-window -v -t "$SESSION_NAME:0.0" -c "$PROJECT_ROOT"
    
    # 左側ペインのサイズを均等に調整（50:50）
    tmux resize-pane -t "$SESSION_NAME:0.0" -y 50%
    tmux resize-pane -t "$SESSION_NAME:0.1" -y 50%
    
    # Manager ペインの設定（上段）
    set_enhanced_pane_title "0" "MANAGER" "$ICON_MANAGER" "チーム統括・進捗管理"
    setup_claude_auto_auth "0" "MANAGER" "manager.md"
    
    # CTO ペインの設定（下段）
    set_enhanced_pane_title "1" "CTO" "$ICON_CTO" "戦略決定・技術監督"
    setup_claude_auto_auth "1" "CTO" "ceo.md"
    
    log_status "Left management panes created - Manager (top), CTO (bottom) with equal space"
}

# 開発者ペイン作成（2/4/6分割対応）
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

# 2開発者構成
create_2_dev_panes() {
    log_action "Setting up 2-developer layout" "右側を上下2分割"
    
    # 右側ペイン（ペイン2）を上下分割
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    
    # 開発者ペインの設定
    set_enhanced_pane_title "2" "DEV0" "$ICON_DEV" "フロントエンド開発"
    setup_claude_auto_auth "2" "DEV0" "developer.md"
    
    set_enhanced_pane_title "3" "DEV1" "$ICON_DEV" "バックエンド開発"
    setup_claude_auto_auth "3" "DEV1" "developer.md"
    
    log_status "2-developer layout completed"
}

# 4開発者構成
create_4_dev_panes() {
    log_action "Setting up 4-developer layout" "右側を4分割"
    
    # 段階的分割
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    tmux split-window -v -t "$SESSION_NAME:0.4" -c "$PROJECT_ROOT"
    
    # 開発者ペインの設定
    set_enhanced_pane_title "2" "DEV0" "$ICON_DEV" "フロントエンド開発"
    setup_claude_auto_auth "2" "DEV0" "developer.md"
    
    set_enhanced_pane_title "3" "DEV1" "$ICON_DEV" "バックエンド開発" 
    setup_claude_auto_auth "3" "DEV1" "developer.md"
    
    set_enhanced_pane_title "4" "DEV2" "$ICON_DEV" "QA・テスト"
    setup_claude_auto_auth "4" "DEV2" "developer.md"
    
    set_enhanced_pane_title "5" "DEV3" "$ICON_DEV" "インフラ・DevOps"
    setup_claude_auto_auth "5" "DEV3" "developer.md"
    
    log_status "4-developer layout completed"
}

# 6開発者構成（格子状レイアウトで確実に6ペイン作成）
create_6_dev_panes() {
    log_action "Setting up 6-developer layout" "格子状レイアウトで確実に6つの開発者ペイン作成"
    
    echo -e "${CYAN}🏗️ 格子状6開発者レイアウト作成中...${NC}"
    echo -e "${YELLOW}配置: 右側に3列2行の格子配列${NC}"
    
    # 現在のターミナル情報表示
    local term_width=$(tmux display-message -p '#{client_width}')
    local term_height=$(tmux display-message -p '#{client_height}')
    log_action "Terminal size" "${term_width}x${term_height}"
    
    # 格子状レイアウト作成（3列2行）
    log_action "Creating grid layout" "3 columns × 2 rows = 6 developer panes"
    
    # Step 1: 右側ペイン（0.2）を水平に3分割
    echo -e "${CYAN}Step 1: 右側を3列に分割${NC}"
    
    # 第1列（DEV0）は既に存在
    # 第2列（DEV2）を作成
    tmux split-window -h -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    sleep 0.2
    log_action "Column 1 created" "Split pane 0.2 horizontally"
    
    # 第3列（DEV4）を作成
    tmux split-window -h -t "$SESSION_NAME:0.3" -c "$PROJECT_ROOT"
    sleep 0.2
    log_action "Column 2 created" "Split pane 0.3 horizontally"
    
    # 現在の状況: 3つの縦列（ペイン2, 3, 4）
    
    # Step 2: 各列を縦に2分割
    echo -e "${CYAN}Step 2: 各列を上下2行に分割${NC}"
    
    # 第1列を分割（ペイン2 → 2,3）
    tmux split-window -v -t "$SESSION_NAME:0.2" -c "$PROJECT_ROOT"
    sleep 0.2
    log_action "Row 1 created" "Split column 1 vertically"
    
    # 第2列を分割（ペイン3 → 4,5）※番号がシフトしている
    tmux split-window -v -t "$SESSION_NAME:0.4" -c "$PROJECT_ROOT"
    sleep 0.2
    log_action "Row 2 created" "Split column 2 vertically"
    
    # 第3列を分割（ペイン4 → 6,7）※番号がシフトしている
    tmux split-window -v -t "$SESSION_NAME:0.6" -c "$PROJECT_ROOT"
    sleep 0.2
    log_action "Row 3 created" "Split column 3 vertically"
    
    # ペインサイズを均等に調整
    echo -e "${CYAN}Step 3: グリッドサイズを均等に調整${NC}"
    tmux select-layout -t "$SESSION_NAME" tiled 2>/dev/null || {
        # tiledレイアウトが使えない場合、手動調整
        log_action "Manual adjustment" "Tiled layout not available, using manual resize"
        
        # 各ペインを均等サイズに調整
        local total_width=$(tmux display-message -p '#{window_width}')
        local pane_width=$((total_width / 2))  # 左右50:50
        local right_width=$((pane_width / 3))  # 右側を3等分
        
        # 右側の各列を均等に
        for pane in 2 4 6; do
            if tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}' | grep -q "^$pane$"; then
                tmux resize-pane -t "$SESSION_NAME:0.$pane" -x "$right_width" 2>/dev/null || true
            fi
        done
    }
    
    # 実際に作成されたペインを確認
    log_action "Verifying grid creation" "Checking all 6 developer panes"
    
    local available_panes=()
    local pane_mapping=()
    
    # ペイン2-7をチェック
    for i in {2..7}; do
        if tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}' | grep -q "^$i$"; then
            available_panes+=($i)
            log_action "Grid pane detected" "Pane 0.$i is available"
        fi
    done
    
    local pane_count=${#available_panes[@]}
    log_action "Grid creation result" "Successfully created $pane_count developer panes"
    
    # 開発者配置（格子状配列）
    local dev_roles=("フロントエンド開発" "バックエンド開発" "QA・テスト" "インフラ・DevOps" "データベース設計" "UI/UX・品質管理")
    
    # 格子配列でのDEV番号割り当て
    # 配列: [2,3] [4,5] [6,7] 
    #      DEV0,1  DEV2,3  DEV4,5
    
    local dev_assignments=(
        "2:0:0"  # ペイン2 = DEV0, role[0]
        "3:1:1"  # ペイン3 = DEV1, role[1]  
        "4:2:2"  # ペイン4 = DEV2, role[2]
        "5:3:3"  # ペイン5 = DEV3, role[3]
        "6:4:4"  # ペイン6 = DEV4, role[4]
        "7:5:5"  # ペイン7 = DEV5, role[5]
    )
    
    for assignment in "${dev_assignments[@]}"; do
        IFS=':' read -r pane_num dev_num role_index <<< "$assignment"
        
        # ペイン存在確認
        if tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}' | grep -q "^$pane_num$"; then
            if [ $role_index -lt ${#dev_roles[@]} ]; then
                set_enhanced_pane_title "$pane_num" "DEV$dev_num" "$ICON_DEV" "${dev_roles[$role_index]}"
                setup_claude_auto_auth "$pane_num" "DEV$dev_num" "developer.md"
                log_action "Grid developer assigned" "DEV$dev_num → pane 0.$pane_num (${dev_roles[$role_index]})"
            fi
        else
            log_action "Missing pane" "Pane 0.$pane_num not found for DEV$dev_num"
        fi
    done
    
    # 結果報告
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ $pane_count -eq 6 ]; then
        echo -e "${GREEN}✅ 6-developer grid layout completed successfully!${NC}"
        echo -e "${CYAN}🏗️ Layout: Manager/CTO (equal) + 3×2 Developer Grid${NC}"
        echo -e "${CYAN}📊 Team: DEV0 through DEV5 in grid formation${NC}"
    elif [ $pane_count -ge 4 ]; then
        echo -e "${YELLOW}⚠️ Partial grid created: $pane_count developers${NC}"
        echo -e "${CYAN}💡 Grid layout partially successful${NC}"
    else
        echo -e "${RED}❌ Grid creation failed - Only $pane_count panes created${NC}"
        echo -e "${CYAN}💡 Try 4-developer layout for better compatibility${NC}"
    fi
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 最終ペイン配列表示
    echo ""
    echo -e "${CYAN}Final Grid Layout:${NC}"
    echo -e "${YELLOW}Left Side (Management):${NC}"
    echo "  Manager (0.0) - チーム統括・進捗管理"
    echo "  CTO (0.1)     - 戦略決定・技術監督"
    echo ""
    echo -e "${YELLOW}Right Side (Developer Grid):${NC}"
    
    # グリッド表示
    local grid_display=""
    for i in {2..7}; do
        if tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}' | grep -q "^$i$"; then
            local dev_num=$((i-2))
            if [ $i -eq 2 ] || [ $i -eq 4 ] || [ $i -eq 6 ]; then
                echo -n "  "
            fi
            echo -n "DEV$dev_num(0.$i) "
            if [ $i -eq 3 ] || [ $i -eq 5 ] || [ $i -eq 7 ]; then
                echo ""
            fi
        fi
    done
    
    echo ""
    tmux list-panes -t "$SESSION_NAME" -F '  Pane #{pane_index}: #{pane_title} (#{pane_width}x#{pane_height})'
    
    log_status "6-developer grid layout completed with $pane_count panes"
}

# ペインサイズ調整（格子レイアウト対応）
adjust_pane_sizes() {
    local dev_count=$1
    log_action "Adjusting pane sizes" "Optimizing layout for $dev_count developers"
    
    if [ "$dev_count" -eq 6 ]; then
        # 6開発者グリッドレイアウトの場合
        log_action "Grid layout adjustment" "Optimizing for 3×2 developer grid"
        
        # 左右の比率を40:60に調整（管理側を少し小さく、開発側を大きく）
        tmux resize-pane -t "$SESSION_NAME:0.0" -x 40%
        
        # 左側Management の上下比率を50:50に調整（均等スペース）
        tmux resize-pane -t "$SESSION_NAME:0.0" -y 50%
        tmux resize-pane -t "$SESSION_NAME:0.1" -y 50%
        
        # 右側グリッドのバランス調整
        # tiled レイアウトを使用してペインを均等に
        tmux select-layout -t "$SESSION_NAME" tiled 2>/dev/null || {
            # tiledが使えない場合は手動調整
            log_action "Manual grid adjustment" "Adjusting grid panes manually"
            
            # 各列の幅を均等に（右側の3等分）
            local window_width=$(tmux display-message -p '#{window_width}')
            local management_width=$((window_width * 40 / 100))
            local grid_width=$((window_width - management_width))
            local column_width=$((grid_width / 3))
            
            # 各行の高さを均等に（上下50:50）
            local window_height=$(tmux display-message -p '#{window_height}')
            local row_height=$((window_height / 2))
            
            # 可能な限り調整
            for pane in 2 4 6; do
                if tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}' | grep -q "^$pane$"; then
                    tmux resize-pane -t "$SESSION_NAME:0.$pane" -x "$column_width" 2>/dev/null || true
                fi
            done
            
            for pane in 2 3 4 5 6 7; do
                if tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}' | grep -q "^$pane$"; then
                    tmux resize-pane -t "$SESSION_NAME:0.$pane" -y "$row_height" 2>/dev/null || true
                fi
            done
        }
    else
        # 従来の2/4開発者レイアウト
        log_action "Standard layout adjustment" "Optimizing for linear developer layout"
        
        # 左右の比率を50:50に調整
        tmux resize-pane -t "$SESSION_NAME:0.0" -x 50%
        
        # 左側の上下比率を50:50に調整（均等スペース）
        tmux resize-pane -t "$SESSION_NAME:0.0" -y 50%
        tmux resize-pane -t "$SESSION_NAME:0.1" -y 50%
    fi
    
    log_status "Pane sizes adjusted for $dev_count-developer layout"
}

# Claude一括自動起動（安全モード）
start_claude_sessions() {
    local dev_count=$1
    log_claude "Starting enhanced Claude auto-authentication for all panes"
    
    # Claude CLI存在確認
    if ! command -v claude &> /dev/null; then
        log_claude "WARNING: Claude CLI not found - skipping auto-authentication"
        echo -e "${YELLOW}⚠️ Claude CLI not found. Installing Claude CLI is recommended.${NC}"
        echo -e "${CYAN}💡 Visit: https://claude.ai/download${NC}"
        echo -e "${CYAN}💡 Manual setup: Run 'claude' in each pane after installation${NC}"
        return 1
    fi
    
    # tmux環境での安全性確認
    log_claude "Checking tmux compatibility for Claude integration"
    
    # 一括でClaude起動スクリプトを実行（エラーハンドリング付き）
    for ((i=0; i<=dev_count+1; i++)); do
        if [ -f "/tmp/claude_setup_$i.sh" ]; then
            log_claude "Starting enhanced Claude for pane $i"
            update_pane_status "$i" "Claude起動中" "安全モード認証中"
            
            # 安全なClaude起動（エラー耐性）
            tmux send-keys -t "$SESSION_NAME:0.$i" "/tmp/claude_setup_$i.sh" C-m 2>/dev/null || {
                log_claude "WARNING: Failed to send Claude setup to pane $i"
                update_pane_status "$i" "待機中" "手動Claude起動推奨"
            }
            
            sleep 1  # 起動間隔を短縮（安全性向上）
        else
            log_claude "WARNING: Claude setup script not found for pane $i"
        fi
    done
    
    log_claude "Enhanced Claude sessions initiated with error handling"
    echo -e "${GREEN}✅ Claude integration started with fallback support${NC}"
    echo -e "${CYAN}💡 If any pane fails, you can manually run 'claude' in that pane${NC}"
}

# 開発環境初期化
initialize_development_environment() {
    local dev_count=$1
    log_action "Initializing development environment" "Setting up team workspace"
    
    # Manager ペイン初期化（上段）
    update_pane_status "0" "準備完了" "チーム統括待機"
    
    # CTO ペイン初期化（下段）
    update_pane_status "1" "準備完了" "システム監督待機"
    
    # 開発者ペイン初期化
    for ((i=2; i<=dev_count+1; i++)); do
        update_pane_status "$i" "準備完了" "開発タスク待機"
    done
    
    log_status "Development environment initialized"
}

# リアルタイム状態監視
start_real_time_monitoring() {
    log_action "Starting real-time monitoring" "Team status and communication"
    
    # 監視スクリプト作成
    cat > "$TMUX_DIR/monitor-team.sh" << 'EOF'
#!/bin/bash
while true; do
    echo "=== $(date '+%H:%M:%S') チーム状態 ==="
    
    # 各ペインの状態表示
    for i in {0..7}; do
        if tmux list-panes -t "news-dev-team:0.$i" 2>/dev/null; then
            title=$(tmux display-message -t "news-dev-team:0.$i" -p '#{pane_title}')
            echo "Pane $i: $title"
        fi
    done
    
    sleep 30
done
EOF
    
    chmod +x "$TMUX_DIR/monitor-team.sh"
    
    # バックグラウンドで監視開始
    nohup "$TMUX_DIR/monitor-team.sh" > "$LOG_DIR/team-monitor.log" 2>&1 &
    
    log_status "Real-time monitoring started"
}

# メインレイアウト作成関数
create_enhanced_team_layout() {
    local dev_count=$1
    
    show_header
    log_realtime "Starting enhanced team layout creation with $dev_count developers"
    
    # 通信システムセットアップ
    setup_communication_system
    
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
    
    initialize_development_environment "$dev_count"
    sleep 1
    
    # Claude一括起動（オプション化・安全性向上）
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🤖 Claude統合オプション${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Claude CLI存在確認と選択肢提示
    if command -v claude &> /dev/null; then
        echo -e "${GREEN}✅ Claude CLI detected${NC}"
        echo -e "${CYAN}選択肢:${NC}"
        echo "  1. 自動Claude認証を開始 (推奨)"
        echo "  2. 手動Claude起動（各ペインで個別起動）"
        echo "  3. Claude統合をスキップ（基本tmux環境のみ）"
        echo ""
        read -p "選択してください (1/2/3): " claude_choice
        
        case "$claude_choice" in
            1)
                echo -e "${CYAN}🚀 Claude自動認証を開始します...${NC}"
                if start_claude_sessions "$dev_count"; then
                    echo -e "${GREEN}✅ Claude統合が正常に開始されました${NC}"
                else
                    echo -e "${YELLOW}⚠️ Claude自動認証に問題が発生しました${NC}"
                    echo -e "${CYAN}💡 各ペインで手動で 'claude' コマンドを実行してください${NC}"
                fi
                ;;
            2)
                echo -e "${CYAN}📋 手動Claude起動モード${NC}"
                echo -e "${YELLOW}各ペインで以下を実行してください:${NC}"
                echo "  claude"
                echo ""
                echo -e "${CYAN}💡 ロール別指示は tmux/instructions/ を参照${NC}"
                ;;
            3)
                echo -e "${CYAN}⏭️ Claude統合をスキップしました${NC}"
                echo -e "${YELLOW}基本tmux環境が利用可能です${NC}"
                ;;
            *)
                echo -e "${YELLOW}⚠️ 無効な選択です。Claude統合をスキップします${NC}"
                ;;
        esac
    else
        echo -e "${YELLOW}⚠️ Claude CLI not found${NC}"
        echo -e "${CYAN}オプション:${NC}"
        echo "  1. Claude CLIをインストール（推奨）"
        echo "  2. Claude統合なしで続行"
        echo ""
        read -p "選択してください (1/2): " install_choice
        
        case "$install_choice" in
            1)
                echo -e "${CYAN}🔗 Claude CLI インストール情報:${NC}"
                echo "  Visit: https://claude.ai/download"
                echo "  インストール後、このスクリプトを再実行してください"
                echo ""
                read -p "Press Enter to continue without Claude..."
                ;;
            2)
                echo -e "${CYAN}⏭️ Claude統合なしで続行します${NC}"
                ;;
            *)
                echo -e "${YELLOW}⚠️ 無効な選択です。Claude統合なしで続行します${NC}"
                ;;
        esac
    fi
    
    # リアルタイム監視開始
    start_real_time_monitoring
    
    log_realtime "Enhanced team layout creation completed successfully"
    show_layout_info "$dev_count"
    
    return 0
}

# レイアウト情報表示
show_layout_info() {
    local dev_count=$1
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                Enhanced Layout Information                   ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${GREEN}Session Name:${NC} $SESSION_NAME"
    echo -e "${GREEN}Team Members:${NC} Manager + CTO + $dev_count Developers"
    if [ "$dev_count" -eq 6 ]; then
        echo -e "${GREEN}Layout:${NC} Left($ICON_MANAGER Manager/$ICON_CTO CTO Equal) | Right(3×2 $ICON_DEV Grid)"
    else
        echo -e "${GREEN}Layout:${NC} Left($ICON_MANAGER Manager/$ICON_CTO CTO Equal) | Right($dev_count × $ICON_DEV Linear)"
    fi
    echo -e "${GREEN}Claude Auth:${NC} Auto-authentication with role-specific instructions"
    echo -e "${GREEN}Communication:${NC} Real-time instruction/report system"
    echo -e "${GREEN}Project Root:${NC} $PROJECT_ROOT"
    echo -e "${GREEN}Logs:${NC} $LAYOUT_LOG"
    echo ""
    echo -e "${YELLOW}Team Communication Commands:${NC}"
    echo "  $TMUX_DIR/send-instruction.sh [role] [message]    # 指示送信"
    echo "  $TMUX_DIR/receive-report.sh [role] [report]       # 報告受信"
    echo ""
    echo -e "${YELLOW}Available tmux commands:${NC}"
    echo "  tmux attach -t $SESSION_NAME  # セッションにアタッチ"
    echo "  tmux list-panes -t $SESSION_NAME  # ペイン一覧表示"
    echo ""
    echo -e "${CYAN}ペイン構成:${NC}"
    echo "  $ICON_MANAGER Manager (0.0)  - チーム統括・進捗管理 [Equal Space]"
    echo "  $ICON_CTO CTO (0.1)      - 技術戦略決定・システム監督 [Equal Space]"
    
    if [ "$dev_count" -eq 6 ]; then
        echo -e "${CYAN}  開発者グリッド (3列×2行):${NC}"
        echo "    Column 1: $ICON_DEV DEV0 (0.2), $ICON_DEV DEV1 (0.3)"
        echo "    Column 2: $ICON_DEV DEV2 (0.4), $ICON_DEV DEV3 (0.5)"  
        echo "    Column 3: $ICON_DEV DEV4 (0.6), $ICON_DEV DEV5 (0.7)"
    else
        echo -e "${CYAN}  開発者リニア配列:${NC}"
        for ((i=0; i<dev_count; i++)); do
            echo "    $ICON_DEV DEV$i (0.$((i+2)))   - 開発作業・実装"
        done
    fi
    echo ""
}

# インタラクティブメニュー
show_enhanced_menu() {
    while true; do
        show_header
        echo -e "${CYAN}=== Enhanced Pane Layout Manager Menu ===${NC}"
        echo ""
        echo "1. Create 2-Developer Team (Manager/CTO Equal + 2 Devs Linear + Claude)"
        echo "2. Create 4-Developer Team (Manager/CTO Equal + 4 Devs Linear + Claude)"  
        echo "3. Create 6-Developer Team (Manager/CTO Equal + 6 Devs Grid + Claude)"
        echo "4. Attach to existing session"
        echo "5. Show team status & communication logs"
        echo "6. Send instruction to team member"
        echo "7. Kill session & cleanup"
        echo "8. Show team communication help"
        echo "q. Quit"
        echo ""
        read -p "Select option: " choice
        
        case $choice in
            1)
                echo ""
                if create_enhanced_team_layout 2; then
                    echo -e "${GREEN}✓ 2-Developer team layout created!${NC}"
                    echo "Attaching to session in 3 seconds..."
                    sleep 3
                    tmux attach -t "$SESSION_NAME"
                fi
                ;;
            2)
                echo ""
                if create_enhanced_team_layout 4; then
                    echo -e "${GREEN}✓ 4-Developer team layout created!${NC}"
                    echo "Attaching to session in 3 seconds..."
                    sleep 3
                    tmux attach -t "$SESSION_NAME"
                fi
                ;;
            3)
                echo ""
                if create_enhanced_team_layout 6; then
                    echo -e "${GREEN}✓ 6-Developer team layout created!${NC}"
                    echo "Attaching to session in 3 seconds..."
                    sleep 3
                    tmux attach -t "$SESSION_NAME"
                fi
                ;;
            4)
                if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
                    tmux attach -t "$SESSION_NAME"
                else
                    echo -e "${RED}No session exists. Create one first.${NC}"
                    read -p "Press Enter to continue..."
                fi
                ;;
            5)
                echo ""
                echo -e "${GREEN}Team Status:${NC}"
                if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
                    tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}: #{pane_title}'
                    echo ""
                    echo -e "${GREEN}Recent Communication Logs:${NC}"
                    if [ -f "$LOG_DIR/team-reports.log" ]; then
                        tail -10 "$LOG_DIR/team-reports.log"
                    else
                        echo "No communication logs yet"
                    fi
                else
                    echo -e "${YELLOW}No active session${NC}"
                fi
                read -p "Press Enter to continue..."
                ;;
            6)
                echo ""
                echo -e "${YELLOW}Available roles:${NC} manager, cto, dev0, dev1, dev2, dev3, dev4, dev5"
                read -p "Target role: " target_role
                read -p "Instruction: " instruction
                if [ -f "$TMUX_DIR/send-instruction.sh" ]; then
                    "$TMUX_DIR/send-instruction.sh" "$target_role" "$instruction"
                    echo -e "${GREEN}Instruction sent!${NC}"
                else
                    echo -e "${RED}Communication system not set up${NC}"
                fi
                read -p "Press Enter to continue..."
                ;;
            7)
                if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
                    echo ""
                    read -p "Kill team session and cleanup? (y/N): " confirm
                    if [[ $confirm =~ ^[Yy]$ ]]; then
                        tmux kill-session -t "$SESSION_NAME"
                        # Cleanup temp files
                        rm -f /tmp/claude_setup_*.sh
                        pkill -f monitor-team.sh 2>/dev/null
                        echo -e "${GREEN}Session killed and cleaned up${NC}"
                    fi
                else
                    echo -e "${YELLOW}No session to kill${NC}"
                fi
                read -p "Press Enter to continue..."
                ;;
            8)
                echo ""
                echo -e "${CYAN}=== Team Communication Help ===${NC}"
                echo ""
                echo -e "${YELLOW}Instruction System:${NC}"
                echo "  CTO → Manager: 技術戦略・方針決定"
                echo "  Manager → Devs: 具体的開発タスク配布"
                echo "  Devs → Manager: 進捗・完了報告"
                echo "  Manager → CTO: 統合・完了報告"
                echo ""
                echo -e "${YELLOW}Communication Commands:${NC}"
                echo "  $TMUX_DIR/send-instruction.sh cto \"technical decision needed\""
                echo "  $TMUX_DIR/send-instruction.sh manager \"start development\""
                echo "  $TMUX_DIR/send-instruction.sh dev0 \"implement frontend\""
                echo "  $TMUX_DIR/receive-report.sh dev0 \"frontend completed\""
                echo ""
                echo -e "${YELLOW}Role Responsibilities:${NC}"
                echo "  $ICON_CTO CTO: 技術戦略・アーキテクチャ決定・品質監督"
                echo "  $ICON_MANAGER Manager: チーム統括・タスク管理・進捗監視"
                echo "  $ICON_DEV Developers: 実装・テスト・技術報告"
                echo ""
                read -p "Press Enter to continue..."
                ;;
            q|Q)
                echo -e "${GREEN}Exiting Enhanced Pane Layout Manager${NC}"
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
    
    # claudeの存在確認
    if ! command -v claude &> /dev/null; then
        echo -e "${YELLOW}Warning: claude CLI not found. Claude auto-auth will be skipped.${NC}"
    fi
    
    # instructionsディレクトリの確認
    if [ ! -d "$INSTRUCTIONS_DIR" ]; then
        echo -e "${YELLOW}Warning: Instructions directory not found: $INSTRUCTIONS_DIR${NC}"
    fi
    
    case "${1:-}" in
        "2"|"dev2")
            create_enhanced_team_layout 2
            tmux attach -t "$SESSION_NAME"
            ;;
        "4"|"dev4")
            create_enhanced_team_layout 4
            tmux attach -t "$SESSION_NAME"
            ;;
        "6"|"dev6")
            create_enhanced_team_layout 6
            tmux attach -t "$SESSION_NAME"
            ;;
        "status")
            if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
                tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}: #{pane_title}'
            else
                echo "No session exists"
            fi
            ;;
        "kill")
            if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
                tmux kill-session -t "$SESSION_NAME"
                rm -f /tmp/claude_setup_*.sh
                pkill -f monitor-team.sh 2>/dev/null
                echo "Session killed and cleaned up"
            else
                echo "No session to kill"
            fi
            ;;
        "help"|"-h"|"--help")
            echo "Enhanced Pane Layout Manager - Usage:"
            echo "  $0 [menu]    - Open interactive menu"
            echo "  $0 2         - Create 2-developer team + Claude"
            echo "  $0 4         - Create 4-developer team + Claude" 
            echo "  $0 6         - Create 6-developer team + Claude"
            echo "  $0 status    - Show team status"
            echo "  $0 kill      - Kill session and cleanup"
            ;;
        *)
            show_enhanced_menu
            ;;
    esac
}

# ファイナライザー（終了時クリーンアップ）
cleanup_on_exit() {
    log_action "Script terminating" "Cleaning up temporary files"
    rm -f /tmp/claude_setup_*.sh
    pkill -f monitor-team.sh 2>/dev/null || true
}

trap cleanup_on_exit EXIT

# スクリプト実行
main "$@"