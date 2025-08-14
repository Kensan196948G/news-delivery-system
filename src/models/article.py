"""Article data models for News Delivery System
ニュース配信システム 記事データモデル - CLAUDE.md仕様準拠"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import hashlib
import json


class ArticleCategory(Enum):
    """Article categories as defined in CLAUDE.md specification"""
    DOMESTIC_SOCIAL = "domestic_social"
    INTERNATIONAL_SOCIAL = "international_social"
    DOMESTIC_ECONOMY = "domestic_economy"
    INTERNATIONAL_ECONOMY = "international_economy"
    TECH = "tech"
    SECURITY = "security"


class ArticleLanguage(Enum):
    """Article languages"""
    JAPANESE = "ja"
    ENGLISH = "en"
    CHINESE = "zh"
    KOREAN = "ko"


class SentimentType(Enum):
    """Sentiment types as per CLAUDE.md specification"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class Article:
    """Article data model - CLAUDE.md仕様準拠
    
    データベーススキーマに対応した記事データモデル:
    - url: 記事URL (UNIQUE NOT NULL)
    - url_hash: 重複チェック用ハッシュ
    - title: 元タイトル
    - translated_title: 翻訳されたタイトル
    - description: 記事概要
    - content: 記事本文
    - translated_content: 翻訳された本文
    - summary: 200-250文字の要約
    - source_name: 配信元名
    - author: 記事作成者
    - published_at: 公開日時
    - collected_at: 収集日時
    - category: カテゴリ
    - importance_score: 重要度 (1-10)
    - keywords: キーワード配列 (JSON)
    - sentiment: センチメント
    - processed: 処理済みフラグ
    - created_at: 作成日時
    """
    # Required fields per CLAUDE.md schema
    url: str
    title: str
    
    # Core content fields
    description: Optional[str] = None
    content: Optional[str] = None
    source_name: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    category: Optional[str] = None
    
    # Translation fields
    translated_title: Optional[str] = None
    translated_content: Optional[str] = None
    
    # Analysis fields
    summary: Optional[str] = None
    importance_score: int = 5  # Default as per CLAUDE.md
    keywords: List[str] = field(default_factory=list)
    sentiment: str = "neutral"  # positive/neutral/negative
    
    # System fields
    url_hash: Optional[str] = None
    collected_at: datetime = field(default_factory=datetime.now)
    processed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    # Legacy compatibility fields
    language: Optional[ArticleLanguage] = None
    sentiment_score: float = 0.0  # -1.0 to 1.0
    cvss_score: Optional[float] = None
    cve_id: Optional[str] = None
    delivered: bool = False
    is_urgent: bool = False
    hash_content: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization processing per CLAUDE.md requirements"""
        # Generate URL hash for deduplication if not provided
        if not self.url_hash:
            self.url_hash = self.generate_hash()
        
        # Determine if article is urgent based on CLAUDE.md requirements
        self.is_urgent = (
            self.importance_score >= 10 or 
            (self.cvss_score is not None and self.cvss_score >= 9.0)
        )
        
        # Ensure published_at has a default
        if not self.published_at:
            self.published_at = self.collected_at
    
    def generate_hash(self) -> str:
        """記事のハッシュ値生成（重複チェック用） - CLAUDE.md準拠"""
        title = self.title or ''
        url = self.url or ''
        published_at = self.published_at.isoformat() if isinstance(self.published_at, datetime) else str(self.published_at)
        content = f"{title}{url}{published_at}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary for database storage - CLAUDE.md schema compliant"""
        return {
            'url': self.url,
            'url_hash': self.url_hash,
            'title': self.title,
            'translated_title': self.translated_title,
            'description': self.description,
            'content': self.content,
            'translated_content': self.translated_content,
            'summary': self.summary,
            'source_name': self.source_name,
            'author': self.author,
            'published_at': self.published_at.isoformat() if isinstance(self.published_at, datetime) else str(self.published_at or ''),
            'collected_at': self.collected_at.isoformat() if isinstance(self.collected_at, datetime) else str(self.collected_at),
            'category': self.category,
            'importance_score': self.importance_score,
            'keywords': json.dumps(self.keywords, ensure_ascii=False),
            'sentiment': self.sentiment,
            'processed': self.processed,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            # Legacy fields for backward compatibility
            'language': self.language.value if self.language else None,
            'sentiment_score': self.sentiment_score,
            'cvss_score': self.cvss_score,
            'cve_id': self.cve_id,
            'delivered': self.delivered,
            'is_urgent': self.is_urgent,
            'hash_content': self.hash_content
        }
    
    def to_database_tuple(self) -> tuple:
        """Convert article to tuple for database insertion - CLAUDE.md schema order"""
        return (
            self.url,
            self.url_hash,
            self.title,
            self.translated_title,
            self.description,
            self.content,
            self.translated_content,
            self.summary,
            self.source_name,
            self.author,
            self.published_at.isoformat() if isinstance(self.published_at, datetime) else str(self.published_at or ''),
            self.collected_at.isoformat() if isinstance(self.collected_at, datetime) else str(self.collected_at),
            self.category,
            self.importance_score,
            json.dumps(self.keywords, ensure_ascii=False),
            self.sentiment,
            self.processed
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Article':
        """Create article from dictionary - CLAUDE.md schema compliant"""
        # Parse keywords if stored as JSON string
        keywords = data.get('keywords', [])
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except (json.JSONDecodeError, TypeError):
                keywords = []
        
        # Parse datetime fields
        published_at = None
        if data.get('published_at'):
            try:
                published_at = datetime.fromisoformat(data['published_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                published_at = None
        
        collected_at = datetime.now()
        if data.get('collected_at'):
            try:
                collected_at = datetime.fromisoformat(data['collected_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                collected_at = datetime.now()
        
        created_at = datetime.now()
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                created_at = datetime.now()
        
        # Parse language enum if present
        language = None
        if data.get('language'):
            try:
                language = ArticleLanguage(data['language'])
            except ValueError:
                language = None
        
        return cls(
            url=data['url'],
            title=data['title'],
            description=data.get('description'),
            content=data.get('content'),
            source_name=data.get('source_name'),
            author=data.get('author'),
            published_at=published_at,
            category=data.get('category'),
            translated_title=data.get('translated_title'),
            translated_content=data.get('translated_content'),
            summary=data.get('summary'),
            importance_score=data.get('importance_score', 5),
            keywords=keywords,
            sentiment=data.get('sentiment', 'neutral'),
            url_hash=data.get('url_hash'),
            collected_at=collected_at,
            processed=data.get('processed', False),
            created_at=created_at,
            # Legacy fields
            language=language,
            sentiment_score=data.get('sentiment_score', 0.0),
            cvss_score=data.get('cvss_score'),
            cve_id=data.get('cve_id'),
            delivered=data.get('delivered', False),
            is_urgent=data.get('is_urgent', False),
            hash_content=data.get('hash_content')
        )
    
    @classmethod
    def from_database_row(cls, row) -> 'Article':
        """Create article from database row - CLAUDE.md schema compliant"""
        # Convert sqlite3.Row to dictionary
        if hasattr(row, 'keys'):
            data = dict(row)
        else:
            # Assume it's a tuple/list in the expected order
            columns = [
                'id', 'url', 'url_hash', 'title', 'translated_title', 'description',
                'content', 'translated_content', 'summary', 'source_name', 'author',
                'published_at', 'collected_at', 'category', 'importance_score',
                'keywords', 'sentiment', 'processed', 'created_at'
            ]
            data = dict(zip(columns, row))
        
        return cls.from_dict(data)


@dataclass 
class SecurityVulnerability:
    """Security vulnerability data model"""
    cve_id: str
    title: str
    description: str
    cvss_score: float
    severity: str
    published_date: datetime
    
    # Optional fields
    cvss_vector: Optional[str] = None
    modified_date: Optional[datetime] = None
    affected_products: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    cwe_ids: List[str] = field(default_factory=list)
    
    # System fields
    collected_at: datetime = field(default_factory=datetime.now)
    processed: bool = False
    notified: bool = False
    importance_score: int = 0
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Calculate importance based on CVSS score
        if self.cvss_score >= 9.0:
            self.importance_score = 10
        elif self.cvss_score >= 7.0:
            self.importance_score = 8
        elif self.cvss_score >= 4.0:
            self.importance_score = 6
        else:
            self.importance_score = 4
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vulnerability to dictionary"""
        return {
            'cve_id': self.cve_id,
            'title': self.title,
            'description': self.description,
            'cvss_score': self.cvss_score,
            'cvss_vector': self.cvss_vector,
            'severity': self.severity,
            'published_date': self.published_date.isoformat() if isinstance(self.published_date, datetime) else str(self.published_date),
            'modified_date': self.modified_date.isoformat() if self.modified_date and isinstance(self.modified_date, datetime) else (str(self.modified_date) if self.modified_date else None),
            'affected_products': self.affected_products,
            'references': self.references,
            'cwe_ids': self.cwe_ids,
            'collected_at': self.collected_at.isoformat() if isinstance(self.collected_at, datetime) else str(self.collected_at),
            'processed': self.processed,
            'notified': self.notified,
            'importance_score': self.importance_score
        }


@dataclass
class DeliveryRecord:
    """Delivery record data model - CLAUDE.md delivery_history schema compliant
    
    データベーススキーマ対応:
    - delivery_type: 'scheduled' または 'urgent'
    - recipient_email: 配信先メールアドレス
    - subject: メール件名
    - article_count: 配信記事数
    - categories: カテゴリ配列 (JSON)
    - status: 'sent' または 'failed'
    - error_message: エラーメッセージ
    - html_path: HTMLファイルパス
    - pdf_path: PDFファイルパス
    - delivered_at: 配信日時
    """
    delivery_type: str  # 'scheduled' or 'urgent' per CLAUDE.md
    recipient_email: str
    subject: str
    article_count: int
    status: str  # 'sent' or 'failed' per CLAUDE.md
    delivered_at: datetime = field(default_factory=datetime.now)
    
    # Optional fields per CLAUDE.md schema
    categories: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None
    
    # Legacy compatibility fields
    recipients: List[str] = field(default_factory=list)
    content_hash: Optional[str] = None
    urgent_count: int = 0
    report_format: str = "html"
    report_path: Optional[str] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        """Post-initialization to maintain compatibility"""
        if not self.recipients:
            self.recipients = [self.recipient_email]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert delivery record to dictionary - CLAUDE.md schema compliant"""
        return {
            'delivery_type': self.delivery_type,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'article_count': self.article_count,
            'categories': json.dumps(self.categories, ensure_ascii=False),
            'status': self.status,
            'error_message': self.error_message,
            'html_path': self.html_path,
            'pdf_path': self.pdf_path,
            'delivered_at': self.delivered_at.isoformat() if isinstance(self.delivered_at, datetime) else str(self.delivered_at),
            # Legacy fields for backward compatibility
            'recipients': ','.join(self.recipients),
            'content_hash': self.content_hash,
            'urgent_count': self.urgent_count,
            'report_format': self.report_format,
            'report_path': self.report_path,
            'processing_time_seconds': self.processing_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeliveryRecord':
        """Create delivery record from dictionary - CLAUDE.md schema compliant"""
        # Parse categories if stored as JSON string
        categories = data.get('categories', [])
        if isinstance(categories, str):
            try:
                categories = json.loads(categories)
            except (json.JSONDecodeError, TypeError):
                categories = []
        
        # Parse datetime
        delivered_at = datetime.now()
        if data.get('delivered_at'):
            try:
                delivered_at = datetime.fromisoformat(data['delivered_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                delivered_at = datetime.now()
        
        # Parse recipients from comma-separated string if needed
        recipients = []
        if data.get('recipients'):
            if isinstance(data['recipients'], str):
                recipients = [email.strip() for email in data['recipients'].split(',')]
            else:
                recipients = data['recipients']
        
        return cls(
            delivery_type=data.get('delivery_type', 'scheduled'),
            recipient_email=data.get('recipient_email', recipients[0] if recipients else ''),
            subject=data.get('subject', ''),
            article_count=data.get('article_count', 0),
            status=data.get('status', 'sent'),
            delivered_at=delivered_at,
            categories=categories,
            error_message=data.get('error_message'),
            html_path=data.get('html_path'),
            pdf_path=data.get('pdf_path'),
            # Legacy fields
            recipients=recipients,
            content_hash=data.get('content_hash'),
            urgent_count=data.get('urgent_count', 0),
            report_format=data.get('report_format', 'html'),
            report_path=data.get('report_path'),
            processing_time=data.get('processing_time_seconds', 0.0)
        )


@dataclass
class APIUsageRecord:
    """API usage record data model - CLAUDE.md api_usage schema compliant
    
    データベーススキーマ対応:
    - api_name: API名
    - endpoint: エンドポイント
    - request_count: リクエスト数
    - response_status: レスポンスステータス
    - error_message: エラーメッセージ
    - created_at: 作成日時
    """
    api_name: str
    endpoint: Optional[str] = None
    request_count: int = 1
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert API usage record to dictionary"""
        return {
            'api_name': self.api_name,
            'endpoint': self.endpoint,
            'request_count': self.request_count,
            'response_status': self.response_status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIUsageRecord':
        """Create API usage record from dictionary"""
        created_at = datetime.now()
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                created_at = datetime.now()
        
        return cls(
            api_name=data.get('api_name', ''),
            endpoint=data.get('endpoint'),
            request_count=data.get('request_count', 1),
            response_status=data.get('response_status'),
            error_message=data.get('error_message'),
            created_at=created_at
        )


@dataclass
class CacheEntry:
    """Cache entry data model - CLAUDE.md cache schema compliant
    
    データベーススキーマ対応:
    - key: キャッシュキー (PRIMARY KEY)
    - value: キャッシュ値
    - expire_at: 有効期限
    - created_at: 作成日時
    """
    key: str
    value: str
    expire_at: datetime
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary"""
        return {
            'key': self.key,
            'value': self.value,
            'expire_at': self.expire_at.isoformat() if isinstance(self.expire_at, datetime) else str(self.expire_at),
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create cache entry from dictionary"""
        expire_at = datetime.now()
        if data.get('expire_at'):
            try:
                expire_at = datetime.fromisoformat(data['expire_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                expire_at = datetime.now()
        
        created_at = datetime.now()
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                created_at = datetime.now()
        
        return cls(
            key=data.get('key', ''),
            value=data.get('value', ''),
            expire_at=expire_at,
            created_at=created_at
        )


# Utility functions for data model conversions
def article_from_collector_data(data: Dict[str, Any], category: str = None, source_name: str = None) -> Article:
    """Create Article from collector data (NewsAPI, GNews, etc.)
    
    Args:
        data: Raw data from news collector
        category: Article category
        source_name: Source name override
        
    Returns:
        Article instance
    """
    # Extract and clean data from various collector formats
    title = data.get('title', '') or data.get('headline', '') or ''
    description = data.get('description', '') or data.get('summary', '')
    content = data.get('content', '') or description
    url = data.get('url', '') or data.get('link', '')
    author = data.get('author', '')
    
    # Handle different date formats from APIs
    published_at = None
    for date_field in ['publishedAt', 'published_at', 'pubDate', 'date']:
        if data.get(date_field):
            try:
                published_at = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
                break
            except (ValueError, TypeError):
                continue
    
    # Extract source name
    if not source_name:
        source_data = data.get('source', {})
        if isinstance(source_data, dict):
            source_name = source_data.get('name', '') or source_data.get('id', '')
        else:
            source_name = str(source_data) if source_data else ''
    
    return Article(
        url=url,
        title=title,
        description=description,
        content=content,
        source_name=source_name,
        author=author,
        published_at=published_at,
        category=category,
        collected_at=datetime.now()
    )


def vulnerability_to_article(vuln: SecurityVulnerability) -> Article:
    """Convert SecurityVulnerability to Article for unified handling
    
    Args:
        vuln: SecurityVulnerability instance
        
    Returns:
        Article instance with vulnerability data
    """
    return Article(
        url=f"https://nvd.nist.gov/vuln/detail/{vuln.cve_id}",
        title=f"{vuln.cve_id}: {vuln.title}",
        description=vuln.description[:500] + "..." if len(vuln.description) > 500 else vuln.description,
        content=vuln.description,
        source_name="NVD",
        published_at=vuln.published_date,
        category="security",
        importance_score=vuln.importance_score,
        cvss_score=vuln.cvss_score,
        cve_id=vuln.cve_id,
        keywords=[vuln.cve_id, "vulnerability", "security"],
        sentiment="negative",
        collected_at=vuln.collected_at,
        processed=vuln.processed
    )