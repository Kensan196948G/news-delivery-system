#!/usr/bin/env python3
"""
Gmail App Password Setup
Gmailアプリパスワード設定 - OAuth2.0の代替方法
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def setup_gmail_app_password():
    """Gmailアプリパスワード設定"""
    
    print("=" * 60)
    print("📧 Gmail App Password Setup")
    print("=" * 60)
    
    # アプリパスワード情報
    app_password = "sxsg mzbv ubsa jtok"
    
    # .envファイルを更新
    print("🔧 Updating .env file with Gmail settings...")
    
    env_additions = f"""
# Gmail App Password Configuration (追加設定)
GMAIL_USE_APP_PASSWORD=true
GMAIL_APP_PASSWORD={app_password}
GMAIL_SMTP_SERVER=smtp.gmail.com
GMAIL_SMTP_PORT=587
"""
    
    try:
        with open('.env', 'a') as f:
            f.write(env_additions)
        print("✅ Gmail settings added to .env file")
    except Exception as e:
        print(f"❌ Failed to update .env: {e}")
        return False
    
    return True

def create_simple_gmail_sender():
    """シンプルなGmail送信クラスを作成"""
    
    gmail_sender_code = '''"""
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
'''
    
    # ファイルに保存
    try:
        with open('src/notifiers/simple_gmail_sender.py', 'w', encoding='utf-8') as f:
            f.write(gmail_sender_code)
        print("✅ Simple Gmail sender module created")
        return True
    except Exception as e:
        print(f"❌ Failed to create Gmail sender: {e}")
        return False

def test_gmail_connection():
    """Gmail接続テスト"""
    
    print("\n🔍 Testing Gmail connection...")
    
    # 環境変数を設定
    os.environ['GMAIL_APP_PASSWORD'] = 'sxsg mzbv ubsa jtok'
    os.environ['GMAIL_USE_APP_PASSWORD'] = 'true'
    os.environ['GMAIL_SMTP_SERVER'] = 'smtp.gmail.com'
    os.environ['GMAIL_SMTP_PORT'] = '587'
    
    # 送信者メールアドレスの入力を求める
    sender_email = input("📧 Enter your Gmail address (sender): ").strip()
    if not sender_email:
        print("❌ Sender email is required")
        return False
    
    # 受信者メールアドレスの入力を求める（デフォルトは送信者と同じ）
    recipient_email = input(f"📨 Enter recipient email (default: {sender_email}): ").strip()
    if not recipient_email:
        recipient_email = sender_email
    
    # 環境変数に設定
    os.environ['SENDER_EMAIL'] = sender_email
    
    try:
        # シンプルなSMTP接続テスト
        import smtplib
        
        print("🔐 Testing SMTP connection...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, 'sxsg mzbv ubsa jtok')
        
        print("✅ SMTP login successful!")
        
        # テストメール作成
        from email.mime.text import MIMEText
        
        msg = MIMEText(f"""
News Delivery System - Gmail Test

This is a test email to confirm that Gmail App Password setup is working.

Sent from: {sender_email}
Sent to: {recipient_email}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Gmail connection is working correctly!
        """)
        
        msg['Subject'] = '📧 News Delivery System - Gmail Test'
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # メール送信
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Test email sent successfully to {recipient_email}")
        
        # .envファイルに保存
        env_update = f"""
# Gmail Configuration (Updated)
SENDER_EMAIL={sender_email}
RECIPIENT_EMAILS={recipient_email}
"""
        
        with open('.env', 'a') as f:
            f.write(env_update)
        
        print("✅ Email addresses saved to .env file")
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Please check:")
        print("   1. Gmail address is correct")
        print("   2. App Password is correct: sxsg mzbv ubsa jtok")
        print("   3. 2-step verification is enabled on your Google account")
        return False
    except Exception as e:
        print(f"❌ Gmail connection failed: {e}")
        return False

def main():
    """メイン実行"""
    print("🚀 Gmail App Password Configuration")
    
    # 設定を適用
    if not setup_gmail_app_password():
        return False
    
    # シンプルGmail送信クラス作成
    if not create_simple_gmail_sender():
        return False
    
    # 接続テスト
    if test_gmail_connection():
        print("\n" + "="*60)
        print("🎉 Gmail Setup Complete!")
        print("="*60)
        print("✅ App Password configured")
        print("✅ SMTP connection tested")
        print("✅ Test email sent")
        print("✅ Configuration saved")
        print("\n📋 Next steps:")
        print("1. Run full system test: python3 src/main.py --mode test")
        print("2. Send test news report: python3 test_news_with_email.py")
        return True
    else:
        print("\n⚠️ Gmail setup incomplete. Please check the configuration.")
        return False

if __name__ == "__main__":
    main()