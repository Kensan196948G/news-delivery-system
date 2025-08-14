# APIキー設定ガイド

## 📋 概要

ニュース自動配信システムを動作させるために必要なAPIキーの取得方法と設定手順を説明します。

## 🔑 必要なAPIキー一覧

### 1. **NewsAPI キー**
- **用途**: 英語圏のニュース記事収集
- **必要性**: ⭐⭐⭐ (必須)
- **料金**: 無料プラン有り（1日1,000リクエスト）

### 2. **GNews API キー**  
- **用途**: 多言語ニュース記事収集（バックアップ）
- **必要性**: ⭐⭐ (推奨)
- **料金**: 無料プラン有り（1日100リクエスト）

### 3. **DeepL API キー**
- **用途**: 高品質な記事翻訳
- **必要性**: ⭐⭐⭐ (必須)
- **料金**: 無料プラン有り（月50万文字）

### 4. **Anthropic API キー (Claude)**
- **用途**: AI記事分析・要約・重要度判定
- **必要性**: ⭐⭐⭐ (必須)
- **料金**: 従量課金制

### 5. **Gmail API 認証情報**
- **用途**: レポート配信
- **必要性**: ⭐⭐⭐ (必須)
- **料金**: 無料

## 📝 APIキー取得手順

### 1. NewsAPI キー取得

#### 手順:
1. [NewsAPI公式サイト](https://newsapi.org/) にアクセス
2. 「Get API Key」をクリック
3. アカウント登録（名前、メール、パスワード）
4. メール認証を完了
5. ダッシュボードでAPIキーを確認

#### 取得できる情報:
```
API Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
プラン: Developer (無料)
制限: 1,000 requests/day
```

#### 注意事項:
- 商用利用の場合は有料プランが必要
- レート制限: 1秒間に5リクエストまで
- 過去30日以内の記事のみ取得可能

---

### 2. GNews API キー取得

#### 手順:
1. [GNews公式サイト](https://gnews.io/) にアクセス
2. 「Get API Key」をクリック
3. アカウント登録（メール、パスワード）
4. メール認証を完了
5. ダッシュボードでAPIキーを確認

#### 取得できる情報:
```
API Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
プラン: Free
制限: 100 requests/day
```

#### 注意事項:
- 日本語記事の取得も可能
- 有料プランで制限拡張可能
- リアルタイム配信対応

---

### 3. DeepL API キー取得

#### 手順:
1. [DeepL API公式サイト](https://www.deepl.com/ja/pro-api) にアクセス
2. 「無料で登録」をクリック
3. アカウント登録（メール、パスワード、住所）
4. メール認証を完了
5. API管理画面で認証キーを確認

#### 取得できる情報:
```
Authentication Key: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
プラン: DeepL API Free
制限: 500,000 characters/month
```

#### 注意事項:
- 無料版は月50万文字まで
- 高品質な翻訳が可能
- 日本語⇔英語の翻訳精度が高い
- API v2を使用

---

### 4. Anthropic API キー取得

#### 手順:
1. [Anthropic Console](https://console.anthropic.com/) にアクセス
2. アカウント登録（メール、電話番号認証）
3. 支払い方法の登録（クレジットカード）
4. API Keys ページでキーを生成

#### 取得できる情報:
```
API Key: sk-ant-apixx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxx
プラン: 従量課金制
```

#### 注意事項:
- 初回$5のクレジット付与
- Claude-3-Sonnet使用推奨
- トークン使用量に応じて課金
- レート制限あり

#### 料金目安:
- Claude-3-Sonnet: 入力$3/1M tokens, 出力$15/1M tokens
- 1日100記事処理で約$2-5程度

---

### 5. Gmail API 認証情報取得

#### 手順:
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成
3. Gmail API を有効化
4. 認証情報を作成（OAuth 2.0）
5. 認証情報をダウンロード

#### 詳細手順:

##### ステップ1: プロジェクト作成
1. Google Cloud Console にログイン
2. プロジェクトを選択 → 「新しいプロジェクト」
3. プロジェクト名: `news-delivery-system`
4. 「作成」をクリック

##### ステップ2: Gmail API有効化
1. 「APIとサービス」→「ライブラリ」
2. 「Gmail API」を検索
3. 「有効にする」をクリック

##### ステップ3: OAuth認証情報作成
1. 「APIとサービス」→「認証情報」
2. 「認証情報を作成」→「OAuth クライアント ID」
3. アプリケーションの種類: 「デスクトップアプリケーション」
4. 名前: `News Delivery Gmail Client`
5. 認証情報をJSONでダウンロード

#### 取得できるファイル:
```json
{
  "installed": {
    "client_id": "xxxxx.apps.googleusercontent.com",
    "project_id": "news-delivery-system-xxxxx",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "xxxxxxxxxxxxxxxxxxxxxx"
  }
}
```

#### 注意事項:
- JSONファイルを `config/gmail_credentials.json` として保存
- 初回実行時にブラウザ認証が必要
- 認証トークンは自動保存される

---

## 🔧 環境変数設定

### .env ファイルの設定

```bash
# News APIs
NEWSAPI_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GNEWS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Translation API
DEEPL_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx

# AI Analysis API
ANTHROPIC_API_KEY=sk-ant-apixx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxx

# Email Configuration
SENDER_EMAIL=your-email@gmail.com
ADMIN_EMAIL=admin@example.com

# Gmail API (ファイルパス)
GMAIL_CREDENTIALS_FILE=config/gmail_credentials.json
GMAIL_TOKEN_FILE=config/gmail_token.json
```

### 設定手順:
1. `.env.example` を `.env` にコピー
2. 各APIキーを設定
3. Gmail認証ファイルのパスを確認

---

## 💰 料金試算

### 月間100記事/日の場合:

| サービス | 料金 | 備考 |
|---------|------|------|
| NewsAPI | $0 | 無料プラン内 |
| GNews | $0 | 無料プラン内 |
| DeepL | $0-$6.99 | 文字数による |
| Anthropic | $60-150 | 使用量による |
| Gmail | $0 | 無料 |
| **合計** | **$60-157/月** | |

### 節約のコツ:
- キャッシュ機能を有効活用
- 重複記事の除去で処理量削減
- 重要度の低い記事は翻訳スキップ

---

## 🛡️ セキュリティ対策

### APIキー保護:
- ✅ 環境変数での管理
- ✅ .envファイルの.gitignore登録
- ✅ 定期的なキーローテーション
- ✅ 最小権限の原則

### 推奨設定:
```bash
# .envファイルの権限設定
chmod 600 .env

# Gitから除外
echo ".env" >> .gitignore
echo "config/*.json" >> .gitignore
```

---

## 🚨 トラブルシューティング

### よくある問題:

#### 1. NewsAPI: 403 Forbidden
```
原因: APIキーが無効 or レート制限超過
解決: キーの確認、リクエスト間隔の調整
```

#### 2. DeepL: 456 Quota Exceeded
```
原因: 月間文字数制限超過
解決: 有料プランへのアップグレード
```

#### 3. Anthropic: 401 Unauthorized
```
原因: APIキー無効 or 残高不足
解決: キー再確認、クレジット追加
```

#### 4. Gmail: OAuth Error
```
原因: 認証情報の設定ミス
解決: credentials.jsonの再ダウンロード
```

### エラー確認コマンド:
```bash
# APIキー確認
python -c "import os; print('NewsAPI:', os.getenv('NEWSAPI_KEY')[:10] + '...' if os.getenv('NEWSAPI_KEY') else 'Not set')"

# 接続テスト
python main.py check
```

---

## 📞 サポート情報

### 各APIのサポート:
- **NewsAPI**: [help@newsapi.org](mailto:help@newsapi.org)
- **GNews**: [contact@gnews.io](mailto:contact@gnews.io)  
- **DeepL**: [support@deepl.com](mailto:support@deepl.com)
- **Anthropic**: [support@anthropic.com](mailto:support@anthropic.com)
- **Google**: [Google Cloud Support](https://cloud.google.com/support)

### ドキュメント:
- [NewsAPI Docs](https://newsapi.org/docs)
- [GNews Docs](https://gnews.io/docs/v4)
- [DeepL API Docs](https://www.deepl.com/ja/docs-api)
- [Anthropic Docs](https://docs.anthropic.com/)
- [Gmail API Docs](https://developers.google.com/gmail/api)

---

## ✅ セットアップ確認チェックリスト

- [ ] NewsAPI キー取得・設定完了
- [ ] GNews API キー取得・設定完了（推奨）
- [ ] DeepL API キー取得・設定完了
- [ ] Anthropic API キー取得・設定完了
- [ ] Gmail API 認証情報取得・設定完了
- [ ] .env ファイル作成・編集完了
- [ ] APIキー動作確認完了
- [ ] セキュリティ設定確認完了

すべてのチェックが完了したら、システムの本格運用開始が可能です！