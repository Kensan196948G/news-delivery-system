#!/bin/bash

# Stop All GitHub Workflow Runs Script
# このスクリプトは全ての実行中のワークフローを停止します

echo "🛑 GitHub Workflow停止スクリプト"
echo "================================"

# リポジトリ情報
OWNER="Kensan196948G"
REPO="news-delivery-system"

# 認証チェック
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLIの認証が必要です"
    echo "実行: gh auth login"
    exit 1
fi

echo "📊 実行中のワークフローを取得中..."

# カウンター初期化
TOTAL=0
CANCELLED=0
FAILED=0

# 実行中のワークフローを取得してキャンセル
echo ""
echo "🔄 実行中(in_progress)のワークフローをキャンセル中..."
IN_PROGRESS=$(gh run list --repo "$OWNER/$REPO" --status in_progress --json databaseId --jq '.[].databaseId')

if [ -n "$IN_PROGRESS" ]; then
    for run_id in $IN_PROGRESS; do
        ((TOTAL++))
        echo -n "  Cancelling run #$run_id... "
        if gh run cancel $run_id --repo "$OWNER/$REPO" 2>/dev/null; then
            echo "✅"
            ((CANCELLED++))
        else
            echo "❌"
            ((FAILED++))
        fi
    done
else
    echo "  実行中のワークフローはありません"
fi

# キュー中のワークフローを取得してキャンセル
echo ""
echo "⏳ キュー中(queued)のワークフローをキャンセル中..."
QUEUED=$(gh run list --repo "$OWNER/$REPO" --status queued --json databaseId --jq '.[].databaseId')

if [ -n "$QUEUED" ]; then
    for run_id in $QUEUED; do
        ((TOTAL++))
        echo -n "  Cancelling run #$run_id... "
        if gh run cancel $run_id --repo "$OWNER/$REPO" 2>/dev/null; then
            echo "✅"
            ((CANCELLED++))
        else
            echo "❌"
            ((FAILED++))
        fi
    done
else
    echo "  キュー中のワークフローはありません"
fi

# 待機中のワークフローを取得してキャンセル
echo ""
echo "⏸️ 待機中(waiting)のワークフローをキャンセル中..."
WAITING=$(gh run list --repo "$OWNER/$REPO" --status waiting --json databaseId --jq '.[].databaseId')

if [ -n "$WAITING" ]; then
    for run_id in $WAITING; do
        ((TOTAL++))
        echo -n "  Cancelling run #$run_id... "
        if gh run cancel $run_id --repo "$OWNER/$REPO" 2>/dev/null; then
            echo "✅"
            ((CANCELLED++))
        else
            echo "❌"
            ((FAILED++))
        fi
    done
else
    echo "  待機中のワークフローはありません"
fi

# 結果表示
echo ""
echo "================================"
echo "📈 実行結果サマリー"
echo "================================"
echo "  合計対象数: $TOTAL"
echo "  ✅ キャンセル成功: $CANCELLED"
echo "  ❌ キャンセル失敗: $FAILED"
echo ""

# 現在の状態を確認
echo "📊 現在のワークフロー状態:"
echo "--------------------------------"
gh run list --repo "$OWNER/$REPO" --limit 5

echo ""
echo "✨ 完了しました！"
echo ""
echo "📝 次のステップ:"
echo "1. GitHubのActionsページで確認: https://github.com/$OWNER/$REPO/actions"
echo "2. 必要に応じて手動で残りをキャンセル"
echo "3. 新しいワークフローが自動的に開始されます"