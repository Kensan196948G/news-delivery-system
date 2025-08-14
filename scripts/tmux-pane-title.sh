#!/bin/bash
# News Delivery System - tmux ペインタイトル自動設定スクリプト
# 各ペインに適切なアイコンと役割名を設定

# セッション名を取得
SESSION_NAME=$(tmux display-message -p '#S')

# news-mainセッションでない場合は何もしない
if [[ "$SESSION_NAME" != "news-main" ]]; then
    exit 0
fi

# 現在のウィンドウの全ペインを取得
WINDOW_ID=$(tmux display-message -p '#I')
PANES=$(tmux list-panes -t "$SESSION_NAME:$WINDOW_ID" -F '#{pane_index}')

# 各ペインにタイトルを設定
for pane in $PANES; do
    case $pane in
        0)
            tmux select-pane -t "$SESSION_NAME:$WINDOW_ID.$pane" -T "🖥️ システム監視"
            ;;
        1)
            tmux select-pane -t "$SESSION_NAME:$WINDOW_ID.$pane" -T "🔧 手動実行"
            ;;
        2)
            tmux select-pane -t "$SESSION_NAME:$WINDOW_ID.$pane" -T "⏰ スケジューラー"
            ;;
        3)
            tmux select-pane -t "$SESSION_NAME:$WINDOW_ID.$pane" -T "⚙️ 設定編集"
            ;;
        4)
            tmux select-pane -t "$SESSION_NAME:$WINDOW_ID.$pane" -T "🤖 Claude指示用"
            ;;
        *)
            tmux select-pane -t "$SESSION_NAME:$WINDOW_ID.$pane" -T "📋 その他"
            ;;
    esac
done