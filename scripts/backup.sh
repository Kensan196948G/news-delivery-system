#!/bin/bash
# News Delivery System Automatic Backup Script
# 30分ごとにフルバックアップを実行

# バックアップ元とバックアップ先の設定
# スクリプトの場所から相対パスで設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)/news-delivery-system-BackUp"

# 日付フォーマット（YYYYMMDDHHMM）
DATE_FORMAT=$(date +"%Y%m%d%H%M")
BACKUP_DIR="${BACKUP_BASE_DIR}/news-delivery-system-${DATE_FORMAT}"

# ログファイル
LOG_FILE="${BACKUP_BASE_DIR}/backup.log"

# バックアップ実行関数
perform_backup() {
    echo "[$(date)] バックアップ開始: ${BACKUP_DIR}" >> "${LOG_FILE}"
    
    # rsyncでバックアップ実行（除外設定付き）
    rsync -av --delete \
        --exclude='venv/' \
        --exclude='news-env/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.git/' \
        --exclude='*.log' \
        --exclude='node_modules/' \
        --exclude='.env' \
        "${SOURCE_DIR}/" "${BACKUP_DIR}/" >> "${LOG_FILE}" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "[$(date)] バックアップ完了: ${BACKUP_DIR}" >> "${LOG_FILE}"
        
        # バックアップサイズを記録
        SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
        echo "[$(date)] バックアップサイズ: ${SIZE}" >> "${LOG_FILE}"
    else
        echo "[$(date)] バックアップ失敗: ${BACKUP_DIR}" >> "${LOG_FILE}"
        exit 1
    fi
}

# 古いバックアップの削除（7日以上前のものを削除）
cleanup_old_backups() {
    echo "[$(date)] 古いバックアップの削除開始" >> "${LOG_FILE}"
    
    find "${BACKUP_BASE_DIR}" -maxdepth 1 -type d -name "news-delivery-system-*" -mtime +7 -exec rm -rf {} \; 2>/dev/null
    
    echo "[$(date)] 古いバックアップの削除完了" >> "${LOG_FILE}"
}

# ディスク容量チェック
check_disk_space() {
    AVAILABLE_SPACE=$(df -BG "${BACKUP_BASE_DIR}" | awk 'NR==2 {print $4}' | sed 's/G//')
    
    if [ "$AVAILABLE_SPACE" -lt 10 ]; then
        echo "[$(date)] 警告: ディスク容量が少なくなっています（残り: ${AVAILABLE_SPACE}GB）" >> "${LOG_FILE}"
    fi
}

# メイン処理
main() {
    # バックアップベースディレクトリの確認
    if [ ! -d "${BACKUP_BASE_DIR}" ]; then
        mkdir -p "${BACKUP_BASE_DIR}"
    fi
    
    # ログファイルの初期化（サイズが10MBを超えたらローテート）
    if [ -f "${LOG_FILE}" ] && [ $(stat -c%s "${LOG_FILE}") -gt 10485760 ]; then
        mv "${LOG_FILE}" "${LOG_FILE}.old"
        echo "[$(date)] ログファイルをローテートしました" > "${LOG_FILE}"
    fi
    
    echo "========================================" >> "${LOG_FILE}"
    echo "[$(date)] バックアップスクリプト開始" >> "${LOG_FILE}"
    
    # ディスク容量チェック
    check_disk_space
    
    # バックアップ実行
    perform_backup
    
    # 古いバックアップの削除
    cleanup_old_backups
    
    echo "[$(date)] バックアップスクリプト終了" >> "${LOG_FILE}"
    echo "========================================" >> "${LOG_FILE}"
}

# スクリプト実行
main