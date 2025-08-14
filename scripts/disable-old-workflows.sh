#!/bin/bash

# Disable Old Workflows Script
# 古いワークフローを無効化します

echo "🔧 古いワークフローを無効化します"
echo "===================================="

# 無効化すべき古いワークフロー
OLD_WORKFLOWS=(
    "auto-flow-complete.yml"
    "auto-repair-cycle.yml"
    "Test Basic Workflow"
    "Test Issue Automation Fixed"
    "Test Minimal Issue Automation"
    "Test Simplified Workflow"
)

echo "📋 無効化対象:"
for wf in "${OLD_WORKFLOWS[@]}"; do
    echo "  - $wf"
done
echo ""

read -p "⚠️ これらのワークフローを無効化しますか？ (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ キャンセルしました"
    exit 0
fi

echo ""
echo "🔧 無効化を開始..."

for workflow in "${OLD_WORKFLOWS[@]}"; do
    echo -n "  無効化中: $workflow ... "
    
    # ワークフローIDを取得
    WF_ID=$(gh workflow list --repo Kensan196948G/news-delivery-system --json name,id | jq -r ".[] | select(.name == \"$workflow\") | .id")
    
    if [ -n "$WF_ID" ]; then
        if gh workflow disable $WF_ID --repo Kensan196948G/news-delivery-system 2>/dev/null; then
            echo "✅"
        else
            echo "❌"
        fi
    else
        echo "⚠️ 見つかりません"
    fi
done

echo ""
echo "✅ 完了しました！"
echo ""
echo "📊 現在のアクティブなワークフロー:"
gh workflow list --repo Kensan196948G/news-delivery-system | grep active