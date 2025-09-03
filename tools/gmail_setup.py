#!/usr/bin/env python3
"""
Gmail認証設定ツール

Gmail APIのOAuth2認証またはSMTP認証を設定するためのユーティリティ

使用方法:
  python tools/gmail_setup.py        # 対話的設定
  python tools/gmail_setup.py test   # 接続テスト
  python tools/gmail_setup.py smtp   # SMTP設定のみ
"""

import os
import sys
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from typing import Optional, Dict

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.notifiers.gmail_sender_simple import SimplifiedGmailSender, SMTPConfig
except ImportError:
    print("Failed to import SimplifiedGmailSender. Make sure the project is properly set up.")
    sys.exit(1)

class GmailSetupWizard:
    """Gmail設定ウィザード"""
    
    def __init__(self):
        self.project_root = project_root
        self.env_file = self.project_root / '.env'
        self.credentials_dir = self.project_root / 'credentials'
        
    def run_setup_wizard(self):
        """設定ウィザードを実行"""
        print("=" * 60)
        print("Gmail Authentication Setup Wizard")
        print("=" * 60)
        
        print("\nこのツールはGmail認証を設定します。")
        print("2つの認証方法から選択できます：")
        print("1. SMTP + App Password (推奨 - 簡単)")
        print("2. OAuth2 (高度 - より安全)")
        
        while True:
            choice = input("\n選択してください (1/2): ").strip()
            if choice in ['1', '2']:
                break
            print("1または2を入力してください。")
        
        if choice == '1':
            return self._setup_smtp()
        else:
            return self._setup_oauth2()
    
    def _setup_smtp(self) -> bool:
        """SMTP設定"""
        print("\n" + "=" * 50)
        print("SMTP認証設定")
        print("=" * 50)
        
        print("\n手順:")
        print("1. Googleアカウントで2段階認証を有効化")
        print("2. Google アカウント設定 > セキュリティ > アプリパスワード")
        print("3. 「メール」用のアプリパスワードを生成")
        print("4. 16文字のパスワードをメモ")
        print("\n詳細: https://support.google.com/accounts/answer/185833")
        
        input("\n準備ができたらEnterを押してください...")
        
        # メールアドレス入力
        while True:
            email = input("\nGmailアドレスを入力: ").strip()
            if '@gmail.com' in email.lower():
                break
            print("有効なGmailアドレスを入力してください。")
        
        # アプリパスワード入力
        while True:
            password = input("アプリパスワード (16文字): ").strip().replace(' ', '')
            if len(password) == 16:
                break
            print("16文字のアプリパスワードを入力してください。")
        
        # 接続テスト
        print("\n接続をテストしています...")
        config = SMTPConfig(email=email, password=password)
        
        try:
            sender = SimplifiedGmailSender(config)
            if sender.test_connection():
                print("✅ SMTP接続テスト成功!")
                
                # テストメール送信確認
                send_test = input("\nテストメールを送信しますか? (y/n): ").lower() == 'y'
                if send_test:
                    if sender.send_test_email():
                        print("✅ テストメール送信成功!")
                    else:
                        print("❌ テストメール送信失敗")
                
                # .env設定保存
                self._save_smtp_config(email, password)
                print(f"✅ 設定を {self.env_file} に保存しました。")
                return True
            else:
                print("❌ SMTP接続テスト失敗")
                print("設定を確認してください：")
                print("- 2段階認証が有効になっているか")
                print("- アプリパスワードが正しいか")
                print("- ネットワーク接続に問題がないか")
                return False
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    def _setup_oauth2(self) -> bool:
        """OAuth2設定"""
        print("\n" + "=" * 50)
        print("OAuth2認証設定")
        print("=" * 50)
        
        print("\nOAuth2設定は以下の手順が必要です：")
        print("1. Google Cloud Console でプロジェクト作成")
        print("2. Gmail API を有効化")
        print("3. OAuth 2.0 クライアントID 作成")
        print("4. credentials.json ダウンロード")
        
        print(f"\ncredentials.json を以下に配置してください:")
        print(f"{self.credentials_dir / 'gmail_credentials.json'}")
        
        # credentials ディレクトリ作成
        self.credentials_dir.mkdir(exist_ok=True)
        
        credentials_path = self.credentials_dir / 'gmail_credentials.json'
        
        if not credentials_path.exists():
            print(f"\n❌ {credentials_path} が見つかりません。")
            print("Google Cloud Console から credentials.json をダウンロードしてください。")
            return False
        
        # OAuth2 ライブラリの確認
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            print("❌ Google API ライブラリが不足しています。")
            print("インストール: pip install google-auth google-auth-oauthlib google-api-python-client")
            return False
        
        print("✅ OAuth2設定は複雑なため、現在はSMTP認証を推奨します。")
        print("OAuth2が必要な場合は、開発者にお問い合わせください。")
        return False
    
    def _save_smtp_config(self, email: str, password: str):
        """SMTP設定を.envファイルに保存"""
        config_lines = [
            "# Gmail SMTP Configuration",
            "GMAIL_AUTH_METHOD=smtp",
            "GMAIL_SMTP_SERVER=smtp.gmail.com",
            "GMAIL_SMTP_PORT=587",
            f"GMAIL_EMAIL={email}",
            f"GMAIL_APP_PASSWORD={password}",
            "GMAIL_USE_TLS=true",
            "GMAIL_TIMEOUT=30",
            "",
            "# Email Recipients (comma-separated)",
            f"GMAIL_RECIPIENTS={email}",
            "GMAIL_FROM_NAME=News Delivery System",
            ""
        ]
        
        # 既存の.envファイルを読み込み、Gmail設定を更新
        existing_lines = []
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # Gmail関連の行を削除
        filtered_lines = []
        for line in existing_lines:
            if not any(line.strip().startswith(prefix) for prefix in [
                'GMAIL_', '# Gmail', 'GMAIL_RECIPIENTS', 'GMAIL_FROM_NAME'
            ]):
                filtered_lines.append(line.rstrip('\n'))
        
        # 新しい設定を追加
        with open(self.env_file, 'w', encoding='utf-8') as f:
            # 既存の設定
            for line in filtered_lines:
                f.write(line + '\n')
            
            # Gmail設定追加
            f.write('\n')
            for line in config_lines:
                f.write(line + '\n')
    
    def test_existing_config(self):
        """既存の設定をテスト"""
        if not self.env_file.exists():
            print(f"❌ {self.env_file} が見つかりません。")
            print("先に設定を行ってください。")
            return False
        
        # 環境変数読み込み
        from dotenv import load_dotenv
        load_dotenv(self.env_file)
        
        auth_method = os.getenv('GMAIL_AUTH_METHOD', 'smtp')
        
        if auth_method == 'smtp':
            return self._test_smtp_config()
        else:
            return self._test_oauth2_config()
    
    def _test_smtp_config(self) -> bool:
        """SMTP設定をテスト"""
        print("SMTP設定をテストしています...")
        
        try:
            sender = SimplifiedGmailSender()
            if sender.test_connection():
                print("✅ SMTP接続テスト成功!")
                
                # テストメール送信
                test_email = input("\nテストメール送信先 (空欄で送信者と同じ): ").strip()
                if not test_email:
                    test_email = sender.config.email
                
                if sender.send_test_email(test_email):
                    print("✅ テストメール送信成功!")
                    return True
                else:
                    print("❌ テストメール送信失敗")
                    return False
            else:
                print("❌ SMTP接続テスト失敗")
                return False
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    def _test_oauth2_config(self) -> bool:
        """OAuth2設定をテスト"""
        print("OAuth2設定は現在サポートされていません。")
        print("SMTP認証を使用してください。")
        return False


def main():
    """メイン関数"""
    wizard = GmailSetupWizard()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            success = wizard.test_existing_config()
            sys.exit(0 if success else 1)
        elif command == 'smtp':
            success = wizard._setup_smtp()
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: test, smtp")
            sys.exit(1)
    else:
        # 対話的設定
        success = wizard.run_setup_wizard()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()