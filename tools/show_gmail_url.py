#!/usr/bin/env python3
"""
Gmail認証URL表示ツール
"""

import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    client_id = os.getenv('GMAIL_CLIENT_ID')
    
    if not client_id:
        print("❌ GMAIL_CLIENT_ID が設定されていません")
        return
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri=urn:ietf:wg:oauth:2.0:oob&"
        f"scope=https://www.googleapis.com/auth/gmail.send&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    print("🔗 Gmail認証URL:")
    print("=" * 80)
    print(auth_url)
    print("=" * 80)
    print()
    print("📋 手順:")
    print("1. 上記URLをコピーしてブラウザで開く")
    print("2. Googleアカウントでログインして権限を許可")
    print("3. 表示される認証コードをコピー")
    print("4. python tools/simple_gmail_auth.py を実行")
    print("5. 認証コードを入力")

if __name__ == "__main__":
    main()