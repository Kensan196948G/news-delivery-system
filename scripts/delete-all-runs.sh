#!/bin/bash

# Delete All Workflow Runs Script
# 全てのワークフロー実行履歴を削除します

echo "🗑️ GitHub Workflow実行履歴削除スクリプト"
echo "========================================="

# リポジトリ情報を自動取得
REPO_URL=$(git remote get-url origin)
OWNER=$(echo $REPO_URL | sed -E 's/.*github.com[:/]([^/]+)\/.*/\1/')
REPO=$(echo $REPO_URL | sed -E 's/.*github.com[:/][^/]+\/([^.]+)(\.git)?/\1/')

echo "📌 リポジトリ: $OWNER/$REPO"
echo ""

# 認証チェック
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLIの認証が必要です"
    echo "実行: gh auth login"
    exit 1
fi

# 削除カウンター
TOTAL=0
DELETED=0
FAILED=0
BATCH_SIZE=30

echo "📊 ワークフロー実行履歴を取得中..."

# 全ての実行履歴を取得（最大1000件）
ALL_RUNS=$(gh run list --repo "$OWNER/$REPO" --limit 1000 --json databaseId --jq '.[].databaseId' 2>/dev/null)

if [ -z "$ALL_RUNS" ]; then
    echo "⚠️ 実行履歴が見つかりません"
    echo ""
    echo "考えられる原因:"
    echo "1. リポジトリにActionsが設定されていない"
    echo "2. 既に全て削除済み"
    echo "3. 権限不足"
    exit 0
fi

# 実行履歴の総数をカウント
TOTAL=$(echo "$ALL_RUNS" | wc -l)
echo "📋 見つかった実行履歴: $TOTAL 件"
echo ""

# 確認プロンプト
read -p "⚠️ $TOTAL 件の実行履歴を削除しますか？ (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ キャンセルしました"
    exit 0
fi

echo ""
echo "🗑️ 削除を開始します..."
echo "================================"

# プログレスバー関数
show_progress() {
    local current=$1
    local total=$2
    local percent=$((current * 100 / total))
    local bar_length=30
    local filled_length=$((percent * bar_length / 100))
    
    printf "\r["
    printf "%${filled_length}s" | tr ' ' '='
    printf "%$((bar_length - filled_length))s" | tr ' ' ' '
    printf "] %3d%% (%d/%d)" $percent $current $total
}

# バッチごとに削除
COUNTER=0
for run_id in $ALL_RUNS; do
    ((COUNTER++))
    
    # プログレス表示
    show_progress $COUNTER $TOTAL
    
    # 削除実行（エラー出力を抑制）
    if gh run delete $run_id --repo "$OWNER/$REPO" --confirm 2>/dev/null; then
        ((DELETED++))
    else
        ((FAILED++))
    fi
    
    # レート制限対策（30件ごとに短い待機）
    if [ $((COUNTER % BATCH_SIZE)) -eq 0 ]; then
        echo ""
        echo "  💤 レート制限回避のため1秒待機..."
        sleep 1
    fi
done

echo ""
echo ""
echo "================================"
echo "📈 削除結果サマリー"
echo "================================"
echo "  対象総数: $TOTAL"
echo "  ✅ 削除成功: $DELETED"
echo "  ❌ 削除失敗: $FAILED"
echo ""

# 残っている実行履歴を確認
echo "📊 現在の実行履歴を確認中..."
REMAINING=$(gh api \
  -H "Accept: application/vnd.github+json" \
  "/repos/$OWNER/$REPO/actions/runs?per_page=100" \
  --jq '.total_count' 2>/dev/null)

if [ -n "$REMAINING" ]; then
    echo "  残り: $REMAINING 件"
else
    echo "  確認できませんでした"
fi

echo ""
echo "✨ 完了しました！"
echo ""
echo "📝 次のステップ:"
echo "1. GitHubのActionsページで確認: https://github.com/$OWNER/$REPO/actions"
echo "2. 新しいワークフローを実行できます"