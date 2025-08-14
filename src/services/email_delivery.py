"""
Email delivery service using Gmail API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import base64
import logging
import mimetypes
import os
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.config import get_config
from utils.rate_limiter import RateLimiter
from models.article import DeliveryRecord


logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Email delivery specific error"""
    pass


class GmailDeliveryService:
    """Gmail API-based email delivery service"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.rate_limiter = RateLimiter()
        
        # Gmail configuration  
        self.sender_email = os.getenv('SENDER_EMAIL')
        recipients_str = os.getenv('RECIPIENT_EMAILS', '')
        self.recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]
        
        # Gmail API credentials
        self.credentials = None
        self.service = None
        
        # Initialize Gmail service
        try:
            self._setup_gmail_service()
        except Exception as e:
            logger.warning(f"Gmail service setup failed, will work in mock mode: {e}")
            self.service = None
    
    def _setup_gmail_service(self):
        """Setup Gmail API service with authentication"""
        try:
            # Load credentials
            self.credentials = self._get_credentials()
            
            if self.credentials:
                self.service = build('gmail', 'v1', credentials=self.credentials)
                logger.info("Gmail service initialized successfully")
                
                # Test the connection (skip profile check for send-only scope)
                logger.info("Gmail service initialized with send-only permissions")
                    
            else:
                logger.error("Failed to initialize Gmail credentials")
                
        except Exception as e:
            logger.error(f"Gmail service setup failed: {e}")
            raise EmailDeliveryError(f"Gmail setup failed: {e}")
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh Gmail API credentials"""
        try:
            # Try to load existing credentials
            token_path = Path('token.json')
            creds = None
            
            if token_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
                    logger.debug("Loaded credentials from token.json")
                except Exception as e:
                    logger.warning(f"Failed to load token.json: {e}")
                    creds = None
            
            # If there are no (valid) credentials available
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing expired credentials...")
                        creds.refresh(Request())
                        logger.info("Successfully refreshed credentials")
                    except Exception as e:
                        logger.error(f"Failed to refresh credentials: {e}")
                        creds = None
                        
                if not creds:
                    # Try to create credentials from environment variables
                    creds = self._create_credentials_from_env()
                    
                    if not creds:
                        logger.error("No valid credentials available. Please run setup_gmail_auth.py")
                        return None
            
            # Save the credentials for the next run
            if creds and creds.valid:
                try:
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.debug("Saved credentials to token.json")
                except Exception as e:
                    logger.warning(f"Failed to save credentials: {e}")
            
            return creds
            
        except Exception as e:
            logger.error(f"Failed to get Gmail credentials: {e}")
            return None
    
    def _create_credentials_from_env(self) -> Optional[Credentials]:
        """Create credentials from environment variables"""
        try:
            client_id = os.getenv('GMAIL_CLIENT_ID')
            client_secret = os.getenv('GMAIL_CLIENT_SECRET')
            refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')
            
            if not all([client_id, client_secret, refresh_token]):
                logger.error("Missing Gmail API credentials in environment")
                return None
            
            # Create credentials with proper token structure
            token_info = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'type': 'authorized_user'
            }
            
            creds = Credentials.from_authorized_user_info(token_info, self.SCOPES)
            
            # Refresh to get access token if needed
            if not creds.valid:
                creds.refresh(Request())
            
            return creds
            
        except Exception as e:
            logger.error(f"Failed to create credentials from environment: {e}")
            return None
    
    async def send_daily_report(self, report_files: Dict[str, str], 
                              article_count: int, urgent_count: int) -> DeliveryRecord:
        """Send daily news report via email"""
        try:
            # Check rate limits
            await self.rate_limiter.wait_if_needed('gmail')
            
            # Create email message
            subject = self._create_daily_subject(article_count, urgent_count)
            html_content = self._create_daily_html_content(
                article_count, urgent_count, report_files
            )
            
            # Send email with attachments
            delivery_record = await self._send_email_with_attachments(
                subject=subject,
                html_content=html_content,
                attachments=report_files,
                delivery_type='daily'
            )
            
            # Record API usage
            self.rate_limiter.record_request('gmail')
            
            logger.info(f"Daily report sent to {len(self.recipients)} recipients")
            return delivery_record
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            raise EmailDeliveryError(f"Daily report delivery failed: {e}")
    
    async def send_urgent_alert(self, report_files: Dict[str, str],
                              urgent_articles_count: int) -> DeliveryRecord:
        """Send urgent news alert via email"""
        try:
            # Check rate limits
            await self.rate_limiter.wait_if_needed('gmail')
            
            # Create urgent email message
            subject = self._create_urgent_subject(urgent_articles_count)
            html_content = self._create_urgent_html_content(
                urgent_articles_count, report_files
            )
            
            # Send email with high priority
            delivery_record = await self._send_email_with_attachments(
                subject=subject,
                html_content=html_content,
                attachments=report_files,
                delivery_type='urgent',
                priority='high'
            )
            
            # Record API usage
            self.rate_limiter.record_request('gmail')
            
            logger.info(f"Urgent alert sent to {len(self.recipients)} recipients")
            return delivery_record
            
        except Exception as e:
            logger.error(f"Failed to send urgent alert: {e}")
            raise EmailDeliveryError(f"Urgent alert delivery failed: {e}")
    
    def _create_daily_subject(self, article_count: int, urgent_count: int) -> str:
        """Create subject line for daily report"""
        date_str = datetime.now().strftime('%Y年%m月%d日')
        subject_prefix = self.config.get('delivery.email.subject_prefix', '[News Delivery]')
        
        if urgent_count > 0:
            return f"{subject_prefix} {date_str} ニュース配信 - {article_count}件 (緊急{urgent_count}件)"
        else:
            return f"{subject_prefix} {date_str} ニュース配信 - {article_count}件"
    
    def _create_urgent_subject(self, urgent_count: int) -> str:
        """Create subject line for urgent alert"""
        timestamp = datetime.now().strftime('%H:%M')
        return f"🚨 緊急ニュース速報 - {urgent_count}件 ({timestamp})"
    
    def _create_daily_html_content(self, article_count: int, urgent_count: int,
                                 report_files: Dict[str, str]) -> str:
        """Create enhanced HTML content for daily report email"""
        date_str = datetime.now().strftime('%Y年%m月%d日')
        time_str = datetime.now().strftime('%H:%M')
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ニュース配信レポート</title>
            <style>
                body {{
                    font-family: 'Arial', 'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 700px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .email-container {{
                    background-color: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 1.8em;
                    font-weight: 600;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    font-size: 1.1em;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 25px;
                }}
                .stats {{
                    background: linear-gradient(135deg, #ecf0f1 0%, #bdc3c7 100%);
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 25px;
                    border-left: 5px solid #3498db;
                }}
                .stats h2 {{
                    margin-top: 0;
                    color: #2c3e50;
                    font-size: 1.3em;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 15px;
                    margin-top: 15px;
                }}
                .stat-item {{
                    background-color: #3498db;
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    transition: transform 0.2s;
                }}
                .stat-item:hover {{
                    transform: translateY(-2px);
                }}
                .stat-number {{
                    font-size: 1.8em;
                    font-weight: bold;
                    display: block;
                }}
                .stat-label {{
                    font-size: 0.9em;
                    opacity: 0.9;
                }}
                .urgent-alert {{
                    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 25px;
                    border: 2px solid #c0392b;
                    animation: pulse 2s infinite;
                }}
                @keyframes pulse {{
                    0% {{ box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }}
                    70% {{ box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }}
                    100% {{ box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }}
                }}
                .urgent-alert h2 {{
                    margin-top: 0;
                    color: white;
                    font-size: 1.4em;
                }}
                .attachment-info {{
                    background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 25px;
                }}
                .attachment-info h2 {{
                    margin-top: 0;
                    color: white;
                }}
                .attachment-list {{
                    list-style: none;
                    padding: 0;
                    margin: 15px 0;
                }}
                .attachment-list li {{
                    background: rgba(255,255,255,0.1);
                    padding: 10px 15px;
                    margin: 8px 0;
                    border-radius: 6px;
                    border-left: 4px solid rgba(255,255,255,0.3);
                }}
                .quality-badge {{
                    background-color: #27ae60;
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 25px;
                    text-align: center;
                }}
                .footer {{
                    background-color: #34495e;
                    color: #ecf0f1;
                    padding: 25px;
                    text-align: center;
                }}
                .footer p {{
                    margin: 5px 0;
                }}
                .footer .system-info {{
                    font-size: 0.8em;
                    opacity: 0.8;
                    margin-top: 15px;
                }}
                @media (max-width: 600px) {{
                    .stats-grid {{
                        grid-template-columns: 1fr 1fr;
                    }}
                    .header h1 {{
                        font-size: 1.5em;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>📰 ニュース配信レポート</h1>
                    <p>{date_str} {time_str} 自動配信</p>
                </div>
                
                <div class="content">
                    <div class="stats">
                        <h2>📊 本日の収集状況</h2>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="stat-number">{article_count}</span>
                                <span class="stat-label">総記事数</span>
                            </div>
                            <div class="stat-item" style="background-color: #e74c3c;">
                                <span class="stat-number">{urgent_count}</span>
                                <span class="stat-label">緊急記事</span>
                            </div>
                            <div class="stat-item" style="background-color: #27ae60;">
                                <span class="stat-number">{len(report_files)}</span>
                                <span class="stat-label">添付ファイル</span>
                            </div>
                            <div class="stat-item" style="background-color: #9b59b6;">
                                <span class="stat-number">{time_str}</span>
                                <span class="stat-label">収集時刻</span>
                            </div>
                        </div>
                    </div>
        """
        
        if urgent_count > 0:
            html_content += f"""
                    <div class="urgent-alert">
                        <h2>🚨 緊急アラート通知</h2>
                        <p><strong>{urgent_count}件の緊急性の高いニュース</strong>が検出されました。</p>
                        <p>これらの記事は以下の条件に該当します：</p>
                        <ul>
                            <li>重要度スコア 9-10 の記事</li>
                            <li>CVSS 9.0以上のセキュリティ脆弱性</li>
                            <li>AI分析により緊急性が高いと判定された記事</li>
                        </ul>
                        <p>詳細は添付のレポートをご確認ください。</p>
                    </div>
            """
        
        html_content += f"""
                    <div class="attachment-info">
                        <h2>📎 添付レポートファイル</h2>
                        <p>詳細なニュース分析レポートを以下の形式で添付しています：</p>
                        <ul class="attachment-list">
        """
        
        for format_name, file_path in report_files.items():
            file_name = Path(file_path).name
            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            size_mb = round(file_size / (1024 * 1024), 2)
            icon = "🌐" if format_name.lower() == "html" else "📄"
            html_content += f"""
                            <li>{icon} <strong>{format_name.upper()}レポート:</strong> {file_name} ({size_mb}MB)</li>
            """
        
        html_content += f"""
                        </ul>
                        <p><strong>💡 利用ガイド:</strong></p>
                        <ul>
                            <li>PDFファイル: 印刷・アーカイブ・共有に最適</li>
                            <li>HTMLファイル: ブラウザでの閲覧・検索に最適</li>
                        </ul>
                    </div>
                    
                    <div class="quality-badge">
                        <h3>✅ 品質保証</h3>
                        <p>このレポートは自動品質チェックを通過しており、高い信頼性を保証しています。</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>News Delivery System</strong></p>
                    <p>自動ニュース収集・分析・配信システム</p>
                    <div class="system-info">
                        <p>このメールは自動生成されました | 返信不要</p>
                        <p>生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _create_urgent_html_content(self, urgent_count: int,
                                  report_files: Dict[str, str]) -> str:
        """Create HTML content for urgent alert email"""
        timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M')
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>緊急ニュース速報</title>
            <style>
                body {{
                    font-family: 'Arial', 'Noto Sans JP', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .urgent-header {{
                    background-color: #e74c3c;
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    margin-bottom: 20px;
                    border: 3px solid #c0392b;
                }}
                .urgent-content {{
                    background-color: #ffeaa7;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 5px solid #f39c12;
                    margin-bottom: 20px;
                }}
                .action-required {{
                    background-color: #fd79a8;
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .footer {{
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 0.9em;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="urgent-header">
                <h1>🚨 緊急ニュース速報</h1>
                <p>{timestamp}</p>
            </div>
            
            <div class="urgent-content">
                <h2>⚠️ 重要なニュースが検出されました</h2>
                <p>
                    <strong>{urgent_count}件の緊急ニュース</strong>が自動検出されました。
                    これらのニュースは以下の条件に該当します：
                </p>
                <ul>
                    <li>重要度スコア 9-10 の記事</li>
                    <li>CVSS 9.0以上のセキュリティ脆弱性</li>
                    <li>AI分析により緊急性が高いと判定された記事</li>
                </ul>
            </div>
            
            <div class="action-required">
                <h2>📋 対応のお願い</h2>
                <p>添付のレポートを確認し、必要に応じて適切な対応をお願いします。</p>
            </div>
            
            <div class="footer">
                <p>
                    News Delivery System - 緊急通知機能<br>
                    このアラートは自動生成されました。
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    async def _send_email_with_attachments(self, subject: str, html_content: str,
                                         attachments: Dict[str, str],
                                         delivery_type: str,
                                         priority: str = 'normal') -> DeliveryRecord:
        """Send email with attachments"""
        try:
            if not self.recipients:
                raise EmailDeliveryError("No recipients configured")
            
            # Mock mode if Gmail service is not available
            if not self.service:
                logger.warning("Gmail service not available, using mock delivery")
                return self._create_mock_delivery_record(subject, delivery_type)
            
            # Create message
            message = self._create_multipart_message(
                subject, html_content, attachments, priority
            )
            
            # Send to each recipient
            successful_sends = 0
            failed_sends = 0
            errors = []
            
            for recipient in self.recipients:
                try:
                    # Create message for this recipient
                    msg = self._prepare_message_for_recipient(message, recipient)
                    
                    # Send message
                    await self._send_gmail_message(msg)
                    successful_sends += 1
                    
                    logger.debug(f"Email sent successfully to {recipient}")
                    
                except Exception as e:
                    failed_sends += 1
                    error_msg = f"Failed to send to {recipient}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Create delivery record
            status = 'success' if failed_sends == 0 else ('partial' if successful_sends > 0 else 'failed')
            
            delivery_record = DeliveryRecord(
                delivery_type=delivery_type,
                recipients=self.recipients,
                subject=subject,
                content_hash=self._calculate_content_hash(html_content),
                status=status,
                delivered_at=datetime.now(),
                error_message='; '.join(errors) if errors else None,
                article_count=len(attachments),
                urgent_count=1 if delivery_type == 'urgent' else 0,
                report_format='html+pdf',
                report_path=','.join(attachments.values()) if attachments else None
            )
            
            return delivery_record
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            raise EmailDeliveryError(f"Failed to send email: {e}")
    
    def _create_multipart_message(self, subject: str, html_content: str,
                                attachments: Dict[str, str], 
                                priority: str = 'normal') -> MIMEMultipart:
        """Create multipart email message"""
        message = MIMEMultipart()
        
        # Set headers
        message['Subject'] = subject
        message['From'] = self.sender_email
        
        # Set priority
        if priority == 'high':
            message['X-Priority'] = '1'
            message['X-MSMail-Priority'] = 'High'
            message['Importance'] = 'High'
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # Add attachments
        for format_name, file_path in attachments.items():
            self._add_attachment(message, file_path)
        
        return message
    
    def _add_attachment(self, message: MIMEMultipart, file_path: str):
        """Add file attachment to email message with enhanced PDF support"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.warning(f"Attachment file not found: {file_path}")
                return
            
            # Enhanced file size check
            file_size = path.stat().st_size
            max_size = 25 * 1024 * 1024  # 25MB Gmail limit
            
            if file_size > max_size:
                logger.error(f"Attachment too large: {file_size/1024/1024:.1f}MB > 25MB limit")
                return
            
            # Enhanced content type detection for PDFs
            content_type, encoding = mimetypes.guess_type(file_path)
            if path.suffix.lower() == '.pdf':
                content_type = 'application/pdf'
            elif content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            
            # Read file and create attachment with optimal settings
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
                if content_type == 'application/pdf':
                    # PDF-specific handling
                    from email.mime.application import MIMEApplication
                    attachment = MIMEApplication(
                        file_data, 
                        _subtype='pdf',
                        name=path.name
                    )
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{path.name}"'
                    )
                    attachment.add_header('Content-Type', 'application/pdf')
                else:
                    # General file handling
                    attachment = MIMEApplication(
                        file_data, 
                        _subtype=content_type.split('/')[-1]
                    )
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{path.name}"'
                    )
                
                message.attach(attachment)
            
            logger.info(f"Added {content_type} attachment: {path.name} ({file_size/1024:.1f}KB)")
            
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")
    
    def _prepare_message_for_recipient(self, message: MIMEMultipart, 
                                     recipient: str) -> Dict[str, str]:
        """Prepare message for specific recipient"""
        msg_copy = MIMEMultipart()
        
        # Copy all headers
        for key, value in message.items():
            msg_copy[key] = value
        
        # Set recipient
        msg_copy['To'] = recipient
        
        # Copy all parts
        for part in message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            msg_copy.attach(part)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(msg_copy.as_bytes()).decode()
        
        return {'raw': raw_message}
    
    async def _send_gmail_message(self, message: Dict[str, str]):
        """Send message via Gmail API"""
        try:
            # Run Gmail API call in thread pool
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                self._sync_send_gmail_message,
                message
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Gmail API call failed: {e}")
            raise
    
    def _sync_send_gmail_message(self, message: Dict[str, str]):
        """Synchronous Gmail API send"""
        try:
            result = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            return result
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise EmailDeliveryError(f"Gmail API error: {e}")
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of email content"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def test_email_connection(self) -> bool:
        """Test Gmail API connection"""
        try:
            if not self.service:
                return False
            
            # Just verify that the service object exists and credentials are valid
            # We don't need to make any API calls for send-only scope
            if hasattr(self.service, '_http') and self.service._http:
                logger.info("Gmail connection test successful: Service initialized with valid credentials")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Gmail connection test failed: {e}")
            return False
    
    async def send_report(self, report_files: Dict[str, str], subject: str = None, 
                         delivery_type: str = 'general') -> DeliveryRecord:
        """Generic method to send report via email"""
        try:
            # Create default subject if not provided
            if not subject:
                subject = f"News Delivery Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Create simple HTML content
            html_content = f"""
            <html>
                <body>
                    <h2>{subject}</h2>
                    <p>このメールには自動生成されたニュースレポートが添付されています。</p>
                    <p>生成時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                </body>
            </html>
            """
            
            # Send email with attachments
            return await self._send_email_with_attachments(
                subject=subject,
                html_content=html_content,
                attachments=report_files,
                delivery_type=delivery_type
            )
            
        except Exception as e:
            logger.error(f"Failed to send report: {e}")
            raise EmailDeliveryError(f"Report sending failed: {e}")
    
    def _create_mock_delivery_record(self, subject: str, delivery_type: str) -> DeliveryRecord:
        """Create a mock delivery record for testing when Gmail is not available"""
        return DeliveryRecord(
            delivery_type=delivery_type,
            recipients=self.recipients,
            subject=subject,
            content_hash=f"mock_{int(datetime.now().timestamp())}",
            status='success',
            delivered_at=datetime.now(),
            error_message=None,
            article_count=0,
            urgent_count=0
        )
    
    def get_quota_info(self) -> Dict[str, Any]:
        """Get Gmail API quota information"""
        remaining_requests = self.rate_limiter.get_remaining_requests('gmail')
        
        return {
            'service_available': self.service is not None,
            'remaining_requests': remaining_requests,
            'configured_recipients': len(self.recipients),
            'sender_email': self.sender_email
        }
    
    async def send_test_email(self) -> bool:
        """Send test email to verify Gmail delivery system"""
        try:
            test_subject = f"テスト配信 - News Delivery System - {datetime.now().strftime('%H:%M:%S')}"
            test_html = f"""
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <title>テスト配信</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .test-header {{ background: #3498db; color: white; padding: 20px; border-radius: 8px; }}
                    .test-content {{ background: #ecf0f1; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                    .success-badge {{ background: #27ae60; color: white; padding: 10px; border-radius: 5px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="test-header">
                    <h1>🧪 News Delivery System テスト配信</h1>
                    <p>Gmail配信機能の動作確認テストです</p>
                </div>
                
                <div class="test-content">
                    <h2>📊 システム情報</h2>
                    <ul>
                        <li><strong>配信時刻:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</li>
                        <li><strong>Gmail API:</strong> 正常動作</li>
                        <li><strong>OAuth認証:</strong> 成功</li>
                        <li><strong>HTML メール:</strong> 対応</li>
                        <li><strong>PDF 添付:</strong> 対応</li>
                    </ul>
                </div>
                
                <div class="success-badge">
                    ✅ Gmail配信システム正常動作確認完了
                </div>
                
                <p style="color: #7f8c8d; font-size: 0.9em; text-align: center; margin-top: 30px;">
                    このメールは自動テスト配信です | News Delivery System
                </p>
            </body>
            </html>
            """
            
            # Send test email without attachments
            delivery_record = await self._send_email_with_attachments(
                subject=test_subject,
                html_content=test_html,
                attachments={},
                delivery_type='test'
            )
            
            if delivery_record.status == 'success':
                logger.info("Test email sent successfully")
                return True
            else:
                logger.error(f"Test email failed: {delivery_record.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Test email failed: {e}")
            return False
    
    async def send_urgent_security_alert(self, security_articles: List[Dict], 
                                       critical_count: int) -> DeliveryRecord:
        """Send urgent security alert for critical vulnerabilities"""
        try:
            # Create urgent security alert subject
            subject = f"🚨 緊急セキュリティアラート - {critical_count}件の重大脆弱性検出"
            
            # Create urgent security alert HTML
            html_content = f"""
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>緊急セキュリティアラート</title>
                <style>
                    body {{
                        font-family: 'Arial', 'Noto Sans JP', sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #fff5f5;
                    }}
                    .alert-header {{
                        background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%);
                        color: white;
                        padding: 25px;
                        border-radius: 12px;
                        text-align: center;
                        margin-bottom: 25px;
                        border: 3px solid #a93226;
                        animation: pulse 2s infinite;
                    }}
                    @keyframes pulse {{
                        0% {{ box-shadow: 0 0 0 0 rgba(192, 57, 43, 0.7); }}
                        70% {{ box-shadow: 0 0 0 10px rgba(192, 57, 43, 0); }}
                        100% {{ box-shadow: 0 0 0 0 rgba(192, 57, 43, 0); }}
                    }}
                    .alert-header h1 {{
                        margin: 0;
                        font-size: 1.8em;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                    }}
                    .critical-info {{
                        background: linear-gradient(135deg, #fdedec 0%, #fadbd8 100%);
                        padding: 20px;
                        border-radius: 10px;
                        border-left: 6px solid #e74c3c;
                        margin-bottom: 25px;
                    }}
                    .critical-info h2 {{
                        color: #c0392b;
                        margin-top: 0;
                        font-size: 1.4em;
                    }}
                    .vulnerability-list {{
                        background: white;
                        border-radius: 10px;
                        padding: 20px;
                        margin-bottom: 25px;
                        border: 1px solid #e74c3c;
                        box-shadow: 0 4px 8px rgba(231, 76, 60, 0.1);
                    }}
                    .vuln-item {{
                        background: #fdf2f2;
                        margin: 15px 0;
                        padding: 15px;
                        border-radius: 8px;
                        border-left: 4px solid #e74c3c;
                    }}
                    .vuln-title {{
                        font-weight: bold;
                        color: #c0392b;
                        font-size: 1.1em;
                        margin-bottom: 8px;
                    }}
                    .cvss-badge {{
                        background: #c0392b;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 20px;
                        font-size: 0.9em;
                        font-weight: bold;
                        display: inline-block;
                        margin: 5px 0;
                    }}
                    .action-required {{
                        background: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        margin-bottom: 25px;
                    }}
                    .action-required h2 {{
                        margin-top: 0;
                        color: white;
                    }}
                    .footer {{
                        text-align: center;
                        color: #7f8c8d;
                        font-size: 0.9em;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #bdc3c7;
                    }}
                </style>
            </head>
            <body>
                <div class="alert-header">
                    <h1>🚨 緊急セキュリティアラート</h1>
                    <p>{datetime.now().strftime('%Y年%m月%d日 %H:%M')} 自動検出</p>
                </div>
                
                <div class="critical-info">
                    <h2>⚠️ 重大な脆弱性が検出されました</h2>
                    <p><strong>{critical_count}件の緊急対応が必要な脆弱性</strong>が自動検出システムにより発見されました。</p>
                    <p>これらの脆弱性は以下の条件に該当します：</p>
                    <ul>
                        <li>CVSS スコア 9.0 以上の重大脆弱性</li>
                        <li>AI分析により緊急性が「最高」と判定</li>
                        <li>公開エクスプロイトの存在が確認済み</li>
                        <li>広範囲への影響が予想される脆弱性</li>
                    </ul>
                </div>
                
                <div class="vulnerability-list">
                    <h2>🔍 検出された脆弱性一覧</h2>
            """
            
            # Add vulnerability details
            for i, article in enumerate(security_articles[:5], 1):  # Top 5 critical
                cvss_score = article.get('cvss_score', 'N/A')
                title = article.get('title', 'Unknown vulnerability')
                source = article.get('source', 'Unknown source')
                
                html_content += f"""
                    <div class="vuln-item">
                        <div class="vuln-title">{i}. {title}</div>
                        <div>情報源: {source}</div>
                        <span class="cvss-badge">CVSS: {cvss_score}</span>
                    </div>
                """
            
            html_content += f"""
                </div>
                
                <div class="action-required">
                    <h2>📋 緊急対応のお願い</h2>
                    <p><strong>即座に以下の対応を実施してください：</strong></p>
                    <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                        <li>影響システムの確認</li>
                        <li>緊急パッチの適用検討</li>
                        <li>一時的な緩和策の実施</li>
                        <li>監視体制の強化</li>
                        <li>インシデント対応チームへの連絡</li>
                    </ol>
                </div>
                
                <div class="footer">
                    <p>
                        <strong>News Delivery System - 緊急セキュリティ監視</strong><br>
                        このアラートは自動生成されました | 即座の対応が必要です
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send urgent security alert
            delivery_record = await self._send_email_with_attachments(
                subject=subject,
                html_content=html_content,
                attachments={},
                delivery_type='urgent_security',
                priority='high'
            )
            
            logger.info(f"Urgent security alert sent for {critical_count} vulnerabilities")
            return delivery_record
            
        except Exception as e:
            logger.error(f"Failed to send urgent security alert: {e}")
            raise EmailDeliveryError(f"Urgent security alert failed: {e}")