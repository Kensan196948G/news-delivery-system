# ニュース配信システム 自動バックアップシステム

## 概要
30分ごとに自動的にシステム全体のバックアップを実行します。

## バックアップ設定

### バックアップ場所
- **バックアップ元**: `/media/kensan/LinuxHDD/news-delivery-system/`
- **バックアップ先**: `/media/kensan/LinuxHDD/news-delivery-system-BackUp/`
- **バックアップ形式**: `news-delivery-system-YYYYMMDDHHMM`

### 実行スケジュール
- **頻度**: 30分ごと（毎時00分と30分）
- **Cronジョブ**: `*/30 * * * * /media/kensan/LinuxHDD/news-delivery-system/scripts/backup.sh`

## 機能詳細

### 1. 自動バックアップ
- rsyncを使用した高速・効率的なバックアップ
- 差分同期による効率的なディスク使用

### 2. 除外設定
以下のディレクトリ/ファイルはバックアップから除外：
- `venv/`, `news-env/` - 仮想環境
- `__pycache__/`, `*.pyc` - Pythonキャッシュ
- `.git/` - Gitリポジトリ
- `*.log` - ログファイル
- `node_modules/` - Node.jsモジュール
- `.env` - 環境変数ファイル（セキュリティ）

### 3. 自動クリーンアップ
- 7日以上前のバックアップを自動削除
- ディスク容量の効率的な管理

### 4. ロギング
- バックアップログ: `/media/kensan/LinuxHDD/news-delivery-system-BackUp/backup.log`
- ログファイルは10MBを超えると自動ローテート

### 5. ディスク容量監視
- 残り容量が10GB未満になると警告をログに記録

## 管理コマンド

### バックアップの手動実行
```bash
/media/kensan/LinuxHDD/news-delivery-system/scripts/backup.sh
```

### Cronジョブの確認
```bash
crontab -l
```

### バックアップ一覧の確認
```bash
ls -la /media/kensan/LinuxHDD/news-delivery-system-BackUp/
```

### ログの確認
```bash
tail -f /media/kensan/LinuxHDD/news-delivery-system-BackUp/backup.log
```

### バックアップからの復元
```bash
# 特定のバックアップから復元
rsync -av /media/kensan/LinuxHDD/news-delivery-system-BackUp/news-delivery-system-YYYYMMDDHHMM/ /media/kensan/LinuxHDD/news-delivery-system/
```

## トラブルシューティング

### Cronジョブが実行されない場合
1. Cronサービスの状態確認
   ```bash
   systemctl status cron
   ```

2. Cronジョブの再設定
   ```bash
   /media/kensan/LinuxHDD/news-delivery-system/scripts/setup_backup_cron.sh
   ```

### ディスク容量不足
1. 古いバックアップの手動削除
   ```bash
   find /media/kensan/LinuxHDD/news-delivery-system-BackUp/ -maxdepth 1 -type d -name "news-delivery-system-*" -mtime +3 -exec rm -rf {} \;
   ```

2. ログファイルのクリア
   ```bash
   > /media/kensan/LinuxHDD/news-delivery-system-BackUp/backup.log
   ```

## セキュリティ考慮事項
- `.env`ファイルはバックアップから除外（APIキー保護）
- バックアップディレクトリのアクセス権限は所有者のみ
- ログファイルに機密情報を含まない設計