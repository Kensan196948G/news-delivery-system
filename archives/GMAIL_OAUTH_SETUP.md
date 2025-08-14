# Gmail OAuth2 設定ガイド
News Delivery System用 Gmail API設定手順

## 📋 必要な情報・準備

### 1. Googleアカウント
- **Gmailアカウント** (送信用メールアドレス)
- **Google Cloud Console**へのアクセス権限

### 2. 受信者情報
- **配信先メールアドレス** (複数指定可能)

---

## 🔧 Google Cloud Console設定手順

### Step 1: プロジェクト作成
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成
   - プロジェクト名: `news-delivery-system` (任意)
   - 組織: 個人使用の場合は「組織なし」

### Step 2: Gmail API有効化
1. APIとサービス → ライブラリ
2. "Gmail API" を検索して選択
3. 「有効にする」をクリック

### Step 3: OAuth同意画面設定
1. APIとサービス → OAuth同意画面
2. ユーザータイプ: **外部** を選択
3. 必要な情報を入力:
   ```
   アプリ名: News Delivery System
   ユーザーサポートメール: あなたのメールアドレス
   承認済みドメイン: (空欄でOK)
   開発者の連絡先情報: あなたのメールアドレス
   ```
4. スコープ追加で以下を選択:
   - `.../auth/gmail.send` (メール送信)

### Step 4: OAuth 2.0クライアント作成
1. APIとサービス → 認証情報
2. 「認証情報を作成」→「OAuth 2.0 クライアントID」
3. アプリケーションの種類: **デスクトップアプリケーション**
4. 名前: `News Delivery Desktop Client`
5. 作成後、**JSONファイルをダウンロード**

---

## 📁 認証ファイル配置

### ダウンロードしたJSONファイルの配置
```bash
# ファイル名を変更して配置
mv ~/Downloads/client_secret_xxxxx.json config/gmail_credentials.json
```

### ファイル構造確認
```
config/
├── config.json
├── .env
└── gmail_credentials.json  ← 新規追加
```

---

## ⚙️ 環境変数設定

### .envファイル更新
以下の情報を`.env`ファイルに追加・更新:

```env
# Gmail設定
SENDER_EMAIL=your-gmail@gmail.com          # 送信用Gmailアドレス
RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com  # 配信先(カンマ区切り)

# Gmail OAuth パス
GMAIL_CREDENTIALS_PATH=/media/kensan/LinuxHDD/news-delivery-system/config/gmail_credentials.json
GMAIL_TOKEN_PATH=/media/kensan/LinuxHDD/news-delivery-system/config/gmail_token.json
```

---

## 🔐 初回認証手順

### Step 1: 認証スクリプト実行
```bash
# 仮想環境内で実行
python3 -c "
import sys
sys.path.insert(0, 'src')
from notifiers.gmail_sender import GmailSender
import asyncio

async def setup_gmail():
    sender = GmailSender()
    await sender.initialize()
    print('Gmail OAuth setup completed!')

asyncio.run(setup_gmail())
"
```

### Step 2: ブラウザ認証
1. スクリプト実行後、ブラウザが自動で開く
2. Googleアカウントでログイン
3. 「このアプリは確認されていません」警告が出た場合:
   - 「詳細設定」→「News Delivery System（安全ではないページ）に移動」
4. アクセス許可を承認

### Step 3: 認証完了確認
- `config/gmail_token.json`が自動生成される
- コンソールに「Gmail OAuth setup completed!」と表示

---

## 📧 テストメール送信

### 基本テスト
```bash
python3 -c "
import sys, asyncio
sys.path.insert(0, 'src')
from notifiers.gmail_sender import GmailSender

async def test_email():
    sender = GmailSender()
    result = await sender.send_test_email()
    print('Test result:', result)

asyncio.run(test_email())
"
```

### 実際のニュースレポート送信テスト
```bash
python3 -c "
import sys, asyncio
sys.path.insert(0, 'src')
from notifiers.gmail_sender import GmailSender

async def test_report():
    sender = GmailSender()
    
    # テスト用HTML
    test_html = '''
    <!DOCTYPE html>
    <html><head><meta charset=\"UTF-8\"><title>Test Report</title></head>
    <body>
        <h1>📰 News Delivery System Test</h1>
        <p>This is a test email from your News Delivery System!</p>
        <p>System is working correctly.</p>
    </body></html>
    '''
    
    success = await sender.send_daily_report(
        html_content=test_html,
        articles=[]
    )
    print('Report send result:', success)

asyncio.run(test_report())
"
```

---

## 🛡️ セキュリティ設定

### アプリパスワード（2段階認証使用時）
Googleアカウントで2段階認証を有効にしている場合:
1. Googleアカウント設定 → セキュリティ
2. アプリパスワードを生成
3. 生成されたパスワードを使用

### スコープ制限
OAuth設定で最小限のスコープのみ許可:
- `https://www.googleapis.com/auth/gmail.send` (送信のみ)

---

## 📊 設定確認チェックリスト

### Google Cloud Console
- [ ] プロジェクト作成完了
- [ ] Gmail API有効化済み
- [ ] OAuth同意画面設定済み
- [ ] デスクトップアプリケーション認証情報作成済み
- [ ] JSONファイルダウンロード済み

### ローカル設定
- [ ] `config/gmail_credentials.json`配置済み
- [ ] `.env`ファイル更新済み
- [ ] 送信者・受信者メールアドレス設定済み

### 認証・テスト
- [ ] 初回OAuth認証完了
- [ ] `config/gmail_token.json`生成確認
- [ ] テストメール送信成功
- [ ] レポート送信テスト成功

---

## ❓ トラブルシューティング

### よくある問題と解決方法

**1. 「このアプリは確認されていません」エラー**
- 解決: 詳細設定 → 安全ではないページに移動

**2. 「access_denied」エラー**  
- 解決: OAuth同意画面の設定を確認、スコープが正しく設定されているか確認

**3. 「insufficient permissions」エラー**
- 解決: Gmail APIが有効になっているか確認

**4. 認証ファイルが見つからない**
- 解決: `gmail_credentials.json`のパスが正しいか確認

**5. メール送信に失敗**
- 解決: 送信者メールアドレスが認証したアカウントと一致しているか確認

---

## 📞 必要な情報（確認項目）

設定に必要な情報をお聞かせください:

1. **送信用Gmailアドレス**: `your-email@gmail.com`
2. **配信先メールアドレス**: `recipient@example.com` (複数可)
3. **Google Cloud Consoleアクセス**: 可能か？
4. **2段階認証**: 有効か無効か？

これらの情報があれば、より具体的な設定手順をご案内できます！