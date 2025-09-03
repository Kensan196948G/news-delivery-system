#!/usr/bin/env python3
"""
簡易Gmail送信モジュール

SMTP認証方式を使用した簡単なGmail送信機能
OAuth2が複雑な場合の代替手段として使用

必要な設定:
1. Googleアカウントの2段階認証を有効化
2. アプリパスワードの生成
3. .envファイルに認証情報を設定
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SMTPConfig:
    """SMTP設定"""
    server: str = 'smtp.gmail.com'
    port: int = 587
    email: str = ''
    password: str = ''
    use_tls: bool = True
    timeout: int = 30

class SimplifiedGmailSender:
    """簡易Gmail送信クラス"""
    
    def __init__(self, config: SMTPConfig = None):
        """
        初期化
        
        Args:
            config: SMTP設定。未指定の場合は環境変数から読み込み
        """
        if config is None:
            config = self._load_config_from_env()
        
        self.config = config
        self._validate_config()
    
    def _load_config_from_env(self) -> SMTPConfig:
        """環境変数からSMTP設定を読み込み"""
        return SMTPConfig(
            server=os.getenv('GMAIL_SMTP_SERVER', 'smtp.gmail.com'),
            port=int(os.getenv('GMAIL_SMTP_PORT', 587)),
            email=os.getenv('GMAIL_EMAIL', ''),
            password=os.getenv('GMAIL_APP_PASSWORD', ''),
            use_tls=os.getenv('GMAIL_USE_TLS', 'true').lower() == 'true',
            timeout=int(os.getenv('GMAIL_TIMEOUT', 30))
        )
    
    def _validate_config(self):
        """設定の検証"""
        if not self.config.email:
            raise ValueError("Gmail address is required")
        if not self.config.password:
            raise ValueError("Gmail app password is required")
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str = None,
        text_content: str = None,
        attachments: List[str] = None,
        from_name: str = None
    ) -> bool:
        """
        メール送信
        
        Args:
            to_emails: 送信先メールアドレスリスト
            subject: 件名
            html_content: HTML本文
            text_content: テキスト本文
            attachments: 添付ファイルパスのリスト
            from_name: 送信者名
        
        Returns:
            bool: 送信成功時True
        """
        try:
            msg = self._create_message(
                to_emails, subject, html_content, text_content, from_name
            )
            
            # 添付ファイル追加
            if attachments:
                self._add_attachments(msg, attachments)
            
            # SMTP送信
            return self._send_via_smtp(msg, to_emails)
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _create_message(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: str,
        from_name: str
    ) -> MIMEMultipart:
        """メッセージ作成"""
        msg = MIMEMultipart('alternative')
        
        # ヘッダー設定
        from_address = f"{from_name} <{self.config.email}>" if from_name else self.config.email
        msg['From'] = from_address
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        # 本文設定
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
        
        if html_content:
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
        
        return msg
    
    def _add_attachments(self, msg: MIMEMultipart, attachments: List[str]):
        """添付ファイル追加"""
        for file_path in attachments:
            if not os.path.exists(file_path):
                logger.warning(f"Attachment file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'rb') as f:
                    attach = MIMEBase('application', 'octet-stream')
                    attach.set_payload(f.read())
                    encoders.encode_base64(attach)
                    
                    filename = Path(file_path).name
                    attach.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    msg.attach(attach)
                    
            except Exception as e:
                logger.error(f"Failed to attach file {file_path}: {e}")
    
    def _send_via_smtp(self, msg: MIMEMultipart, to_emails: List[str]) -> bool:
        """SMTP経由でメール送信"""
        try:
            server = smtplib.SMTP(self.config.server, self.config.port, timeout=self.config.timeout)
            
            if self.config.use_tls:
                server.starttls()
            
            server.login(self.config.email, self.config.password)
            
            text = msg.as_string()
            server.sendmail(self.config.email, to_emails, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {', '.join(to_emails)}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipients refused: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during email sending: {e}")
            return False
    
    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            server = smtplib.SMTP(self.config.server, self.config.port, timeout=self.config.timeout)
            
            if self.config.use_tls:
                server.starttls()
            
            server.login(self.config.email, self.config.password)
            server.quit()
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def send_test_email(self, to_email: str = None) -> bool:
        """テストメール送信"""
        if not to_email:
            to_email = self.config.email
        
        test_subject = "News Delivery System - Test Email"
        test_html = """
        <html>
            <body>
                <h2>Test Email from News Delivery System</h2>
                <p>This is a test email to verify SMTP configuration.</p>
                <p>If you received this email, the Gmail SMTP setup is working correctly.</p>
                <hr>
                <p><small>Sent from News Delivery System</small></p>
            </body>
        </html>
        """
        test_text = """
        Test Email from News Delivery System
        
        This is a test email to verify SMTP configuration.
        If you received this email, the Gmail SMTP setup is working correctly.
        
        ---
        Sent from News Delivery System
        """
        
        return self.send_email(
            to_emails=[to_email],
            subject=test_subject,
            html_content=test_html,
            text_content=test_text,
            from_name="News Delivery System"
        )


class NewsDeliveryMailer:
    """ニュース配信専用メーラー"""
    
    def __init__(self):
        self.sender = SimplifiedGmailSender()
        self.recipients = self._load_recipients()
        self.from_name = os.getenv('GMAIL_FROM_NAME', 'News Delivery System')
    
    def _load_recipients(self) -> List[str]:
        """受信者リストを環境変数から読み込み"""
        recipients_str = os.getenv('GMAIL_RECIPIENTS', '')
        if not recipients_str:
            return []
        
        return [email.strip() for email in recipients_str.split(',') if email.strip()]
    
    def send_daily_report(
        self,
        html_content: str,
        pdf_path: str = None,
        date_str: str = None
    ) -> bool:
        """日次レポート送信"""
        if not self.recipients:
            logger.warning("No recipients configured")
            return False
        
        subject = f"ニュース配信レポート - {date_str or 'Today'}"
        
        attachments = []
        if pdf_path and os.path.exists(pdf_path):
            attachments.append(pdf_path)
        
        return self.sender.send_email(
            to_emails=self.recipients,
            subject=subject,
            html_content=html_content,
            attachments=attachments,
            from_name=self.from_name
        )
    
    def send_urgent_alert(
        self,
        title: str,
        content: str,
        importance_score: int = 10
    ) -> bool:
        """緊急アラート送信"""
        if not self.recipients:
            logger.warning("No recipients configured for urgent alert")
            return False
        
        subject = f"【緊急】{title} (重要度: {importance_score})"
        
        html_content = f"""
        <html>
            <body>
                <div style="border: 2px solid #ff4444; padding: 20px; background-color: #fff8f8;">
                    <h2 style="color: #ff4444;">🚨 緊急ニュースアラート</h2>
                    <h3>{title}</h3>
                    <p><strong>重要度:</strong> {importance_score}/10</p>
                    <div style="margin: 15px 0; padding: 15px; background-color: #f8f8f8; border-left: 4px solid #ff4444;">
                        {content}
                    </div>
                    <hr>
                    <p><small>News Delivery System - 緊急アラート機能</small></p>
                </div>
            </body>
        </html>
        """
        
        return self.sender.send_email(
            to_emails=self.recipients,
            subject=subject,
            html_content=html_content,
            from_name=self.from_name
        )
    
    def send_error_notification(self, error_message: str, error_type: str = "System Error") -> bool:
        """エラー通知送信"""
        if not self.recipients:
            return False
        
        subject = f"【エラー】News Delivery System - {error_type}"
        
        html_content = f"""
        <html>
            <body>
                <div style="border: 2px solid #ff8800; padding: 20px; background-color: #fff9f0;">
                    <h2 style="color: #ff8800;">⚠️ システムエラー通知</h2>
                    <p><strong>エラー種別:</strong> {error_type}</p>
                    <div style="margin: 15px 0; padding: 15px; background-color: #f8f8f8; border-left: 4px solid #ff8800;">
                        <pre>{error_message}</pre>
                    </div>
                    <p>システム管理者による確認が必要です。</p>
                    <hr>
                    <p><small>News Delivery System - エラー通知機能</small></p>
                </div>
            </body>
        </html>
        """
        
        return self.sender.send_email(
            to_emails=self.recipients,
            subject=subject,
            html_content=html_content,
            from_name=self.from_name
        )


def main():
    """テスト実行用メイン関数"""
    import sys
    
    # ログ設定
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # 接続テスト
        sender = SimplifiedGmailSender()
        
        print("Testing SMTP connection...")
        if sender.test_connection():
            print("✅ SMTP connection successful")
            
            print("Sending test email...")
            if sender.send_test_email():
                print("✅ Test email sent successfully")
            else:
                print("❌ Failed to send test email")
        else:
            print("❌ SMTP connection failed")
            print("Please check your Gmail settings:")
            print("1. 2-factor authentication enabled")
            print("2. App password generated")
            print("3. Environment variables set correctly")


if __name__ == '__main__':
    main()