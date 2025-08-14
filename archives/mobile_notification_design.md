# モバイル通知機能 実装計画

## ファイル構成

- `src/services/mobile_notification.py`

## 実装手順

### 1. FCMクライアントライブラリの実装

- firebase-adminの実装

### 2. MobileNotificationServiceクラスの実装

- 既存のserviceを参考に実装
- プッシュ通知送信処理の実装
- デバイストークン管理処理の実装

### 3. 設定ファイルの更新

- `config.json`や`.env`にFCMの設定を追加

### 4. データベーススキーマの更新

- デバイストークン管理用のテーブルを追加

### 5. テストコードの作成

- MobileNotificationServiceのテストコードを作成

## 実装詳細

### FCMクライアントライブラリ

- firebase-adminを使用する。
- 理由: Firebase Cloud Messaging (FCM) を使用してAndroidとiOSの両方に対応するため。

### MobileNotificationServiceクラス

- `email_delivery.py`を参考に実装。
- プッシュ通知送信処理:
  - FCMを使用してプッシュ通知を送信。
- デバイストークン管理処理:
  - ユーザーのデバイストークンをデータベースに保存。
  - 通知設定（カテゴリ別、時間帯別）を管理。

### 設定ファイル

- `.env`にFirebaseのサービスアカウントキーのパスを追加。
- `config.json`に通知設定（カテゴリ別、時間帯別）を追加。

### データベーススキーマ

- `data/database/schema.sql`にデバイストークン管理用のテーブルを追加。
- テーブル名: `device_tokens`
- カラム: `id`, `user_id`, `device_token`, `platform`, `created_at`, `updated_at`

### テストコード

- `tests/services/test_mobile_notification.py`を作成。
- プッシュ通知送信処理のテスト。
- デバイストークン管理処理のテスト。