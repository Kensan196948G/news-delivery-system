#!/bin/bash

# Delete Workflow Runs by Date Range
# 日付範囲を指定して実行履歴を削除

echo "📅 日付指定ワークフロー削除スクリプト"
echo "========================================="

# リポジトリ情報を自動取得
REPO_URL=$(git remote get-url origin)
OWNER=$(echo $REPO_URL | sed -E 's/.*github.com[:/]([^/]+)\/.*/\1/')
REPO=$(echo $REPO_URL | sed -E 's/.*github.com[:/][^/]+\/([^.]+)(\.git)?/\1/')

echo "📌 リポジトリ: $OWNER/$REPO"
echo ""

# 日付入力
echo "削除する実行履歴の日付範囲を指定してください"
echo "例: 2024-01-01"
echo ""
read -p "開始日 (YYYY-MM-DD) [default: 2024-01-01]: " START_DATE
START_DATE=${START_DATE:-2024-01-01}

read -p "終了日 (YYYY-MM-DD) [default: $(date +%Y-%m-%d)]: " END_DATE
END_DATE=${END_DATE:-$(date +%Y-%m-%d)}

echo ""
echo "📊 $START_DATE から $END_DATE までの実行履歴を検索中..."

# 指定期間の実行履歴を取得
RUNS=$(gh run list \
  --repo "$OWNER/$REPO" \
  --limit 1000 \
  --json databaseId,createdAt,status,conclusion,name \
  --jq ".[] | select(.createdAt >= \"${START_DATE}\" and .createdAt <= \"${END_DATE}\") | .databaseId")

if [ -z "$RUNS" ]; then
    echo "⚠️ 指定期間の実行履歴が見つかりません"
    exit 0
fi

TOTAL=$(echo "$RUNS" | wc -l)
echo "📋 見つかった実行履歴: $TOTAL 件"
echo ""

# 確認
read -p "⚠️ これらの実行履歴を削除しますか？ (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ キャンセルしました"
    exit 0
fi

echo ""
echo "🗑️ 削除を開始します..."
DELETED=0
FAILED=0

for run_id in $RUNS; do
    echo -n "  削除中: Run #$run_id ... "
    if gh run delete $run_id --repo "$OWNER/$REPO" --confirm 2>/dev/null; then
        echo "✅"
        ((DELETED++))
    else
        echo "❌"
        ((FAILED++))
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
echo "  ❌ 削除失敗: $FAILED"
echo ""
echo "✨ 完了しました！"