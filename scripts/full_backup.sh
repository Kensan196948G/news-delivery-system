#!/bin/bash

# フルバックアップスクリプト
# 30分おきに実行される自動バックアップ

# 設定
SOURCE_DIR="/mnt/Linux-ExHDD/news-delivery-system"
BACKUP_BASE_DIR="/mnt/Linux-ExHDD/news-delivery-system-BackUp"
LOG_DIR="${SOURCE_DIR}/logs"

# タイムスタンプ生成（YYYYMMDDHHMM形式）
TIMESTAMP=$(date +"%Y%m%d%H%M")
BACKUP_DIR="${BACKUP_BASE_DIR}/news-delivery-system-${TIMESTAMP}"

# ログファイル
LOG_FILE="${LOG_DIR}/backup_${TIMESTAMP}.log"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# エラーハンドリング
set -e
trap 'handle_backup_error $LINENO' ERR

# バックアップエラー処理関数
handle_backup_error() {
    local line_number="$1"
    local error_details="Backup failed at line $line_number\nTimestamp: $(date)\nBackup directory: $BACKUP_DIR"
    
    log "ERROR: Backup failed at line $line_number"
    
    # エラー通知送信
    source "${SOURCE_DIR}/scripts/error_notifier.sh"
    notify_backup_error "$error_details" "$LOG_FILE"
}

# バックアップ開始
log "=== フルバックアップ開始 ==="
log "バックアップ元: $SOURCE_DIR"
log "バックアップ先: $BACKUP_DIR"

# バックアップディレクトリ作成
mkdir -p "$BACKUP_DIR"
log "バックアップディレクトリ作成: $BACKUP_DIR"

# rsyncでフルバックアップ実行
# --archive: アーカイブモード（パーミッション、タイムスタンプ保持）
# --verbose: 詳細出力
# --exclude: 不要なファイルを除外
log "rsyncでバックアップ開始..."

rsync -av \
    --exclude='logs/backup_*.log' \
    --exclude='cache/*' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.env' \
    "$SOURCE_DIR/" "$BACKUP_DIR/" >> "$LOG_FILE" 2>&1

# バックアップサイズ確認
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "バックアップサイズ: $BACKUP_SIZE"

# 古いバックアップの削除（7日以上前）
log "古いバックアップのクリーンアップ開始..."
find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "news-delivery-system-*" -mtime +7 -print0 | while IFS= read -r -d '' old_backup; do
    log "削除: $old_backup"
    rm -rf "$old_backup"
done

# バックアップ完了
log "=== フルバックアップ完了 ==="
log "バックアップ先: $BACKUP_DIR"
log "バックアップサイズ: $BACKUP_SIZE"

# 成功通知
exit 0