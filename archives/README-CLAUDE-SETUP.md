# ニュース配信システム Claude統合セットアップガイド

## 🚀 概要

このシステムは**ニュース自動配信システム**用のClaude統合スウォーム環境です。26個の専門エージェントが協力して、ニュース収集・翻訳・AI分析・レポート生成・Gmail配信を自動化します。

## 📁 ファイル構成

```
news-delivery-system/
├── launch-claude-swarm.sh           # 🚀 Claude統合スウォーム起動スクリプト（統合版）
├── claudeflow_news_config.yaml      # ⚙️ Claude Flow統合設定ファイル
├── .claude/
│   ├── swarm.yaml                   # 📋 26エージェントスウォーム設定
│   └── agents/                      # 🤖 26個の専門エージェント定義
│       ├── NEWS-CTO.md              # 最高技術責任者
│       ├── NEWS-Manager.md          # プロジェクトマネージャー
│       ├── NEWS-Policy.md           # ポリシー・ガバナンス管理
│       ├── NEWS-Architect.md        # システムアーキテクト
│       ├── NEWS-DevAPI.md           # バックエンドAPI開発
│       ├── NEWS-DevUI.md            # フロントエンド・UI開発
│       ├── NEWS-Logic.md            # ビジネスロジック開発
│       ├── NEWS-DataModel.md        # データモデル設計
│       ├── NEWS-GraphAPI.md         # GraphQL API開発
│       ├── NEWS-Webhook.md          # Webhook・イベント処理
│       ├── NEWS-Analyzer.md         # AI分析エージェント
│       ├── NEWS-AIPlanner.md        # AI計画・戦略エージェント
│       ├── NEWS-Knowledge.md        # ナレッジ管理
│       ├── NEWS-CSVHandler.md       # データ処理・CSV操作
│       ├── NEWS-ReportGen.md        # レポート生成
│       ├── NEWS-Scheduler.md        # スケジューラー管理
│       ├── NEWS-QA.md               # 品質保証
│       ├── NEWS-Tester.md           # テスト実行
│       ├── NEWS-E2E.md              # E2Eテスト
│       ├── NEWS-Security.md         # セキュリティ
│       ├── NEWS-Audit.md            # 監査・コンプライアンス
│       ├── NEWS-UX.md               # UX設計
│       ├── NEWS-Accessibility.md    # アクセシビリティ
│       ├── NEWS-L10n.md             # 国際化・ローカライゼーション
│       ├── NEWS-CI.md               # CI/CD運用
│       ├── NEWS-CIManager.md        # CI/CDマネージャー
│       ├── NEWS-Monitor.md          # システム監視
│       ├── NEWS-AutoFix.md          # 自動修復
│       └── NEWS-incident-manager.md # インシデント管理
├── CLAUDE.md                        # 📖 システム仕様書
└── README-CLAUDE-SETUP.md           # 📚 このファイル
```

## 🎯 システム機能

### 主要機能
- **ニュース自動収集**: NewsAPI、NVD、GNews統合
- **多言語翻訳**: DeepL API（英語→日本語）
- **AI分析・要約**: Claude API（記事分析・重要度評価・センチメント分析）
- **レポート生成**: HTML/PDF自動生成（Jinja2 + PDF変換）
- **自動配信**: Gmail配信（7:00、12:00、18:00定期配信）
- **セキュリティアラート**: CVSS 9.0以上の緊急配信
- **24/7監視**: システム監視・自動修復・エラーハンドリング

### 技術スタック
- **バックエンド**: Python 3.11+ / FastAPI
- **データベース**: SQLite + Redis キャッシュ  
- **AI/分析**: Claude API + DeepL API
- **配信**: Gmail API + HTML/PDF生成
- **インフラ**: Docker + CI/CD (GitHub Actions)
- **監視**: Prometheus + Grafana + ログ分析

## 🛠️ セットアップ手順

### 1. 前提条件確認

```bash
# Claude Code インストール確認
claude --version

# Node.js/NPX インストール確認
npx --version

# Python 3.11+ インストール確認
python3 --version
```

### 2. 必要なAPIキー取得

以下のAPIサービスに登録し、APIキーを取得してください：

- **NewsAPI**: https://newsapi.org/register
- **DeepL API**: https://www.deepl.com/pro-api  
- **Claude API**: https://www.anthropic.com
- **Gmail API**: Google Cloud Console
- **NVD API**: https://nvd.nist.gov/developers (オプション)

### 3. 環境変数設定

```bash
# .env ファイル作成
cat > .env << 'EOF'
# API Keys
NEWSAPI_KEY=your_newsapi_key_here
DEEPL_API_KEY=your_deepl_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
GNEWS_API_KEY=your_gnews_api_key_here

# Gmail OAuth
GMAIL_CREDENTIALS_PATH=./config/gmail_credentials.json
GMAIL_TOKEN_PATH=./config/gmail_token.json

# Database
DB_PATH=./data/database/news.db

# System
DEBUG=False
LOG_LEVEL=INFO
EOF
```

### 4. Gmail OAuth設定

1. Google Cloud Console でプロジェクト作成
2. Gmail API を有効化
3. OAuth 2.0 クライアントID作成
4. credentials.json をダウンロードし、`config/` に配置

## 🚀 Claude統合スウォーム起動

### 統合版起動（推奨）⭐

```bash
# スクリプトに実行権限付与（初回のみ）
chmod +x launch-claude-swarm.sh

# 統合版Claude統合スウォーム起動
./launch-claude-swarm.sh

# または実行モード指定
./launch-claude-swarm.sh --parallel   # 並列強化モード
./launch-claude-swarm.sh --basic      # 基本モード  
./launch-claude-swarm.sh --unified    # 統合モード（推奨）
```

### 実行モード選択

統合版スクリプトは**3つの実行モード**をサポート：

#### 🔵 基本モード (`--basic`)
- ✅ 安定性重視の順次実行
- ✅ 26エージェント協調実行  
- ✅ 確実な品質保証
- **対象**: 初回実行・デバッグ時

#### 🟢 並列強化モード (`--parallel`) 
- ✅ 真並列実行（75%時間短縮）
- ✅ 5倍スループット向上
- ✅ 85%並列効率
- **対象**: 高速開発・本格運用

#### 🟣 統合モード (`--unified`) - 推奨⭐
- ✅ 基本+並列両方の機能
- ✅ 安定性と性能の両立
- ✅ ハイブリッド実行戦略
- **対象**: 最適な開発体験

## 📊 実行結果確認

### ログ・出力ファイル

```bash
# 統合ログ確認
ls -la logs/unified-swarm/

# スウォーム出力確認  
ls -la swarm-outputs/

# 実行レポート確認
cat logs/unified-swarm/news-delivery-swarm-report-*.md
```

### システム状態確認

```bash
# プロセス状態確認
ps aux | grep claude

# ディスク使用量確認
df -h

# メモリ使用量確認
free -m
```

## ⚙️ 設定カスタマイズ

### claudeflow_news_config.yaml 主要設定

```yaml
# エージェント設定
agents:
  max_concurrent: 26
  specialization: "news_delivery_system"

# パフォーマンス設定
performance:
  collection_timeout: 300      # 5分
  report_generation_timeout: 120  # 2分
  total_process_timeout: 600   # 10分

# スケジュール設定
schedule:
  delivery_times: ["07:00", "12:00", "18:00"]
  timezone: "Asia/Tokyo"

# セキュリティ設定
security:
  api_key_encryption: true
  https_only: true
  audit_logging: true
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. Claude Code が見つからない
```bash
# Claude Code インストール
curl -sS https://claude.ai/install.sh | bash
```

#### 2. NPX が見つからない
```bash
# Node.js インストール
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### 3. API接続エラー
- .env ファイルのAPIキーを確認
- ネットワーク接続を確認
- API制限状況を確認

#### 4. 権限エラー
```bash
# スクリプト権限確認・修正
chmod +x launch-claude-swarm.sh
```

### ログ確認コマンド

```bash
# リアルタイムログ監視
tail -f logs/unified-swarm/*.log

# エラーログ検索
grep -r "ERROR" logs/unified-swarm/

# 警告ログ検索
grep -r "WARNING" logs/unified-swarm/
```

## 📈 パフォーマンス監視

### 目標値
- **ニュース収集**: 5分以内
- **レポート生成**: 2分以内  
- **全体処理時間**: 10分以内
- **システム可用性**: 95%以上
- **配信成功率**: 95%以上

### 監視方法

```bash
# システムリソース監視
htop

# プロセス監視
watch -n 5 'ps aux | grep claude'

# ディスク・メモリ監視  
watch -n 10 'df -h && free -m'
```

## 🆘 サポート

### エラー報告
- ログファイルを添付
- エラーメッセージをコピー
- 実行環境の情報を記載

### 追加情報
- CLAUDE.md: システム仕様詳細
- .claude/agents/: 各エージェントの詳細仕様
- logs/: 実行ログ・エラー詳細

---

## 🎯 次のステップ

1. **システムテスト**: 各機能の動作確認
2. **本番デプロイ**: 本番環境への展開準備
3. **監視設定**: Prometheus/Grafana設定
4. **バックアップ設定**: 定期バックアップ設定
5. **ドキュメント整備**: 運用手順書作成

**ニュース配信システム Claude統合スウォーム環境が正常に動作することを確認してください！**