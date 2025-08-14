#!/bin/bash
# Claude Monitor Log Suppression Script
# Claudeモニターログ抑制スクリプト

# Hook handler が存在するか確認
HOOK_HANDLER_PATH="/home/kensan/claude-monitor/bin/claude-hook-handler.sh"

if [ -f "$HOOK_HANDLER_PATH" ]; then
    echo "Patching claude-hook-handler.sh to suppress repetitive messages..."
    
    # バックアップ作成
    cp "$HOOK_HANDLER_PATH" "$HOOK_HANDLER_PATH.backup.$(date +%Y%m%d_%H%M%S)"
    
    # 成功メッセージを抑制するパッチを適用
    sed -i 's/echo "Stop.*completed successfully"/# &/g' "$HOOK_HANDLER_PATH"
    sed -i 's/echo ".*completed successfully"/# &/g' "$HOOK_HANDLER_PATH"
    
    # 重複防止のフラグファイルチェックを追加
    sed -i '/completed successfully/i\
    # Check if already processed to avoid duplicates\
    FLAG_FILE="/tmp/claude-hook-$(basename $0)-$$"\
    if [ -f "$FLAG_FILE" ]; then\
        exit 0\
    fi\
    touch "$FLAG_FILE"' "$HOOK_HANDLER_PATH"
    
    echo "✅ Patching completed"
else
    echo "⚠️  Hook handler not found at $HOOK_HANDLER_PATH"
fi

# Claude Flow hooks を無効化/静穏化
if command -v npx >/dev/null 2>&1; then
    echo "Setting claude-flow to quiet mode..."
    
    # Claude Flow の静穏モードを設定
    export CLAUDE_FLOW_QUIET=true
    export CLAUDE_FLOW_LOG_LEVEL=error
    export CLAUDE_HOOKS_SILENT=true
    
    # 環境変数を永続化
    echo "export CLAUDE_FLOW_QUIET=true" >> ~/.bashrc
    echo "export CLAUDE_FLOW_LOG_LEVEL=error" >> ~/.bashrc
    echo "export CLAUDE_HOOKS_SILENT=true" >> ~/.bashrc
    
    echo "✅ Claude Flow quiet mode enabled"
fi

# プロセス重複チェック
RUNNING_HANDLERS=$(pgrep -f claude-hook-handler | wc -l)
if [ "$RUNNING_HANDLERS" -gt 1 ]; then
    echo "⚠️  Multiple claude-hook-handlers detected ($RUNNING_HANDLERS), terminating duplicates..."
    
    # 最新以外のプロセスを終了
    pgrep -f claude-hook-handler | head -n -1 | xargs -r kill 2>/dev/null
    
    echo "✅ Duplicate handlers terminated"
fi

echo "🎉 Claude monitor log suppression completed"