#!/bin/bash

set -euo pipefail  # エラー時即座に終了

# スクリプトのベースディレクトリ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTRUCTIONS_DIR="$BASE_DIR/tmux/instructions"
SESSION="claude-team-2devs"

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

# セッション初期化
tmux kill-session -t $SESSION 2>/dev/null || true

log_info "2 Developers構成作成（新仕様・認証高速化版）"
echo "================================"
echo "仕様: 左側CEO/Manager固定、右側2Dev均等分割"

echo "ステップ1: 新しいセッションを作成"
tmux new-session -d -s $SESSION

echo "ステップ2: まず左右に分割（縦線）"
# 左右分割 - これで0（左）、1（右）になる
tmux split-window -h -t $SESSION:0.0
echo "分割後: 0（左）、1（右）"

echo "ステップ3: 左側を上下に分割（横線）"
# 左側（ペイン0）を上下分割 - 0（上）、1（下）になり、元の1は2になる
tmux split-window -v -t $SESSION:0.0
echo "分割後: 0（左上・Manager）、1（左下・CEO）、2（右全体）"

echo "ステップ4: 右側を1回分割して2つのペインにする"
echo "現在の構成: 0（左上）、1（左下）、2（右全体）"

# 右側（現在のペイン2）を上下分割
tmux split-window -v -t $SESSION:0.2
echo "分割1: 0（左上）、1（左下）、2（右上・Dev0）、3（右下・Dev1）"

echo "ステップ5: サイズ調整"
# 左右のバランス調整（左40%、右60%）
tmux resize-pane -t $SESSION:0.0 -x 40%

# 右側の2つのペインを完全に均等にする
echo "右側Developer領域を均等化中..."
sleep 1

# 右側全体の高さを取得して2等分
WINDOW_HEIGHT=$(tmux display-message -t $SESSION -p '#{window_height}')
DEV_HEIGHT=$((WINDOW_HEIGHT / 2))

echo "ウィンドウ総高さ: $WINDOW_HEIGHT, 各Devペイン目標高さ: $DEV_HEIGHT"

# 各Developerペインを絶対値で均等に設定
tmux resize-pane -t $SESSION:0.2 -y $DEV_HEIGHT
tmux resize-pane -t $SESSION:0.3 -y $DEV_HEIGHT

# 微調整：最終均等化（絶対値で再調整）
FINAL_HEIGHT=$((WINDOW_HEIGHT / 2))
tmux resize-pane -t $SESSION:0.2 -y $FINAL_HEIGHT
tmux resize-pane -t $SESSION:0.3 -y $FINAL_HEIGHT

echo "ステップ6: 各ペインの確認とタイトル設定"
echo "現在のペイン構成:"
tmux list-panes -t $SESSION -F "ペイン#{pane_index}: (#{pane_width}x#{pane_height})"

# 各ペインにタイトルと確認メッセージを設定
tmux send-keys -t $SESSION:0.0 'clear; echo "👔 Manager（ペイン0・左上）"; echo "構成確認: 左上の管理者ペイン"' C-m
tmux send-keys -t $SESSION:0.1 'clear; echo "👑 CEO（ペイン1・左下）"; echo "構成確認: 左下のCEOペイン"' C-m
tmux send-keys -t $SESSION:0.2 'clear; echo "💻 Dev0（ペイン2・右上）"; echo "構成確認: 右側上部の開発者"' C-m
tmux send-keys -t $SESSION:0.3 'clear; echo "💻 Dev1（ペイン3・右下）"; echo "構成確認: 右側下部の開発者"' C-m

# ペイン数の検証
PANE_COUNT=$(tmux list-panes -t $SESSION | wc -l)
echo ""
echo "🔍 ペイン数検証: $PANE_COUNT/4"

if [ "$PANE_COUNT" -eq 4 ]; then
    log_success "全ペインが正常に作成されました"
    
    echo ""
    echo "⏳ 3秒後にClaudeエージェントを起動します..."
    sleep 3
    
    # Claudeエージェント起動
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    INSTRUCTIONS_DIR="$BASE_DIR/tmux/instructions"
    
    echo "📂 指示ファイルディレクトリ: $INSTRUCTIONS_DIR"
    echo "📄 ファイル確認:"
    ls -la "$INSTRUCTIONS_DIR"/ 2>/dev/null || echo "⚠️ ディレクトリが見つかりません: $INSTRUCTIONS_DIR"
    
    # Claude認証統一設定を各ペインに適用
    echo "🔧 Claude認証統一設定を全ペインに適用中..."
    
    # tmux環境変数設定（全ペインで認証統一）
    tmux set-environment -g CLAUDE_CODE_CONFIG_PATH "$HOME/.local/share/claude"
    tmux set-environment -g CLAUDE_CODE_CACHE_PATH "$HOME/.cache/claude" 
    tmux set-environment -g CLAUDE_CODE_AUTO_START "true"
    
    if [ -f "$INSTRUCTIONS_DIR/manager.md" ]; then
        # 各ペインで環境変数を設定してからClaude起動（認証高速化付き）
        echo "🚀 Claudeエージェント高速起動中..."
        
        # 並列でClaude起動（認証時間短縮）
        tmux send-keys -t $SESSION:0.0 "export CLAUDE_CODE_CONFIG_PATH='$HOME/.local/share/claude' && export CLAUDE_CODE_CACHE_PATH='$HOME/.cache/claude' && claude --continue --dangerously-skip-permissions --model opus '$INSTRUCTIONS_DIR/manager.md'" C-m &
        tmux send-keys -t $SESSION:0.1 "export CLAUDE_CODE_CONFIG_PATH='$HOME/.local/share/claude' && export CLAUDE_CODE_CACHE_PATH='$HOME/.cache/claude' && claude --continue --dangerously-skip-permissions --model opus '$INSTRUCTIONS_DIR/ceo.md'" C-m &
        tmux send-keys -t $SESSION:0.2 "export CLAUDE_CODE_CONFIG_PATH='$HOME/.local/share/claude' && export CLAUDE_CODE_CACHE_PATH='$HOME/.cache/claude' && claude --continue --dangerously-skip-permissions --model sonnet '$INSTRUCTIONS_DIR/developer.md'" C-m &
        tmux send-keys -t $SESSION:0.3 "export CLAUDE_CODE_CONFIG_PATH='$HOME/.local/share/claude' && export CLAUDE_CODE_CACHE_PATH='$HOME/.cache/claude' && claude --continue --dangerously-skip-permissions --model sonnet '$INSTRUCTIONS_DIR/developer.md'" C-m &
        
        # 並列処理完了を待機
        wait
        
        echo "✅ Claude高速起動完了（認証時間短縮）"
        
        # 全ペインで「Bypassing Permissions」が表示されるまで待機
        echo "⏳ 認証完了確認中（自動監視）..."
        
        # 並列で全ペインの認証完了を監視
        "$SCRIPT_DIR/wait-for-bypassing-permissions.sh" "$SESSION" "0" 15 &
        "$SCRIPT_DIR/wait-for-bypassing-permissions.sh" "$SESSION" "1" 15 &
        "$SCRIPT_DIR/wait-for-bypassing-permissions.sh" "$SESSION" "2" 15 &
        "$SCRIPT_DIR/wait-for-bypassing-permissions.sh" "$SESSION" "3" 15 &
        
        # 全ペインの認証完了を待機
        wait
        
        log_success "全ペイン認証完了！「Bypassing Permissions」表示確認済み"
    else
        echo "⚠️ Claudeエージェント指示ファイルが見つかりません"
        echo "各ペインでmanual setupが必要です"
    fi

    # ペインタイトルを設定
    echo "🏷️ ペインタイトル設定中..."
    sleep 1
    tmux select-pane -t $SESSION:0.0 -T "👔 Manager"
    tmux select-pane -t $SESSION:0.1 -T "👑 CEO"
    tmux select-pane -t $SESSION:0.2 -T "💻 Dev0"
    tmux select-pane -t $SESSION:0.3 -T "💻 Dev1"
    
    echo ""
    echo "✅ 2 Developers構成起動完了！"
else
    log_error "ペイン作成に失敗しました（$PANE_COUNT/4）"
fi

echo ""
echo "📊 最終ペイン構成:"
tmux list-panes -t $SESSION -F "ペイン#{pane_index}: #{pane_title} (#{pane_width}x#{pane_height})"

echo ""
echo "📐 実現した構成図:"
echo "┌─────────┬─────────┐"
echo "│         │         │"
echo "│👔Manager│ 💻 Dev0 │ ← ペイン2"
echo "│(ペイン0)│         │"
echo "├─────────┼─────────┤"
echo "│         │         │"
echo "│👑 CEO   │ 💻 Dev1 │ ← ペイン3"
echo "│(ペイン1)│         │"
echo "└─────────┴─────────┘"

echo ""
echo "🎯 分割手順の詳細:"
echo "1. 初期ペイン0を左右分割 → 0（左）、1（右）"
echo "2. ペイン0を上下分割 → 0（左上）、1（左下）、2（右）"
echo "3. ペイン2を上下分割 → 0（左上）、1（左下）、2（右上）、3（右下）"

echo ""
echo "📋 最終ペイン配置:"
echo "- ペイン0: 👔 Manager（左上）"
echo "- ペイン1: 👑 CEO（左下）"
echo "- ペイン2: 💻 Dev0（右上）"
echo "- ペイン3: 💻 Dev1（右下）"

echo ""
echo "🚀 接続コマンド: tmux attach-session -t $SESSION"
echo ""
echo "💡 操作のヒント:"
echo "- ペイン切り替え: Ctrl+b → 矢印キー"
echo "- ペインサイズ調整: Ctrl+b → Ctrl+矢印キー"
echo "- セッション切断: Ctrl+b → d"
echo "- セッション終了: exit（各ペインで）またはtmux kill-session -t $SESSION"

# セッションにアタッチ
echo ""
read -p "セッションに接続しますか？ (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    tmux attach-session -t $SESSION
else
    echo ""
    echo "手動接続: tmux attach-session -t $SESSION"
fi