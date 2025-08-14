#!/bin/bash
# Cronジョブ設定スクリプト

SCRIPT_PATH="/media/kensan/LinuxHDD/news-delivery-system/scripts/backup.sh"
CRON_JOB="*/30 * * * * ${SCRIPT_PATH}"

# 現在のcrontabを取得
crontab -l > /tmp/current_cron 2>/dev/null || touch /tmp/current_cron

# 既存のバックアップジョブを削除（重複防止）
grep -v "${SCRIPT_PATH}" /tmp/current_cron > /tmp/new_cron

# 新しいバックアップジョブを追加
echo "${CRON_JOB}" >> /tmp/new_cron

# 新しいcrontabを設定
crontab /tmp/new_cron

# 一時ファイルを削除
rm -f /tmp/current_cron /tmp/new_cron

echo "Cronジョブが設定されました:"
echo "${CRON_JOB}"
echo ""
echo "現在のcrontab:"
crontab -l