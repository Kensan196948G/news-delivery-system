#!/bin/bash
# News Delivery System - シンプルtmux環境セットアップ
# 確実に動作するシンプルなレイアウト作成

set -e

# 設定
SESSION_NAME="news-main"
BASE_DIR="/mnt/e/news-delivery-system"
CLAUDE_CMD="/home/kensa/.nvm/versions/node/v22.16.0/bin/claude-yolo"

# 色付きメッセージ関数
print_info() {
    echo -e "\033[0;32m[INFO]\033[0m $1"
}

print_warning() {
    echo -e "\033[0;33m[WARNING]\033[0m $1"
}

# 既存セッション削除
cleanup_existing_session() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        print_warning "既存のセッション '$SESSION_NAME' を終了中..."
        tmux kill-session -t "$SESSION_NAME"
        sleep 1
    fi
}

# tmux設定適用
apply_tmux_config() {
    local tmux_conf="$BASE_DIR/.tmux.conf"
    
    if [[ -f "$tmux_conf" ]]; then
        print_info "tmux設定ファイルを適用中..."
        
        # ホームディレクトリにシンボリックリンクを作成
        if [[ -L "$HOME/.tmux.conf" ]] || [[ -f "$HOME/.tmux.conf" ]]; then
            print_warning "既存の ~/.tmux.conf をバックアップ中..."
            mv "$HOME/.tmux.conf" "$HOME/.tmux.conf.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
        fi
        
        ln -sf "$tmux_conf" "$HOME/.tmux.conf"
        print_info "tmux設定適用完了"
    fi
}

# メインセッション作成
create_session() {
    print_info "News Delivery System セッションを作成中..."
    
    cd "$BASE_DIR"
    
    # セッション作成（基本ウィンドウ）
    tmux new-session -d -s "$SESSION_NAME" -c "$BASE_DIR"
    
    # パターンAレイアウト：5ペイン分割
    print_info "5ペイン分割を実行中..."
    
    # 最下段にClaude指示用ペインを作成（8行の高さ）
    tmux split-window -v -l 8 -c "$BASE_DIR"
    print_info "ステップ1完了: 縦分割"
    
    # 上の部分を左右に分割
    tmux select-pane -t 0
    tmux split-window -h -c "$BASE_DIR"
    print_info "ステップ2完了: 横分割"
    
    # 左を上下に分割
    tmux select-pane -t 0
    tmux split-window -v -c "$BASE_DIR"
    print_info "ステップ3完了: 左側分割"
    
    # 右を上下に分割
    tmux select-pane -t 2
    tmux split-window -v -c "$BASE_DIR"
    print_info "ステップ4完了: 右側分割"
    
    print_info "5ペイン分割完了"
}

# ペインタイトル設定
setup_titles() {
    print_info "ペインタイトルを設定中..."
    
    tmux select-pane -t 0 -T "🖥️ システム監視"
    tmux select-pane -t 1 -T "🔧 手動実行"
    tmux select-pane -t 2 -T "⏰ スケジューラー"
    tmux select-pane -t 3 -T "⚙️ 設定編集"
    tmux select-pane -t 4 -T "🤖 Claude指示用"
    
    print_info "タイトル設定完了"
}

# 初期メッセージ送信
setup_messages() {
    print_info "初期メッセージを設定中..."
    
    # 各ペインに役割を明示
    tmux send-keys -t 0 "clear && echo 'ペイン0: 🖥️ システム監視'" C-m
    tmux send-keys -t 1 "clear && echo 'ペイン1: 🔧 手動実行'" C-m
    tmux send-keys -t 2 "clear && echo 'ペイン2: ⏰ スケジューラー'" C-m
    tmux send-keys -t 3 "clear && echo 'ペイン3: ⚙️ 設定編集'" C-m
    tmux send-keys -t 4 "clear && echo 'ペイン4: 🤖 Claude指示用（最下段・全幅）'" C-m
    
    print_info "初期メッセージ設定完了"
}

# Claude Yolo起動（別の関数として分離）
start_claude_in_all_panes() {
    print_info "全ペインでClaude Yolo起動中..."
    
    # 少し待機
    sleep 2
    
    # 各ペインで個別にClaude Yolo起動（インタラクティブモード）
    for pane in 0 1 2 3 4; do
        print_info "ペイン$pane でClaude Yolo起動..."
        tmux send-keys -t $pane "echo 'Claude Yolo起動中...'" C-m
        tmux send-keys -t $pane "$CLAUDE_CMD" C-m
        sleep 0.5
    done
    
    print_info "Claude Yolo起動完了"
}

# セッション情報表示
show_info() {
    print_info "セッション情報:"
    echo "  セッション名: $SESSION_NAME"
    echo "  ベースディレクトリ: $BASE_DIR"
    echo ""
    echo "ペイン構成 (パターンA):"
    echo "  ┌─────────────────┬─────────────────┐"
    echo "  │ 0: 🖥️ システム監視 │ 2: ⏰ スケジューラー │"
    echo "  ├─────────────────┼─────────────────┤"
    echo "  │ 1: 🔧 手動実行    │ 3: ⚙️ 設定編集     │"
    echo "  ├─────────────────┴─────────────────┤"
    echo "  │ 4: 🤖 Claude指示用 (メイン)       │"
    echo "  └───────────────────────────────────┘"
    echo ""
    echo "接続方法:"
    echo "  tmux attach -t $SESSION_NAME"
    echo ""
    echo "指示コマンド例:"
    echo "  $BASE_DIR/scripts/tmux-pane-commander.sh help"
}

# メイン実行
main() {
    echo "================================================"
    echo "News Delivery System - シンプルtmux環境セットアップ"
    echo "================================================"
    echo ""
    
    cleanup_existing_session
    apply_tmux_config
    create_session
    setup_titles
    setup_messages
    start_claude_in_all_panes
    
    # Claude指示用ペインをアクティブに
    tmux select-pane -t 4
    
    echo ""
    show_info
    
    print_info "tmuxセットアップが完了しました！"
    echo ""
    echo "次のコマンドでセッションに接続してください:"
    echo "  tmux attach -t $SESSION_NAME"
}

# スクリプト実行
main "$@"