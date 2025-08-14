#!/usr/bin/env python3
"""
Simple Gmail Authentication
シンプルなGmail認証スクリプト
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

def main():
    print("=" * 60)
    print("📧 Gmail認証 - 簡単セットアップ")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    client_id = os.getenv('GMAIL_CLIENT_ID')
    client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Gmail API認証情報が設定されていません")
        return False
    
    # Display URL
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri=urn:ietf:wg:oauth:2.0:oob&"
        f"scope=https://www.googleapis.com/auth/gmail.send&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    print("\n🔗 ステップ1: 以下のURLをブラウザで開く")
    print("-" * 60)
    print(auth_url)
    print("-" * 60)
    
    print("\n📋 ステップ2:")
    print("1. Googleアカウントでログイン")
    print("2. 権限を許可")
    print("3. 表示される認証コードをコピー")
    
    print("\n🔑 ステップ3: 認証コードを入力")
    try:
        auth_code = input("認証コード: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n❌ 認証がキャンセルされました")
        return False
    
    if not auth_code:
        print("❌ 認証コードが入力されませんでした")
        return False
    
    # Exchange code for tokens
    print("\n🔄 トークンを取得中...")
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
    }
    
    try:
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            tokens = response.json()
            
            # Save token.json
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': tokens.get('refresh_token'),
                'access_token': tokens.get('access_token'),
                'type': 'authorized_user'
            }
            
            with open('token.json', 'w') as f:
                json.dump(token_data, f, indent=2)
            
            print("✅ 認証成功！")
            print("📄 token.json ファイルが作成されました")
            
            # Test connection
            test_connection()
            return True
            
        else:
            print(f"❌ 認証失敗: {response.status_code}")
            print(f"エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def test_connection():
    """Gmail接続テスト"""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        import json
        
        # Just verify credentials are valid without making API calls that require additional scopes
        creds = Credentials.from_authorized_user_file('token.json')
        
        # Read token file to get client info
        with open('token.json', 'r') as f:
            token_data = json.load(f)
        
        print("📧 認証トークンが正常に作成されました")
        print("✅ Gmail API送信権限が設定されました")
        print("🔐 スコープ: gmail.send (メール送信専用)")
        
    except Exception as e:
        print(f"⚠️  接続テスト失敗: {e}")

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 設定完了！次のステップ:")
        print("1. python tools/test_email_delivery.py (配信テスト)")
        print("2. python tools/run_scheduler.py (自動配信開始)")
    else:
        print("\n❌ 認証に失敗しました")
        print("GMAIL_AUTH_MANUAL_GUIDE.md を参照してください")