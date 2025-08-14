#!/bin/bash

set -euo pipefail  # エラー時即座に終了

# tmux AI並列開発システム - 統合ランチャー
# テンプレートベストプラクティス適用版

# スクリプトの場所を取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTRUCTIONS_DIR="$BASE_DIR/tmux/instructions"

# ログ関数
log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1" >&2
}

log_warning() {
    echo "⚠️  $1"
}

# Claude認証統一設定
setup_claude_auth() {
    log_info "Claude認証統一設定を適用中..."
    
    # tmux環境変数設定
    tmux set-environment -g CLAUDE_CODE_CONFIG_PATH "$HOME/.local/share/claude" 2>/dev/null || true
    tmux set-environment -g CLAUDE_CODE_CACHE_PATH "$HOME/.cache/claude" 2>/dev/null || true
    tmux set-environment -g CLAUDE_CODE_AUTO_START "true" 2>/dev/null || true
    
    # bash環境変数設定
    export CLAUDE_CODE_CONFIG_PATH="$HOME/.local/share/claude"
    export CLAUDE_CODE_CACHE_PATH="$HOME/.cache/claude"
    export CLAUDE_CODE_AUTO_START="true"
    
    log_success "Claude認証統一設定完了"
}

# 前提条件チェック
check_prerequisites() {
    log_info "前提条件をチェック中..."
    
    # tmuxがインストールされているか
    if ! command -v tmux &> /dev/null; then
        log_error "tmuxがインストールされていません"
        exit 1
    fi
    
    # claudeがインストールされているか
    if ! command -v claude &> /dev/null; then
        log_error "claudeがインストールされていません"
        exit 1
    fi
    
    # Claude認証統一設定を適用
    setup_claude_auth
    
    # 指示ファイルディレクトリが存在するか
    if [ ! -d "$INSTRUCTIONS_DIR" ]; then
        log_warning "指示ファイルディレクトリが見つかりません: $INSTRUCTIONS_DIR"
        log_info "マニュアルセットアップが必要になります"
    fi
    
    # 実行可能かチェック
    for script in "$SCRIPT_DIR"/setup_*.sh; do
        if [ -f "$script" ] && [ ! -x "$script" ]; then
            log_info "実行権限を設定中: $(basename "$script")"
            chmod +x "$script"
        fi
    done
    
    log_success "前提条件チェック完了"
}

# セッション終了確認
cleanup_sessions() {
    log_info "既存のセッションをチェック中..."
    
    local sessions=$(tmux list-sessions 2>/dev/null | grep -E "claude-team-" | cut -d: -f1 || true)
    
    if [ -n "$sessions" ]; then
        log_warning "既存のClaudeセッションが見つかりました:"
        echo "$sessions"
        echo ""
        read -p "既存セッションを終了しますか？ (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$sessions" | while read -r session; do
                tmux kill-session -t "$session" 2>/dev/null || true
                log_info "セッション終了: $session"
            done
        fi
    fi
}

# スクリプト実行
run_script() {
    local script_path="$1"
    local script_name=$(basename "$script_path")
    
    if [ ! -f "$script_path" ]; then
        log_error "スクリプトが見つかりません: $script_name"
        return 1
    fi
    
    if [ ! -x "$script_path" ]; then
        log_error "スクリプトに実行権限がありません: $script_name"
        return 1
    fi
    
    log_info "$script_name を実行中..."
    
    # スクリプト実行（エラーハンドリング付き）
    if ! "$script_path"; then
        log_error "$script_name の実行中にエラーが発生しました"
        return 1
    fi
    
    log_success "$script_name の実行が完了しました"
}

# メイン表示関数
show_menu() {
    clear
    echo "🚀 Claude AI チーム開発システム v4.0"
    echo "======================================"
    echo ""
    echo "👥 開発チーム構成 (--dangerously-skip-permissions対応):"
    echo "1) 2 Developers  - 小規模開発 (Manager + CEO + Dev0-1)"
    echo "2) 4 Developers  - 中規模開発 (Manager + CEO + Dev0-3)"  
    echo "3) 6 Developers  - 大規模開発 (Manager + CEO + Dev0-5) 🌟推奨"
    echo ""
    echo "⚡ 高速認証機能:"
    echo "• --continue オプションで認証時間短縮"
    echo "• 並列Claude起動で効率化"
    echo "• 自動認証監視システム"
    echo ""
    echo "🛠️  管理・設定:"
    echo "4) 現在のセッション確認・接続"
    echo "5) 既存セッション確認・終了"
    echo ""
    echo "📊 システム仕様:"
    echo "   • 左側: Manager(上) + CEO(下) 固定"
    echo "   • 右側: Dev0-Dev5 均等分割"
    echo "   • Claude AI 自動起動・認証高速化"
    echo "   • Bypassing Permissions 自動監視"
    echo ""
    echo "0) 終了"
    echo ""
}

# 現在のセッション確認・接続
show_current_sessions() {
    log_info "現在のtmuxセッションを確認中..."
    
    local sessions=$(tmux list-sessions 2>/dev/null | grep -E "claude-team-" | cut -d: -f1 || true)
    
    if [ -n "$sessions" ]; then
        log_success "アクティブなClaudeセッションが見つかりました:"
        echo "$sessions" | while read -r session; do
            local pane_count=$(tmux list-panes -t "$session" 2>/dev/null | wc -l)
            echo "  📊 $session (ペイン数: $pane_count)"
        done
        echo ""
        
        # 最初のセッションに接続するか確認
        local first_session=$(echo "$sessions" | head -n1)
        read -p "セッション '$first_session' に接続しますか？ (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "セッション '$first_session' に接続中..."
            tmux attach-session -t "$first_session"
        fi
    else
        log_warning "アクティブなClaudeセッションが見つかりません"
        log_info "新しいセッションを作成するには、メニューから選択してください"
    fi
}

# メイン処理
main() {
    # 前提条件チェック
    check_prerequisites
    
    while true; do
        show_menu
        read -p "選択してください (0-5): " choice
        echo ""
        
        case $choice in
            1)
                log_info "2 Developers構成を起動します（認証高速化版）"
                cleanup_sessions
                run_script "$SCRIPT_DIR/setup_2devs_new.sh"
                ;;
            2)
                log_info "4 Developers構成を起動します（認証高速化版）"
                cleanup_sessions
                run_script "$SCRIPT_DIR/setup_4devs_new.sh"
                ;;
            3)
                log_info "6 Developers構成を起動します（認証高速化版）"
                cleanup_sessions
                run_script "$SCRIPT_DIR/setup_6devs_new.sh"
                ;;
            4)
                log_info "現在のセッション確認・接続"
                show_current_sessions
                ;;
            5)
                cleanup_sessions
                echo ""
                read -p "メニューに戻りますか？ (y/n): " -n 1 -r
                echo ""
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    break
                fi
                ;;
            0)
                log_info "システムを終了します"
                exit 0
                ;;
            *)
                log_error "無効な選択です: $choice"
                sleep 2
                ;;
        esac
        
        if [ "$choice" != "5" ] && [ "$choice" != "0" ] && [ "$choice" != "4" ]; then
            echo ""
            read -p "メニューに戻りますか？ (y/n): " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                break
            fi
        fi
    done
}

# エラートラップ
trap 'log_error "予期しないエラーが発生しました (行: $LINENO)"' ERR

# メイン実行
main "$@"