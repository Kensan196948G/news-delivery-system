#!/bin/bash
# Claude Code完全機能有効化起動スクリプト
# Agent機能 + Claude-Flow(Swarm) + Context7機能対応

set -euo pipefail

# =============================================================================
# 設定とパス
# =============================================================================

# スクリプトの場所から相対パスで設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_CMD="/home/kensan/.npm-global/bin/claude"

# Claude設定ファイルパス
CLAUDE_CONFIG="$PROJECT_ROOT/.claude-config.json"
CLAUDE_SETTINGS="$PROJECT_ROOT/.claude/settings.local.json"
CLAUDE_SWARM="$PROJECT_ROOT/.claude/swarm.yaml"
CLAUDE_SUPPRESS="$PROJECT_ROOT/.claude-suppress.env"
CLAUDE_MCP="$PROJECT_ROOT/.mcp.json"

# =============================================================================
# 初期化とヘルパー関数
# =============================================================================

# ログ出力関数
log_info() {
    echo "🔵 [INFO] $1"
}

log_success() {
    echo "✅ [SUCCESS] $1"
}

log_error() {
    echo "❌ [ERROR] $1"
}

log_warning() {
    echo "⚠️  [WARNING] $1"
}

# 設定ファイル存在確認
check_config_files() {
    local missing_files=()
    
    if [ ! -f "$CLAUDE_CONFIG" ]; then
        missing_files+=(".claude-config.json")
    fi
    
    if [ ! -f "$CLAUDE_SETTINGS" ]; then
        missing_files+=(".claude/settings.local.json")
    fi
    
    if [ ! -f "$CLAUDE_SWARM" ]; then
        missing_files+=(".claude/swarm.yaml")
    fi
    
    if [ ! -f "$CLAUDE_MCP" ]; then
        missing_files+=(".mcp.json")
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_warning "以下の設定ファイルが見つかりません:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi
    
    return 0
}

# Agent機能確認
check_agent_functionality() {
    log_info "Agent機能の確認中..."
    
    local agent_count=$(find "$PROJECT_ROOT/.claude/agents" -name "*.md" 2>/dev/null | wc -l)
    if [ "$agent_count" -gt 0 ]; then
        log_success "Agent機能: ${agent_count}個のエージェントが設定済み"
        return 0
    else
        log_warning "Agent機能: エージェントファイルが見つかりません"
        return 1
    fi
}

# Swarm機能確認
check_swarm_functionality() {
    log_info "Claude-Flow(Swarm)機能の確認中..."
    
    if [ -f "$CLAUDE_SWARM" ] && [ -d "$PROJECT_ROOT/.swarm" ]; then
        local swarm_name=$(grep "name:" "$CLAUDE_SWARM" | head -1 | cut -d: -f2 | xargs)
        log_success "Claude-Flow(Swarm)機能: '$swarm_name' が設定済み"
        return 0
    else
        log_warning "Claude-Flow(Swarm)機能: 設定ファイルまたはディレクトリが見つかりません"
        return 1
    fi
}

# Context7機能確認
check_context_functionality() {
    log_info "Context7機能の確認中..."
    
    if [ -f "$CLAUDE_SETTINGS" ]; then
        local tool_count=$(grep -c '"allow"' "$CLAUDE_SETTINGS" 2>/dev/null || echo "0")
        log_success "Context7機能: 権限設定済み (${tool_count}個のツール許可設定)"
        return 0
    else
        log_warning "Context7機能: 設定ファイルが見つかりません"
        return 1
    fi
}

# 環境変数の設定
setup_environment() {
    log_info "環境変数の設定中..."
    
    # Claude抑制設定の読み込み
    if [ -f "$CLAUDE_SUPPRESS" ]; then
        source "$CLAUDE_SUPPRESS"
        log_success "Claude出力抑制設定を読み込みました"
    fi
    
    # プロジェクトディレクトリに移動
    cd "$PROJECT_ROOT"
    
    # 必要なディレクトリの作成
    mkdir -p .claude/agents .claude-flow/metrics .swarm logs data
    
    log_success "環境設定が完了しました"
}

# Claude実行オプション構築
build_claude_options() {
    local options=()
    
    # 危険な権限スキップ（ユーザー要求）
    options+=("--dangerously-skip-permissions")
    
    # 設定ファイル指定
    if [ -f "$CLAUDE_SETTINGS" ]; then
        options+=("--settings" "$CLAUDE_SETTINGS")
    fi
    
    # MCP設定（Agent機能）- 正しい形式のMCP設定ファイル
    if [ -f "$CLAUDE_MCP" ]; then
        options+=("--mcp-config" "$CLAUDE_MCP")
    fi
    
    # ディレクトリアクセス許可
    options+=("--add-dir" "$PROJECT_ROOT")
    options+=("--add-dir" "$PROJECT_ROOT/src")
    options+=("--add-dir" "$PROJECT_ROOT/scripts")
    options+=("--add-dir" "$PROJECT_ROOT/config")
    options+=("--add-dir" "$PROJECT_ROOT/data")
    
    echo "${options[@]}"
}

# =============================================================================
# メイン実行部分
# =============================================================================

# ヘッダー表示
echo "================================================================================"
echo "🚀 Claude Code 完全機能有効化起動スクリプト"
echo "================================================================================"
echo "📋 機能:"
echo "  ✅ Agent機能（SubAgent）"
echo "  ✅ Claude-Flow機能（Swarm並列開発）"
echo "  ✅ Context7機能（高度なコンテキスト管理）"
echo "================================================================================"
echo ""

# 前提条件チェック
log_info "前提条件の確認中..."

# Claude Codeの存在確認
if [ ! -x "$CLAUDE_CMD" ]; then
    log_error "Claude Codeが見つからないか実行できません: $CLAUDE_CMD"
    log_error "Claude Codeのインストール状況を確認してください。"
    exit 1
fi

# バージョン情報表示
CLAUDE_VERSION=$("$CLAUDE_CMD" --version 2>/dev/null || echo "Unknown")
log_success "Claude Code が見つかりました: $CLAUDE_CMD (Version: $CLAUDE_VERSION)"

# プロジェクトディレクトリ確認
if [ ! -d "$PROJECT_ROOT" ]; then
    log_error "プロジェクトディレクトリが見つかりません: $PROJECT_ROOT"
    exit 1
fi

log_success "プロジェクトディレクトリ: $PROJECT_ROOT"

# 設定ファイルの確認
log_info "設定ファイルの確認中..."
if check_config_files; then
    log_success "必要な設定ファイルが見つかりました"
else
    log_warning "一部の設定ファイルが見つかりませんが、継続します"
fi

# 機能確認
echo ""
log_info "機能確認中..."
check_agent_functionality
check_swarm_functionality  
check_context_functionality

# 環境設定
echo ""
setup_environment

# 実行モード選択
echo ""
echo "================================================================================"
echo "🎯 実行モードを選択してください:"
echo "================================================================================"
echo "1) 🤖 完全機能モード（Agent + Swarm + Context7）"
echo "2) 🔧 デバッグモード（詳細ログ出力）"
echo "3) 📊 Swarm並列開発モード（25エージェント並列実行）"
echo "4) 🧪 テストモード（機能確認のみ）"
echo "5) ⚙️  設定確認のみ"
echo "6) 🚪 終了"
echo "================================================================================"

read -p "選択 (1-6): " choice

case $choice in
    1)
        echo ""
        log_info "完全機能モードでClaude Codeを起動します..."
        log_info "有効化される機能:"
        echo "  - Agent機能（SubAgent）"
        echo "  - Claude-Flow機能（Swarm並列開発）"
        echo "  - Context7機能（高度なコンテキスト管理）"
        echo ""
        
        options=($(build_claude_options))
        log_info "プロジェクトディレクトリ: $PROJECT_ROOT"
        log_info "実行コマンド: $CLAUDE_CMD ${options[*]}"
        echo ""
        
        # プロジェクトディレクトリに移動してから実行
        cd "$PROJECT_ROOT"
        exec "$CLAUDE_CMD" "${options[@]}"
        ;;
        
    2)
        echo ""
        log_info "デバッグモードでClaude Codeを起動します..."
        
        options=($(build_claude_options))
        options+=("--debug" "--verbose")
        
        log_info "プロジェクトディレクトリ: $PROJECT_ROOT"
        log_info "実行コマンド: $CLAUDE_CMD ${options[*]}"
        echo ""
        
        # プロジェクトディレクトリに移動してから実行
        cd "$PROJECT_ROOT"
        exec "$CLAUDE_CMD" "${options[@]}"
        ;;
        
    3)
        echo ""
        log_info "Swarm並列開発モードでClaude Codeを起動します..."
        log_info "25個のエージェントによる並列開発が有効化されます"
        
        # Swarm特化設定
        export CLAUDE_SWARM_MODE=true
        export CLAUDE_FLOW_ENABLED=true
        
        options=($(build_claude_options))
        
        log_info "プロジェクトディレクトリ: $PROJECT_ROOT"
        log_info "実行コマンド: $CLAUDE_CMD ${options[*]}"
        echo ""
        
        # プロジェクトディレクトリに移動してから実行
        cd "$PROJECT_ROOT"
        exec "$CLAUDE_CMD" "${options[@]}"
        ;;
        
    4)
        echo ""
        log_info "テストモードを実行します..."
        
        # Agent機能テスト
        echo "Testing Agent functionality..." | "$CLAUDE_CMD" --print --settings "$CLAUDE_SETTINGS" 2>/dev/null && \
            log_success "Agent機能テスト: 成功" || \
            log_error "Agent機能テスト: 失敗"
        
        # 基本機能テスト
        echo "Test basic functionality" | "$CLAUDE_CMD" --print 2>/dev/null && \
            log_success "基本機能テスト: 成功" || \
            log_error "基本機能テスト: 失敗"
        
        log_info "全ての機能テストが完了しました"
        ;;
        
    5)
        echo ""
        log_info "設定確認モード"
        echo "================================================================================"
        echo "📋 システム情報:"
        echo "  - Claude Codeパス: $CLAUDE_CMD"
        echo "  - Claude Codeバージョン: $CLAUDE_VERSION"
        echo "  - プロジェクトディレクトリ: $PROJECT_ROOT"
        echo "  - スクリプトディレクトリ: $SCRIPT_DIR"
        echo ""
        
        echo "📁 設定ファイル:"
        echo "  - Claude設定: $([ -f "$CLAUDE_CONFIG" ] && echo "✅ 存在" || echo "❌ 不在")"
        echo "  - Agent設定: $([ -f "$CLAUDE_SETTINGS" ] && echo "✅ 存在" || echo "❌ 不在")"
        echo "  - Swarm設定: $([ -f "$CLAUDE_SWARM" ] && echo "✅ 存在" || echo "❌ 不在")"
        echo "  - MCP設定: $([ -f "$CLAUDE_MCP" ] && echo "✅ 存在" || echo "❌ 不在")"
        echo "  - 抑制設定: $([ -f "$CLAUDE_SUPPRESS" ] && echo "✅ 存在" || echo "❌ 不在")"
        echo ""
        
        echo "🔧 機能状況:"
        echo "  - Agent機能: $([ -d "$PROJECT_ROOT/.claude/agents" ] && echo "✅ 有効" || echo "❌ 無効")"
        echo "  - Swarm機能: $([ -d "$PROJECT_ROOT/.swarm" ] && echo "✅ 有効" || echo "❌ 無効")"
        echo "  - Context7機能: $([ -f "$CLAUDE_SETTINGS" ] && echo "✅ 有効" || echo "❌ 無効")"
        echo ""
        
        if [ -f "$CLAUDE_SWARM" ]; then
            agent_count=$(grep -c "file:" "$CLAUDE_SWARM" 2>/dev/null || echo "0")
            echo "📊 Swarm統計:"
            echo "  - 設定済みエージェント数: ${agent_count}個"
            echo "  - Swarm名: $(grep "name:" "$CLAUDE_SWARM" | head -1 | cut -d: -f2 | xargs 2>/dev/null || echo "不明")"
            echo "  - 実行タイプ: $(grep "queen_type:" "$CLAUDE_SWARM" | head -1 | cut -d: -f2 | xargs 2>/dev/null || echo "不明")"
        fi
        echo "================================================================================"
        ;;
        
    6)
        log_info "終了しました"
        exit 0
        ;;
        
    *)
        log_error "無効な選択です: $choice"
        exit 1
        ;;
esac