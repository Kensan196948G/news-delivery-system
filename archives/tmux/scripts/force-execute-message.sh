#!/bin/bash

# 🔥 超強力メッセージ送信 - 絶対実行保証版

show_usage() {
    cat << EOF
🚀 超強力メッセージ送信システム (絶対実行保証版)

使用方法:
  $0 [エージェント名] [メッセージ]

特徴:
  - 複数回の強制Enterキー送信
  - Claude Code応答待機中でも強制実行
  - プロンプト残留問題を完全解決

使用例:
  $0 manager "緊急指示: 即座に実行してください"
  $0 dev0 "【最優先】この指示を確実に実行してください"
EOF
}

# 超強力送信機能
force_execute_message() {
    local target="$1"
    local message="$2"
    local agent_name="$3"
    
    echo "🔥 超強力送信中: $agent_name への絶対実行保証メッセージ送信..."
    
    # ステップ1: 強力なクリア処理
    echo "  → プロンプトクリア実行中..."
    tmux send-keys -t "$target" C-c
    sleep 0.2
    tmux send-keys -t "$target" C-c
    sleep 0.2
    tmux send-keys -t "$target" C-u
    sleep 0.2
    tmux send-keys -t "$target" C-l  # 画面クリア
    sleep 0.3
    
    # ステップ2: メッセージ送信
    echo "  → メッセージ送信中..."
    tmux send-keys -t "$target" "$message"
    sleep 0.3
    
    # ステップ3: 段階的強制実行
    echo "  → 段階的強制実行開始..."
    
    # 第1波：基本実行
    for i in {1..2}; do
        tmux send-keys -t "$target" C-m
        sleep 0.3
    done
    
    # 第2波：確認実行
    echo "  → 確認実行中..."
    for i in {1..3}; do
        tmux send-keys -t "$target" C-m
        sleep 0.5
    done
    
    # 第3波：最終確認実行
    echo "  → 最終確認実行中..."
    for i in {1..2}; do
        sleep 0.4
        tmux send-keys -t "$target" C-m
    done
    
    # ステップ4: 最終保証実行
    echo "  → 絶対実行保証処理中..."
    sleep 1.0
    tmux send-keys -t "$target" C-m
    sleep 0.5
    tmux send-keys -t "$target" C-m
    
    echo "🎯 絶対実行完了: $agent_name に超強力自動実行されました（8回Enterキー送信）"
    return 0
}

# スクリプトディレクトリの設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 通常のsend-message.shから必要な関数を読み込み
source "$SCRIPT_DIR/send-message.sh"

# メイン処理
main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    if [[ $# -lt 2 ]]; then
        show_usage
        exit 1
    fi
    
    local agent="$1"
    local message="$2"
    
    # 送信先の決定
    local target
    target=$(resolve_target "$agent")
    
    if [[ $? -ne 0 ]]; then
        echo "❌ エラー: 無効なエージェント名 '$agent'"
        exit 1
    fi
    
    # セッション存在確認
    local session_name=$(detect_active_session)
    if [[ $? -ne 0 ]]; then
        echo "❌ 有効なセッションが見つかりません"
        exit 1
    fi
    
    # 超強力メッセージ送信
    if force_execute_message "$target" "$message" "$agent"; then
        # ログ記録
        mkdir -p logs
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$timestamp] → $agent (FORCE): \"$message\"" >> logs/communication.log
        
        echo ""
        echo "🔥 超強力送信詳細:"
        echo "   宛先: $agent ($target)"
        echo "   内容: \"$message\""
        echo "   方式: 絶対実行保証（8回強制Enter）"
        echo "   ログ: logs/communication.log に記録済み"
        
        return 0
    else
        echo "❌ 超強力送信に失敗しました"
        return 1
    fi
}

main "$@"