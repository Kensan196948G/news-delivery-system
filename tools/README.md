# 🛠️ Tools Directory - ツールディレクトリ

このディレクトリには、ニュース配信システムの管理・設定・テスト用ツールが含まれています。

## 📋 含まれるツール

### 🔐 認証・設定ツール
| ファイル | 説明 | 使用例 |
|---------|------|-------|
| `setup_gmail_auth.py` | Gmail API認証設定 | `python tools/setup_gmail_auth.py` |
| `check_api_keys.py` | 全APIキー検証 | `python tools/check_api_keys.py` |

### ⏰ スケジューラー管理ツール
| ファイル | 説明 | 使用例 |
|---------|------|-------|
| `run_scheduler.py` | スケジューラー起動 | `python tools/run_scheduler.py` |
| `scheduler_manager.py` | スケジューラー管理CLI | `python tools/scheduler_manager.py status` |

### ✅ テストツール
| ファイル | 説明 | 使用例 |
|---------|------|-------|
| `test_email_delivery.py` | メール配信テスト | `python tools/test_email_delivery.py` |

## 📖 詳細な使用方法

各ツールの詳細な使用方法については、以下のドキュメントを参照してください：
- [クイックスタートガイド](../QUICK_START_GUIDE.md)
- [スケジューラー詳細ガイド](../README_SCHEDULER.md)
- [メインマニュアル](../README.md)