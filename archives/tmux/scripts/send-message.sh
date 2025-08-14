#!/bin/bash

# 🤖 AI並列開発チーム - 拡張メッセージ送信システム

# 使用方法表示
show_usage() {
    cat << EOF
🚀 AIチーム メッセージ送信システム (拡張版)

使用方法:
  $0 [エージェント名] [メッセージ]
  $0 --list
  $0 --detect

利用可能エージェント:
  ceo      - 最高経営責任者（全体統括）
  manager  - プロジェクトマネージャー（柔軟なチーム管理）
  dev0-9   - 実行エージェント0-9（柔軟な役割対応）
  broadcast - 全開発エージェントに同時送信

使用例:
  $0 manager "新しいプロジェクトを開始してください"
  $0 dev0 "【フロントエンド担当として】UI開発を実施してください"
  $0 broadcast "全員で進捗状況を報告してください"
  $0 --detect で現在のペイン構成を自動検出
EOF
}

# ペイン番号マッピング読み込み
load_pane_mapping() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local mapping_file="$script_dir/logs/pane_mapping.txt"
    
    if [[ -f "$mapping_file" ]]; then
        source "$mapping_file"
        return 0
    else
        return 1
    fi
}

# セッション名を動的に検出
detect_active_session() {
    # claude-team-で始まるセッションを検索
    local claude_sessions=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "^claude-team-")
    
    if [[ -n "$claude_sessions" ]]; then
        # 複数ある場合は最初の一つを使用
        echo "$claude_sessions" | head -n1
        return 0
    fi
    
    # 従来のteamセッションもチェック
    if tmux has-session -t team 2>/dev/null; then
        echo "team"
        return 0
    fi
    
    return 1
}

# 現在のペイン構成を検出
detect_panes() {
    echo "📋 現在のtmux構成を検出中..."
    
    local session_name=$(detect_active_session)
    if [[ $? -ne 0 || -z "$session_name" ]]; then
        echo "❌ 有効なClaude AI teamセッションが見つかりません"
        echo "💡 利用可能セッション:"
        tmux list-sessions -F "  - #{session_name}" 2>/dev/null || echo "  (セッションが存在しません)"
        return 1
    fi
    
    echo "🎯 検出されたセッション: $session_name"
    
    local pane_count=$(tmux list-panes -t "$session_name" -F "#{pane_index}" | wc -l)
    echo "検出されたペイン数: $pane_count"
    
    # マッピング情報を読み込み
    if load_pane_mapping; then
        echo "📊 レイアウト種別: $LAYOUT_TYPE"
        
        if [[ "$LAYOUT_TYPE" == "hierarchical" ]]; then
            echo "🏗️  階層レイアウト (Developer数: $DEVELOPER_COUNT)"
            echo ""
            echo "📋 利用可能なエージェント:"
            echo "======================="
            echo "  ceo     → $session_name:0.$CEO_PANE (下段)          (最高経営責任者)"
            echo "  manager → $session_name:0.$MANAGER_PANE (中段)          (プロジェクトマネージャー)"
            
            IFS=',' read -ra dev_panes <<< "$DEVELOPER_PANES"
            for i in "${!dev_panes[@]}"; do
                local dev_num=$((i+1))
                echo "  dev$dev_num    → $session_name:0.${dev_panes[$i]} (上段)          (実行エージェント$dev_num)"
            done
            
            echo ""
            echo "特殊コマンド:"
            echo "  broadcast              (dev1-dev$DEVELOPER_COUNT に同時送信)"
            
        else
            echo "📋 従来レイアウト ($LAYOUT_NAME)"
            echo ""
            echo "📋 利用可能なエージェント:"
            echo "======================="
            echo "  ceo     → ceo:0        (最高経営責任者)"
            echo "  manager → $session_name:0.0     (プロジェクトマネージャー)"
            
            for ((i=1; i<pane_count; i++)); do
                echo "  dev$i    → $session_name:0.$i     (実行エージェント$i)"
            done
            
            echo ""
            echo "特殊コマンド:"
            echo "  broadcast              (dev1-dev$((pane_count-1))に同時送信)"
        fi
    else
        echo "⚠️  マッピング情報が見つかりません（従来形式で表示）"
        echo ""
        echo "📋 利用可能なエージェント:"
        echo "======================="
        echo "  manager → $session_name:0.0     (プロジェクトマネージャー)"
        echo "  ceo     → $session_name:0.1     (最高経営責任者)"
        
        local max_dev=0
        for ((i=2; i<pane_count; i++)); do
            local dev_num=$((i-2))
            echo "  dev$dev_num    → $session_name:0.$i     (実行エージェント$dev_num)"
            max_dev=$dev_num
        done
        
        echo ""
        echo "特殊コマンド:"
        echo "  broadcast              (dev0-dev$max_dev に同時送信)"
    fi
}

# エージェント一覧表示（動的）
show_agents() {
    detect_panes
}

# ログ機能
log_message() {
    local agent="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    mkdir -p logs
    echo "[$timestamp] → $agent: \"$message\"" >> logs/communication.log
}

# セッション存在確認
check_session() {
    local session_name="$1"
    if ! tmux has-session -t "$session_name" 2>/dev/null; then
        echo "❌ エラー: セッション '$session_name' が見つかりません"
        echo "先に ./start-ai-team.sh を実行してください"
        return 1
    fi
    return 0
}

# 改良されたペイン存在確認
check_pane_exists() {
    local target="$1"
    local session="${target%:*}"
    local window_pane="${target##*:}"
    local pane="${window_pane##*.}"  # window.pane から pane だけを抽出
    
    # セッション存在確認
    if ! tmux has-session -t "$session" 2>/dev/null; then
        echo "❌ エラー: セッション '$session' が見つかりません"
        return 1
    fi
    
    # ペイン存在確認（より厳密に）
    if ! tmux list-panes -t "$session" 2>/dev/null | grep -q "^${pane}:"; then
        echo "❌ エラー: ペイン '$target' が見つかりません"
        echo "🔍 利用可能ペイン:"
        tmux list-panes -t "$session" -F "  #{pane_index}: #{pane_title}" 2>/dev/null || echo "  (ペイン一覧取得失敗)"
        return 1
    fi
    
    return 0
}

# 後方互換性のため旧関数も残す
check_pane() {
    check_pane_exists "$1"
}

# 改良版メッセージ送信
send_enhanced_message() {
    local target="$1"
    local message="$2"
    local agent_name="$3"
    
    echo "📤 送信中: $agent_name へメッセージを送信..."
    
    # ペイン存在確認
    if ! check_pane "$target"; then
        echo "❌ エラー: ペイン '$target' が見つかりません"
        return 1
    fi
    
    # 1. プロンプトクリア（より確実に）
    tmux send-keys -t "$target" C-c
    sleep 0.4
    
    # 2. 追加のクリア（念のため）
    tmux send-keys -t "$target" C-u
    sleep 0.2
    
    # 3. メッセージ送信（改行を含む場合は複数行で送信）
    # 改行が含まれる場合は行ごとに分けて送信
    if [[ "$message" == *$'\n'* ]]; then
        # 改行で分割して各行を送信
        while IFS= read -r line || [[ -n "$line" ]]; do
            tmux send-keys -t "$target" "$line"
            tmux send-keys -t "$target" C-m
            sleep 0.2
        done <<< "$message"
    else
        # 単一行の場合は従来通り
        tmux send-keys -t "$target" "$message"
        sleep 0.3
        tmux send-keys -t "$target" C-m
    fi
    
    # 4. 確実な実行を保証するための追加Enterキー送信
    sleep 0.5
    tmux send-keys -t "$target" C-m
    sleep 0.3
    
    # 5. さらに確実にするため、もう一度Enterキー送信
    tmux send-keys -t "$target" C-m
    sleep 0.2
    
    # 6. フォーストエンター機能：強制的な実行保証
    for i in {1..3}; do
        sleep 0.4
        tmux send-keys -t "$target" C-m
    done
    
    echo "✅ 送信完了: $agent_name に強制自動実行されました（フォーストエンター適用）"
    return 0
}

# ブロードキャスト送信
broadcast_message() {
    local message="$1"
    
    local session_name=$(detect_active_session)
    if [[ $? -ne 0 || -z "$session_name" ]]; then
        echo "❌ 有効なClaude AI teamセッションが見つかりません"
        return 1
    fi
    
    if ! check_session "$session_name"; then
        return 1
    fi
    
    local success_count=0
    
    echo "📡 ブロードキャスト送信中..."
    
    # マッピング情報を読み込んでブロードキャスト対象を決定
    if load_pane_mapping && [[ "$LAYOUT_TYPE" == "hierarchical" ]]; then
        echo "対象: dev1 から dev$DEVELOPER_COUNT ($DEVELOPER_COUNT エージェント)"
        echo ""
        
        IFS=',' read -ra dev_panes <<< "$DEVELOPER_PANES"
        for i in "${!dev_panes[@]}"; do
            local dev_num=$((i+1))
            local target="$session_name:0.${dev_panes[$i]}"
            local agent_name="dev$dev_num"
            
            if send_enhanced_message "$target" "$message" "$agent_name"; then
                ((success_count++))
                log_message "$agent_name" "$message"
            fi
            
            sleep 0.3  # 送信間隔
        done
        
        echo ""
        echo "🎯 ブロードキャスト完了:"
        echo "   送信成功: $success_count/$DEVELOPER_COUNT エージェント"
    else
        # 従来レイアウトの処理
        local pane_count=$(tmux list-panes -t "$session_name" -F "#{pane_index}" | wc -l)
        local dev_count=$((pane_count-2))  # Manager(0) + CEO(1) を除く
        echo "対象: dev0 から dev$((dev_count-1)) ($dev_count エージェント)"
        echo ""
        
        # manager (ペイン0) + CEO (ペイン1) を除く開発者ペインに送信
        for ((i=2; i<pane_count; i++)); do
            local target="$session_name:0.$i"
            local dev_num=$((i-2))
            local agent_name="dev$dev_num"
            
            if send_enhanced_message "$target" "$message" "$agent_name"; then
                ((success_count++))
                log_message "$agent_name" "$message"
            fi
            
            sleep 0.3  # 送信間隔
        done
        
        echo ""
        echo "🎯 ブロードキャスト完了:"
        echo "   送信成功: $success_count/$dev_count エージェント"
    fi
    
    echo "   メッセージ: \"$message\""
    echo "   ログ: logs/communication.log に記録済み"
}

# エージェント名からターゲットを解決
resolve_target() {
    local agent="$1"
    local session_name=$(detect_active_session)
    
    if [[ $? -ne 0 || -z "$session_name" ]]; then
        return 1
    fi
    
    case $agent in
        "ceo")
            # マッピング情報を読み込んでCEOの場所を確認
            if load_pane_mapping && [[ "$LAYOUT_TYPE" == "hierarchical" ]]; then
                echo "$session_name:0.$CEO_PANE"  # 階層レイアウトでは検出されたセッション内
            else
                echo "$session_name:0.1"  # 現在の構成ではCEOはペイン1
            fi
            return 0
            ;;
        "manager")
            # マッピング情報を読み込んで適切なペインを返す
            if load_pane_mapping && [[ "$LAYOUT_TYPE" == "hierarchical" ]]; then
                echo "$session_name:0.$MANAGER_PANE"
            else
                echo "$session_name:0.0"  # 従来レイアウトではmanagerは常に0
            fi
            return 0
            ;;
        "broadcast")
            echo "broadcast"
            return 0
            ;;
        dev[0-9]|dev1[0-2])  # dev0-dev12 まで対応
            local dev_num="${agent#dev}"
            
            # 階層レイアウトでは動的にペイン番号を解決
            if load_pane_mapping && [[ "$LAYOUT_TYPE" == "hierarchical" ]]; then
                IFS=',' read -ra dev_panes <<< "$DEVELOPER_PANES"
                local dev_index=$dev_num
                
                if [[ $dev_index -ge 0 && $dev_index -lt ${#dev_panes[@]} ]]; then
                    echo "$session_name:0.${dev_panes[$dev_index]}"
                    return 0
                else
                    return 1  # 指定されたDeveloper番号が範囲外
                fi
            else
                # 従来レイアウトではdev0=ペイン2, dev1=ペイン3, ... 
                local pane_num=$((dev_num + 2))
                echo "$session_name:0.$pane_num"
                return 0
            fi
            ;;
        *)
            return 1
            ;;
    esac
}

# メイン処理
main() {
    # 引数チェック
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    # --listオプション
    if [[ "$1" == "--list" ]]; then
        show_agents
        exit 0
    fi
    
    # --detectオプション
    if [[ "$1" == "--detect" ]]; then
        detect_panes
        exit 0
    fi
    
    if [[ $# -lt 2 ]]; then
        show_usage
        exit 1
    fi
    
    local agent="$1"
    local message="$2"
    
    # ブロードキャスト処理
    if [[ "$agent" == "broadcast" ]]; then
        broadcast_message "$message"
        return $?
    fi
    
    # 送信先の決定
    local target
    target=$(resolve_target "$agent")
    
    if [[ $? -ne 0 ]]; then
        echo "❌ エラー: 無効なエージェント名 '$agent'"
        echo "利用可能エージェント: $0 --list"
        exit 1
    fi
    
    # セッション存在確認
    local session
    if [[ "$agent" == "ceo" ]]; then
        # CEOの場所を確認
        if load_pane_mapping && [[ "$LAYOUT_TYPE" == "hierarchical" ]]; then
            session=$(detect_active_session)  # 階層レイアウトでは検出されたセッション
        else
            session=$(detect_active_session)   # 現在の構成では同じセッション内
        fi
    else
        session=$(detect_active_session)
    fi
    
    if ! check_session "$session"; then
        exit 1
    fi
    
    # メッセージ送信
    if send_enhanced_message "$target" "$message" "$agent"; then
        # ログ記録
        log_message "$agent" "$message"
        
        echo ""
        echo "🎯 メッセージ詳細:"
        echo "   宛先: $agent ($target)"
        echo "   内容: \"$message\""
        echo "   ログ: logs/communication.log に記録済み"
        
        return 0
    else
        echo "❌ メッセージ送信に失敗しました"
        return 1
    fi
}

main "$@"