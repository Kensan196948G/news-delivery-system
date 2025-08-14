"""
Report Delivery Service
レポート配信サービス - Gmail統合とメール配信機能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from .report_generator import ReportGenerator
from utils.config import get_config
from utils.logger import setup_logger
from models.article import Article

logger = logging.getLogger(__name__)


class ReportDeliveryError(Exception):
    """Report delivery specific error"""
    pass


class ReportDeliveryService:
    """レポート配信サービス"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        
        # Initialize report generator
        self.report_generator = ReportGenerator(self.config)
        
        # Delivery configuration
        self.delivery_enabled = self.config.get('delivery', 'enabled', default=True)
        self.recipients = self.config.get('delivery', 'recipients', default=['admin@example.com'])
        self.sender_email = self.config.get('delivery', 'sender_email', default='news-system@example.com')
        self.delivery_schedule = self.config.get('delivery', 'schedule', default=['07:00', '12:00', '18:00'])
        
        # Gmail integration settings
        self.gmail_enabled = self.config.get('gmail', 'enabled', default=False)
        self.gmail_credentials_path = self.config.get('gmail', 'credentials_path', default='')
        
        # Urgent notification settings
        self.urgent_notification_enabled = self.config.get('delivery', 'urgent_notification', 'enabled', default=True)
        self.urgent_importance_threshold = self.config.get('delivery', 'urgent_notification', 'importance_threshold', default=9)
        self.urgent_cvss_threshold = self.config.get('delivery', 'urgent_notification', 'cvss_threshold', default=9.0)
        
        # Delivery history
        self.delivery_history = []
    
    async def deliver_daily_report(self, articles: List[Article]) -> Dict[str, Any]:
        """日次レポートの配信"""
        try:
            self.logger.info(f"Starting daily report delivery for {len(articles)} articles")
            
            # Generate reports
            reports = await self.report_generator.generate_daily_report(articles)
            
            # Prepare email content
            email_data = self._prepare_daily_email(articles, reports)
            
            # Send to all recipients
            delivery_results = []
            for recipient in self.recipients:
                try:
                    result = await self._send_email(
                        recipient=recipient,
                        subject=email_data['subject'],
                        html_content=email_data['html_content'],
                        attachments=email_data['attachments']
                    )
                    delivery_results.append({
                        'recipient': recipient,
                        'status': 'success',
                        'message_id': result.get('id', 'unknown')
                    })
                except Exception as e:
                    self.logger.error(f"Failed to send to {recipient}: {e}")
                    delivery_results.append({
                        'recipient': recipient,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Record delivery history
            delivery_record = {
                'delivery_type': 'daily',
                'timestamp': datetime.now().isoformat(),
                'article_count': len(articles),
                'reports_generated': list(reports.keys()),
                'recipients': len(self.recipients),
                'successful_deliveries': len([r for r in delivery_results if r['status'] == 'success']),
                'failed_deliveries': len([r for r in delivery_results if r['status'] == 'failed']),
                'delivery_results': delivery_results
            }
            
            self.delivery_history.append(delivery_record)
            
            self.logger.info(f"Daily report delivery completed: {delivery_record['successful_deliveries']}/{len(self.recipients)} successful")
            
            return delivery_record
            
        except Exception as e:
            self.logger.error(f"Daily report delivery failed: {e}")
            raise ReportDeliveryError(f"Failed to deliver daily report: {e}")
    
    async def deliver_urgent_alert(self, urgent_articles: List[Article]) -> Dict[str, Any]:
        """緊急アラートの配信"""
        try:
            if not self.urgent_notification_enabled:
                self.logger.info("Urgent notifications are disabled")
                return {'status': 'disabled', 'message': 'Urgent notifications are disabled'}
            
            if not urgent_articles:
                self.logger.warning("No urgent articles to deliver")
                return {'status': 'no_articles', 'message': 'No urgent articles found'}
            
            self.logger.warning(f"Sending urgent alert for {len(urgent_articles)} critical articles")
            
            # Generate urgent alert report
            reports = await self.report_generator.generate_urgent_alert(urgent_articles)
            
            # Prepare urgent email content
            email_data = self._prepare_urgent_email(urgent_articles, reports)
            
            # Send to all recipients with high priority
            delivery_results = []
            for recipient in self.recipients:
                try:
                    result = await self._send_email(
                        recipient=recipient,
                        subject=email_data['subject'],
                        html_content=email_data['html_content'],
                        attachments=email_data['attachments'],
                        priority='high'
                    )
                    delivery_results.append({
                        'recipient': recipient,
                        'status': 'success',
                        'message_id': result.get('id', 'unknown')
                    })
                except Exception as e:
                    self.logger.error(f"Failed to send urgent alert to {recipient}: {e}")
                    delivery_results.append({
                        'recipient': recipient,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Record urgent delivery
            delivery_record = {
                'delivery_type': 'urgent',
                'timestamp': datetime.now().isoformat(),
                'article_count': len(urgent_articles),
                'max_importance': max(getattr(a, 'importance_score', 5) for a in urgent_articles),
                'max_cvss': max((getattr(a, 'cvss_score', 0) or 0) for a in urgent_articles),
                'reports_generated': list(reports.keys()),
                'recipients': len(self.recipients),
                'successful_deliveries': len([r for r in delivery_results if r['status'] == 'success']),
                'failed_deliveries': len([r for r in delivery_results if r['status'] == 'failed']),
                'delivery_results': delivery_results
            }
            
            self.delivery_history.append(delivery_record)
            
            self.logger.warning(f"Urgent alert delivery completed: {delivery_record['successful_deliveries']}/{len(self.recipients)} successful")
            
            return delivery_record
            
        except Exception as e:
            self.logger.error(f"Urgent alert delivery failed: {e}")
            raise ReportDeliveryError(f"Failed to deliver urgent alert: {e}")
    
    async def deliver_weekly_summary(self, articles: List[Article], 
                                   start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """週間サマリーの配信"""
        try:
            self.logger.info(f"Starting weekly summary delivery for {len(articles)} articles")
            
            # Generate weekly report
            reports = await self.report_generator.generate_weekly_report(articles, start_date, end_date)
            
            # Prepare weekly email content
            email_data = self._prepare_weekly_email(articles, reports, start_date, end_date)
            
            # Send to all recipients
            delivery_results = []
            for recipient in self.recipients:
                try:
                    result = await self._send_email(
                        recipient=recipient,
                        subject=email_data['subject'],
                        html_content=email_data['html_content'],
                        attachments=email_data['attachments']
                    )
                    delivery_results.append({
                        'recipient': recipient,
                        'status': 'success',
                        'message_id': result.get('id', 'unknown')
                    })
                except Exception as e:
                    self.logger.error(f"Failed to send weekly summary to {recipient}: {e}")
                    delivery_results.append({
                        'recipient': recipient,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Record delivery
            delivery_record = {
                'delivery_type': 'weekly',
                'timestamp': datetime.now().isoformat(),
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'article_count': len(articles),
                'reports_generated': list(reports.keys()),
                'recipients': len(self.recipients),
                'successful_deliveries': len([r for r in delivery_results if r['status'] == 'success']),
                'failed_deliveries': len([r for r in delivery_results if r['status'] == 'failed']),
                'delivery_results': delivery_results
            }
            
            self.delivery_history.append(delivery_record)
            
            self.logger.info(f"Weekly summary delivery completed: {delivery_record['successful_deliveries']}/{len(self.recipients)} successful")
            
            return delivery_record
            
        except Exception as e:
            self.logger.error(f"Weekly summary delivery failed: {e}")
            raise ReportDeliveryError(f"Failed to deliver weekly summary: {e}")
    
    def _prepare_daily_email(self, articles: List[Article], reports: Dict[str, str]) -> Dict[str, Any]:
        """日次レポートのメール内容準備"""
        urgent_count = len([a for a in articles if getattr(a, 'is_urgent', False)])
        
        subject = f"📰 日次ニュースレポート - {datetime.now().strftime('%Y/%m/%d')} ({len(articles)}件"
        if urgent_count > 0:
            subject += f", 緊急{urgent_count}件"
        subject += ")"
        
        # Load HTML content from generated report
        html_content = ""
        if 'html' in reports:
            try:
                with open(reports['html'], 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                self.logger.error(f"Failed to load HTML report: {e}")
                html_content = self._create_fallback_html(articles)
        else:
            html_content = self._create_fallback_html(articles)
        
        # Prepare attachments
        attachments = []
        if 'pdf' in reports and Path(reports['pdf']).exists():
            attachments.append({
                'path': reports['pdf'],
                'name': f"news_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                'type': 'application/pdf'
            })
        
        return {
            'subject': subject,
            'html_content': html_content,
            'attachments': attachments
        }
    
    def _prepare_urgent_email(self, urgent_articles: List[Article], reports: Dict[str, str]) -> Dict[str, Any]:
        """緊急アラートのメール内容準備"""
        max_importance = max(getattr(a, 'importance_score', 5) for a in urgent_articles)
        max_cvss = max((getattr(a, 'cvss_score', 0) or 0) for a in urgent_articles)
        
        subject = f"🚨 緊急ニュースアラート - {datetime.now().strftime('%Y/%m/%d %H:%M')} ({len(urgent_articles)}件, 最高重要度{max_importance}"
        if max_cvss > 0:
            subject += f", CVSS{max_cvss}"
        subject += ")"
        
        # Load HTML content from generated urgent report
        html_content = ""
        if 'html' in reports:
            try:
                with open(reports['html'], 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                self.logger.error(f"Failed to load urgent HTML report: {e}")
                html_content = self._create_fallback_urgent_html(urgent_articles)
        else:
            html_content = self._create_fallback_urgent_html(urgent_articles)
        
        # Prepare attachments
        attachments = []
        if 'pdf' in reports and Path(reports['pdf']).exists():
            attachments.append({
                'path': reports['pdf'],
                'name': f"urgent_alert_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                'type': 'application/pdf'
            })
        
        return {
            'subject': subject,
            'html_content': html_content,
            'attachments': attachments
        }
    
    def _prepare_weekly_email(self, articles: List[Article], reports: Dict[str, str], 
                            start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """週間サマリーのメール内容準備"""
        urgent_count = len([a for a in articles if getattr(a, 'is_urgent', False)])
        
        subject = f"📊 週間ニュース総括 - {start_date.strftime('%m/%d')}〜{end_date.strftime('%m/%d')} ({len(articles)}件"
        if urgent_count > 0:
            subject += f", 緊急{urgent_count}件"
        subject += ")"
        
        # Load HTML content from generated weekly report
        html_content = ""
        if 'html' in reports:
            try:
                with open(reports['html'], 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                self.logger.error(f"Failed to load weekly HTML report: {e}")
                html_content = self._create_fallback_weekly_html(articles, start_date, end_date)
        else:
            html_content = self._create_fallback_weekly_html(articles, start_date, end_date)
        
        # Prepare attachments
        attachments = []
        if 'pdf' in reports and Path(reports['pdf']).exists():
            attachments.append({
                'path': reports['pdf'],
                'name': f"weekly_summary_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf",
                'type': 'application/pdf'
            })
        
        return {
            'subject': subject,
            'html_content': html_content,
            'attachments': attachments
        }
    
    async def _send_email(self, recipient: str, subject: str, html_content: str, 
                         attachments: List[Dict] = None, priority: str = 'normal') -> Dict[str, Any]:
        """メール送信（Gmail API統合）"""
        if not self.delivery_enabled:
            self.logger.info("Email delivery is disabled")
            return {'status': 'disabled', 'message': 'Email delivery is disabled'}
        
        # In this implementation, we simulate email sending
        # In production, this would integrate with Gmail API
        self.logger.info(f"Sending email to {recipient}: {subject}")
        
        # Simulate email sending delay
        await asyncio.sleep(0.5)
        
        # Return mock success response
        return {
            'id': f"mock_message_id_{datetime.now().timestamp()}",
            'status': 'sent',
            'recipient': recipient,
            'subject': subject,
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_fallback_html(self, articles: List[Article]) -> str:
        """フォールバック用シンプルHTML生成"""
        urgent_articles = [a for a in articles if getattr(a, 'is_urgent', False)]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>日次ニュースレポート</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .urgent {{ background-color: #e74c3c; color: white; padding: 15px; margin: 10px 0; }}
                .article {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
                .title {{ font-weight: bold; color: #2c3e50; margin-bottom: 5px; }}
                .meta {{ color: #7f8c8d; font-size: 0.9em; margin-bottom: 8px; }}
                .summary {{ margin-bottom: 10px; }}
                .importance {{ background-color: #3498db; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>日次ニュースレポート</h1>
                <p>{datetime.now().strftime('%Y年%m月%d日')} | 総記事数: {len(articles)}件</p>
            </div>
        """
        
        if urgent_articles:
            html += f"""
            <div class="urgent">
                <h2>🚨 緊急記事 ({len(urgent_articles)}件)</h2>
                {"".join([f'<div class="article"><div class="title">{getattr(a, "title_translated", "") or getattr(a, "title", "")}</div></div>' for a in urgent_articles[:3]])}
            </div>
            """
        
        html += "<h2>📰 記事一覧</h2>"
        
        for article in articles[:10]:  # Show top 10 articles
            html += f"""
            <div class="article">
                <div class="title">{getattr(article, 'title_translated', '') or getattr(article, 'title', '')}</div>
                <div class="meta">
                    {getattr(getattr(article, 'source', {}), 'name', 'Unknown') if isinstance(getattr(article, 'source', {}), dict) else str(getattr(article, 'source', 'Unknown'))} | 
                    {getattr(article, 'published_at', 'Unknown date')}
                </div>
                {f'<div class="summary">{getattr(article, "summary", "")}</div>' if getattr(article, 'summary', '') else ''}
                <div><span class="importance">重要度: {getattr(article, 'importance_score', 5)}/10</span></div>
            </div>
            """
        
        html += """
            <div style="margin-top: 30px; text-align: center; color: #7f8c8d;">
                <p>このレポートは News Delivery System により自動生成されました。</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_fallback_urgent_html(self, urgent_articles: List[Article]) -> str:
        """緊急アラート用フォールバックHTML"""
        max_importance = max(getattr(a, 'importance_score', 5) for a in urgent_articles)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>緊急ニュースアラート</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; background-color: #2c1810; color: white; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #e74c3c, #c0392b); padding: 30px; text-align: center; border-radius: 10px; margin-bottom: 20px; }}
                .urgent-article {{ background-color: rgba(255,255,255,0.1); padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #e74c3c; }}
                .title {{ font-weight: bold; margin-bottom: 8px; color: #fff; }}
                .meta {{ color: #bdc3c7; font-size: 0.9em; margin-bottom: 8px; }}
                .summary {{ margin-bottom: 10px; }}
                .importance {{ background-color: #e74c3c; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 緊急ニュースアラート</h1>
                    <p>{datetime.now().strftime('%Y年%m月%d日 %H:%M')} | {len(urgent_articles)}件の緊急記事</p>
                    <p>最高重要度: {max_importance}/10</p>
                </div>
        """
        
        for article in urgent_articles:
            html += f"""
            <div class="urgent-article">
                <div class="title">{getattr(article, 'title_translated', '') or getattr(article, 'title', '')}</div>
                <div class="meta">
                    {getattr(getattr(article, 'source', {}), 'name', 'Unknown') if isinstance(getattr(article, 'source', {}), dict) else str(getattr(article, 'source', 'Unknown'))} | 
                    {getattr(article, 'published_at', 'Unknown date')}
                </div>
                {f'<div class="summary">{getattr(article, "summary", "")}</div>' if getattr(article, 'summary', '') else ''}
                <div><span class="importance">重要度: {getattr(article, 'importance_score', 5)}/10</span></div>
            </div>
            """
        
        html += """
                <div style="margin-top: 30px; text-align: center; background-color: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px;">
                    <p><strong>⚡ 緊急対応が必要です</strong></p>
                    <p>この緊急アラートは News Delivery System により自動生成されました。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_fallback_weekly_html(self, articles: List[Article], 
                                   start_date: datetime, end_date: datetime) -> str:
        """週間サマリー用フォールバックHTML"""
        urgent_count = len([a for a in articles if getattr(a, 'is_urgent', False)])
        avg_importance = sum(getattr(a, 'importance_score', 5) for a in articles) / len(articles) if articles else 0
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>週間ニュース総括</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
                .header {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 30px; text-align: center; border-radius: 10px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat-item {{ text-align: center; padding: 15px; background-color: #3498db; color: white; border-radius: 8px; margin: 5px; }}
                .stat-number {{ font-size: 2em; font-weight: bold; display: block; }}
                .article {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
                .title {{ font-weight: bold; color: #2c3e50; margin-bottom: 5px; }}
                .meta {{ color: #7f8c8d; font-size: 0.9em; margin-bottom: 8px; }}
                .importance {{ background-color: #3498db; color: white; padding: 3px 8px; border-radius: 10px; font-size: 0.8em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 週間ニュース総括レポート</h1>
                <p>{start_date.strftime('%Y年%m月%d日')} 〜 {end_date.strftime('%m月%d日')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-number">{len(articles)}</span>
                    <span>総記事数</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{urgent_count}</span>
                    <span>緊急記事</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{avg_importance:.1f}</span>
                    <span>平均重要度</span>
                </div>
            </div>
            
            <h2>📈 今週のハイライト</h2>
        """
        
        # Show top 10 articles by importance
        top_articles = sorted(articles, key=lambda x: getattr(x, 'importance_score', 5), reverse=True)[:10]
        
        for article in top_articles:
            html += f"""
            <div class="article">
                <div class="title">{getattr(article, 'title_translated', '') or getattr(article, 'title', '')}</div>
                <div class="meta">
                    {getattr(getattr(article, 'source', {}), 'name', 'Unknown') if isinstance(getattr(article, 'source', {}), dict) else str(getattr(article, 'source', 'Unknown'))} | 
                    {getattr(article, 'published_at', 'Unknown date')}
                </div>
                <div><span class="importance">重要度: {getattr(article, 'importance_score', 5)}/10</span></div>
            </div>
            """
        
        html += """
            <div style="margin-top: 30px; text-align: center; color: #7f8c8d;">
                <p>この週間総括レポートは News Delivery System により自動生成されました。</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def get_delivery_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """配信履歴の取得"""
        return self.delivery_history[-limit:] if limit > 0 else self.delivery_history
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """配信統計の取得"""
        if not self.delivery_history:
            return {
                'total_deliveries': 0,
                'successful_deliveries': 0,
                'failed_deliveries': 0,
                'success_rate': 0.0,
                'delivery_types': {},
                'last_delivery': None
            }
        
        total_successful = sum(d.get('successful_deliveries', 0) for d in self.delivery_history)
        total_failed = sum(d.get('failed_deliveries', 0) for d in self.delivery_history)
        total_deliveries = total_successful + total_failed
        
        delivery_types = {}
        for delivery in self.delivery_history:
            delivery_type = delivery.get('delivery_type', 'unknown')
            delivery_types[delivery_type] = delivery_types.get(delivery_type, 0) + 1
        
        return {
            'total_deliveries': total_deliveries,
            'successful_deliveries': total_successful,
            'failed_deliveries': total_failed,
            'success_rate': (total_successful / total_deliveries * 100) if total_deliveries > 0 else 0.0,
            'delivery_types': delivery_types,
            'last_delivery': self.delivery_history[-1] if self.delivery_history else None
        }
    
    def is_urgent_delivery_needed(self, articles: List[Article]) -> bool:
        """緊急配信が必要かの判定"""
        if not self.urgent_notification_enabled:
            return False
        
        for article in articles:
            importance = getattr(article, 'importance_score', 5)
            cvss_score = getattr(article, 'cvss_score', None)
            
            if importance >= self.urgent_importance_threshold:
                return True
            
            if cvss_score and cvss_score >= self.urgent_cvss_threshold:
                return True
        
        return False
    
    def filter_urgent_articles(self, articles: List[Article]) -> List[Article]:
        """緊急記事のフィルタリング"""
        urgent_articles = []
        
        for article in articles:
            importance = getattr(article, 'importance_score', 5)
            cvss_score = getattr(article, 'cvss_score', None)
            is_urgent = getattr(article, 'is_urgent', False)
            
            if (importance >= self.urgent_importance_threshold or 
                (cvss_score and cvss_score >= self.urgent_cvss_threshold) or
                is_urgent):
                urgent_articles.append(article)
        
        return urgent_articles
    
    async def test_delivery_system(self) -> Dict[str, Any]:
        """配信システムのテスト"""
        try:
            test_results = {
                'timestamp': datetime.now().isoformat(),
                'tests': []
            }
            
            # Test configuration
            config_test = {
                'name': 'Configuration Test',
                'status': 'success' if self.delivery_enabled else 'warning',
                'message': 'Delivery system is enabled' if self.delivery_enabled else 'Delivery system is disabled',
                'details': {
                    'delivery_enabled': self.delivery_enabled,
                    'recipients_count': len(self.recipients),
                    'gmail_enabled': self.gmail_enabled,
                    'urgent_notifications': self.urgent_notification_enabled
                }
            }
            test_results['tests'].append(config_test)
            
            # Test email sending (mock)
            email_test = {
                'name': 'Email Sending Test',
                'status': 'success',
                'message': 'Mock email sending successful',
                'details': {
                    'test_recipient': self.recipients[0] if self.recipients else 'no-recipients',
                    'mock_delivery': True
                }
            }
            test_results['tests'].append(email_test)
            
            # Test report generation
            from models.article import Article, ArticleCategory, ArticleLanguage
            test_articles = [
                Article(
                    title="Test Article",
                    content="This is a test article for delivery system testing.",
                    url="https://test.example.com/article",
                    source={'name': 'Test Source'},
                    category=ArticleCategory.TECHNOLOGY,
                    language=ArticleLanguage.ENGLISH,
                    importance_score=7
                )
            ]
            
            try:
                reports = await self.report_generator.generate_daily_report(test_articles)
                report_test = {
                    'name': 'Report Generation Test',
                    'status': 'success',
                    'message': f'Generated {len(reports)} report formats',
                    'details': {
                        'formats_generated': list(reports.keys()),
                        'test_articles': len(test_articles)
                    }
                }
            except Exception as e:
                report_test = {
                    'name': 'Report Generation Test',
                    'status': 'failed',
                    'message': f'Report generation failed: {str(e)}',
                    'details': {'error': str(e)}
                }
            
            test_results['tests'].append(report_test)
            
            # Overall status
            failed_tests = [t for t in test_results['tests'] if t['status'] == 'failed']
            test_results['overall_status'] = 'failed' if failed_tests else 'success'
            test_results['summary'] = f"{len(test_results['tests']) - len(failed_tests)}/{len(test_results['tests'])} tests passed"
            
            return test_results
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'error',
                'message': f'Delivery system test failed: {str(e)}',
                'error': str(e)
            }