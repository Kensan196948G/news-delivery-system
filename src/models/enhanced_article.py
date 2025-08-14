"""
Enhanced Article Data Models for News Delivery System
ニュース配信システム 拡張記事データモデル - CLAUDE.md仕様完全準拠
CLAUDE.md準拠の高度なデータモデルシステム
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import hashlib
import json


class ArticleCategory(Enum):
    """Article categories - CLAUDE.md仕様準拠"""
    DOMESTIC_SOCIAL = "domestic_social"      # 国内社会ニュース
    INTERNATIONAL_SOCIAL = "international_social"  # 国際社会ニュース(人権関連優先)
    DOMESTIC_ECONOMY = "domestic_economy"      # 国内経済ニュース
    INTERNATIONAL_ECONOMY = "international_economy"  # 国際経済ニュース
    TECH = "tech"                            # IT/AIニュース
    SECURITY = "security"                    # サイバーセキュリティニュース
    
    @property
    def display_name(self) -> str:
        """カテゴリ表示名取得"""
        mapping = {
            self.DOMESTIC_SOCIAL: "国内社会",
            self.INTERNATIONAL_SOCIAL: "国際社会",
            self.DOMESTIC_ECONOMY: "国内経済",
            self.INTERNATIONAL_ECONOMY: "国際経済",
            self.TECH: "IT/AI",
            self.SECURITY: "セキュリティ"
        }
        return mapping.get(self, self.value)
    
    @property 
    def collection_count(self) -> int:
        """収集件数(カテゴリ別) - CLAUDE.md仕様準拠"""
        mapping = {
            self.DOMESTIC_SOCIAL: 10,
            self.INTERNATIONAL_SOCIAL: 15,
            self.DOMESTIC_ECONOMY: 8,
            self.INTERNATIONAL_ECONOMY: 15,
            self.TECH: 20,
            self.SECURITY: 20
        }
        return mapping.get(self, 10)
    
    @property
    def priority(self) -> int:
        """カテゴリ優先度 - CLAUDE.md仕様準拠"""
        mapping = {
            self.DOMESTIC_SOCIAL: 1,
            self.INTERNATIONAL_SOCIAL: 2,
            self.DOMESTIC_ECONOMY: 3,
            self.INTERNATIONAL_ECONOMY: 4,
            self.TECH: 5,
            self.SECURITY: 6  # 最高優先度(緊急アラート対応)
        }
        return mapping.get(self, 99)


@dataclass
class Article:
    """Article data model - CLAUDE.md仕様完全準拠"""
    # Required fields - CLAUDE.md必須フィールド
    url: str                                    # 記事のURL(ユニークキー)
    title: str                                  # 元タイトル
    source_name: str                           # 配信元(メディア名)
    category: ArticleCategory                   # カテゴリ(列挙型)
    published_at: datetime                      # 公開日時
    
    # Optional content fields - CLAUDE.mdオプションコンテンツ
    description: Optional[str] = None           # 記事の要約/説明
    content: Optional[str] = None               # 記事本文
    author: Optional[str] = None                # 著者
    
    # Translation fields - CLAUDE.md翻訳関連
    translated_title: Optional[str] = None      # 翻訳タイトル
    translated_content: Optional[str] = None    # 翻訳コンテンツ
    
    # AI Analysis fields - CLAUDE.md AI分析関連
    summary: Optional[str] = None               # 200-250文字の要約
    importance_score: int = 5                   # 重要度(1-10スケール)
    keywords: List[str] = field(default_factory=list)  # キーワード(5個)
    sentiment: str = 'neutral'                  # センチメント(positive/neutral/negative)
    
    # Security fields - CLAUDE.mdセキュリティ関連
    cvss_score: Optional[float] = None          # CVSSスコア(9.0以上は緊急)
    cve_id: Optional[str] = None                # CVE識別子
    
    # System fields - CLAUDE.mdシステム関連 
    collected_at: datetime = field(default_factory=datetime.now)  # 収集日時
    processed: bool = False                     # 処理済みフラグ
    url_hash: Optional[str] = None              # URLハッシュ(重複チェック用)
    
    def __post_init__(self):
        """Post-initialization processing - CLAUDE.md仕様準拠"""
        # URLハッシュ生成(重複チェック用)
        if self.url_hash is None:
            self.url_hash = hashlib.md5(self.url.encode('utf-8')).hexdigest()
        
        # キーワード数制限(5個まで)
        if len(self.keywords) > 5:
            self.keywords = self.keywords[:5]
    
    @property
    def is_urgent(self) -> bool:
        """緊急送信対象か判定 - CLAUDE.md仕様準拠"""
        return (
            self.importance_score >= 10 or 
            (self.cvss_score is not None and self.cvss_score >= 9.0)
        )
    
    @property
    def display_category(self) -> str:
        """カテゴリ表示名取得"""
        return self.category.display_name
    
    @property
    def needs_translation(self) -> bool:
        """翻訳が必要か判定"""
        # 国際カテゴリかつ翻訳がまだされていない場合
        is_international = self.category in [
            ArticleCategory.INTERNATIONAL_SOCIAL,
            ArticleCategory.INTERNATIONAL_ECONOMY,
            ArticleCategory.TECH,
            ArticleCategory.SECURITY
        ]
        return is_international and not self.translated_title
    
    @property
    def analysis_status(self) -> Dict[str, bool]:
        """分析状態取得"""
        return {
            'has_summary': bool(self.summary),
            'has_keywords': len(self.keywords) > 0,
            'has_sentiment': self.sentiment != 'neutral',
            'has_importance': self.importance_score > 5,
            'is_complete': bool(self.summary and self.keywords and self.importance_score > 0)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary for database storage - CLAUDE.md仕様準拠"""
        return {
            # Required fields
            'url': self.url,
            'url_hash': self.url_hash,
            'title': self.title,
            'source_name': self.source_name,
            'category': self.category.value,
            'published_at': self.published_at.isoformat() if isinstance(self.published_at, datetime) else str(self.published_at),
            
            # Optional content
            'description': self.description,
            'content': self.content,
            'author': self.author,
            
            # Translation
            'translated_title': self.translated_title,
            'translated_content': self.translated_content,
            
            # AI Analysis
            'summary': self.summary,
            'importance_score': self.importance_score,
            'keywords': self.keywords,  # JSON配列として保存
            'sentiment': self.sentiment,
            
            # Security
            'cvss_score': self.cvss_score,
            'cve_id': self.cve_id,
            
            # System
            'collected_at': self.collected_at.isoformat() if isinstance(self.collected_at, datetime) else str(self.collected_at),
            'processed': self.processed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Article':
        """Create article from dictionary - CLAUDE.md仕様準拠"""
        # 日時フィールドの処理
        published_at = data['published_at']
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at)
        
        collected_at = data.get('collected_at', datetime.now().isoformat())
        if isinstance(collected_at, str):
            collected_at = datetime.fromisoformat(collected_at)
        
        return cls(
            # Required fields
            url=data['url'],
            title=data['title'],
            source_name=data['source_name'],
            category=ArticleCategory(data['category']),
            published_at=published_at,
            
            # Optional content
            description=data.get('description'),
            content=data.get('content'),
            author=data.get('author'),
            
            # Translation
            translated_title=data.get('translated_title'),
            translated_content=data.get('translated_content'),
            
            # AI Analysis 
            summary=data.get('summary'),
            importance_score=data.get('importance_score', 5),
            keywords=data.get('keywords', []),
            sentiment=data.get('sentiment', 'neutral'),
            
            # Security
            cvss_score=data.get('cvss_score'),
            cve_id=data.get('cve_id'),
            
            # System
            collected_at=collected_at,
            processed=data.get('processed', False),
            url_hash=data.get('url_hash')
        )
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], category: ArticleCategory, source_name: str) -> 'Article':
        """APIレスポンスから記事作成 - NewsAPI/GNews対応"""
        # 日時フィールドの正規化
        published_at_str = api_data.get('publishedAt') or api_data.get('published_at')
        if published_at_str:
            try:
                published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            except ValueError:
                published_at = datetime.now()
        else:
            published_at = datetime.now()
        
        return cls(
            url=api_data['url'],
            title=api_data['title'],
            source_name=source_name,
            category=category,
            published_at=published_at,
            description=api_data.get('description'),
            content=api_data.get('content'),
            author=api_data.get('author')
        )
    
    def update_translation(self, translated_title: str, translated_content: str = None):
        """翻訳結果を更新"""
        self.translated_title = translated_title
        if translated_content:
            self.translated_content = translated_content
    
    def update_analysis(self, summary: str, importance_score: int, keywords: List[str], sentiment: str = 'neutral'):
        """AI分析結果を更新 - CLAUDE.md仕様準拠"""
        self.summary = summary[:250] if summary else None  # 200-250文字制限
        self.importance_score = max(1, min(10, importance_score))  # 1-10スケール
        self.keywords = keywords[:5] if keywords else []  # 5個まで
        self.sentiment = sentiment if sentiment in ['positive', 'neutral', 'negative'] else 'neutral'
    
    def mark_processed(self):
        """処理完了としてマーク"""
        self.processed = True


@dataclass 
class SecurityVulnerability:
    """Security vulnerability data model - CLAUDE.md仕様準拠セキュリティ情報"""
    cve_id: str                                 # CVE識別子(ユニークキー)
    title: str                                  # 脆弱性タイトル
    description: str                           # 脆弱性説明
    cvss_score: float                          # CVSSスコア(0.0-10.0)
    severity: str                              # 深刻度(LOW/MEDIUM/HIGH/CRITICAL)
    published_date: datetime                   # 公開日
    
    # Optional fields - オプションフィールド
    cvss_vector: Optional[str] = None          # CVSSベクター文字列
    modified_date: Optional[datetime] = None   # 更新日
    affected_products: List[str] = field(default_factory=list)  # 影響する製品リスト
    reference_urls: List[str] = field(default_factory=list)     # 参考URLリスト
    cwe_ids: List[str] = field(default_factory=list)           # CWE識別子リスト
    
    # System fields - システム関連
    collected_at: datetime = field(default_factory=datetime.now)
    processed: bool = False                    # 処理済みフラグ
    notified: bool = False                     # 通知済みフラグ
    importance_score: int = 0                  # 重要度スコア
    
    def __post_init__(self):
        """Post-initialization processing - CLAUDE.md仕様準拠"""
        # CVSSスコアに基づく重要度算出
        if self.cvss_score >= 9.0:
            self.importance_score = 10  # 緊急アラートレベル
        elif self.cvss_score >= 7.0:
            self.importance_score = 8
        elif self.cvss_score >= 4.0:
            self.importance_score = 6
        else:
            self.importance_score = 4
    
    @property
    def is_emergency(self) -> bool:
        """緊急アラート対象か判定 - CLAUDE.md仕様準拠"""
        return self.cvss_score >= 9.0
    
    @property
    def severity_level(self) -> int:
        """深刻度レベルを数値で取得"""
        mapping = {
            'CRITICAL': 4,
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1
        }
        return mapping.get(self.severity.upper(), 0)
    
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
            'reference_urls': self.reference_urls,
            'cwe_ids': self.cwe_ids,
            'collected_at': self.collected_at.isoformat() if isinstance(self.collected_at, datetime) else str(self.collected_at),
            'processed': self.processed,
            'notified': self.notified,
            'importance_score': self.importance_score
        }


@dataclass
class DeliveryRecord:
    """Delivery record data model - CLAUDE.md仕様準拠配信履歴"""
    delivery_type: str                         # 'scheduled', 'urgent' - CLAUDE.md仕様
    recipient_email: str                       # 配信先メールアドレス
    subject: str                               # メール件名
    status: str                                # 'sent', 'failed' - CLAUDE.md仕様
    delivered_at: datetime                     # 配信日時
    
    # Optional fields - オプションフィールド
    article_count: int = 0                     # 配信記事数
    categories: List[str] = field(default_factory=list)  # 配信カテゴリリスト
    error_message: Optional[str] = None        # エラーメッセージ
    html_path: Optional[str] = None            # HTMLレポートパス
    pdf_path: Optional[str] = None             # PDFレポートパス
    processing_time: float = 0.0               # 処理時間(秒)
    
    @property
    def is_successful(self) -> bool:
        """配信成功判定"""
        return self.status == 'sent'
    
    @property
    def category_display(self) -> str:
        """カテゴリ表示用文字列"""
        if not self.categories:
            return "カテゴリ不明"
        return ', '.join(self.categories)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert delivery record to dictionary - CLAUDE.md仕様準拠"""
        return {
            'delivery_type': self.delivery_type,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'status': self.status,
            'delivered_at': self.delivered_at.isoformat() if isinstance(self.delivered_at, datetime) else str(self.delivered_at),
            'article_count': self.article_count,
            'categories': self.categories,  # JSON配列として保存
            'error_message': self.error_message,
            'html_path': self.html_path,
            'pdf_path': self.pdf_path,
            'processing_time_seconds': self.processing_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeliveryRecord':
        """Create delivery record from dictionary"""
        delivered_at = data['delivered_at']
        if isinstance(delivered_at, str):
            delivered_at = datetime.fromisoformat(delivered_at)
        
        return cls(
            delivery_type=data['delivery_type'],
            recipient_email=data['recipient_email'],
            subject=data['subject'],
            status=data['status'],
            delivered_at=delivered_at,
            article_count=data.get('article_count', 0),
            categories=data.get('categories', []),
            error_message=data.get('error_message'),
            html_path=data.get('html_path'),
            pdf_path=data.get('pdf_path'),
            processing_time=data.get('processing_time_seconds', 0.0)
        )


# Utility functions for data model operations
def create_article_from_newsapi(api_data: Dict[str, Any], category: ArticleCategory) -> Article:
    """NewsAPIレスポンスから記事作成"""
    source_name = api_data.get('source', {}).get('name', 'Unknown')
    return Article.from_api_response(api_data, category, source_name)


def create_article_from_nvd(cve_data: Dict[str, Any]) -> Article:
    """NVD APIレスポンスからセキュリティ記事作成"""
    metrics = cve_data.get('metrics', {}).get('cvssMetricV31', [{}])[0]
    cvss_data = metrics.get('cvssData', {})
    
    return Article(
        url=f"https://nvd.nist.gov/vuln/detail/{cve_data['id']}",
        title=f"Security Vulnerability: {cve_data['id']}",
        source_name="National Vulnerability Database",
        category=ArticleCategory.SECURITY,
        published_at=datetime.fromisoformat(cve_data['published'].replace('Z', '+00:00')),
        description=cve_data.get('descriptions', [{}])[0].get('value', ''),
        cvss_score=cvss_data.get('baseScore', 0.0),
        cve_id=cve_data['id']
    )


def filter_articles_by_importance(articles: List[Article], min_importance: int = 5) -> List[Article]:
    """重要度による記事フィルタリング"""
    return [article for article in articles if article.importance_score >= min_importance]


def group_articles_by_category(articles: List[Article]) -> Dict[ArticleCategory, List[Article]]:
    """カテゴリ別記事グルーピング"""
    grouped = {}
    for article in articles:
        if article.category not in grouped:
            grouped[article.category] = []
        grouped[article.category].append(article)
    return grouped


def get_urgent_articles(articles: List[Article]) -> List[Article]:
    """緊急記事の抽出 - CLAUDE.md仕様準拠"""
    return [article for article in articles if article.is_urgent]


def sort_articles_by_importance(articles: List[Article], reverse: bool = True) -> List[Article]:
    """重要度による記事ソート"""
    return sorted(articles, key=lambda x: (x.importance_score, x.published_at), reverse=reverse)


def get_articles_for_category(articles: List[Article], category: ArticleCategory, limit: Optional[int] = None) -> List[Article]:
    """指定カテゴリの記事取得"""
    category_articles = [article for article in articles if article.category == category]
    category_articles = sort_articles_by_importance(category_articles)
    
    if limit:
        return category_articles[:limit]
    return category_articles


def calculate_delivery_statistics(records: List[DeliveryRecord]) -> Dict[str, Any]:
    """配信統計計算"""
    if not records:
        return {'total': 0, 'success_rate': 0, 'avg_articles': 0}
    
    total = len(records)
    successful = len([r for r in records if r.is_successful])
    success_rate = (successful / total) * 100 if total > 0 else 0
    avg_articles = sum(r.article_count for r in records) / total if total > 0 else 0
    
    return {
        'total': total,
        'successful': successful,
        'success_rate': round(success_rate, 2),
        'avg_articles': round(avg_articles, 1),
        'avg_processing_time': round(sum(r.processing_time for r in records) / total, 2) if total > 0 else 0
    }


def validate_article_data(article_data: Dict[str, Any]) -> List[str]:
    """記事データの妥当性検証"""
    errors = []
    
    # Required fields check
    required_fields = ['url', 'title', 'source_name', 'category', 'published_at']
    for field in required_fields:
        if not article_data.get(field):
            errors.append(f"Required field missing: {field}")
    
    # Category validation
    if article_data.get('category'):
        try:
            ArticleCategory(article_data['category'])
        except ValueError:
            errors.append(f"Invalid category: {article_data['category']}")
    
    # Importance score validation
    importance = article_data.get('importance_score', 5)
    if not isinstance(importance, int) or importance < 1 or importance > 10:
        errors.append("Importance score must be integer between 1-10")
    
    # Keywords validation
    keywords = article_data.get('keywords', [])
    if len(keywords) > 5:
        errors.append("Keywords list cannot exceed 5 items")
    
    return errors