# 一時的に無効化されたワークフロー

これらのワークフローは、プッシュイベントで実行されないように設計されていますが、
GitHub Actionsの画面でエラーとして表示されるため、一時的に無効化しています。

## 無効化されたワークフロー：
- issue-automation.yml - issueイベント専用
- auto-flow-complete.yml - スケジュール実行専用
- self-heal.yml - 手動実行/スケジュール専用

これらを有効にするには、ファイルを `.github/workflows/` ディレクトリに戻してください。