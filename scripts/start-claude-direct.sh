#!/bin/bash
# Claude Code直接起動スクリプト（完全機能有効化版）
# Agent機能 + Claude-Flow(Swarm) + Context7機能対応

echo "🚀 Claude Code起動中..."
echo "⚠️  このスクリプトは基本機能版です"
echo ""
echo "📢 完全機能版を使用することを強く推奨します:"
echo "   ./scripts/start-claude-enhanced.sh"
echo ""
echo "完全機能版には以下が含まれます:"
echo "  ✅ Agent機能（SubAgent）"
echo "  ✅ Claude-Flow機能（Swarm並列開発）"
echo "  ✅ Context7機能（高度なコンテキスト管理）"
echo ""

read -p "完全機能版を実行しますか？ (Y/n): " use_enhanced

if [[ "$use_enhanced" != "n" && "$use_enhanced" != "N" ]]; then
    echo "🔄 完全機能版に切り替えます..."
    exec "$(dirname "$0")/start-claude-enhanced.sh"
fi

echo ""
echo "⚠️  基本機能版を継続します（非推奨）"
echo ""

CLAUDE_CMD="/home/kensan/.npm-global/bin/claude"

# Claude Codeの実行可能性を確認
if [ ! -x "$CLAUDE_CMD" ]; then
    echo "❌ エラー: Claude Codeが見つからないか実行できません: $CLAUDE_CMD"
    echo "Claude Codeのインストール状況を確認してください。"
    exit 1
fi

echo "✅ Claude Code見つかりました: $CLAUDE_CMD"
echo ""
echo "📱 起動方法:"
echo "  1. インタラクティブモード: $CLAUDE_CMD"
echo "  2. プロジェクトモード: $CLAUDE_CMD --project \$(pwd)"
echo ""
echo "📂 現在のディレクトリ: $(pwd)"
echo "📁 プロジェクトディレクトリ: \$(pwd)"
echo ""

# 選択メニュー
echo "実行モードを選択してください:"
echo "1) インタラクティブモード（通常起動）"
echo "2) プロジェクトモード（プロジェクトディレクトリ指定）"
echo "3) 設定確認のみ"
echo "4) 完全機能版に切り替え"
echo "5) 終了"

read -p "選択 (1-5): " choice

case $choice in
    1)
        echo "🤖 Claude Codeをインタラクティブモードで起動します..."
        exec "$CLAUDE_CMD" --dangerously-skip-permissions
        ;;
    2)
        echo "🤖 Claude Codeをプロジェクトモードで起動します..."
        # スクリプトがあるディレクトリの一つ上に移動
        cd "$(dirname "$0")/.."
        exec "$CLAUDE_CMD" --project . --dangerously-skip-permissions
        ;;
    3)
        echo "📋 設定情報:"
        echo "  - Claude Codeパス: $CLAUDE_CMD"
        echo "  - バージョン:"
        "$CLAUDE_CMD" --version 2>/dev/null || echo "    バージョン情報取得失敗"
        echo "  - プロジェクトディレクトリ: \$(pwd)"
        echo "  - 現在のディレクトリ: $(pwd)"
        ;;
    4)
        echo "🔄 完全機能版に切り替えます..."
        exec "$(dirname "$0")/start-claude-enhanced.sh"
        ;;
    5)
        echo "終了しました。"
        exit 0
        ;;
    *)
        echo "❌ 無効な選択です。"
        exit 1
        ;;
esac