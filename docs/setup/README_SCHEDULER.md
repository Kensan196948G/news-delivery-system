# News Delivery System - 自動スケジューラー

## 概要

News Delivery Systemの自動スケジューラーは、定期的なニュース収集と配信を自動化するシステムです。

## 主な機能

### 1. 定期タスク

- **daily_news_collection**: 毎日7:00にニュース収集と配信
- **urgent_news_check**: 1時間ごとに緊急ニュースをチェック
- **system_health_check**: 毎日23:00にシステム健全性チェック
- **weekly_summary**: 毎週日曜18:00に週次サマリー（デフォルト無効）

### 2. スケジュールタイプ

- **daily**: 毎日指定時刻に実行 (例: "07:00")
- **hourly**: 毎時指定分に実行 (例: "30" = 毎時30分)
- **weekly**: 毎週指定曜日・時刻に実行 (例: "SUN:18:00")
- **interval**: 指定秒間隔で実行 (例: "3600" = 1時間間隔)

## 使用方法

### スケジューラーの起動

```bash
# 手動起動
python run_scheduler.py

# またはvenv環境で
source venv/bin/activate
python run_scheduler.py
```

### スケジューラー管理

```bash
# ステータス確認
python scheduler_manager.py status

# タスク一覧表示
python scheduler_manager.py list

# タスクの有効化
python scheduler_manager.py enable task_name

# タスクの無効化
python scheduler_manager.py disable task_name

# タスクを即座に実行
python scheduler_manager.py run task_name

# 設定のエクスポート
python scheduler_manager.py export config_backup.json

# 設定のインポート
python scheduler_manager.py import config_backup.json
```

### システムサービスとしてのインストール

```bash
# サービスインストール (要root権限)
sudo ./install_scheduler_service.sh

# サービス管理
sudo systemctl start news-delivery-scheduler
sudo systemctl stop news-delivery-scheduler
sudo systemctl status news-delivery-scheduler
sudo systemctl enable news-delivery-scheduler  # 自動起動有効

# ログ確認
sudo journalctl -u news-delivery-scheduler -f
```

## 設定ファイル

### schedule_config.json

スケジュール設定を管理するJSONファイル：

```json
{
  "daily_news_collection": {
    "schedule_type": "daily",
    "schedule_time": "07:00",
    "enabled": true,
    "description": "Daily news collection and delivery at 7:00 AM"
  },
  "urgent_news_check": {
    "schedule_type": "interval",
    "schedule_time": "3600",
    "enabled": true,
    "description": "Check for urgent/breaking news every hour"
  }
}
```

### scheduler_state.json

スケジューラーの実行状態を保存（自動生成）：

- 最後の実行時刻
- 次回実行予定時刻
- 実行回数
- エラー回数

## メール配信テスト

### 包括的テストの実行

```bash
# 全テストを実行
python test_email_delivery.py
```

### テスト内容

1. **Gmail接続テスト**: API接続確認
2. **日次レポート配信テスト**: サンプル記事での日次レポート送信
3. **緊急アラート配信テスト**: 緊急記事での速報送信
4. **カスタムレポート配信テスト**: カスタムファイル添付テスト
5. **ライブニュース配信テスト**: 実際のニュース収集→配信テスト

### テスト結果

テスト結果は `reports/email_delivery_test_results_YYYYMMDD_HHMMSS.json` に保存されます。

## ログ管理

### ログファイル

- `logs/scheduler.log`: スケジューラーメインログ
- `logs/system_health.json`: システム健全性チェック結果
- `logs/performance.log`: パフォーマンスログ

### ログレベル

- INFO: 通常の動作ログ
- WARNING: 警告（継続可能な問題）
- ERROR: エラー（処理失敗）
- DEBUG: デバッグ情報（詳細ログ）

## トラブルシューティング

### よくある問題

1. **Gmail認証エラー**
   ```bash
   python setup_gmail_auth.py
   ```

2. **APIキーエラー**
   ```bash
   python check_api_keys.py
   ```

3. **スケジューラーが動かない**
   - .env ファイルの確認
   - 権限の確認
   - ログファイルの確認

4. **メール送信失敗**
   - Gmail API認証状態確認
   - 受信者メールアドレス設定確認
   - レート制限確認

### エラー復旧

- エラー回数が最大値（デフォルト5回）に達したタスクは自動的に無効化されます
- 手動で有効化するか、エラー原因を修正してから再有効化してください

## パフォーマンス監視

### システム健全性チェック

毎日23:00に自動実行される健全性チェックで以下を監視：

- API接続状況
- スケジューラー動作状況
- アクティブタスク数
- システムリソース使用状況

### 結果確認

```bash
# 最新の健全性チェック結果
cat logs/system_health.json

# スケジューラー状態確認
python scheduler_manager.py status
```

## セキュリティ

### 認証情報

- API キーは .env ファイルで管理
- Gmail認証はOAuth2トークンで管理
- 認証ファイルのパーミッション確認必須

### システムサービス

- 専用ユーザーでの実行推奨
- ログファイルの適切な権限設定
- 定期的なセキュリティ更新

## 拡張機能

### カスタムタスクの追加

1. `src/services/scheduler.py` にタスク関数を追加
2. `schedule_config.json` に設定を追加
3. スケジューラーを再起動

### 通知設定

- Slack通知
- Discord通知
- SMS通知

などの追加通知手段を実装可能。

## サポート

問題が発生した場合：

1. ログファイルを確認
2. システム健全性チェック結果を確認
3. API キー状況を確認
4. Gmail認証状況を確認

詳細なサポートが必要な場合は、システム管理者にお問い合わせください。