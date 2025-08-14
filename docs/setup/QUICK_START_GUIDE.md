# 📚 ニュース配信システム - クイックスタートガイド

## 🚀 5分で始めるニュース自動配信 ⚡

**システム稼働率: 95%完了** - Gmail認証のみで100%稼働開始！

---

## 📊 現在の状況 (2024-06-28更新)

### ✅ **完了済み**
- ✅ **NewsAPI**: 稼働中 (35記事取得可能)
- ✅ **Claude AI**: 稼働中 (コンテンツ分析準備完了)
- ✅ **NVD API**: 稼働中 (299,754件のCVE利用可能)
- ✅ **DeepL API**: 稼働中 (月50万文字利用可能)
- ✅ **スケジューラー**: 完全実装済み
- ✅ **レポート生成**: HTML/PDF生成準備完了
- ✅ **APIキー**: 全て設定済み

### ⚠️ **残り作業**
- 🔐 **Gmail認証**: 5分のOAuth認証のみ
- 📰 **GNews API**: アカウント有効化 (オプション)

## 📋 事前準備チェックリスト

### ✅ 必要なもの
- [x] Python 3.12以上がインストール済み ✅
- [x] インターネット接続 ✅
- [x] Gmailアカウント ✅
- [x] 全APIキー設定済み ✅
  - [x] [NewsAPI](https://newsapi.org/) キー ✅
  - [x] [DeepL API](https://www.deepl.com/pro-api) キー ✅
  - [x] [Anthropic Claude API](https://www.anthropic.com/) キー ✅
  - [x] [Gmail API](https://console.cloud.google.com/) 認証情報 ✅

---

## ⚡ Gmail認証のみで完了 (5分)

**95%完了済み** - 残りはGmail認証だけ！

### 手順1: 仮想環境の有効化
```bash
# プロジェクトディレクトリに移動
cd /mnt/e/news-delivery-system

# 仮想環境の有効化
source venv/bin/activate
```

### 手順2: Gmail OAuth認証 🔐
```bash
# ステップ1: 認証URLを表示
python tools/show_gmail_url.py

# ステップ2: ブラウザで認証
# → 表示されたURLをブラウザで開く
# → Googleでログイン → 権限許可 → 認証コードをコピー

# ステップ3: 認証コードを入力
python tools/simple_gmail_auth.py
# → コピーした認証コードを貼り付け → Enter
```

**📋 認証で許可する内容:**
- ✅ Gmail送信権限のみ (安全)
- ❌ メール読み取り権限なし
- ❌ 個人情報アクセスなし

### 手順3: 認証完了確認
```bash
# 全APIの状況確認
python tools/check_api_keys.py
```

**期待結果**: 全APIが ✅ WORKING になる

---

## 🚀 システム稼働開始 (即座)

### テスト実行
```bash
# メール配信テスト実行
PYTHONPATH=/mnt/e/news-delivery-system python tools/test_email_delivery.py
```

### 自動化開始
```bash
# スケジューラー起動（前景実行）
python tools/run_scheduler.py

# または、バックグラウンド実行（推奨）
sudo ./system/install_scheduler_service.sh
sudo systemctl start news-delivery-scheduler
sudo systemctl enable news-delivery-scheduler
```

**期待結果**: 
- ✅ メールが配信される
- ✅ HTMLとPDFファイルが添付される
- ✅ 100%自動化開始

---

## 🎯 自動実行スケジュール

---

## 📊 ステップ5: 動作確認

### 5.1 スケジュール確認
```bash
# スケジューラー状態確認
python tools/scheduler_manager.py status
```

### 5.2 ログ確認
```bash
# リアルタイムログ監視
sudo journalctl -u news-delivery-scheduler -f
```

---

## 🎯 デフォルト動作スケジュール

| タスク | 実行時刻 | 説明 |
|--------|----------|------|
| 📰 日次ニュース配信 | 毎日 7:00 | 全ジャンルからニュース収集・分析・配信 |
| 🚨 緊急ニュースチェック | 毎時間 | 重要度9以上、CVSS 9.0以上の緊急情報 |
| 🔍 システム健全性チェック | 毎日 23:00 | API状況・システム状態の確認 |

---

## 🛠️ 基本管理コマンド

### スケジューラー管理
```bash
# 状態確認
python tools/scheduler_manager.py status

# タスクを今すぐ実行
python tools/scheduler_manager.py run daily_news_collection

# タスクの停止
python tools/scheduler_manager.py disable urgent_news_check

# タスクの開始
python tools/scheduler_manager.py enable urgent_news_check
```

### システム管理
```bash
# サービス状態確認
sudo systemctl status news-delivery-scheduler

# サービス再起動
sudo systemctl restart news-delivery-scheduler

# サービス停止
sudo systemctl stop news-delivery-scheduler
```

---

## 🆘 トラブルシューティング

### よくある問題と解決法

#### ❌ Gmail認証エラー
```bash
# 再認証を実行
python tools/setup_gmail_auth.py
```

#### ❌ APIキーエラー
```bash
# APIキー状況確認
python tools/check_api_keys.py

# .envファイルを再確認
cat .env
```

#### ❌ メールが届かない
1. スパムフォルダを確認
2. 受信者メールアドレスを確認
3. Gmail API制限を確認

#### ❌ スケジューラーが動かない
```bash
# エラーログ確認
sudo journalctl -u news-delivery-scheduler --no-pager

# 手動実行でテスト
python tools/scheduler_manager.py run daily_news_collection
```

---

## 📝 カスタマイズ

### 配信時刻の変更
```bash
# 設定ファイルを編集
nano system/schedule_config.json
```

### 受信者の追加
```bash
# 環境設定を編集
nano .env

# RECIPIENT_EMAILSに追加（カンマ区切り）
RECIPIENT_EMAILS=user1@example.com,user2@example.com,user3@example.com
```

---

## 🎉 完了！

これでニュース自動配信システムが稼働開始しました！

### 次にすること
1. **毎日7:00**: 自動でニュースが配信されます
2. **毎時**: 緊急ニュースがチェックされます  
3. **毎日23:00**: システム健全性がチェックされます

### より詳しい情報
- 📖 [詳細マニュアル](README.md)
- ⚙️ [スケジューラー詳細ガイド](README_SCHEDULER.md)
- 🔧 [API設定ガイド](docs/API_KEYS_SETUP.md)

---

**🎯 重要**: 初回は手動でテスト実行して、正常に動作することを確認してください！

```bash
# テスト実行コマンド
python tools/scheduler_manager.py run daily_news_collection
```

**質問・問題があれば、ログファイルを確認してトラブルシューティングセクションを参照してください。**