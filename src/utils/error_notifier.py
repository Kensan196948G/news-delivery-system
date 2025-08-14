"""
Error Notification System
エラー通知システム - 重大エラーの検出と管理者への通知
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import smtplib
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from enum import Enum
import traceback
import sys

from .config import get_config
from .cache_manager import get_cache_manager


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorEvent:
    """エラーイベント"""
    timestamp: datetime
    error_type: str
    message: str
    severity: ErrorSeverity
    context: str
    traceback_info: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class ErrorNotifier:
    """エラー通知システム"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.cache = get_cache_manager()
        
        # 通知設定
        self.admin_email = os.getenv('ADMIN_EMAIL') or os.getenv('SENDER_EMAIL')
        self.notification_cooldown = 3600  # 1時間のクールダウン
        
        # エラー閾値設定
        self.error_thresholds = {
            ErrorSeverity.CRITICAL: 1,    # 即座に通知
            ErrorSeverity.HIGH: 3,        # 3回で通知
            ErrorSeverity.MEDIUM: 10,     # 10回で通知
            ErrorSeverity.LOW: 50         # 50回で通知
        }
        
        # エラー統計
        self.error_counts: Dict[str, int] = {}
        self.last_notification: Dict[str, datetime] = {}
    
    async def handle_error(self, error: Exception, context: str = "", 
                          severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                          additional_info: Optional[Dict[str, Any]] = None) -> str:
        """エラーハンドリングと通知判定"""
        try:
            # エラーイベント作成
            error_event = ErrorEvent(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                message=str(error),
                severity=severity,
                context=context,
                traceback_info=traceback.format_exc(),
                additional_info=additional_info
            )
            
            # ログに記録
            self._log_error(error_event)
            
            # エラー統計更新
            error_key = f"{error_event.error_type}:{context}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # 通知判定
            should_notify = self._should_notify(error_event, error_key)
            
            if should_notify:
                await self._send_error_notification(error_event, error_key)
                self.last_notification[error_key] = datetime.now()
            
            return error_key
            
        except Exception as notification_error:
            logger.error(f"Error notification system failed: {notification_error}")
            return f"notification_failed:{type(error).__name__}"
    
    def _log_error(self, error_event: ErrorEvent):
        """エラーログ記録"""
        log_message = f"[{error_event.severity.value.upper()}] {error_event.context}: {error_event.error_type}: {error_event.message}"
        
        if error_event.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_event.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_event.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # 詳細情報があればDEBUGレベルで記録
        if error_event.additional_info:
            logger.debug(f"Additional info: {error_event.additional_info}")
    
    def _should_notify(self, error_event: ErrorEvent, error_key: str) -> bool:
        """通知すべきかどうかの判定"""
        # 重要度による即座通知
        if error_event.severity == ErrorSeverity.CRITICAL:
            return True
        
        # クールダウン期間チェック
        last_notified = self.last_notification.get(error_key)
        if last_notified and (datetime.now() - last_notified).total_seconds() < self.notification_cooldown:
            return False
        
        # エラー回数による通知判定
        error_count = self.error_counts.get(error_key, 0)
        threshold = self.error_thresholds.get(error_event.severity, 10)
        
        return error_count >= threshold
    
    async def _send_error_notification(self, error_event: ErrorEvent, error_key: str):
        """エラー通知送信"""
        try:
            if not self.admin_email:
                logger.warning("Admin email not configured, skipping notification")
                return
            
            # メール件名
            subject = f"[{error_event.severity.value.upper()}] News Delivery System Error - {error_event.error_type}"
            
            # メール本文
            body = self._create_error_email_body(error_event, error_key)
            
            # メール送信
            await self._send_email(self.admin_email, subject, body)
            
            logger.info(f"Error notification sent for: {error_key}")
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def _create_error_email_body(self, error_event: ErrorEvent, error_key: str) -> str:
        """エラー通知メール本文作成"""
        error_count = self.error_counts.get(error_key, 0)
        
        body = f"""
News Delivery System エラー通知

【エラー概要】
発生時刻: {error_event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
エラー種別: {error_event.error_type}
重要度: {error_event.severity.value.upper()}
コンテキスト: {error_event.context}
発生回数: {error_count}回

【エラーメッセージ】
{error_event.message}

【詳細情報】
"""
        
        if error_event.additional_info:
            body += f"\n追加情報:\n"
            for key, value in error_event.additional_info.items():
                body += f"  {key}: {value}\n"
        
        if error_event.traceback_info:
            body += f"\n【スタックトレース】\n{error_event.traceback_info}\n"
        
        body += f"""
【対処方法】
"""
        
        # エラー種別に応じた対処方法
        if "API" in error_event.error_type or "HTTP" in error_event.error_type:
            body += "- APIキーの確認\n- ネットワーク接続の確認\n- レート制限の確認\n"
        elif "Database" in error_event.error_type or "SQL" in error_event.error_type:
            body += "- データベースファイルの確認\n- ディスク容量の確認\n- 権限の確認\n"
        elif "Translation" in error_event.error_type:
            body += "- DeepL API使用量の確認\n- APIキーの確認\n"
        elif "Gmail" in error_event.error_type or "Email" in error_event.error_type:
            body += "- Gmail認証の確認\n- インターネット接続の確認\n"
        else:
            body += "- ログファイルの詳細確認\n- システムリソースの確認\n"
        
        body += f"""
【システム情報】
Python バージョン: {sys.version}
実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

このメールは自動送信されました。
"""
        
        return body
    
    async def _send_email(self, recipient: str, subject: str, body: str):
        """メール送信"""
        try:
            # Gmail API経由での送信を試行
            from services.email_delivery import GmailDeliveryService
            
            gmail_service = GmailDeliveryService(self.config)
            
            # HTMLメール作成
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #f44336; color: white; padding: 10px; margin-bottom: 20px;">
                <h2>🚨 News Delivery System エラー通知</h2>
            </div>
            <pre style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #f44336;">
{body}
            </pre>
            </body>
            </html>
            """
            
            await gmail_service.send_report(
                recipient=recipient,
                subject=subject,
                html_content=html_body
            )
            
        except Exception as gmail_error:
            logger.error(f"Gmail notification failed: {gmail_error}")
            # フォールバック: SMTPによる送信を試行
            await self._send_smtp_email(recipient, subject, body)
    
    async def _send_smtp_email(self, recipient: str, subject: str, body: str):
        """SMTP経由でのメール送信（フォールバック）"""
        try:
            # SMTP設定
            smtp_server = self.config.get('delivery.email.smtp_server', 'smtp.gmail.com')
            smtp_port = self.config.get('delivery.email.smtp_port', 587)
            sender_email = os.getenv('SENDER_EMAIL')
            sender_password = os.getenv('SENDER_PASSWORD')  # アプリパスワード
            
            if not all([sender_email, sender_password]):
                logger.warning("SMTP credentials not configured")
                return
            
            # メッセージ作成
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # SMTP送信
            def send_smtp():
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
            
            await asyncio.to_thread(send_smtp)
            logger.info(f"SMTP notification sent to: {recipient}")
            
        except Exception as smtp_error:
            logger.error(f"SMTP notification failed: {smtp_error}")
    
    async def send_critical_alert(self, message: str, context: str = "System Alert"):
        """重大アラートの送信"""
        critical_error = Exception(message)
        await self.handle_error(
            critical_error, 
            context=context, 
            severity=ErrorSeverity.CRITICAL
        )
    
    async def send_system_status_alert(self, status_info: Dict[str, Any]):
        """システム状態アラート"""
        if not status_info.get('overall_health') == 'healthy':
            error_message = f"System health degraded: {status_info.get('overall_health', 'unknown')}"
            await self.send_critical_alert(error_message, "System Health Check")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """エラー統計サマリー取得"""
        try:
            total_errors = sum(self.error_counts.values())
            error_types = len(self.error_counts)
            
            # 最も多いエラー
            most_common_error = max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None
            
            # 最近の通知
            recent_notifications = len([
                t for t in self.last_notification.values() 
                if (datetime.now() - t).total_seconds() < 86400  # 24時間以内
            ])
            
            return {
                'total_errors': total_errors,
                'error_types': error_types,
                'most_common_error': most_common_error,
                'recent_notifications': recent_notifications,
                'notification_cooldown_hours': self.notification_cooldown / 3600,
                'admin_email': self.admin_email
            }
            
        except Exception as e:
            logger.error(f"Failed to get error summary: {e}")
            return {}
    
    def reset_error_counts(self):
        """エラーカウントリセット"""
        self.error_counts.clear()
        self.last_notification.clear()
        logger.info("Error counts reset")


# グローバルエラー通知インスタンス
_error_notifier_instance = None


def get_error_notifier() -> ErrorNotifier:
    """グローバルエラー通知インスタンス取得"""
    global _error_notifier_instance
    if _error_notifier_instance is None:
        _error_notifier_instance = ErrorNotifier()
    return _error_notifier_instance


async def handle_critical_error(error: Exception, context: str = ""):
    """重大エラーの簡易ハンドリング"""
    notifier = get_error_notifier()
    return await notifier.handle_error(error, context, ErrorSeverity.CRITICAL)


async def handle_error(error: Exception, context: str = "", severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """一般エラーの簡易ハンドリング"""
    notifier = get_error_notifier()
    return await notifier.handle_error(error, context, severity)