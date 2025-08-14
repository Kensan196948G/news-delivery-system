# ⚙️ System Directory - システムディレクトリ

このディレクトリには、システム設定・サービス化・運用管理に関するファイルが含まれています。

## 🚀 PC自動起動設定

PC起動・再起動時にニュース配信システムが自動的に起動するように設定されています。

### ⚡ 自動起動インストール方法

```bash
# システムに自動起動サービスをインストール（要管理者権限）
sudo /media/kensan/LinuxHDD/news-delivery-system/system/install_auto_start.sh

# 動作テスト
/media/kensan/LinuxHDD/news-delivery-system/system/test_auto_start.sh
```

### 📧 起動時動作

PC起動時に自動的に以下が実行されます：
1. システム初期化テスト ✅
2. 配信スケジュール確認 ⏰
3. 起動通知メール送信 📧 (`kensan1969@gmail.com`)

### 📊 管理コマンド

```bash
# サービス状態確認
sudo systemctl status news-delivery-startup.service

# 手動テスト実行
./test_auto_start.sh

# 自動起動無効化
sudo systemctl disable news-delivery-startup.service
```

## 📋 含まれるファイル

### 🔧 システム設定
| ファイル | 説明 | 編集可能 |
|---------|------|---------|
| `schedule_config.json` | スケジュール設定ファイル | ✅ |

### 🖥️ システムサービス
| ファイル/ディレクトリ | 説明 | 使用例 |
|---------------------|------|-------|
| `install_scheduler_service.sh` | systemdサービス化スクリプト | `sudo ./system/install_scheduler_service.sh` |
| `systemd/` | systemd設定ファイル | - |

## ⚙️ システム設定の編集

### スケジュール設定の変更
```bash
# 設定ファイルを編集
nano system/schedule_config.json

# スケジューラーを再起動（サービス化済みの場合）
sudo systemctl restart news-delivery-scheduler
```

### サービス管理
```bash
# サービス化
sudo ./system/install_scheduler_service.sh

# サービス状態確認
sudo systemctl status news-delivery-scheduler

# サービス開始/停止
sudo systemctl start news-delivery-scheduler
sudo systemctl stop news-delivery-scheduler
```

## 📖 詳細情報

詳細な設定方法については、[スケジューラー詳細ガイド](../README_SCHEDULER.md)を参照してください。