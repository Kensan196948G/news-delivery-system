# News Collectors API Documentation

## 概要

ニュース自動配信システムのニュース収集モジュール群のAPIドキュメントです。

## アーキテクチャ

```
BaseCollector (基底クラス)
├── NewsAPICollector (NewsAPI.org)
├── GNewsCollector (GNews API)
└── NVDCollector (NVD API)
```

## 基底クラス: BaseCollector

### 機能
- 非同期HTTP通信（aiohttp）
- キャッシュ管理（CacheManager統合）
- レート制限管理（RateLimiter統合）
- リトライ機能（指数バックオフ）
- エラーハンドリング

### 主要メソッド

#### `async def collect(self, **kwargs) -> List[Article]`
**概要**: ニュース収集の基底メソッド（サブクラスで実装）

**パラメータ**: サブクラス依存

**戻り値**: `List[Article]` - 収集した記事のリスト

---

#### `async def fetch_with_cache(self, url: str, params: Dict[str, Any], cache_ttl: int = 3600) -> Optional[Dict[str, Any]]`
**概要**: キャッシュ付きHTTPリクエスト

**パラメータ**:
- `url`: リクエストURL
- `params`: クエリパラメータ
- `cache_ttl`: キャッシュ有効期間（秒）

**戻り値**: APIレスポンス（辞書形式）またはNone

**特徴**:
- レート制限チェック
- 最大3回の自動リトライ
- 指数バックオフ
- キャッシュによる重複リクエスト回避

---

## NewsAPICollector

### 概要
NewsAPI.org からのニュース収集を担当

### 設定
- **ベースURL**: `https://newsapi.org/v2`
- **日次制限**: 1,000リクエスト（無料プラン）
- **サポート言語**: 日本語、英語
- **サポート国**: 日本、アメリカ他

### 主要メソッド

#### `async def collect(self, category: str = 'general', country: str = 'jp', language: str = 'ja', page_size: int = 50) -> List[Article]`
**概要**: NewsAPIからニュースを収集

**パラメータ**:
- `category`: ニュースカテゴリ（'general', 'technology', 'business'等）
- `country`: 国コード（'jp', 'us'等）
- `language`: 言語コード（'ja', 'en'等）
- `page_size`: 取得記事数（最大100）

**戻り値**: `List[Article]` - 収集した記事のリスト

**例**:
```python
# 日本の一般ニュースを30件取得
articles = await collector.collect(
    category='general',
    country='jp', 
    language='ja',
    page_size=30
)
```

---

#### `async def collect_everything(self, query: str, language: str = 'en', sort_by: str = 'relevancy', page_size: int = 50) -> List[Article]`
**概要**: NewsAPI Everythingエンドポイントでクエリ検索

**パラメータ**:
- `query`: 検索クエリ
- `language`: 言語コード
- `sort_by`: ソート順（'relevancy', 'popularity', 'publishedAt'）
- `page_size`: 取得記事数

**例**:
```python
# AI関連ニュースを検索
articles = await collector.collect_everything(
    query='artificial intelligence',
    language='en',
    sort_by='publishedAt'
)
```

### カテゴリマッピング
| NewsAPIカテゴリ | システムカテゴリ |
|----------------|-----------------|
| general | DOMESTIC_SOCIAL |
| technology | TECH |
| business | DOMESTIC_ECONOMY |
| science | TECH |
| health | DOMESTIC_SOCIAL |

---

## GNewsCollector

### 概要
GNews API からの国際ニュース収集を担当

### 設定
- **ベースURL**: `https://gnews.io/api/v4`
- **日次制限**: 100リクエスト（無料プラン）
- **特徴**: 人権関連ニュースの優先収集

### 主要メソッド

#### `async def collect(self, query: str = None, category: str = 'general', language: str = 'en', country: str = 'us', max_results: int = 50) -> List[Article]`
**概要**: GNewsからニュースを収集

**パラメータ**:
- `query`: 検索クエリ（Noneの場合はトップヘッドライン）
- `category`: カテゴリ
- `language`: 言語コード
- `country`: 国コード
- `max_results`: 最大取得件数

**例**:
```python
# 世界のトップヘッドライン
articles = await collector.collect(
    category='world',
    language='en',
    max_results=20
)
```

---

#### `async def collect_human_rights_news(self, max_results: int = 30) -> List[Article]`
**概要**: 人権関連ニュースを優先収集

**パラメータ**:
- `max_results`: 最大取得件数

**戻り値**: 人権関連記事のリスト

**対象キーワード**:
- human rights
- social justice
- migration
- refugee
- discrimination
- equality

---

#### `async def collect_tech_news(self, max_results: int = 40) -> List[Article]`
**概要**: IT/AI技術ニュースを収集

**パラメータ**:
- `max_results`: 最大取得件数

**対象キーワード**:
- artificial intelligence
- machine learning
- cybersecurity
- blockchain
- cloud computing

---

## NVDCollector

### 概要
NVD (National Vulnerability Database) からの脆弱性情報収集

### 設定
- **ベースURL**: `https://services.nvd.nist.gov/rest/json/cves/2.0`
- **CVSSしきい値**: 7.0（デフォルト）
- **対象**: HIGH、CRITICAL脆弱性

### 主要メソッド

#### `async def collect(self, days_back: int = 7, cvss_severity: str = 'HIGH,CRITICAL') -> List[Article]`
**概要**: NVDから脆弱性情報を収集

**パラメータ**:
- `days_back`: 遡る日数
- `cvss_severity`: CVSS深刻度レベル

**戻り値**: 脆弱性記事のリスト

**例**:
```python
# 過去3日のCRITICAL脆弱性
articles = await collector.collect(
    days_back=3,
    cvss_severity='CRITICAL'
)
```

---

#### `async def collect_critical_vulnerabilities(self, days_back: int = 3) -> List[Article]`
**概要**: 緊急の重要脆弱性のみを収集（CVSS 9.0以上）

#### `async def collect_recent_high_vulnerabilities(self, days_back: int = 14) -> List[Article]`
**概要**: 最近の高危険度脆弱性を収集

### 脆弱性記事の構造
```python
article.title      # "CVE-2024-1234: CRITICAL セキュリティ脆弱性 (CVSS 9.5)"
article.content    # 詳細な脆弱性情報
article.cvss_score # 9.5
article.cve_id     # "CVE-2024-1234"
article.severity   # "CRITICAL"
```

---

## 共通インターフェース

### サービス状況取得

#### `get_service_status(self) -> Dict[str, Any]`
**概要**: 各コレクターのサービス状況を取得

**戻り値**:
```python
{
    'service': 'newsapi',
    'daily_limit': 1000,
    'requests_made': 150,
    'remaining_requests': 850,
    'rate_limit_status': {...},
    'api_key_configured': True
}
```

### レート制限管理

#### `get_remaining_requests(self) -> int`
**概要**: 残りリクエスト数を取得

#### `get_rate_limit_status(self) -> Dict[str, Any]`
**概要**: レート制限状況を取得

---

## エラーハンドリング

### 対応するHTTPステータス
- **200**: 正常処理
- **401**: 認証エラー（APIキー無効）
- **403**: アクセス禁止
- **429**: レート制限超過（自動リトライ）
- **5xx**: サーバーエラー（指数バックオフでリトライ）

### リトライ戦略
- **最大リトライ回数**: 3回
- **遅延**: 指数バックオフ（1s, 2s, 4s）
- **タイムアウト**: 30秒（NVDは60秒）

---

## 使用例

### 基本的な使用パターン

```python
import asyncio
from src.collectors import NewsAPICollector, GNewsCollector, NVDCollector

async def collect_all_news():
    # コレクター初期化
    newsapi = NewsAPICollector(config, logger)
    gnews = GNewsCollector(config, logger)
    nvd = NVDCollector(config, logger)
    
    # 並行収集
    tasks = [
        newsapi.collect('general', 'jp', 'ja', 30),
        gnews.collect_human_rights_news(20),
        nvd.collect_critical_vulnerabilities(7)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)
    
    return all_articles
```

### エラーハンドリング付きの収集

```python
async def robust_news_collection():
    collectors = [
        ('NewsAPI', NewsAPICollector(config, logger)),
        ('GNews', GNewsCollector(config, logger)),
        ('NVD', NVDCollector(config, logger))
    ]
    
    all_articles = []
    
    for name, collector in collectors:
        try:
            articles = await collector.collect()
            all_articles.extend(articles)
            logger.info(f"{name}: Collected {len(articles)} articles")
            
        except Exception as e:
            logger.error(f"{name} collection failed: {e}")
            continue
    
    return all_articles
```

### レート制限監視

```python
def monitor_rate_limits(collectors):
    for collector in collectors:
        status = collector.get_service_status()
        service = status['service']
        remaining = status['remaining_requests']
        
        if remaining < 10:
            logger.warning(f"{service}: Only {remaining} requests remaining")
        
        print(f"{service}: {remaining}/{status['daily_limit']} requests remaining")
```

---

## パフォーマンス考慮事項

### キャッシュ戦略
- **APIレスポンス**: 1時間キャッシュ
- **脆弱性情報**: 2時間キャッシュ
- **検索結果**: 30分キャッシュ

### 並行実行
- 各コレクターは独立して並行実行可能
- レート制限は個別管理
- 例外は他のコレクターに影響しない

### メモリ使用量
- 記事1件あたり約2KB
- 100件収集時の推定メモリ使用量: 200KB
- キャッシュによる追加メモリ: 最大10MB

---

## 設定要件

### 必須API KEY
```env
NEWSAPI_KEY=your_newsapi_key
GNEWS_API_KEY=your_gnews_key
# NVDはAPIキー不要
```

### 設定例（config.json）
```json
{
    "news_sources": {
        "newsapi": {
            "enabled": true,
            "rate_limit_per_day": 1000
        },
        "gnews": {
            "enabled": true,
            "rate_limit_per_day": 100
        },
        "nvd": {
            "enabled": true,
            "cvss_threshold": 7.0,
            "rate_limit_per_day": 50
        }
    }
}
```