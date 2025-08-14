# 📚 ニュース配信システム - ドキュメント一覧

## 📖 利用者向けドキュメント

### 🚀 はじめに
| ドキュメント | 説明 | 対象ユーザー | 状況 |
|-------------|------|-------------|------|
| [📋 QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) | **5分クイックスタート** - Gmail認証のみで稼働開始 | 🔰 初心者 | ✅ **最新** |
| [📖 README.md](README.md) | **詳細マニュアル** - 機能・設定・使用方法の完全ガイド | 👥 全ユーザー | ✅ **最新** |
| [⚙️ SETUP_GUIDE.md](SETUP_GUIDE.md) | **セットアップガイド** - 詳細な環境構築手順 | 🔧 設定担当者 | ⚠️ **要更新** |

### ⏰ スケジューラー機能
| ドキュメント | 説明 | 対象ユーザー |
|-------------|------|-------------|
| [📅 README_SCHEDULER.md](README_SCHEDULER.md) | **スケジューラー完全ガイド** - 自動実行システム | 👨‍💼 管理者 |

### 🔧 技術設定
| ドキュメント | 説明 | 対象ユーザー |
|-------------|------|-------------|
| [🔑 docs/API_KEYS_SETUP.md](docs/API_KEYS_SETUP.md) | **APIキー設定詳細** - 各API認証手順 | 🔧 設定担当者 |
| [💻 docs/TMUX_GUIDE.md](docs/TMUX_GUIDE.md) | **TMUX使用ガイド** - セッション管理 | 👨‍💻 開発者 |
| [🖥️ TMUX_DEVELOPMENT_GUIDE.md](TMUX_DEVELOPMENT_GUIDE.md) | **TMUX開発環境ガイド** - パターンAレイアウト・指示システム | 👨‍💻 開発者 |

---

## 🛠️ 実行スクリプト一覧

### 🔄 メイン実行
| スクリプト | 説明 | 使用例 |
|-----------|------|-------|
| `main.py` | **基本実行スクリプト** | `python main.py daily` |
| `run_scheduler.py` | **スケジューラー起動** | `python run_scheduler.py` |
| `scheduler_manager.py` | **スケジューラー管理CLI** | `python scheduler_manager.py status` |

### 🔐 認証・設定
| スクリプト | 説明 | 使用例 |
|-----------|------|-------|
| `setup_gmail_auth.py` | **Gmail認証設定** | `python setup_gmail_auth.py` |
| `check_api_keys.py` | **APIキー検証** | `python check_api_keys.py` |

### ✅ テスト・検証
| スクリプト | 説明 | 使用例 |
|-----------|------|-------|
| `test_email_delivery.py` | **メール配信テスト** | `python test_email_delivery.py` |
| `tests/test_system.py` | **システムテスト** | `python -m pytest tests/` |

### ⚙️ システム管理
| スクリプト | 説明 | 使用例 |
|-----------|------|-------|
| `install_scheduler_service.sh` | **システムサービス化** | `sudo ./install_scheduler_service.sh` |

### 🖥️ tmux開発環境
| スクリプト | 説明 | 使用例 |
|-----------|------|-------|
| `scripts/simple-tmux-setup.sh` | **tmux環境セットアップ** | `./scripts/simple-tmux-setup.sh` |
| `scripts/tmux-pane-commander.sh` | **ペイン間指示システム** | `./scripts/tmux-pane-commander.sh help` |
| `scripts/fix-claude-startup.sh` | **Claude Yolo起動修正** | `./scripts/fix-claude-startup.sh` |

---

## 📁 設定ファイル一覧

### 🔧 主要設定
| ファイル | 説明 | 編集対象 |
|---------|------|---------|
| `.env` | **環境変数** - APIキー・メール設定 | ✅ 必須 |
| `config/config.json` | **システム設定** - 収集・分析パラメータ | ⚙️ オプション |
| `schedule_config.json` | **スケジュール設定** - 実行タイミング | ⏰ オプション |

### 🔒 認証ファイル
| ファイル | 説明 | 自動生成 |
|---------|------|---------|
| `token.json` | **Gmail認証トークン** | ✅ 自動 |
| `credentials.json` | **Gmail認証情報**（一時的） | ✅ 自動 |

### 📊 状態管理
| ファイル | 説明 | 自動生成 |
|---------|------|---------|
| `scheduler_state.json` | **スケジューラー状態** | ✅ 自動 |

---

## 📊 出力・ログ

### 📈 レポート出力
| ディレクトリ | 説明 | 保持期間 |
|-------------|------|---------|
| `reports/` | **日次・緊急レポート** (HTML/PDF) | 30日 |
| `E:/NewsDeliverySystem/reports/` | **外付けHDD保存** | 永続 |

### 📝 ログファイル
| ファイル | 説明 | 保持期間 |
|---------|------|---------|
| `logs/scheduler.log` | **スケジューラーログ** | 30日 |
| `logs/system_health.json` | **システム健全性チェック結果** | 30日 |
| `logs/performance.log` | **パフォーマンスログ** | 30日 |

### ✅ テスト結果
| ディレクトリ | 説明 | 保持期間 |
|-------------|------|---------|
| `reports/email_delivery_test_results_*.json` | **メール配信テスト結果** | 永続 |

---

## 🎯 用途別ドキュメント選択ガイド

### 🔰 **初めて使う方 (95%完了済み)**
1. ➡️ [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - **5分で開始** ⚡
2. ➡️ [README.md](README.md) - 詳細機能確認

### 👨‍💼 **システム管理者**
1. ➡️ [README_SCHEDULER.md](README_SCHEDULER.md) - スケジューラー管理
2. ➡️ [docs/API_KEYS_SETUP.md](docs/API_KEYS_SETUP.md) - API管理

### 🔧 **設定・カスタマイズ担当**
1. ➡️ [SETUP_GUIDE.md](SETUP_GUIDE.md) - 詳細設定
2. ➡️ [README.md](README.md) - 設定項目詳細

### 👨‍💻 **開発者・トラブルシューティング**
1. ➡️ [README.md](README.md) - 開発者向け情報
2. ➡️ [docs/TMUX_GUIDE.md](docs/TMUX_GUIDE.md) - セッション管理

---

## 🆘 困ったときのドキュメント

| 問題 | 参照ドキュメント | セクション |
|------|-----------------|-----------|
| ❌ システムが動かない | [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) | トラブルシューティング |
| ❌ Gmail認証エラー | [docs/API_KEYS_SETUP.md](docs/API_KEYS_SETUP.md) | Gmail API設定 |
| ❌ スケジューラー問題 | [README_SCHEDULER.md](README_SCHEDULER.md) | トラブルシューティング |
| ❌ API制限・エラー | [README.md](README.md) | トラブルシューティング |
| ❌ メール配信失敗 | [README.md](README.md) | Gmail認証失敗 |

---

## 📞 サポート情報

### 🔍 問題調査の手順
1. **エラーログ確認**: `sudo journalctl -u news-delivery-scheduler --no-pager`
2. **APIキー確認**: `python check_api_keys.py`
3. **テスト実行**: `python test_email_delivery.py`
4. **ドキュメント確認**: この一覧から適切なドキュメントを選択

### 📝 問題報告時の情報
- OS・Python バージョン
- エラーメッセージ
- 実行していたコマンド
- ログファイルの内容

---

**🎯 ヒント**: 問題解決の95%は、適切なドキュメントを読むことで解決できます！