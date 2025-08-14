#!/bin/bash

# エラー通知スクリプト
# システムエラー発生時にkensan1969@gmail.comへプレーンテキストメールを送信

# 設定
ADMIN_EMAIL="kensan1969@gmail.com"
SYSTEM_NAME="ニュース配信システム"
LOG_DIR="/mnt/Linux-ExHDD/news-delivery-system/logs"

# Gmail設定（sendmailまたはmsmtp使用）
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT="587"

# 関数: エラーメール送信
send_error_notification() {
    local error_type="$1"
    local error_details="$2"
    local log_file="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # メール件名
    local subject="[エラー通知] ${SYSTEM_NAME} - ${error_type}"
    
    # メール本文作成
    local email_body=$(cat << EOF
${SYSTEM_NAME} エラー通知

エラー発生時刻: ${timestamp}
エラー種別: ${error_type}

=== エラー詳細 ===
${error_details}

=== システム情報 ===
ホスト名: $(hostname)
ユーザー: $(whoami)
作業ディレクトリ: $(pwd)
ディスク使用量: $(df -h /mnt/Linux-ExHDD | tail -1)

=== 最新ログ（最後の20行） ===
EOF
)

    # ログファイルが存在する場合は追加
    if [[ -f "$log_file" ]]; then
        email_body+="\n$(tail -20 "$log_file")"
    else
        email_body+="\nログファイルが見つかりません: $log_file"
    fi

    # プロセス情報追加
    email_body+="\n\n=== プロセス情報 ==="
    email_body+="\n$(ps aux | grep -E '(python|news|backup)' | grep -v grep)"

    # メモリ情報
    email_body+="\n\n=== メモリ使用量 ==="
    email_body+="\n$(free -h)"

    # 通知終了
    email_body+="\n\n--- 自動通知システム ---"

    # メール送信（複数の方法を試行）
    send_mail_multiple_ways "$subject" "$email_body"
}

# 関数: 複数の方法でメール送信を試行
send_mail_multiple_ways() {
    local subject="$1"
    local body="$2"
    local sent=false
    
    # 方法1: Python smtplib（推奨）
    if command -v python3 &> /dev/null && [[ "$sent" == false ]]; then
        if python3 -c "
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

try:
    # Gmail SMTP設定
    smtp_server = 'smtp.gmail.com'
    port = 587
    sender_email = os.environ.get('GMAIL_USER', 'system@localhost')
    password = os.environ.get('GMAIL_PASSWORD', '')
    
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = '$ADMIN_EMAIL'
    message['Subject'] = '$subject'
    
    message.attach(MIMEText('$body', 'plain'))
    
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        if password:
            server.login(sender_email, password)
        text = message.as_string()
        server.sendmail(sender_email, '$ADMIN_EMAIL', text)
    
    print('メール送信成功（Python SMTP）')
    exit(0)
except Exception as e:
    print(f'Python SMTP送信失敗: {e}')
    exit(1)
" 2>/dev/null; then
            sent=true
            echo "エラー通知メール送信完了（Python SMTP）"
        fi
    fi
    
    # 方法2: mail コマンド
    if command -v mail &> /dev/null && [[ "$sent" == false ]]; then
        if echo -e "$body" | mail -s "$subject" "$ADMIN_EMAIL" 2>/dev/null; then
            sent=true
            echo "エラー通知メール送信完了（mail）"
        fi
    fi
    
    # 方法3: sendmail
    if command -v sendmail &> /dev/null && [[ "$sent" == false ]]; then
        if (
            echo "To: $ADMIN_EMAIL"
            echo "Subject: $subject"
            echo "Content-Type: text/plain; charset=UTF-8"
            echo ""
            echo -e "$body"
        ) | sendmail "$ADMIN_EMAIL" 2>/dev/null; then
            sent=true
            echo "エラー通知メール送信完了（sendmail）"
        fi
    fi
    
    # 方法4: msmtp
    if command -v msmtp &> /dev/null && [[ "$sent" == false ]]; then
        if (
            echo "To: $ADMIN_EMAIL"
            echo "Subject: $subject"
            echo "Content-Type: text/plain; charset=UTF-8"
            echo ""
            echo -e "$body"
        ) | msmtp "$ADMIN_EMAIL" 2>/dev/null; then
            sent=true
            echo "エラー通知メール送信完了（msmtp）"
        fi
    fi
    
    # すべて失敗した場合
    if [[ "$sent" == false ]]; then
        echo "エラー通知メール送信失敗: すべての送信方法が失敗しました"
        # ローカルログに記録
        echo "[$(date)] メール送信失敗: $subject" >> "$LOG_DIR/mail_errors.log"
        echo "$body" >> "$LOG_DIR/mail_errors.log"
        echo "---" >> "$LOG_DIR/mail_errors.log"
        return 1
    fi
    
    return 0
}

# 関数: ニュース配信エラー通知
notify_news_delivery_error() {
    local delivery_time="$1"
    local error_details="$2"
    local log_file="$3"
    
    send_error_notification "ニュース配信エラー（${delivery_time}）" "$error_details" "$log_file"
}

# 関数: ログクリーンアップエラー通知
notify_log_cleanup_error() {
    local error_details="$1"
    local log_file="$2"
    
    send_error_notification "週次ログクリーンアップエラー" "$error_details" "$log_file"
}

# 関数: ヘルスチェックエラー通知
notify_health_check_error() {
    local error_details="$1"
    local log_file="$2"
    
    send_error_notification "月次ヘルスチェックエラー" "$error_details" "$log_file"
}

# 関数: バックアップエラー通知
notify_backup_error() {
    local error_details="$1"
    local log_file="$2"
    
    send_error_notification "フルバックアップエラー" "$error_details" "$log_file"
}

# 関数: 一般的なシステムエラー通知
notify_system_error() {
    local component="$1"
    local error_details="$2"
    local log_file="$3"
    
    send_error_notification "システムエラー（${component}）" "$error_details" "$log_file"
}

# スクリプトが直接実行された場合のテスト
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # 引数チェック
    if [[ $# -lt 2 ]]; then
        echo "使用方法: $0 <エラー種別> <エラー詳細> [ログファイル]"
        echo ""
        echo "エラー種別:"
        echo "  news_delivery <配信時間>"
        echo "  log_cleanup"
        echo "  health_check" 
        echo "  backup"
        echo "  system <コンポーネント名>"
        echo ""
        echo "例: $0 news_delivery '7:00' 'Python実行エラー' '/path/to/log'"
        exit 1
    fi
    
    error_type="$1"
    shift
    
    case "$error_type" in
        "news_delivery")
            delivery_time="$1"
            error_details="$2"
            log_file="$3"
            notify_news_delivery_error "$delivery_time" "$error_details" "$log_file"
            ;;
        "log_cleanup")
            error_details="$1"
            log_file="$2"
            notify_log_cleanup_error "$error_details" "$log_file"
            ;;
        "health_check")
            error_details="$1"
            log_file="$2"
            notify_health_check_error "$error_details" "$log_file"
            ;;
        "backup")
            error_details="$1"
            log_file="$2"
            notify_backup_error "$error_details" "$log_file"
            ;;
        "system")
            component="$1"
            error_details="$2"
            log_file="$3"
            notify_system_error "$component" "$error_details" "$log_file"
            ;;
        *)
            echo "不明なエラー種別: $error_type"
            exit 1
            ;;
    esac
fi