"""
Simple Gmail Sender using App Password
アプリパスワードを使用したシンプルなGmail送信
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

class SimpleGmailSender:
    """アプリパスワードを使用したシンプルなGmail送信"""
    
    def __init__(self):
        # 環境変数から設定を読み込み
        self.gmail_user = os.environ.get('SENDER_EMAIL')
        self.gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
        self.smtp_server = os.environ.get('GMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('GMAIL_SMTP_PORT', 587))
        
        if not self.gmail_user or not self.gmail_password:
            raise ValueError("SENDER_EMAIL and GMAIL_APP_PASSWORD must be set in .env")
    
    def send_html_email(self, to_emails, subject, html_content, pdf_path=None):
        """HTMLメール送信"""
        try:
            # メッセージ作成
            msg = MIMEMultipart('alternative')
            msg['From'] = self.gmail_user
            msg['To'] = ', '.join(to_emails) if isinstance(to_emails, list) else to_emails
            msg['Subject'] = subject
            
            # HTML部分
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # プレーンテキスト版（フォールバック）
            text_content = self._html_to_text(html_content)
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # PDF添付（オプション）
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    attachment = MIMEBase('application', 'pdf')
                    attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{os.path.basename(pdf_path)}"'
                )
                msg.attach(attachment)
            
            # SMTP送信
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.gmail_user, self.gmail_password)
            
            text = msg.as_string()
            server.sendmail(self.gmail_user, to_emails, text)
            server.quit()
            
            print(f"✅ Email sent successfully to {len(to_emails) if isinstance(to_emails, list) else 1} recipients")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def _html_to_text(self, html_content):
        """HTMLをプレーンテキストに変換（簡易版）"""
        import re
        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', html_content)
        # HTMLエンティティをデコード
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()
    
    def send_test_email(self, test_email=None):
        """テストメール送信"""
        recipient = test_email or self.gmail_user
        
        test_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>News Delivery System Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .header {{ text-align: center; color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 20px; }}
        .content {{ margin: 20px 0; }}
        .success {{ background: #d4edda; padding: 15px; border-radius: 5px; color: #155724; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 News Delivery System</h1>
            <h2>Gmail Test Email</h2>
        </div>
        <div class="content">
            <div class="success">
                <h3>✅ Gmail Connection Successful!</h3>
                <p>This test email confirms that the Gmail App Password setup is working correctly.</p>
                <p><strong>Sent from:</strong> {self.gmail_user}</p>
                <p><strong>Sent at:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            </div>
            <p>Your News Delivery System is ready to send automated news reports!</p>
        </div>
    </div>
</body>
</html>
        """
        
        subject = "📧 News Delivery System - Gmail Test Successful"
        return self.send_html_email([recipient], subject, test_html)
