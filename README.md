# 🤖 ニュース自動配信システム

[![Main CI/CD Pipeline](https://github.com/Kensan196948G/news-delivery-system/actions/workflows/main-ci-cd.yml/badge.svg)](https://github.com/Kensan196948G/news-delivery-system/actions/workflows/main-ci-cd.yml)
[![Local CI Pipeline](https://github.com/Kensan196948G/news-delivery-system/actions/workflows/local-ci.yml/badge.svg)](https://github.com/Kensan196948G/news-delivery-system/actions/workflows/local-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)

**完全自動化対応のニュース収集・AI分析・配信システム**

## ✨ 主な特徴

### 🤖 **完全自動化CI/CDシステム**
- **7段階CI/CDパイプライン**: 品質チェック→テスト→ビルド→自動修復→デプロイ準備→健全性チェック→通知
- **自動エラー修復**: インポート・型ヒント・依存関係・設定ファイルの自動修正
- **マルチ環境テスト**: Ubuntu/Windows × Python 3.10/3.11/3.12
- **セルフヒーリング**: 5種類の自動修復アクション実装

### 📰 **高品質ニュース配信**
- **AI要約**: Claude APIによる200-250文字要約
- **多言語翻訳**: DeepL API（有料版対応）による高精度翻訳
- **英語/日本語分離表示**: 原文と翻訳を見やすく分離
- **フォールバック翻訳**: DeepL失敗時の簡易翻訳機能
- **美しいレポート**: HTML/PDF形式で自動生成
- **分類配信**: 重要度・カテゴリ別整理

### 🛡️ **エンタープライズレベルセキュリティ**
- **脆弱性自動検出**: Safety・Bandit・CodeQL統合
- **暗号化通信**: 全API通信のTLS暗号化
- **アクセス制御**: OAuth2・環境変数管理
- **監査ログ**: 全処理の詳細記録

### 🔄 **クロスプラットフォーム対応**
- **環境自動判別**: Windows/Linux環境を自動検出
- **動的パス解決**: 実行環境に応じた自動パス変換
- **スケジューラ統合**: cron（Linux）/Task Scheduler（Windows）両対応

---

## 🚀 クイックスタート

### システム要件
- **OS**: Linux (Ubuntu 20.04+) / Windows 10+
- **Python**: 3.10以上
- **メモリ**: 2GB以上
- **ディスク**: 10GB以上の空き容量
- **ネットワーク**: 安定したインターネット接続

### 📦 依存関係
- **Gmail アカウント** (アプリパスワード設定済み)
- **API キー**:
  - NewsAPI: ニュース収集用
  - DeepL: 翻訳用（無料版・有料版両対応）
  - Claude (Anthropic): AI分析用
  - GNews: 補助的ニュース収集用（オプション）

### 🛠️ インストール

#### 1. リポジトリのクローン
```bash
git clone https://github.com/Kensan196948G/news-delivery-system.git
cd news-delivery-system
```

#### 2. 仮想環境のセットアップ
```bash
# 仮想環境セットアップスクリプトを実行
./scripts/setup_venv.sh

# 仮想環境を有効化
source venv/bin/activate
```

#### 3. 環境変数の設定
```bash
# .envファイルをコピーして編集
cp .env.example .env
nano .env

# 必須設定:
# - NEWSAPI_KEY=your_key_here
# - DEEPL_API_KEY=your_key_here
# - ANTHROPIC_API_KEY=your_key_here
# - SENDER_EMAIL=your_email@gmail.com
# - RECIPIENT_EMAILS=recipient@example.com
```

#### 4. Gmail認証の設定
```bash
# Gmail OAuth認証のセットアップ
python tools/setup_gmail_auth.py
```

### 🎯 使用方法

#### 手動実行
```bash
# 通常実行
python src/main.py

# テストモード実行（メール送信なし）
python src/main.py --test

# 緊急チェックのみ
python src/main.py --emergency-only
```

#### 自動スケジュール設定
```bash
# スケジューラの設定（7:00, 12:00, 18:00に自動実行）
python src/utils/scheduler_manager.py setup

# スケジュールの確認
python src/utils/scheduler_manager.py list

# スケジュールの削除
python src/utils/scheduler_manager.py remove
```

#### ローカルCI/CD実行
```bash
# ローカルCIパイプラインの実行
./scripts/run_local_ci.sh
```

### 📊 ヘルスモニタリング

システムの健全性を監視：
```bash
# ヘルスモニタの起動
python src/monitoring/health_monitor.py
```

監視項目：
- CPU/メモリ/ディスク使用率
- API接続状態
- データベースサイズ
- キャッシュ状態
- ネットワーク接続性

---

## 📁 プロジェクト構造

```
news-delivery-system/
├── src/                      # ソースコード
│   ├── collectors/          # ニュース収集モジュール
│   ├── processors/          # 翻訳・分析モジュール
│   ├── generators/          # レポート生成モジュール
│   ├── notifiers/           # メール配信モジュール
│   ├── monitoring/          # 監視モジュール
│   ├── utils/              # ユーティリティ
│   └── main.py             # メインプログラム
├── tests/                   # テストコード
├── scripts/                 # スクリプト類
│   ├── fix_imports.py      # インポート自動修正
│   ├── fix_type_hints.py   # 型ヒント自動修正
│   ├── fix_dependencies.py # 依存関係自動修正
│   └── fix_config.py       # 設定自動修正
├── config/                  # 設定ファイル
├── templates/               # HTMLテンプレート
└── .github/workflows/       # GitHub Actions
```

---

## 🧪 テスト

```bash
# 統合テストの実行
pytest tests/test_integration.py -v

# 全テストの実行
pytest tests/ -v --cov=src

# 特定のテストのみ実行
pytest tests/test_integration.py::TestPathResolver -v
```

現在のテストカバレッジ: **19/19 (100%)** ✅

---

## 🚢 デプロイメント

### GitHub Actions
プッシュ時に自動的に以下が実行されます：
1. コード品質チェック（Ruff, Black, isort, mypy）
2. セキュリティスキャン（Bandit, Safety）
3. マルチ環境テスト
4. エラー自動修復
5. ビルド＆パッケージング

### 本番環境へのデプロイ
```bash
# デプロイ準備
python scripts/prepare_deployment.py

# システムサービスとして登録（Linux）
sudo cp system/news-delivery-scheduler.service /etc/systemd/system/
sudo systemctl enable news-delivery-scheduler
sudo systemctl start news-delivery-scheduler
```

---

## 📈 パフォーマンス

- **ニュース収集**: 5分以内で完了
- **レポート生成**: 2分以内で完了
- **全体処理時間**: 10分以内
- **並行処理**: 最大6カテゴリ同時収集
- **キャッシュ**: API応答1時間、翻訳24時間、分析7日間

---

## 🔒 セキュリティ

- APIキーは環境変数で管理
- 全通信はHTTPS/TLS暗号化
- SQLインジェクション対策実装
- XSS対策（HTMLエスケープ）
- レート制限実装
- 監査ログ記録

---

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルをご覧ください。

---

## 🤝 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容について議論してください。

1. フォーク
2. フィーチャーブランチ作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

---

## 📞 サポート

問題が発生した場合は、[Issues](https://github.com/Kensan196948G/news-delivery-system/issues)で報告してください。

---

## 🙏 謝辞

- [NewsAPI](https://newsapi.org/) - ニュースデータ提供
- [DeepL](https://www.deepl.com/) - 高品質翻訳
- [Anthropic Claude](https://www.anthropic.com/) - AI分析
- [Python Community](https://www.python.org/community/) - 素晴らしいツールとライブラリ

---

**開発**: Claude Code による完全自動実装
**最終更新**: 2025年8月20日