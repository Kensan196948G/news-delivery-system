#!/usr/bin/env python3
"""
Gmail API Authentication Setup Script
This script helps set up proper Gmail API authentication for the News Delivery System
"""

import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scopes required for sending emails
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

def create_credentials_file():
    """Create credentials.json file from environment variables"""
    
    client_id = os.getenv('GMAIL_CLIENT_ID')
    client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Error: GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in environment")
        print("Please check your .env file")
        return None
    
    credentials_data = {
        "installed": {
            "client_id": client_id,
            "project_id": "news-delivery-system",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }
    
    credentials_path = Path('credentials.json')
    with open(credentials_path, 'w') as f:
        json.dump(credentials_data, f, indent=2)
    
    print(f"✅ Created credentials.json")
    return credentials_path

def setup_gmail_authentication():
    """Set up Gmail API authentication"""
    
    print("🔧 Setting up Gmail API authentication...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create credentials file
    credentials_path = create_credentials_file()
    if not credentials_path:
        return False
    
    creds = None
    token_path = Path('token.json')
    
    # Check if we already have valid credentials
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            print("📋 Found existing token.json")
        except Exception as e:
            print(f"⚠️  Existing token.json is invalid: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired credentials...")
                creds.refresh(Request())
                print("✅ Successfully refreshed credentials")
            except Exception as e:
                print(f"❌ Failed to refresh credentials: {e}")
                creds = None
        
        if not creds:
            print("🌐 Starting OAuth2 flow...")
            print("This will open a web browser for authentication.")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES
                )
                # Use run_local_server for better user experience
                creds = flow.run_local_server(port=0)
                print("✅ Successfully obtained new credentials")
                
            except Exception as e:
                print(f"❌ OAuth2 flow failed: {e}")
                return False
    
    # Save the credentials for the next run
    if creds:
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"💾 Saved credentials to {token_path}")
        
        # Clean up credentials file (contains sensitive data)
        if credentials_path.exists():
            credentials_path.unlink()
            print("🗑️  Cleaned up temporary credentials.json")
        
        # Test the credentials
        return test_gmail_connection(creds)
    
    return False

def test_gmail_connection(creds):
    """Test Gmail API connection"""
    
    try:
        from googleapiclient.discovery import build
        
        print("🔍 Testing Gmail API connection...")
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Get user profile to verify connection
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress', 'Unknown')
        
        print(f"✅ Successfully connected to Gmail API")
        print(f"📧 Authenticated email: {email_address}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail API test failed: {e}")
        return False

def update_env_file():
    """Update .env file with authentication status"""
    
    env_path = Path('.env')
    if not env_path.exists():
        print("⚠️  .env file not found")
        return
    
    # Read current .env content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Add or update Gmail authentication status
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('GMAIL_AUTH_COMPLETED='):
            lines[i] = 'GMAIL_AUTH_COMPLETED=true\n'
            updated = True
            break
    
    if not updated:
        lines.append('\n# Gmail Authentication Status\n')
        lines.append('GMAIL_AUTH_COMPLETED=true\n')
    
    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print("📝 Updated .env file with authentication status")

def main():
    """Main setup function"""
    
    print("=" * 60)
    print("📮 Gmail API Authentication Setup")
    print("=" * 60)
    
    success = setup_gmail_authentication()
    
    if success:
        update_env_file()
        print("\n" + "=" * 60)
        print("🎉 Gmail authentication setup completed successfully!")
        print("📧 You can now send emails through the News Delivery System")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ Gmail authentication setup failed!")
        print("Please check your credentials and try again")
        print("=" * 60)
        return False

if __name__ == '__main__':
    main()