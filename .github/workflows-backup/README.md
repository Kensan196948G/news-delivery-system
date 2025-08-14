# Workflows Backup Directory

このディレクトリには、以前使用されていたが現在は無効化または削除されたGitHub Actionsワークフローファイルがバックアップされています。

## バックアップ日時
- 2025年8月14日

## バックアップされたワークフロー

### 主要ワークフロー（改善版が稼働中）
- `ci-cd.yml` - CI/CDパイプライン（改善版が稼働中）
- `dependency-update.yml` - 依存関係更新（改善版が稼働中）
- `docs-automation.yml` - ドキュメント自動化（改善版が稼働中）
- `issue-automation.yml` - Issue自動化
- `pr-automation.yml` - PR自動化（改善版が稼働中）
- `quality-gate.yml` - 品質ゲート（改善版が稼働中）
- `security-automation.yml` - セキュリティ自動化（改善版が稼働中）

### 削除されたワークフロー
- `auto-repair-cycle.yml` - 自動修復サイクル（self-heal.ymlに統合）
- `backup-automation.yml` - バックアップ自動化
- `email-notification.yml` - メール通知
- `smart-commit.yml` - スマートコミット
- `workflow-improvements.yml` - ワークフロー改善リファレンス

### テスト用ワークフロー（削除済み）
- `test-basic.yml`
- `test-issue-automation-fixed.yml`
- `test-minimal-issue.yml`
- `test-simplified.yml`
- `test-triggers.yml`

### 無効化されたワークフロー
- `self-heal-disabled.yml` - 旧self-heal.yml（新版が稼働中）

## 復元方法

必要に応じて、以下のコマンドでワークフローを復元できます：

```bash
# 特定のワークフローを復元
cp .github/workflows-backup/<filename>.yml .github/workflows/

# gitに追加
git add .github/workflows/<filename>.yml
git commit -m "Restore <filename> workflow"
```

## 注意事項

- これらのワークフローは改善プロセスの一環として無効化されています
- 現在稼働中のワークフローは `.github/workflows/` ディレクトリにあります
- 復元する場合は、現在のワークフローとの競合に注意してください

## 改善内容の概要

以下の改善が実施されました：

1. **自己修復ループの統合** - `self-heal.yml`が本丸として機能
2. **CI/CD限定の失敗検知** - 無駄な実行を削減
3. **autofix/*ブランチの特別扱い** - 自動修復PRの円滑な処理
4. **最小権限の明示** - セキュリティの向上
5. **タイムアウトの設定** - 無限ループの防止
6. **並行実行の制御** - リソースの効率的な利用
7. **品質ゲートの強化** - Branch Protectionとの連携
8. **異常検知フローの統一** - 一貫した対応フロー

詳細は、各ワークフローファイルのコメントを参照してください。