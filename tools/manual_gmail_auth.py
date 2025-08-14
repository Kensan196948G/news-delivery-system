#!/usr/bin/env python3
"""
Manual Gmail API Authentication Setup
WSL環境用の手動Gmail認証セットアップ
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_manual_auth_instructions():
    """手動認証の手順を表示"""
    
    client_id = os.getenv('GMAIL_CLIENT_ID')
    client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Gmail API認証情報が設定されていません")
        return False
    
    print("=" * 80)
    print("📧 Gmail API 手動認証セットアップ")
    print("=" * 80)
    print("WSL環境では自動ブラウザ起動ができないため、手動で認証を行います。")
    print()
    
    # OAuth URL construction
    scope = "https://www.googleapis.com/auth/gmail.send"
    redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scope}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    print("🔗 ステップ1: 以下のURLをブラウザで開いてください")
    print("-" * 80)
    print(auth_url)
    print("-" * 80)
    print()
    print("📋 ステップ2: Googleアカウントでログインし、権限を許可してください")
    print()
    print("📄 ステップ3: 認証コードが表示されたらコピーしてください")
    print()
    
    # Wait for authorization code
    auth_code = input("🔑 認証コードを入力してください: ").strip()
    
    if not auth_code:
        print("❌ 認証コードが入力されませんでした")
        return False
    
    # Exchange code for tokens
    return exchange_code_for_tokens(auth_code, client_id, client_secret, redirect_uri)

def exchange_code_for_tokens(auth_code, client_id, client_secret, redirect_uri):
    """認証コードをトークンに交換"""
    
    import requests
    
    print("🔄 認証コードをトークンに交換しています...")
    
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    
    try:
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            tokens = response.json()
            
            # Save tokens to file
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': tokens.get('refresh_token'),
                'access_token': tokens.get('access_token'),
                'type': 'authorized_user'
            }
            
            # Save to token.json
            with open('token.json', 'w') as f:
                json.dump(token_data, f, indent=2)
            
            print("✅ 認証成功！token.json ファイルが作成されました")
            
            # Update .env with refresh token
            update_env_with_refresh_token(tokens.get('refresh_token'))
            
            return True
            
        else:
            print(f"❌ トークン取得失敗: {response.status_code}")
            print(f"エラー詳細: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def update_env_with_refresh_token(refresh_token):
    """refresh tokenを.envファイルに保存"""
    
    if not refresh_token:
        return
    
    env_path = Path('.env')
    
    if env_path.exists():
        # Read current content
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update refresh token
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('GMAIL_REFRESH_TOKEN='):
                lines[i] = f'GMAIL_REFRESH_TOKEN={refresh_token}\n'
                updated = True
                break
        
        if not updated:
            lines.append(f'\n# Gmail Refresh Token (Auto-generated)\n')
            lines.append(f'GMAIL_REFRESH_TOKEN={refresh_token}\n')
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        print("✅ .env ファイルにrefresh tokenを保存しました")

def test_gmail_connection():
    """Gmail接続テスト"""
    
    print("\n🧪 Gmail接続テストを実行しています...")
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        # Load credentials
        token_path = Path('token.json')
        if not token_path.exists():
            print("❌ token.json ファイルが見つかりません")
            return False
        
        creds = Credentials.from_authorized_user_file(str(token_path))
        
        # Test Gmail API
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        
        print(f"✅ Gmail接続成功！")
        print(f"📧 認証済みアカウント: {profile.get('emailAddress')}")
        print(f"📊 総メッセージ数: {profile.get('messagesTotal', 0):,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail接続テスト失敗: {e}")
        return False

def main():
    """メイン実行関数"""
    
    print("📧 Gmail API 手動認証セットアップ")
    print()
    
    # Check if already authenticated
    if Path('token.json').exists():
        print("⚠️  token.json ファイルが既に存在します")
        choice = input("再認証しますか？ (y/N): ").strip().lower()
        if choice != 'y':
            print("認証をスキップしました")
            return test_gmail_connection()
    
    # Run manual authentication
    success = create_manual_auth_instructions()
    
    if success:
        print("\n🎉 Gmail認証セットアップが完了しました！")
        
        # Test connection
        test_gmail_connection()
        
        print("\n📋 次のステップ:")
        print("1. python tools/test_email_delivery.py でメール配信テスト")
        print("2. python tools/run_scheduler.py でスケジューラー開始")
        
        return True
    else:
        print("\n❌ Gmail認証セットアップに失敗しました")
        print("再度実行するか、設定を確認してください")
        return False

if __name__ == "__main__":
    main()