#!/bin/bash
#
# News Delivery System Auto-Start Script
# ニュース配信システム自動起動スクリプト
#
# This script is called by systemd on system startup
# to initialize the news delivery system
#

# 設定変数
PROJECT_ROOT="/mnt/Linux-ExHDD/news-delivery-system"
VENV_PATH="$PROJECT_ROOT/venv"
PYTHON_PATH="$VENV_PATH/bin/python"
LOG_DIR="$PROJECT_ROOT/logs"
STARTUP_LOG="$LOG_DIR/startup_$(date +%Y%m%d).log"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# 実行時刻
STARTUP_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$STARTUP_TIME] ======= News Delivery System Startup =======" >> "$STARTUP_LOG"

# 関数: ログ出力
log_info() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] INFO: $1" >> "$STARTUP_LOG"
    echo "INFO: $1"
}

log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] ERROR: $1" >> "$STARTUP_LOG"
    echo "ERROR: $1" >&2
}

# 関数: システムチェック
check_system() {
    log_info "Starting system checks"
    
    # プロジェクトディレクトリ確認
    if [ ! -d "$PROJECT_ROOT" ]; then
        log_error "Project directory not found: $PROJECT_ROOT"
        return 1
    fi
    
    # 仮想環境確認
    if [ ! -f "$PYTHON_PATH" ]; then
        log_error "Python executable not found: $PYTHON_PATH"
        return 1
    fi
    
    # 設定ファイル確認
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error "Environment file not found: $PROJECT_ROOT/.env"
        return 1
    fi
    
    if [ ! -f "$PROJECT_ROOT/config/config.json" ]; then
        log_error "Configuration file not found: $PROJECT_ROOT/config/config.json"
        return 1
    fi
    
    log_info "System checks completed successfully"
    return 0
}

# 関数: サービス起動確認
start_services() {
    log_info "Starting news delivery services"
    
    cd "$PROJECT_ROOT"
    
    # システム初期化テスト
    log_info "Testing system initialization"
    source "$VENV_PATH/bin/activate"
    
    if "$PYTHON_PATH" src/main.py --mode test >> "$STARTUP_LOG" 2>&1; then
        log_info "System initialization test successful"
    else
        log_error "System initialization test failed"
        return 1
    fi
    
    # crontabが有効か確認
    if crontab -l | grep -q "news-delivery-system"; then
        log_info "Crontab schedule confirmed active"
    else
        log_error "Crontab schedule not found - news delivery may not run automatically"
    fi
    
    log_info "Services startup completed"
    return 0
}

# 関数: 起動通知メール送信
send_startup_notification() {
    log_info "Sending startup notification email"
    
    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"
    
    # 起動通知メール送信
    "$PYTHON_PATH" -c "
import asyncio
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

async def send_notification():
    try:
        sender = 'kensan1969@gmail.com'
        password = 'sxsg mzbv ubsa jtok'
        recipient = 'kensan1969@gmail.com'
        
        startup_time = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        
        subject = '🚀 ニュース配信システム - システム起動通知'
        body = f'''ニュース配信システムが起動しました。

起動時刻: {startup_time}
システム状態: ✅ 正常起動完了
配信スケジュール: 7:00, 12:00, 18:00

次回配信予定:
- 朝刊: 明朝 7:00
- 昼刊: 本日 12:00  
- 夕刊: 本日 18:00

システムは自動的に定期配信を開始します。
'''
        
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f'Notification email failed: {e}')
        return False

asyncio.run(send_notification())
" >> "$STARTUP_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_info "Startup notification email sent successfully"
    else
        log_error "Failed to send startup notification email"
    fi
}

# メイン実行フロー
main() {
    log_info "News Delivery System startup initiated"
    
    # システムチェック
    if ! check_system; then
        log_error "System checks failed - aborting startup"
        exit 1
    fi
    
    # ネットワーク接続待機
    log_info "Waiting for network connectivity"
    for i in {1..30}; do
        if ping -c 1 google.com >/dev/null 2>&1; then
            log_info "Network connectivity confirmed"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Network connectivity timeout"
            exit 1
        fi
        sleep 2
    done
    
    # サービス起動
    if start_services; then
        log_info "Services started successfully"
    else
        log_error "Service startup failed"
        exit 1
    fi
    
    # 起動通知
    send_startup_notification
    
    local end_time=$(date '+%Y-%m-%d %H:%M:%S')
    log_info "======= News Delivery System Startup Completed Successfully ======="
    
    exit 0
}

# スクリプト実行
main "$@"