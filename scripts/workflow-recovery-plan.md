# ワークフロー段階的復旧計画

## 🎯 目的
権限エラーで無効化したワークフローを段階的に修正・再有効化する

## 📅 復旧スケジュール

### Phase 1: 基本機能の安定化（現在）
**状態**: ✅ 完了
- [x] CI/CDパイプライン動作確認
- [x] Quality Gate修正と動作確認
- [x] PR #10による権限修正

### Phase 2: Self-Healingの復旧（PR #10マージ後）
**対象**: `self-heal.yml`
**修正内容**:
```yaml
permissions:
  contents: write
  pull-requests: write
  actions: read  # write → read に変更済み
  issues: write
  checks: write
```
**テスト方法**:
```bash
# 修正済みファイルを有効化
cp .github/workflows-disabled/self-heal.yml .github/workflows/

# 手動実行でテスト
gh workflow run self-heal.yml

# 実行状況確認
gh run list --workflow=self-heal.yml
```

### Phase 3: セキュリティ自動化の復旧（Phase 2完了後）
**対象**: `security-automation.yml`
**必要な修正**:
- `actions: read`権限の追加
- 依存関係スキャンの最適化
- CVE通知の閾値調整

**実装手順**:
1. 権限設定の修正
2. ローカルテスト実行
3. 段階的有効化

### Phase 4: ドキュメント自動化の復旧
**対象**: `docs-automation.yml`
**必要な修正**:
- 権限設定の見直し
- トリガー条件の最適化
- 生成頻度の調整（負荷軽減）

### Phase 5: 依存関係更新の復旧
**対象**: `dependency-update.yml`
**必要な修正**:
- Dependabotとの競合回避
- 更新頻度の最適化
- 自動マージ条件の厳格化

## 🔧 共通修正ポイント

### 1. 権限設定の標準化
```yaml
permissions:
  contents: read       # 基本は read
  actions: read        # 必須：他のワークフローアクセス用
  pull-requests: write # PR作成が必要な場合のみ
  issues: write        # Issue作成が必要な場合のみ
  checks: write        # ステータス更新が必要な場合のみ
```

### 2. エラーハンドリングの追加
```yaml
- name: Handle errors
  if: failure()
  run: |
    echo "::warning::Workflow failed but continuing"
    exit 0  # 失敗を許容
```

### 3. リトライ機構の実装
```yaml
- name: Retry on failure
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: |
      # 実行コマンド
```

## 📊 成功指標

### 必須条件
- [ ] エラー率 5%未満
- [ ] 権限エラー 0件
- [ ] 無限ループ発生 0件

### 推奨条件
- [ ] 実行時間 10分以内
- [ ] API使用量 制限の50%以下
- [ ] 成功率 95%以上

## 🚨 ロールバック計画

問題発生時の対処:
```bash
# 1. 問題のあるワークフローを即座に無効化
mv .github/workflows/{問題のワークフロー}.yml .github/workflows-disabled/

# 2. 実行中のワークフローをキャンセル
gh run list --workflow={ワークフロー名} --json databaseId -q '.[0].databaseId' | xargs gh run cancel

# 3. Issueに報告
gh issue comment 11 --body "⚠️ {ワークフロー名}で問題発生。ロールバック実施。"
```

## 📝 チェックリスト

### 各Phase実施前
- [ ] PR #10がマージされている
- [ ] 前のPhaseが安定稼働している
- [ ] テスト環境での動作確認完了

### 各Phase実施後
- [ ] エラーログの確認
- [ ] パフォーマンス指標の確認
- [ ] Issue #11への進捗報告

---
*最終更新: 2024-11-14*
*次回レビュー: Phase 2実施時*