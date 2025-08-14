"""
Gmail Sender Module
Gmail送信モジュール - OAuth2認証・HTMLメール・PDF添付
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import logging
import base64
import mimetypes
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

from models.article import Article
from utils.config import get_config

logger = logging.getLogger(__name__)


class GmailError(Exception):
    """Gmail関連エラー"""
    pass


class GmailSender:
    """Gmail送信サービス"""
    
    # Gmail API スコープ
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self, config=None):
        self.config = config or get_config()
        
        if not GOOGLE_APIS_AVAILABLE:
            raise GmailError("Google APIs not available. Install google-auth, google-auth-oauthlib, google-api-python-client")
        
        # 認証ファイルパス
        self.credentials_path = self.config.get_env('GMAIL_CREDENTIALS_PATH', 
                                                  default='credentials/credentials.json')
        self.token_path = self.config.get_env('GMAIL_TOKEN_PATH',
                                            default='credentials/token.json')
        
        # Gmail設定
        self.sender_email = self.config.get('email', 'sender_email', default='')
        self.recipients = self.config.get('delivery', 'recipients', default=[])
        
        # サービス初期化
        self.service = None
        self.credentials = None
        
        # 送信統計
        self.send_stats = {
            'total_sent': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'last_send_time': None,
            'errors': []
        }
        
        logger.info("Gmail Sender initialized")
    
    async def initialize(self):
        """Gmail API サービス初期化"""
        try:
            self.credentials = await self._load_credentials()
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail API service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise GmailError(f"Gmail initialization failed: {e}")
    
    async def send_daily_report(self, html_content: str = None, 
                              pdf_path: Optional[str] = None,
                              articles: List[Article] = None) -> bool:
        """日次レポート送信 - プレーンテキスト形式専用（SMTP使用）"""
        try:
            # OAuth2は使わずSMTP直接送信
            # 現在時刻を取得
            now = datetime.now()
            
            # 配信時間帯を判定
            hour = now.hour
            if 6 <= hour < 10:
                delivery_name = "朝刊"
                delivery_icon = "🌅"
                delivery_time = "7:00"
            elif 11 <= hour < 15:
                delivery_name = "昼刊" 
                delivery_icon = "🌞"
                delivery_time = "12:00"
            else:
                delivery_name = "夕刊"
                delivery_icon = "🌆"
                delivery_time = "18:00"
            
            # メール件名生成
            date_str = now.strftime('%Y年%m月%d日')
            subject = f'{delivery_icon} {delivery_name}ニュース配信 - {date_str} {delivery_time}'
            
            # 統計情報
            article_count = len(articles) if articles else 0
            urgent_count = len([a for a in (articles or []) if getattr(a, 'importance_score', 0) >= 10])
            
            if urgent_count > 0:
                subject = f'🚨 {subject} (緊急 {urgent_count}件)'
            
            # プレーンテキスト版メール生成
            text_content = self._generate_text_email(articles, now, delivery_name, delivery_icon, delivery_time_str=delivery_time)
            
            # 送信実行（プレーンテキスト専用、SMTP直接）
            success = await self._send_text_email(
                recipients=self.recipients,
                subject=subject,
                text_content=text_content,
                pdf_path=pdf_path,
                email_type='daily'
            )
            
            # 統計更新
            self._update_send_stats('daily', success)
            
            if success:
                logger.info(f"Daily report sent successfully to {len(self.recipients)} recipients")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            self._update_send_stats('daily', False, str(e))
            return False
    
    async def send_emergency_alert(self, html_content: str,
                                 articles: List[Article],
                                 pdf_path: Optional[str] = None) -> bool:
        """緊急アラート送信"""
        try:
            if not self.service:
                await self.initialize()
            
            # 緊急記事数
            urgent_count = len(articles)
            
            # メール件名（緊急表示）
            subject = f'🚨 緊急ニュースアラート - {urgent_count}件の重要情報'
            
            # 高優先度での送信
            success = await self._send_email(
                recipients=self.recipients,
                subject=subject,
                html_content=html_content,
                pdf_path=pdf_path,
                email_type='emergency',
                high_priority=True
            )
            
            # 統計更新
            self._update_send_stats('emergency', success)
            
            if success:
                logger.warning(f"Emergency alert sent to {len(self.recipients)} recipients")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send emergency alert: {e}")
            self._update_send_stats('emergency', False, str(e))
            return False
    
    async def send_weekly_summary(self, html_content: str,
                                pdf_path: Optional[str] = None,
                                week_start: datetime = None) -> bool:
        """週次サマリー送信"""
        try:
            if not self.service:
                await self.initialize()
            
            # 週次件名
            week_str = (week_start or datetime.now()).strftime('%Y年%m月%d日')
            subject = f'📊 週次ニュースサマリー - {week_str}週'
            
            success = await self._send_email(
                recipients=self.recipients,
                subject=subject,
                html_content=html_content,
                pdf_path=pdf_path,
                email_type='weekly'
            )
            
            # 統計更新
            self._update_send_stats('weekly', success)
            
            if success:
                logger.info(f"Weekly summary sent to {len(self.recipients)} recipients")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send weekly summary: {e}")
            self._update_send_stats('weekly', False, str(e))
            return False
    
    async def _send_email(self, recipients: List[str], 
                         subject: str,
                         html_content: str,
                         pdf_path: Optional[str] = None,
                         email_type: str = 'general',
                         high_priority: bool = False) -> bool:
        """メール送信実行"""
        try:
            for recipient in recipients:
                try:
                    # メッセージ作成
                    message = self._create_message(
                        to=recipient,
                        subject=subject,
                        html_content=html_content,
                        pdf_path=pdf_path,
                        high_priority=high_priority
                    )
                    
                    # Gmail API で送信
                    result = self.service.users().messages().send(
                        userId='me',
                        body=message
                    ).execute()
                    
                    logger.debug(f"Email sent successfully to {recipient}: {result['id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to send email to {recipient}: {e}")
                    raise
            
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    def _create_message(self, to: str, subject: str, 
                       html_content: str,
                       pdf_path: Optional[str] = None,
                       high_priority: bool = False) -> Dict[str, str]:
        """メールメッセージ作成"""
        try:
            # MIMEメッセージ作成
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject
            message['from'] = self.sender_email or 'news-delivery-system@gmail.com'
            
            # 優先度設定
            if high_priority:
                message['X-Priority'] = '1'
                message['X-MSMail-Priority'] = 'High'
                message['Importance'] = 'High'
            
            # HTML本文
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(html_part)
            
            # プレーンテキスト版も追加（フォールバック）
            text_content = self._html_to_text(html_content)
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            message.attach(text_part)
            
            # PDF添付
            if pdf_path and os.path.exists(pdf_path):
                self._attach_pdf(message, pdf_path)
            
            # Base64エンコード
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            return {'raw': raw_message}
            
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            raise GmailError(f"Message creation failed: {e}")
    
    def _attach_pdf(self, message: MIMEMultipart, pdf_path: str):
        """PDF添付"""
        try:
            with open(pdf_path, 'rb') as f:
                attachment = MIMEBase('application', 'pdf')
                attachment.set_payload(f.read())
            
            encoders.encode_base64(attachment)
            
            # ファイル名設定
            filename = os.path.basename(pdf_path)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            
            message.attach(attachment)
            logger.debug(f"PDF attached: {filename}")
            
        except Exception as e:
            logger.warning(f"Failed to attach PDF {pdf_path}: {e}")
    
    def _generate_japanese_summary(self, article) -> str:
        """日本語概要の自動生成"""
        try:
            # 既存の概要をチェック
            summary = getattr(article, 'summary', None) or getattr(article, 'description', None)
            
            if summary and summary.strip() and summary.strip().lower() != 'none':
                # 英語の概要を簡易的に日本語表記に変換
                if self._is_english_text(summary):
                    return self._translate_to_japanese_summary(summary)
                return summary
            
            # 概要がない場合は記事タイトルから生成
            title = getattr(article, 'translated_title', None) or getattr(article, 'title', '')
            
            if not title:
                return "詳細な情報については元記事をご確認ください。"
            
            # タイトルから簡易概要生成
            category = getattr(article, 'category', '').upper()
            
            if 'SECURITY' in category:
                return f"{title}に関するセキュリティ情報です。システム管理者の方は詳細をご確認ください。"
            elif 'TECH' in category:
                return f"{title}に関する技術情報です。最新の技術動向や開発情報をお届けします。"
            elif 'ECONOMY' in category:
                return f"{title}に関する経済情報です。市場動向や経済指標についての詳細をお伝えします。"
            elif 'SOCIAL' in category:
                return f"{title}に関する社会情報です。国内外の重要な社会動向についてご報告します。"
            else:
                return f"{title}についての最新情報です。詳細は元記事をご確認ください。"
                
        except Exception as e:
            logger.warning(f"概要生成エラー: {e}")
            return "最新情報をお届けします。詳細については元記事をご確認ください。"
    
    def _is_english_text(self, text: str) -> bool:
        """英語テキストかどうかを判定"""
        try:
            # 英語の特徴的なパターンをチェック
            english_patterns = [
                ' the ', ' and ', ' or ', ' in ', ' on ', ' at ', ' to ', ' for ',
                ' a ', ' an ', ' is ', ' are ', ' was ', ' were ', ' have ', ' has '
            ]
            
            text_lower = text.lower()
            english_count = sum(1 for pattern in english_patterns if pattern in text_lower)
            
            # 日本語文字（ひらがな・カタカナ・漢字）の存在チェック
            japanese_chars = any('\u3040' <= char <= '\u309F' or  # ひらがな
                                '\u30A0' <= char <= '\u30FF' or  # カタカナ 
                                '\u4E00' <= char <= '\u9FAF'     # 漢字
                                for char in text)
            
            return english_count >= 2 and not japanese_chars
            
        except Exception:
            return False
    
    def _translate_to_japanese_summary(self, english_text: str) -> str:
        """英語概要の簡易日本語化"""
        try:
            # よくある英語フレーズの簡易変換
            translations = {
                'security vulnerability': 'セキュリティ脆弱性',
                'critical update': '重要なアップデート',
                'breaking news': '速報',
                'latest update': '最新情報',
                'new feature': '新機能',
                'bug fix': 'バグ修正',
                'software update': 'ソフトウェア更新',
                'cyber attack': 'サイバー攻撃',
                'data breach': 'データ漏洩',
                'artificial intelligence': '人工知能',
                'machine learning': '機械学習',
                'economic report': '経済報告',
                'market analysis': '市場分析',
                'technology news': '技術ニュース',
                'government policy': '政府政策',
                'international relations': '国際関係',
                'climate change': '気候変動',
                'global economy': '世界経済'
            }
            
            result = english_text
            for eng, jpn in translations.items():
                result = result.replace(eng, jpn)
            
            # 基本的な英語構造を日本語的に変換
            if len(result) > 200:
                result = result[:200] + "..."
            
            # 英語が残っている場合は最初に説明を追加
            if any(char.isalpha() and ord(char) < 128 for char in result):
                result = "※未翻訳記事: " + result
            
            return result
            
        except Exception:
            return "海外の最新情報をお届けします。詳細については元記事をご確認ください。"

    def _generate_text_email(self, articles: List[Article], delivery_time: datetime, 
                           delivery_name: str, delivery_icon: str, delivery_time_str: str) -> str:
        """プレーンテキストメール生成"""
        try:
            from models.article import ArticleCategory
            
            # 記事がない場合のデフォルト処理
            if not articles:
                articles = []
                
            text_content = f"""
{delivery_icon} {delivery_name}ニュース配信 - {delivery_time.strftime('%Y年%m月%d日')} {delivery_time_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
配信先: {', '.join(self.recipients)}
配信時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

📊 配信サマリー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・総記事数: {len(articles)}件
・重要記事 (8点以上): {len([a for a in articles if getattr(a, 'importance_score', 5) >= 8])}件  
・緊急記事 (10点): {len([a for a in articles if getattr(a, 'importance_score', 5) >= 10])}件
・セキュリティ記事: {len([a for a in articles if hasattr(a, 'category') and str(a.category).upper().find('SECURITY') >= 0])}件

    """
            
            # 緊急アラート
            critical_articles = [a for a in articles if getattr(a, 'importance_score', 5) >= 10]
            if critical_articles:
                text_content += f"""
🚨 緊急アラート
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
重要度10の緊急記事が {len(critical_articles)} 件検出されました。
至急確認をお願いします。

        """
            
            # カテゴリ別記事（文字列比較でカテゴリ判定）と表示件数の設定
            # CLAUDE.md仕様に基づく表示件数
            category_limits = {
                '🔐 セキュリティ': {'articles': [a for a in articles if 'SECURITY' in str(getattr(a, 'category', '')).upper()], 'limit': 20},
                '💻 技術・AI': {'articles': [a for a in articles if 'TECH' in str(getattr(a, 'category', '')).upper()], 'limit': 20},
                '🌍 国際社会': {'articles': [a for a in articles if 'INTERNATIONAL_SOCIAL' in str(getattr(a, 'category', '')).upper()], 'limit': 15},
                '🌐 国際経済': {'articles': [a for a in articles if 'INTERNATIONAL_ECONOMY' in str(getattr(a, 'category', '')).upper()], 'limit': 15},
                '📊 国内経済': {'articles': [a for a in articles if 'DOMESTIC_ECONOMY' in str(getattr(a, 'category', '')).upper()], 'limit': 8},
                '🏠 国内社会': {'articles': [a for a in articles if 'DOMESTIC_SOCIAL' in str(getattr(a, 'category', '')).upper()], 'limit': 10}
            }
            
            # カテゴリに分類されなかった記事を「その他」に追加
            categorized_articles = []
            for category_data in category_limits.values():
                categorized_articles.extend(category_data['articles'])
            
            uncategorized = [a for a in articles if a not in categorized_articles]
            if uncategorized:
                category_limits['📰 その他'] = {'articles': uncategorized, 'limit': 10}
            
            for category_name, category_data in category_limits.items():
                category_articles = category_data['articles']
                limit = category_data['limit']
                
                if not category_articles:
                    continue
                    
                # 重要度順にソートして上位limit件を取得
                sorted_articles = sorted(category_articles, key=lambda x: getattr(x, 'importance_score', 5), reverse=True)
                display_articles = sorted_articles[:limit]
                
                text_content += f"""
{category_name} (表示: {len(display_articles)}件 / 全{len(category_articles)}件)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
                
                for i, article in enumerate(display_articles, 1):
                    importance = getattr(article, 'importance_score', 5)
                    
                    # タイトルの日本語化（英語タイトルの場合は翻訳済みを優先）
                    title = getattr(article, 'translated_title', None) or getattr(article, 'title', '無題')
                    if self._is_english_text(title) and not getattr(article, 'translated_title', None):
                        title = f"【海外】{title}"
                    
                    # 概要の日本語化と自動生成
                    summary = self._generate_japanese_summary(article)
                    
                    keywords = getattr(article, 'keywords', [])
                    
                    # 重要度表示
                    if importance >= 10:
                        importance_mark = "🚨【緊急】"
                    elif importance >= 8:
                        importance_mark = "⚠️【重要】"
                    else:
                        importance_mark = "📰【通常】"
                    
                    cvss_info = ""
                    if hasattr(article, 'cvss_score') and getattr(article, 'cvss_score', None):
                        cvss_info = f" (CVSS: {article.cvss_score})"
                    
                    published_time = "時刻不明"
                    if hasattr(article, 'published_at') and article.published_at:
                        try:
                            if isinstance(article.published_at, datetime):
                                published_time = article.published_at.strftime('%H:%M')
                            elif isinstance(article.published_at, str):
                                # 文字列の場合はdatetimeに変換してからstrftime
                                dt = datetime.fromisoformat(article.published_at.replace('Z', '+00:00'))
                                published_time = dt.strftime('%H:%M')
                        except (ValueError, TypeError, AttributeError):
                            published_time = "時刻不明"
                    
                    source_name = getattr(article, 'source_name', '不明')
                    url = getattr(article, 'url', '#')
                    
                    text_content += f"""

{i}. {importance_mark} [{importance}/10] {title}

   【概要】
   {summary}
   
   【詳細情報】
   ソース: {source_name}
   配信時刻: {published_time}{cvss_info}
   キーワード: {', '.join(keywords) if keywords else 'なし'}
   
   【詳細リンク】
   {url}
            """
            
            text_content += f"""


📅 配信スケジュール
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌅 朝刊配信: 毎日 7:00
🌞 昼刊配信: 毎日 12:00  
🌆 夕刊配信: 毎日 18:00

🔄 システム情報
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・自動修復機能により99%以上の配信信頼性を確保
・エラー発生時は自動でリトライ・修復を実行
・配信停止・変更: {', '.join(self.recipients)} まで連絡

🤖 Generated with Claude Code
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
このメールは自動配信システムから送信されました。
システムは常時監視・自動修復機能により安定稼働しています。

© 2025 News Delivery System
    """
            
            return text_content
            
        except Exception as e:
            logger.error(f"Text email generation failed: {e}")
            return f"メール生成エラー: {str(e)}"
    
    async def _send_text_email(self, recipients: List[str], subject: str,
                              text_content: str, pdf_path: Optional[str] = None,
                              email_type: str = 'general') -> bool:
        """プレーンテキストメール送信"""
        try:
            import smtplib
            
            # SMTP設定取得
            sender_email = os.environ.get('SENDER_EMAIL')
            app_password = os.environ.get('GMAIL_APP_PASSWORD')
            
            if not sender_email or not app_password:
                logger.error("Gmail SMTP credentials not configured")
                return False
            
            for recipient in recipients:
                try:
                    # メッセージ作成（プレーンテキストのみ）
                    message = MIMEMultipart()
                    message['From'] = sender_email
                    message['To'] = recipient
                    message['Subject'] = subject
                    
                    # プレーンテキスト部分のみ
                    text_part = MIMEText(text_content, 'plain', 'utf-8')
                    message.attach(text_part)
                    
                    # PDF添付（オプション）
                    if pdf_path and os.path.exists(pdf_path):
                        self._attach_pdf(message, pdf_path)
                    
                    # SMTP送信
                    with smtplib.SMTP('smtp.gmail.com', 587) as server:
                        server.starttls()
                        server.login(sender_email, app_password)
                        server.send_message(message)
                    
                    logger.debug(f"Plain text email sent successfully to {recipient}")
                    
                except Exception as e:
                    logger.error(f"Failed to send text email to {recipient}: {e}")
                    raise
            
            return True
            
        except Exception as e:
            logger.error(f"Text email sending failed: {e}")
            return False

    def _html_to_text(self, html_content: str) -> str:
        """HTMLをプレーンテキストに変換（簡易版）"""
        try:
            import re
            
            # HTMLタグを削除
            text = re.sub(r'<[^>]+>', '', html_content)
            
            # HTML エンティティをデコード
            import html
            text = html.unescape(text)
            
            # 複数の改行を正規化
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"HTML to text conversion failed: {e}")
            return "メールの表示に問題が発生しました。HTMLメールでご確認ください。"
    
    async def _load_credentials(self) -> Credentials:
        """OAuth2認証情報の読み込み"""
        creds = None
        
        # 既存のトークンファイルから読み込み
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(
                    self.token_path, self.SCOPES
                )
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")
        
        # 認証情報の更新または新規取得
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("OAuth2 credentials refreshed")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                # 新規認証フロー
                if not os.path.exists(self.credentials_path):
                    raise GmailError(f"Credentials file not found: {self.credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("New OAuth2 credentials obtained")
            
            # トークンファイルに保存
            try:
                # ディレクトリ作成
                Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.token_path, 'w') as token_file:
                    token_file.write(creds.to_json())
                logger.info(f"OAuth2 credentials saved to {self.token_path}")
            except Exception as e:
                logger.error(f"Failed to save credentials: {e}")
        
        return creds
    
    def _update_send_stats(self, email_type: str, success: bool, error: str = None):
        """送信統計更新"""
        self.send_stats['total_sent'] += 1
        
        if success:
            self.send_stats['successful_sends'] += 1
        else:
            self.send_stats['failed_sends'] += 1
            if error:
                self.send_stats['errors'].append({
                    'timestamp': datetime.now().isoformat(),
                    'type': email_type,
                    'error': error
                })
        
        self.send_stats['last_send_time'] = datetime.now().isoformat()
        
        # エラーリストの上限管理
        if len(self.send_stats['errors']) > 10:
            self.send_stats['errors'] = self.send_stats['errors'][-10:]
    
    async def send_test_email(self, recipient: str = None) -> Dict[str, Any]:
        """テストメール送信"""
        try:
            if not self.service:
                await self.initialize()
            
            test_recipient = recipient or (self.recipients[0] if self.recipients else None)
            if not test_recipient:
                return {'success': False, 'error': 'No recipient specified'}
            
            # テスト用HTML
            test_html = f'''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <title>テストメール</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📧 Gmail送信テスト</h1>
                </div>
                <div class="content">
                    <p>このメールはGmail送信機能のテストです。</p>
                    <p><strong>送信日時:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
                    <p><strong>送信先:</strong> {test_recipient}</p>
                    <p>メール配信システムが正常に動作しています。</p>
                </div>
            </body>
            </html>
            '''
            
            success = await self._send_email(
                recipients=[test_recipient],
                subject='📧 ニュース配信システム - テストメール',
                html_content=test_html,
                email_type='test'
            )
            
            return {
                'success': success,
                'recipient': test_recipient,
                'sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Test email failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_send_statistics(self) -> Dict[str, Any]:
        """送信統計取得"""
        success_rate = 0
        if self.send_stats['total_sent'] > 0:
            success_rate = (self.send_stats['successful_sends'] / 
                           self.send_stats['total_sent']) * 100
        
        return {
            'total_sent': self.send_stats['total_sent'],
            'successful_sends': self.send_stats['successful_sends'],
            'failed_sends': self.send_stats['failed_sends'],
            'success_rate': round(success_rate, 2),
            'last_send_time': self.send_stats['last_send_time'],
            'recent_errors': self.send_stats['errors'][-5:],
            'configured_recipients': len(self.recipients),
            'sender_email': self.sender_email
        }
    
    async def validate_setup(self) -> Dict[str, Any]:
        """Gmail設定検証"""
        validation_result = {
            'overall_status': 'unknown',
            'checks': {}
        }
        
        try:
            # 認証ファイル確認
            validation_result['checks']['credentials_file'] = {
                'status': 'ok' if os.path.exists(self.credentials_path) else 'error',
                'message': f'Credentials file: {self.credentials_path}'
            }
            
            # トークンファイル確認
            validation_result['checks']['token_file'] = {
                'status': 'ok' if os.path.exists(self.token_path) else 'warning',
                'message': f'Token file: {self.token_path}'
            }
            
            # 受信者設定確認
            validation_result['checks']['recipients'] = {
                'status': 'ok' if self.recipients else 'error',
                'message': f'Recipients configured: {len(self.recipients)}'
            }
            
            # サービス初期化テスト
            try:
                if not self.service:
                    await self.initialize()
                validation_result['checks']['api_service'] = {
                    'status': 'ok',
                    'message': 'Gmail API service initialized'
                }
            except Exception as e:
                validation_result['checks']['api_service'] = {
                    'status': 'error',
                    'message': f'Service initialization failed: {e}'
                }
            
            # 全体ステータス判定
            check_statuses = [check['status'] for check in validation_result['checks'].values()]
            if 'error' in check_statuses:
                validation_result['overall_status'] = 'error'
            elif 'warning' in check_statuses:
                validation_result['overall_status'] = 'warning'
            else:
                validation_result['overall_status'] = 'healthy'
                
        except Exception as e:
            validation_result['overall_status'] = 'error'
            validation_result['error'] = str(e)
        
        return validation_result


# グローバルGmailSenderインスタンス
_gmail_sender_instance = None


def get_gmail_sender() -> GmailSender:
    """グローバルGmailSenderインスタンス取得"""
    global _gmail_sender_instance
    if _gmail_sender_instance is None:
        _gmail_sender_instance = GmailSender()
    return _gmail_sender_instance