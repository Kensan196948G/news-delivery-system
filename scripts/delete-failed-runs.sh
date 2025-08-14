#!/bin/bash

# Delete Failed Workflow Runs Only
# 失敗した実行履歴のみを削除

echo "❌ 失敗ワークフロー削除スクリプト"
echo "========================================="

# リポジトリ情報を自動取得
REPO_URL=$(git remote get-url origin)
OWNER=$(echo $REPO_URL | sed -E 's/.*github.com[:/]([^/]+)\/.*/\1/')
REPO=$(echo $REPO_URL | sed -E 's/.*github.com[:/][^/]+\/([^.]+)(\.git)?/\1/')

echo "📌 リポジトリ: $OWNER/$REPO"
echo ""

# 失敗した実行履歴を取得
echo "📊 失敗した実行履歴を検索中..."

FAILED_RUNS=$(gh run list \
  --repo "$OWNER/$REPO" \
  --status failure \
  --limit 1000 \
  --json databaseId,name,createdAt \
  --jq '.[].databaseId')

CANCELLED_RUNS=$(gh run list \
  --repo "$OWNER/$REPO" \
  --status cancelled \
  --limit 1000 \
  --json databaseId,name,createdAt \
  --jq '.[].databaseId')

# 統合
ALL_FAILED=$(echo -e "$FAILED_RUNS\n$CANCELLED_RUNS" | sort -u | grep -v '^$')

if [ -z "$ALL_FAILED" ]; then
    echo "✅ 失敗した実行履歴はありません"
    exit 0
fi

TOTAL=$(echo "$ALL_FAILED" | wc -l)
echo "📋 見つかった失敗/キャンセル済み実行: $TOTAL 件"
echo ""

# 確認
read -p "⚠️ これらを削除しますか？ (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ キャンセルしました"
    exit 0
fi

echo ""
echo "🗑️ 削除を開始します..."
DELETED=0
ERRORS=0

for run_id in $ALL_FAILED; do
    echo -n "  削除中: Run #$run_id ... "
    if gh run delete $run_id --repo "$OWNER/$REPO" --confirm 2>/dev/null; then
        echo "✅"
        ((DELETED++))
    else
        echo "❌"
        ((ERRORS++))
    fi
    
    # レート制限対策
    if [ $((DELETED % 30)) -eq 0 ]; then
        sleep 1
    fi
done

echo ""
echo "================================"
echo "📈 削除結果"
echo "================================"
echo "  ✅ 削除成功: $DELETED"
echo "  ❌ 削除失敗: $ERRORS"
echo ""
echo "✨ 完了しました！"