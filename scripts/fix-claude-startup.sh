#!/bin/bash
# Claude Yolo起動修正スクリプト

SESSION_NAME="news-main"
CLAUDE_CMD="/home/kensa/.nvm/versions/node/v22.16.0/bin/claude-yolo"

echo "🚀 Claude Yolo起動を修正中..."

# 確実な起動方法：各ペインを個別に処理
for pane in 0 1 2 3 4; do
    echo "ペイン$pane でClaude Yolo起動中..."
    
    # まずCtrl+Cで既存プロセスを終了
    tmux send-keys -t $SESSION_NAME.$pane C-c 2>/dev/null || true
    sleep 0.5
    
    # クリアして起動
    tmux send-keys -t $SESSION_NAME.$pane "clear" Enter
    sleep 0.2
    
    # ペイン情報表示
    case $pane in
        0) tmux send-keys -t $SESSION_NAME.$pane "echo 'ペイン0: 🖥️ システム監視 - Claude Yolo起動中...'" Enter ;;
        1) tmux send-keys -t $SESSION_NAME.$pane "echo 'ペイン1: 🔧 手動実行 - Claude Yolo起動中...'" Enter ;;
        2) tmux send-keys -t $SESSION_NAME.$pane "echo 'ペイン2: ⏰ スケジューラー - Claude Yolo起動中...'" Enter ;;
        3) tmux send-keys -t $SESSION_NAME.$pane "echo 'ペイン3: ⚙️ 設定編集 - Claude Yolo起動中...'" Enter ;;
        4) tmux send-keys -t $SESSION_NAME.$pane "echo 'ペイン4: 🤖 Claude指示用 - Claude Yolo起動中...'" Enter ;;
    esac
    
    sleep 0.5
    
    # Claude Yolo起動（インタラクティブモード）
    tmux send-keys -t $SESSION_NAME.$pane "$CLAUDE_CMD" Enter
    sleep 1
done

echo "✅ Claude Yolo起動修正完了"
echo ""
echo "確認コマンド:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "各ペインでClaude Yoloが起動しているか確認してください。"