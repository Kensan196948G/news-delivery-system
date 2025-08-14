#!/bin/bash

# Cron ラッパースクリプト
# 各cronジョブを実行し、エラー発生時に通知を送信

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"

# エラー通知スクリプトを読み込み
source "$SCRIPT_DIR/error_notifier.sh"

# ログクリーンアップ用ラッパー
run_log_cleanup() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_file="$LOG_DIR/log_cleanup_$(date +%Y%m).log"
    
    echo "[$timestamp] Starting weekly log cleanup" >> "$log_file"
    
    # ログクリーンアップ実行
    if find "$LOG_DIR" -name "*.log" -mtime +30 -delete >> "$log_file" 2>&1; then
        echo "[$timestamp] Log cleanup completed successfully" >> "$log_file"
    else
        local error_details="Weekly log cleanup failed\nTimestamp: $timestamp\nDirectory: $LOG_DIR\nError: $(find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>&1)"
        
        echo "[$timestamp] Log cleanup failed" >> "$log_file"
        notify_log_cleanup_error "$error_details" "$log_file"
        exit 1
    fi
}

# ヘルスチェック用ラッパー
run_health_check() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_file="$LOG_DIR/health_check_$(date +%Y%m).log"
    
    echo "[$timestamp] Starting monthly health check" >> "$log_file"
    
    # ヘルスチェック実行
    if "$SCRIPT_DIR/robust_cron_runner.sh" --health-check >> "$log_file" 2>&1; then
        echo "[$timestamp] Health check completed successfully" >> "$log_file"
    else
        local error_details="Monthly health check failed\nTimestamp: $timestamp\nError: $(tail -10 "$log_file" 2>/dev/null || echo 'No log details available')"
        
        echo "[$timestamp] Health check failed" >> "$log_file"
        notify_health_check_error "$error_details" "$log_file"
        exit 1
    fi
}

# メイン処理
case "$1" in
    "log_cleanup")
        run_log_cleanup
        ;;
    "health_check")
        run_health_check
        ;;
    *)
        echo "Usage: $0 {log_cleanup|health_check}"
        echo "  log_cleanup  - Run weekly log cleanup with error notification"
        echo "  health_check - Run monthly health check with error notification"
        exit 1
        ;;
esac