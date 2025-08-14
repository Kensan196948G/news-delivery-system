"""
Email Sender Service - Wrapper for Gmail delivery functionality
メール送信サービス
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .email_delivery import GmailDeliveryService, EmailDeliveryError
from .emergency_alert_system import EmergencyAlertService
from models.article import Article
from utils.config import get_config
from utils.logger import setup_logger


class EmailSender:
    """
    Main email sender service that coordinates different email delivery methods
    メール送信サービスのメインクラス
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        
        # Initialize Gmail delivery service
        try:
            self.gmail_service = GmailDeliveryService(self.config)
            self.logger.info("Gmail delivery service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gmail service: {e}")
            self.gmail_service = None
        
        # Initialize emergency alert service
        try:
            self.emergency_service = EmergencyAlertService(self.config)
            self.logger.info("Emergency alert service initialized successfully")
        except Exception as e:
            self.logger.warning(f"Emergency alert service not available: {e}")
            self.emergency_service = None
    
    async def send_report(self, html_content: str, pdf_path: Optional[str] = None, articles: List[Article] = None) -> bool:
        """
        Send regular daily/scheduled report
        定期レポートの送信
        """
        if not self.gmail_service:
            self.logger.error("Gmail service not available")
            return False
        
        try:
            self.logger.info("Sending daily news report")
            
            # Prepare email details
            subject = self._generate_report_subject(articles)
            recipients = self.config.get('delivery', 'recipients', default=[])
            
            if not recipients:
                self.logger.warning("No recipients configured")
                return False
            
            # Send email using Gmail service
            result = await self.gmail_service.send_email(
                to_emails=recipients,
                subject=subject,
                html_content=html_content,
                attachments=[pdf_path] if pdf_path and Path(pdf_path).exists() else None
            )
            
            if result.get('success', False):
                self.logger.info(f"Report sent successfully to {len(recipients)} recipients")
                return True
            else:
                self.logger.error(f"Failed to send report: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending report: {e}")
            return False
    
    async def send_emergency_alert(self, html_content: str, emergency_articles: List[Article]) -> bool:
        """
        Send emergency alert for high-priority news
        緊急アラートの送信
        """
        if not emergency_articles:
            self.logger.info("No emergency articles to send")
            return True
        
        try:
            self.logger.warning(f"Sending emergency alert for {len(emergency_articles)} articles")
            
            # Use emergency service if available, otherwise fallback to Gmail
            if self.emergency_service:
                result = await self.emergency_service.send_emergency_alert(
                    articles=emergency_articles,
                    html_content=html_content
                )
            elif self.gmail_service:
                subject = self._generate_emergency_subject(emergency_articles)
                recipients = self.config.get('delivery', 'recipients', default=[])
                
                result = await self.gmail_service.send_email(
                    to_emails=recipients,
                    subject=subject,
                    html_content=html_content,
                    priority='high'
                )
            else:
                self.logger.error("No email services available for emergency alert")
                return False
            
            if result.get('success', False):
                self.logger.info("Emergency alert sent successfully")
                return True
            else:
                self.logger.error(f"Failed to send emergency alert: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending emergency alert: {e}")
            return False
    
    async def send_test_email(self) -> bool:
        """
        Send test email to verify email configuration
        テストメールの送信
        """
        if not self.gmail_service:
            self.logger.error("Gmail service not available for test email")
            return False
        
        try:
            self.logger.info("Sending test email")
            
            test_subject = f"[テスト] ニュース配信システム - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            test_content = """
            <html>
            <body>
            <h2>ニュース配信システム テストメール</h2>
            <p>このメールは、ニュース配信システムの動作確認のために送信されました。</p>
            <p>システムが正常に動作しています。</p>
            <hr>
            <p><small>送信時刻: {}</small></p>
            </body>
            </html>
            """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            recipients = self.config.get('delivery', 'recipients', default=[])
            
            result = await self.gmail_service.send_email(
                to_emails=recipients,
                subject=test_subject,
                html_content=test_content
            )
            
            if result.get('success', False):
                self.logger.info("Test email sent successfully")
                return True
            else:
                self.logger.error(f"Failed to send test email: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending test email: {e}")
            return False
    
    def _generate_report_subject(self, articles: List[Article] = None) -> str:
        """
        Generate subject line for regular report
        定期レポートの件名生成
        """
        date_str = datetime.now().strftime('%Y年%m月%d日')
        time_str = datetime.now().strftime('%H:%M')
        
        if articles:
            article_count = len(articles)
            high_priority_count = len([a for a in articles if getattr(a, 'importance_score', 0) >= 8])
            
            if high_priority_count > 0:
                return f"【重要】ニュース配信レポート ({date_str} {time_str}) - {article_count}件 (重要{high_priority_count}件)"
            else:
                return f"ニュース配信レポート ({date_str} {time_str}) - {article_count}件"
        else:
            return f"ニュース配信レポート ({date_str} {time_str})"
    
    def _generate_emergency_subject(self, emergency_articles: List[Article]) -> str:
        """
        Generate subject line for emergency alert
        緊急アラートの件名生成
        """
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        article_count = len(emergency_articles)
        
        # Check for security vulnerabilities
        vuln_articles = [a for a in emergency_articles if getattr(a, 'cvss_score', 0) >= 9.0]
        
        if vuln_articles:
            return f"🚨【緊急】重要セキュリティ脆弱性アラート ({date_str}) - {article_count}件"
        else:
            return f"🔴【緊急】重要ニュースアラート ({date_str}) - {article_count}件"
    
    def get_sender_status(self) -> Dict[str, Any]:
        """
        Get current email sender status
        メール送信サービスの状態取得
        """
        status = {
            'service': 'EmailSender',
            'gmail_service': {
                'available': self.gmail_service is not None,
                'configured': False
            },
            'emergency_service': {
                'available': self.emergency_service is not None
            },
            'recipients': self.config.get('delivery', 'recipients', default=[]),
            'last_check': datetime.now().isoformat()
        }
        
        # Check Gmail service configuration
        if self.gmail_service:
            try:
                gmail_status = getattr(self.gmail_service, 'get_service_status', lambda: {})()
                status['gmail_service'].update(gmail_status)
            except Exception as e:
                status['gmail_service']['status_error'] = str(e)
        
        return status
    
    async def test_configuration(self) -> Dict[str, Any]:
        """
        Test email configuration and connectivity
        メール設定のテスト
        """
        test_results = {
            'gmail_service': False,
            'emergency_service': False,
            'recipients_configured': False,
            'overall_status': 'failed'
        }
        
        try:
            # Test Gmail service
            if self.gmail_service:
                gmail_test = await self.gmail_service.test_connection()
                test_results['gmail_service'] = gmail_test.get('success', False)
            
            # Test emergency service
            if self.emergency_service:
                emergency_test = getattr(self.emergency_service, 'test_configuration', lambda: {'success': True})()
                test_results['emergency_service'] = emergency_test.get('success', False)
            
            # Check recipients
            recipients = self.config.get('delivery', 'recipients', default=[])
            test_results['recipients_configured'] = len(recipients) > 0
            test_results['recipient_count'] = len(recipients)
            
            # Overall status
            if test_results['gmail_service'] and test_results['recipients_configured']:
                test_results['overall_status'] = 'success'
            elif test_results['gmail_service']:
                test_results['overall_status'] = 'partial'
            
        except Exception as e:
            test_results['error'] = str(e)
        
        return test_results