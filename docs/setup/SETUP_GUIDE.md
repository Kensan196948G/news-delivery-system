# ニュース自動配信システム セットアップガイド

## 📋 事前準備

### 1. システム要件の確認
- **OS**: Windows 10/11 または WSL2
- **Python**: 3.11以上
- **メモリ**: 4GB以上
- **ストレージ**: 外付けHDD 3TB推奨
- **ネットワーク**: 安定したインターネット接続

### 2. 必要なアカウント作成

**このシステムは以下の4つのジャンルからニュースを自動収集します:**
- **最新国内社会ニュース（国内）**: 政治、社会、事件、災害、選挙
- **最新国際社会ニュース（海外）**: 人権、民主主義、紛争、戦争、国際政治
- **最新IT/AIニュース**: AI、機械学習、テクノロジー、ソフトウェア、スタートアップ
- **最新サイバーセキュリティニュース**: CVE脆弱性情報、エクスプロイト、サイバーセキュリティ、マルウェア

#### NewsAPI アカウント（国内社会・IT/AI・セキュリティニュース用）
1. https://newsapi.org/ にアクセス
2. 「Get API Key」をクリック
3. 無料アカウントを作成（1,000件/日まで無料）
4. APIキーをメモ
**収集対象メディア**: NHK、朝日新聞、毎日新聞、読売新聞、TechCrunch、Ars Technica、Wired、ZDNet、Krebs on Security、Bleeping Computer、Security Week

#### GNews API アカウント（国際社会ニュース用）
1. https://gnews.io/ にアクセス
2. 「Get Started」をクリック
3. 無料プランを選択（100件/日まで無料）
4. APIキーをメモ
**収集対象メディア**: BBC、CNN、Reuters、The Guardian

#### DeepL API アカウント（英語記事翻訳用）
1. https://www.deepl.com/pro-api にアクセス
2. 「無料で始める」をクリック
3. アカウント作成後、APIキーを取得（500,000文字/月まで無料）
**用途**: 海外メディア（BBC、CNN、Reuters等）の英語記事を日本語に自動翻訳

#### Anthropic Claude API アカウント（AI分析用）
1. https://www.anthropic.com/ にアクセス
2. Claude APIアクセスを申請
3. APIキーを取得
**用途**: 記事の重要度評価（1-10スケール）、自動要約生成、キーワード抽出、センチメント分析

#### NVD API アカウント（脆弱性情報用）
1. https://nvd.nist.gov/developers にアクセス
2. 「Request an API Key」をクリック
3. アカウント作成後、APIキーを取得（無料）
**用途**: CVE脆弱性情報の収集、CVSS 9.0以上の重大脆弱性の緊急通知

#### Gmail API アカウント（メール配信用）
1. https://console.cloud.google.com/ にアクセス
2. 新しいプロジェクトを作成
3. Gmail APIを有効化
4. OAuth2認証情報を作成
5. Client IDとClient Secretをメモ
**用途**: HTMLレポート・PDFファイルの自動メール配信、緊急アラート通知

#### Gmail API設定
1. Google Cloud Console にアクセス
2. 新しいプロジェクトを作成
3. Gmail APIを有効化
4. OAuth2認証情報を作成

## 🔧 インストール手順

### Step 1: プロジェクトのダウンロード
```powershell
# PowerShellで実行
git clone <repository-url>
cd news-delivery-system
```

### Step 2: Python環境の準備
```powershell
# 仮想環境の作成
python -m venv news-env

# 仮想環境の有効化
news-env\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### Step 3: 外付けHDDの準備
```powershell
# 外付けHDDにディレクトリ作成 (例: E:ドライブ)
mkdir E:\NewsDeliverySystem
mkdir E:\NewsDeliverySystem\articles
mkdir E:\NewsDeliverySystem\reports
mkdir E:\NewsDeliverySystem\database
mkdir E:\NewsDeliverySystem\cache
mkdir E:\NewsDeliverySystem\logs
mkdir E:\NewsDeliverySystem\backup
```

### Step 4: 環境変数の設定
```powershell
# .envファイルをコピー
copy .env.example .env

# .envファイルを編集
notepad .env
```

#### .envファイルの編集内容
```env
# NewsAPI (https://newsapi.org/) - 国内社会・IT/AI・セキュリティニュース用
# 収集対象: NHK、朝日新聞、毎日新聞、読売新聞、TechCrunch、Ars Technica、Wired、ZDNet、Krebs on Security等
NEWSAPI_KEY=your_actual_newsapi_key_here

# GNews API (https://gnews.io/) - 国際社会ニュース用
# 収集対象: BBC、CNN、Reuters、The Guardian
GNEWS_API_KEY=your_actual_gnews_key_here

# DeepL API (https://www.deepl.com/pro-api) - 英語記事翻訳用
# 海外メディアの英語記事を日本語に自動翻訳
DEEPL_API_KEY=your_actual_deepl_key_here

# Anthropic Claude API - AI分析用
# 記事の重要度評価、要約生成、キーワード抽出、センチメント分析
ANTHROPIC_API_KEY=your_actual_anthropic_key_here

# NVD API (https://nvd.nist.gov/developers) - CVE脆弱性情報用
# CVSS 9.0以上の重大脆弱性を即座通知
NVD_API_KEY=your_nvd_key_here

# Gmail API認証情報
GMAIL_CLIENT_ID=your_gmail_client_id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token

# メール設定
SENDER_EMAIL=your_sender@gmail.com
RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com

# ストレージ設定
EXTERNAL_HDD_PATH=E:\NewsDeliverySystem

# システム設定
ENVIRONMENT=production
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### Step 5: Gmail API認証の設定

#### 5.1 Google Cloud Consoleでの設定
1. https://console.cloud.google.com/ にアクセス
2. 新しいプロジェクトを作成
3. 「APIとサービス」→「ライブラリ」で Gmail API を有効化
4. 「認証情報」→「認証情報を作成」→「OAuth 2.0 クライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. クライアントIDとクライアントシークレットをメモ

#### 5.2 認証トークンの取得
```powershell
# 認証スクリプトを実行
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# credentials.jsonファイルを作成（Google Cloud Consoleからダウンロード）
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

print('Refresh Token:', creds.refresh_token)
"
```

### Step 6: 設定ファイルの編集
```powershell
notepad config\config.json
```

#### 重要な設定項目
```json
{
  "data_paths": {
    "external_hdd": "E:",
    "articles_dir": "data/articles",
    "reports_dir": "data/reports"
  },
  "delivery": {
    "schedule": {
      "regular": ["07:00", "12:00", "18:00"]
    },
    "email": {
      "enabled": true
    }
  }
}
```

## ✅ 動作確認

### Step 1: システムヘルスチェック
```powershell
python main.py check
```

期待される出力:
```
Command: check
Status: success
Database: OK
Email service: OK
Translation service: OK
AI analyzer: OK
News collector: OK
```

### Step 2: メール送信テスト
```powershell
python -c "
from src.services.email_delivery import GmailDeliveryService
service = GmailDeliveryService()
result = service.test_email_connection()
print('Email test result:', result)
"
```

### Step 3: 翻訳サービステスト
```powershell
python -c "
from src.services.translation import TranslationService
service = TranslationService()
print('Translation service enabled:', service.is_translation_enabled())
print('Usage info:', service.get_usage_info())
"
```

### Step 4: ニュース収集テスト
```powershell
python scheduler.py --run-once daily --verbose
```

## 🔄 自動スケジューリング設定

### Windows タスクスケジューラーの設定

#### 1. タスクスケジューラーを開く
```powershell
taskschd.msc
```

#### 2. 基本タスクを作成
1. 「操作」→「基本タスクの作成」
2. 名前: "News Delivery System - Daily"
3. トリガー: "毎日"
4. 時刻: "07:00" (他の時刻も同様に作成)

#### 3. 操作を設定
- プログラム: `C:\Path\To\news-env\Scripts\python.exe`
- 引数: `C:\Path\To\news-delivery-system\main.py daily`
- 開始場所: `C:\Path\To\news-delivery-system`

#### 4. 緊急チェック用タスク
- 名前: "News Delivery System - Urgent Check"
- トリガー: "繰り返し" (30分間隔)
- 引数: `C:\Path\To\news-delivery-system\main.py urgent`

### スケジューラー サービスとして実行
```powershell
# バックグラウンド実行
python scheduler.py &

# または、サービスとしてインストール
# (Windows Service Wrapperなどを使用)
```

## 📊 運用開始

### 初回実行
```powershell
# 日次収集の手動実行
python main.py daily --verbose
```

### スケジューラー起動
```powershell
# スケジューラーの開始
python scheduler.py

# スケジュール確認
python scheduler.py --show-schedule
```

### 監視とメンテナンス
```powershell
# システム状態確認
python main.py status

# ログ確認
type E:\NewsDeliverySystem\logs\news_system.log

# エラーログ確認
type E:\NewsDeliverySystem\logs\errors.log
```

## 🚨 トラブルシューティング

### 一般的な問題と解決方法

#### 1. ModuleNotFoundError
```powershell
# 仮想環境の確認
news-env\Scripts\activate
pip list

# 依存関係の再インストール
pip install -r requirements.txt --force-reinstall
```

#### 2. API認証エラー
```powershell
# APIキーの確認
python -c "import os; print('NewsAPI Key exists:', bool(os.getenv('NEWSAPI_KEY')))"

# 設定ファイルの確認
python main.py check
```

#### 3. Gmail認証失敗
```powershell
# トークンファイルの削除（再認証のため）
del token.json

# 再認証
python main.py check
```

#### 4. 外付けHDDアクセスエラー
```powershell
# ディレクトリの存在確認
dir E:\NewsDeliverySystem

# 権限確認
icacls E:\NewsDeliverySystem
```

#### 5. 文字化け問題
```powershell
# システムロケールの確認
python -c "import locale; print(locale.getpreferredencoding())"

# UTF-8設定の確認
chcp 65001
```

### ログの分析
```powershell
# エラーパターンの確認
findstr "ERROR" E:\NewsDeliverySystem\logs\*.log

# 特定日のログ
findstr "2024-01-01" E:\NewsDeliverySystem\logs\*.log
```

## 🔧 カスタマイズ

### 配信時間の変更
`config/config.json`:
```json
{
  "delivery": {
    "schedule": {
      "regular": ["06:00", "12:00", "18:00", "22:00"]
    }
  }
}
```

### 収集カテゴリの調整
```json
{
  "news_collection": {
    "categories": {
      "cybersecurity": {
        "enabled": true,
        "max_articles": 30,
        "cvss_threshold": 6.0
      }
    }
  }
}
```

### レポートテンプレートのカスタマイズ
`src/templates/report_template.html` を編集

## 📞 サポート

### よくある質問
1. **Q: APIの制限を超えた場合は？**
   A: 各APIの制限内で動作するよう自動調整されます。有料プランの検討をお勧めします。

2. **Q: 配信が停止した場合は？**
   A: `python main.py check` でシステム状態を確認し、ログを確認してください。

3. **Q: 翻訳精度を向上させるには？**
   A: DeepL Proプランへのアップグレードを検討してください。

### ログ確認コマンド
```powershell
# システム全体の状態
python main.py status

# 直近のエラー
python -c "
from src.utils.logger import LogAnalyzer
from pathlib import Path
analyzer = LogAnalyzer(Path('E:/NewsDeliverySystem/logs'))
print(analyzer.analyze_error_patterns())
"
```

## 🚀 自動化設定（v1.1.0新機能）

### スケジューラーシステムの設定

#### 1. Gmail認証の完了
```bash
# Gmail API認証をセットアップ
python setup_gmail_auth.py
```

#### 2. APIキーの検証
```bash
# 全APIキーの動作確認
python check_api_keys.py
```

#### 3. メール配信テスト
```bash
# 包括的なメール配信テスト
python test_email_delivery.py
```

#### 4. 自動スケジューラーの開始
```bash
# 前景での実行（テスト用）
python run_scheduler.py

# システムサービス化（推奨）
sudo ./install_scheduler_service.sh
sudo systemctl start news-delivery-scheduler
sudo systemctl enable news-delivery-scheduler
```

### スケジューラー管理

#### 基本コマンド
```bash
# 状態確認
python scheduler_manager.py status

# タスクの管理
python scheduler_manager.py enable daily_news_collection
python scheduler_manager.py disable weekly_summary
python scheduler_manager.py run urgent_news_check
```

#### システムサービス管理
```bash
# サービス状態確認
sudo systemctl status news-delivery-scheduler

# ログ確認
sudo journalctl -u news-delivery-scheduler -f

# サービス再起動
sudo systemctl restart news-delivery-scheduler
```

### デフォルトスケジュール

| タスク | 実行時刻 | 説明 |
|--------|----------|------|
| 日次ニュース配信 | 毎日 7:00 | 全ジャンルのニュース収集・分析・配信 |
| 緊急ニュースチェック | 毎時間 | 重要度9以上・CVSS 9.0以上の緊急確認 |
| システム健全性チェック | 毎日 23:00 | API状況・システム状態の監視 |

## 🎯 次のステップ

1. **自動化開始**: スケジューラーを設定して完全自動化
2. **2週間の試運転**: 初期設定後、2週間程度様子を見る
3. **設定の最適化**: 収集記事数や配信時間の調整
4. **フィルタリング強化**: 不要な記事の除外設定
5. **監視の自動化**: アラート機能とログ監視の活用

## 📚 追加ドキュメント

- [📋 クイックスタートガイド](QUICK_START_GUIDE.md) - 15分で開始
- [📅 スケジューラー詳細ガイド](README_SCHEDULER.md) - 自動化システム
- [📖 全ドキュメント一覧](DOCUMENTATION_INDEX.md) - ドキュメント索引

---

このガイドに従って設定することで、ニュース自動配信システムが正常に動作し、完全自動化されたニュース配信が開始されます。問題が発生した場合は、ログを確認し、適切なドキュメントを参照してください。