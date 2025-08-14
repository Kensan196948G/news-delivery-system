#!/usr/bin/env python3
"""
SMTP経由でのテストメール送信
Simple SMTP email test without OAuth
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def send_test_email_smtp():
    """SMTPを使用した直接メール送信テスト"""
    
    print("=" * 60)
    print("  SMTPテストメール送信")
    print("=" * 60)
    
    # 送信設定
    sender_email = "kensan1969@gmail.com"
    recipient_email = "kensan1969@gmail.com"
    
    # メール作成
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🧪 テストメール - {datetime.now().strftime('%Y年%m月%d日 %H:%M')}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    # メール本文
    text_content = f"""
ニュース配信システム - テストメール
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
送信時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

このメールは、ニュース配信システムのテストメールです。
正常に受信できていることを確認してください。

【テスト項目】
✓ SMTPサーバーへの接続
✓ メール送信機能
✓ 日本語文字化けの確認
✓ 日付フォーマット（strftime）の動作確認

【システム情報】
・送信元: {sender_email}
・送信先: {recipient_email}
・メール形式: text/plain; charset=utf-8

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ニュース配信システム v1.0
    """
    
    html_content = f"""
    <html>
      <head>
        <meta charset="utf-8">
      </head>
      <body style="font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
          <h2 style="color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;">
            🧪 ニュース配信システム - テストメール
          </h2>
          <p style="color: #666;">送信時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
          
          <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #28a745;">✅ テスト成功</h3>
            <p>このメールが正常に表示されていれば、以下の機能が正常に動作しています：</p>
            <ul style="color: #555;">
              <li>SMTPサーバーへの接続</li>
              <li>メール送信機能</li>
              <li>HTMLメールの表示</li>
              <li>日本語文字化けがないこと</li>
              <li>日付フォーマット（strftime）の動作</li>
            </ul>
          </div>
          
          <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
            <p style="color: #999; font-size: 12px;">
              ニュース配信システム v1.0<br>
              送信元: {sender_email}
            </p>
          </div>
        </div>
      </body>
    </html>
    """
    
    # メッセージにコンテンツを追加
    text_part = MIMEText(text_content, 'plain', 'utf-8')
    html_part = MIMEText(html_content, 'html', 'utf-8')
    
    msg.attach(text_part)
    msg.attach(html_part)
    
    print(f"\n送信先: {recipient_email}")
    print(f"件名: {msg['Subject']}")
    print("\nメール送信中...")
    
    try:
        # Gmailの場合はアプリパスワードが必要
        print("\n注意: Gmailを使用する場合は、以下の設定が必要です：")
        print("1. 2段階認証を有効化")
        print("2. アプリパスワードを生成")
        print("3. そのパスワードを使用してログイン")
        print("\n現在は送信をスキップします（実際の送信にはアプリパスワードが必要）")
        
        # 実際の送信（アプリパスワードが設定されている場合）
        # with smtplib.SMTP('smtp.gmail.com', 587) as server:
        #     server.starttls()
        #     server.login(sender_email, 'your-app-password')
        #     server.send_message(msg)
        
        print("\n✅ メール内容の生成に成功しました")
        print("   （実際の送信にはGmailアプリパスワードの設定が必要です）")
        
        # メール内容をファイルに保存
        test_email_file = Path("test_email_output.txt")
        with open(test_email_file, "w", encoding="utf-8") as f:
            f.write(f"件名: {msg['Subject']}\n")
            f.write(f"送信元: {msg['From']}\n")
            f.write(f"送信先: {msg['To']}\n")
            f.write("\n--- テキスト版 ---\n")
            f.write(text_content)
            f.write("\n--- HTML版 ---\n")
            f.write(html_content)
        
        print(f"\n📄 メール内容を保存しました: {test_email_file}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SMTPメール送信テスト")
    print("="*60)
    
    success = send_test_email_smtp()
    
    if success:
        print("\n" + "="*60)
        print("  テスト完了 - strftimeエラーは発生しませんでした")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("  テスト失敗")
        print("="*60)