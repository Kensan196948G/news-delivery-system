#!/bin/bash

# Claude Fallback Launcher - 代替起動スクリプト
# Claude CLIでエラーが発生した場合の安全な起動方法

# 設定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"
INSTRUCTIONS_DIR="$TMUX_DIR/instructions"

# 色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# アイコン定義
ICON_CLAUDE="🤖"
ICON_WARNING="⚠️"
ICON_INFO="💡"
ICON_SUCCESS="✅"
ICON_ERROR="❌"

show_header() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              Claude Fallback Launcher                       ║${NC}"
    echo -e "${CYAN}║            Claude代替起動・トラブルシューティング           ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Claude環境診断
diagnose_claude_environment() {
    echo -e "${BLUE}=== Claude環境診断 ===${NC}"
    echo ""
    
    # Claude CLI存在確認
    if command -v claude &> /dev/null; then
        echo -e "${GREEN}${ICON_SUCCESS} Claude CLI: インストール済み${NC}"
        claude --version 2>/dev/null || echo -e "${YELLOW}${ICON_WARNING} バージョン情報取得失敗${NC}"
    else
        echo -e "${RED}${ICON_ERROR} Claude CLI: 未インストール${NC}"
        echo -e "${CYAN}${ICON_INFO} インストール方法: https://claude.ai/download${NC}"
        return 1
    fi
    
    # tmux環境確認
    if [ -n "$TMUX" ]; then
        echo -e "${GREEN}${ICON_SUCCESS} tmux環境: 検出済み${NC}"
        echo -e "${CYAN}${ICON_INFO} tmuxでのClaude使用は特別な設定が必要です${NC}"
    else
        echo -e "${YELLOW}${ICON_WARNING} tmux環境: 非検出${NC}"
        echo -e "${CYAN}${ICON_INFO} 通常のターミナル環境${NC}"
    fi
    
    # ターミナル機能確認
    if [ -t 0 ]; then
        echo -e "${GREEN}${ICON_SUCCESS} stdin: 利用可能${NC}"
    else
        echo -e "${RED}${ICON_ERROR} stdin: 利用不可（パイプ経由の可能性）${NC}"
    fi
    
    if [ -t 1 ]; then
        echo -e "${GREEN}${ICON_SUCCESS} stdout: 利用可能${NC}"
    else
        echo -e "${YELLOW}${ICON_WARNING} stdout: リダイレクト済み${NC}"
    fi
    
    echo ""
    return 0
}

# 安全なClaude起動
safe_claude_start() {
    local method="$1"
    local role="${2:-default}"
    
    echo -e "${CYAN}${ICON_CLAUDE} Claude起動方法: $method${NC}"
    
    case "$method" in
        "direct")
            echo -e "${CYAN}${ICON_INFO} 直接起動を試行中...${NC}"
            claude 2>/dev/null
            ;;
        "no-permissions")
            echo -e "${CYAN}${ICON_INFO} 権限スキップモードで起動中...${NC}"
            if [ -n "$TMUX" ]; then
                # tmux環境では入力リダイレクション
                echo "" | claude --dangerously-skip-permissions 2>/dev/null
            else
                claude --dangerously-skip-permissions 2>/dev/null
            fi
            ;;
        "shell-wrapper")
            echo -e "${CYAN}${ICON_INFO} シェルラッパーモードで起動中...${NC}"
            bash -c "claude" 2>/dev/null
            ;;
        "interactive-wrapper")
            echo -e "${CYAN}${ICON_INFO} 対話ラッパーモードで起動中...${NC}"
            bash -i -c "claude" 2>/dev/null
            ;;
        "manual")
            echo -e "${CYAN}${ICON_INFO} 手動起動案内${NC}"
            show_manual_instructions "$role"
            return 0
            ;;
        *)
            echo -e "${RED}${ICON_ERROR} 不明な起動方法: $method${NC}"
            return 1
            ;;
    esac
}

# 手動起動案内
show_manual_instructions() {
    local role="$1"
    
    echo -e "${YELLOW}📋 手動Claude起動手順${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "1. 新しいターミナルを開く"
    echo "2. 以下のコマンドを実行:"
    echo -e "   ${GREEN}claude${NC}"
    echo "3. ブラウザで認証を完了"
    echo "4. このペインに戻る"
    echo ""
    
    if [ "$role" != "default" ] && [ -f "$INSTRUCTIONS_DIR/${role}.md" ]; then
        echo -e "${CYAN}${ICON_INFO} $role 用の指示:${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        head -20 "$INSTRUCTIONS_DIR/${role}.md" | sed 's/^/  /'
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${CYAN}${ICON_INFO} 完全な指示は: $INSTRUCTIONS_DIR/${role}.md${NC}"
    fi
    
    read -p "Press Enter when Claude is ready in another terminal..."
}

# Claude起動トラブルシューティング
troubleshoot_claude() {
    local role="${1:-default}"
    
    show_header
    echo -e "${YELLOW}🔧 Claude起動トラブルシューティング${NC}"
    echo ""
    
    # 環境診断
    if ! diagnose_claude_environment; then
        echo ""
        echo -e "${RED}${ICON_ERROR} Claude CLIが見つかりません${NC}"
        echo -e "${CYAN}${ICON_INFO} 以下の手順でインストールしてください:${NC}"
        echo "1. https://claude.ai/download にアクセス"
        echo "2. 適切なバージョンをダウンロード"
        echo "3. インストール完了後、このスクリプトを再実行"
        return 1
    fi
    
    echo ""
    echo -e "${CYAN}${ICON_INFO} 複数の起動方法を順次試行します${NC}"
    echo ""
    
    # 起動方法を順次試行
    local methods=("direct" "no-permissions" "shell-wrapper" "interactive-wrapper" "manual")
    local method_names=("直接起動" "権限スキップ" "シェルラッパー" "対話ラッパー" "手動起動")
    
    for i in "${!methods[@]}"; do
        local method="${methods[$i]}"
        local name="${method_names[$i]}"
        
        echo -e "${CYAN}方法 $((i+1)): $name${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ "$method" = "manual" ]; then
            safe_claude_start "$method" "$role"
            echo -e "${GREEN}${ICON_SUCCESS} 手動起動案内を表示しました${NC}"
            break
        else
            echo -e "${YELLOW}${ICON_INFO} $name を試行中... (Ctrl+C で次の方法へ)${NC}"
            if timeout 10s safe_claude_start "$method" "$role"; then
                echo -e "${GREEN}${ICON_SUCCESS} $name で起動成功${NC}"
                break
            else
                echo -e "${RED}${ICON_ERROR} $name で起動失敗${NC}"
                echo ""
            fi
        fi
    done
}

# メインメニュー
show_main_menu() {
    while true; do
        show_header
        echo -e "${CYAN}=== Claude Fallback Launcher メニュー ===${NC}"
        echo ""
        echo "1. 🔧 Claude起動トラブルシューティング"
        echo "2. 👔 CTO用Claude起動"
        echo "3. 📋 Manager用Claude起動" 
        echo "4. 💻 Developer用Claude起動"
        echo "5. 🩺 Claude環境診断のみ"
        echo "6. 📖 手動起動案内"
        echo "7. ❓ ヘルプ・FAQ"
        echo "q. 終了"
        echo ""
        read -p "選択してください: " choice
        
        case $choice in
            1)
                troubleshoot_claude
                read -p "Press Enter to continue..."
                ;;
            2)
                troubleshoot_claude "ceo"
                read -p "Press Enter to continue..."
                ;;
            3)
                troubleshoot_claude "manager"
                read -p "Press Enter to continue..."
                ;;
            4)
                troubleshoot_claude "developer"
                read -p "Press Enter to continue..."
                ;;
            5)
                diagnose_claude_environment
                read -p "Press Enter to continue..."
                ;;
            6)
                show_manual_instructions "default"
                read -p "Press Enter to continue..."
                ;;
            7)
                show_help_faq
                read -p "Press Enter to continue..."
                ;;
            q|Q)
                echo -e "${GREEN}Exiting Claude Fallback Launcher${NC}"
                break
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# ヘルプ・FAQ
show_help_faq() {
    echo ""
    echo -e "${CYAN}=== Claude起動 ヘルプ・FAQ ===${NC}"
    echo ""
    echo -e "${YELLOW}Q: ${NC}「G.ref is not a function」エラーが出る"
    echo -e "${CYAN}A: ${NC}tmux環境でのraw mode問題です。手動起動または別ターミナルを使用してください。"
    echo ""
    echo -e "${YELLOW}Q: ${NC}Claude CLIが見つからない"
    echo -e "${CYAN}A: ${NC}https://claude.ai/download からインストールしてください。"
    echo ""
    echo -e "${YELLOW}Q: ${NC}tmux内でClaude起動に失敗する"
    echo -e "${CYAN}A: ${NC}tmux外の新しいターミナルでClaude起動してください。"
    echo ""
    echo -e "${YELLOW}Q: ${NC}権限スキップモードとは？"
    echo -e "${CYAN}A: ${NC}--dangerously-skip-permissions オプションで一部の確認をスキップします。"
    echo ""
    echo -e "${YELLOW}Q: ${NC}ロール別指示ファイルはどこにある？"
    echo -e "${CYAN}A: ${NC}$INSTRUCTIONS_DIR/ にあります。"
    echo ""
    echo -e "${CYAN}推奨解決順序:${NC}"
    echo "1. 環境診断実行"
    echo "2. 直接起動試行"
    echo "3. 権限スキップモード試行"
    echo "4. 手動起動案内に従う"
}

# コマンドライン引数処理
main() {
    case "${1:-}" in
        "troubleshoot"|"ts")
            troubleshoot_claude "${2:-default}"
            ;;
        "diagnose"|"diag")
            diagnose_claude_environment
            ;;
        "cto")
            troubleshoot_claude "ceo"
            ;;
        "manager")
            troubleshoot_claude "manager"
            ;;
        "developer"|"dev")
            troubleshoot_claude "developer"
            ;;
        "manual")
            show_manual_instructions "${2:-default}"
            ;;
        "help"|"-h"|"--help")
            echo "Claude Fallback Launcher - Usage:"
            echo "  $0 [menu]           - Open main menu"
            echo "  $0 troubleshoot     - Run troubleshooting"
            echo "  $0 diagnose         - Run environment diagnosis"
            echo "  $0 cto              - Troubleshoot for CTO"
            echo "  $0 manager          - Troubleshoot for Manager"
            echo "  $0 developer        - Troubleshoot for Developer"
            echo "  $0 manual [role]    - Show manual instructions"
            ;;
        *)
            show_main_menu
            ;;
    esac
}

# スクリプト実行
main "$@"