#!/bin/bash
# Claude Yolo確実起動スクリプト（インタラクティブモード専用）

SESSION_NAME="news-main"
CLAUDE_CMD="/home/kensa/.nvm/versions/node/v22.16.0/bin/claude-yolo"

echo "🚀 Claude Yolo確実起動中（インタラクティブモード）..."

# 各ペインでClaude Yoloを確実に起動
for pane in 0 1 2 3 4; do
    echo "ペイン$pane でClaude Yolo起動..."
    
    # 既存プロセスを終了
    tmux send-keys -t $SESSION_NAME.$pane C-c 2>/dev/null || true
    sleep 0.3
    
    # クリア
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
    
    sleep 0.3
    
    # Claude Yolo起動（インタラクティブモード）
    tmux send-keys -t $SESSION_NAME.$pane "$CLAUDE_CMD" Enter
    sleep 0.8
done

echo "✅ Claude Yolo起動完了"
echo ""
echo "📱 使用方法:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "各ペインでClaude Yoloが正しく起動していることを確認してください。"
echo "エラーが発生した場合は、手動で以下を実行："
echo "  $CLAUDE_CMD"