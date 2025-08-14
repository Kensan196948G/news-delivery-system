"""
Enhanced Gmail OAuth2.0 Authentication Manager
Gmail OAuth2.0認証管理の高度化
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.config import get_config


logger = logging.getLogger(__name__)


class GmailOAuthManager:
    """Gmail OAuth2.0認証マネージャー"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.compose'
    ]
    
    def __init__(self, config=None):
        self.config = config or get_config()
        
        # Credential paths
        self.credentials_path = Path('credentials/credentials.json')
        self.token_path = Path('credentials/token.json')
        
        # Ensure credentials directory exists
        self.credentials_path.parent.mkdir(exist_ok=True)
        
        # Current credentials
        self.credentials = None
        self.service = None
        
        logger.info("Gmail OAuth Manager initialized")
    
    def setup_credentials(self, client_config: Optional[Dict] = None) -> bool:
        """OAuth2.0認証情報の設定"""
        try:
            # Load from environment variables if available
            if not client_config:
                client_config = self._load_client_config_from_env()
            
            if not client_config and self.credentials_path.exists():
                # Load from credentials.json file
                with open(self.credentials_path, 'r') as f:
                    client_config = json.load(f)
            
            if not client_config:
                logger.error("No OAuth client configuration available")
                return False
            
            # Create OAuth flow
            flow = InstalledAppFlow.from_client_config(
                client_config, self.SCOPES
            )
            
            # Run local server for OAuth flow
            self.credentials = flow.run_local_server(
                port=8080,
                open_browser=True,
                authorization_prompt_message='Gmail OAuth認証を開始します...',
                success_message='Gmail OAuth認証が完了しました。このページを閉じてください。'
            )
            
            # Save credentials
            self._save_credentials()
            
            logger.info("Gmail OAuth setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"OAuth setup failed: {e}")
            return False
    
    def _load_client_config_from_env(self) -> Optional[Dict]:
        """環境変数からクライアント設定を読み込み"""
        try:
            client_id = os.getenv('GMAIL_CLIENT_ID')
            client_secret = os.getenv('GMAIL_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                return None
            
            return {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost:8080"]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to load client config from environment: {e}")
            return None
    
    def load_credentials(self) -> bool:
        """保存された認証情報の読み込み"""
        try:
            if not self.token_path.exists():
                logger.warning("No saved credentials found")
                return False
            
            # Load credentials from token file
            self.credentials = Credentials.from_authorized_user_file(
                str(self.token_path), self.SCOPES
            )
            
            # Check if credentials are valid or can be refreshed
            if not self.credentials.valid:
                if self.credentials.expired and self.credentials.refresh_token:
                    try:
                        logger.info("Refreshing expired credentials...")
                        self.credentials.refresh(Request())
                        self._save_credentials()
                        logger.info("Credentials refreshed successfully")
                    except Exception as e:
                        logger.error(f"Failed to refresh credentials: {e}")
                        return False
                else:
                    logger.error("Credentials are invalid and cannot be refreshed")
                    return False
            
            # Test credentials by building Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail credentials loaded and validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return False
    
    def _save_credentials(self):
        """認証情報の保存"""
        try:
            if self.credentials:
                with open(self.token_path, 'w') as token:
                    token.write(self.credentials.to_json())
                logger.debug("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def is_authenticated(self) -> bool:
        """認証状態の確認"""
        return (
            self.credentials is not None and 
            self.credentials.valid and 
            self.service is not None
        )
    
    def get_service(self):
        """Gmail APIサービスの取得"""
        if not self.is_authenticated():
            if not self.load_credentials():
                logger.error("Gmail authentication required")
                return None
        return self.service
    
    def test_connection(self) -> bool:
        """Gmail API接続テスト"""
        try:
            service = self.get_service()
            if not service:
                return False
            
            # Test by getting user profile (minimal operation)
            profile = service.users().getProfile(userId='me').execute()
            email_address = profile.get('emailAddress', 'Unknown')
            
            logger.info(f"Gmail connection test successful for: {email_address}")
            return True
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.warning("Gmail API connection test skipped (insufficient permissions)")
                # For send-only scope, we can't get profile, but connection might still work
                return True
            else:
                logger.error(f"Gmail connection test failed: {e}")
                return False
        except Exception as e:
            logger.error(f"Gmail connection test failed: {e}")
            return False
    
    def revoke_credentials(self) -> bool:
        """認証情報の取り消し"""
        try:
            if self.credentials and self.credentials.token:
                # Revoke the token
                import requests
                response = requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': self.credentials.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
                
                if response.status_code == 200:
                    logger.info("Credentials revoked successfully")
                else:
                    logger.warning(f"Credential revocation returned status: {response.status_code}")
            
            # Remove local token file
            if self.token_path.exists():
                self.token_path.unlink()
                logger.info("Local token file removed")
            
            # Clear in-memory credentials
            self.credentials = None
            self.service = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False
    
    def get_credentials_info(self) -> Dict[str, Any]:
        """認証情報の詳細取得"""
        try:
            if not self.credentials:
                return {'status': 'not_authenticated'}
            
            info = {
                'status': 'authenticated' if self.credentials.valid else 'invalid',
                'has_refresh_token': bool(self.credentials.refresh_token),
                'scopes': list(self.credentials.scopes) if self.credentials.scopes else [],
                'client_id': self.credentials.client_id,
                'token_file_exists': self.token_path.exists()
            }
            
            if self.credentials.expiry:
                info['expires_at'] = self.credentials.expiry.isoformat()
                info['expires_in_seconds'] = (
                    self.credentials.expiry - datetime.utcnow()
                ).total_seconds()
                info['is_expired'] = self.credentials.expired
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get credentials info: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def refresh_credentials_if_needed(self) -> bool:
        """必要に応じて認証情報を更新"""
        try:
            if not self.credentials:
                return False
            
            # Check if credentials will expire soon (within 5 minutes)
            if self.credentials.expiry:
                time_until_expiry = self.credentials.expiry - datetime.utcnow()
                if time_until_expiry < timedelta(minutes=5):
                    if self.credentials.refresh_token:
                        logger.info("Proactively refreshing credentials")
                        self.credentials.refresh(Request())
                        self._save_credentials()
                        return True
                    else:
                        logger.warning("Credentials will expire soon but no refresh token available")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return False


# Global OAuth manager instance
_oauth_manager_instance = None


def get_oauth_manager() -> GmailOAuthManager:
    """グローバルOAuth管理インスタンスの取得"""
    global _oauth_manager_instance
    if _oauth_manager_instance is None:
        _oauth_manager_instance = GmailOAuthManager()
    return _oauth_manager_instance