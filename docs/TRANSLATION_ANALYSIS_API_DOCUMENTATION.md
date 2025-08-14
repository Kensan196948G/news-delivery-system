# 翻訳・AI分析システム API仕様書

## 概要

ニュース自動配信システムの翻訳・AI分析モジュールのAPI仕様書です。DeepL API による高精度翻訳とClaude API による高度な記事分析機能を提供します。

## 主要コンポーネント

### 1. TranslatorService（翻訳サービス）

#### 機能概要
- DeepL API を使用した高精度翻訳
- バッチ翻訳による効率的処理
- 翻訳結果のキャッシュ機能
- 使用量監視と制限管理

#### API仕様

##### `translate_articles(articles: List[Dict]) -> List[Dict]`
記事リストの翻訳処理

**パラメータ:**
- `articles`: 翻訳対象記事のリスト

**戻り値:**
- 翻訳済み記事のリスト

**例:**
```python
translator = TranslatorService()
articles = [
    {
        'title': 'Breaking News: AI Advancement',
        'content': 'Artificial intelligence research...',
        'language': 'en'
    }
]
translated = await translator.translate_articles(articles)
```

##### `translate_single_article(article: Dict) -> Dict`
単一記事の翻訳処理

**パラメータ:**
- `article`: 翻訳対象記事

**戻り値:**
- 翻訳済み記事

##### `get_translation_stats() -> Dict`
翻訳統計情報の取得

**戻り値:**
```json
{
    "deepl_available": true,
    "supported_languages": ["en"],
    "character_count": 15000,
    "character_limit": 500000,
    "character_remaining": 485000,
    "usage_percentage": 3.0
}
```

### 2. ClaudeAnalyzer（AI分析サービス）

#### 機能概要
- Claude API による記事の詳細分析
- 重要度評価（1-10スケール）
- 200-250文字の要約生成
- キーワード抽出（最大5個）
- センチメント分析
- 影響範囲・信頼性評価
- 緊急性判定

#### API仕様

##### `analyze_articles(articles: List[Article]) -> List[Article]`
記事リストの分析処理

**パラメータ:**
- `articles`: 分析対象記事のリスト

**戻り値:**
- 分析済み記事のリスト

##### `analyze_articles_batch_optimized(articles: List[Article], batch_size: int) -> List[Article]`
最適化されたバッチ分析処理

**パラメータ:**
- `articles`: 分析対象記事のリスト
- `batch_size`: バッチサイズ（デフォルト: 5）

**戻り値:**
- 分析済み記事のリスト

##### `create_daily_summary(articles: List[Article]) -> str`
日次サマリーの生成

**パラメータ:**
- `articles`: サマリー対象記事のリスト

**戻り値:**
- 300文字以内の日次サマリー

##### `get_performance_stats() -> Dict`
分析パフォーマンス統計の取得

**戻り値:**
```json
{
    "total_analyzed": 150,
    "cache_hits": 45,
    "api_calls": 105,
    "errors": 2,
    "cache_hit_rate_percent": 30.0,
    "cache_size": 892,
    "average_api_calls_per_article": 0.7,
    "error_rate_percent": 1.33
}
```

### 3. TranslationAnalysisPipeline（統合パイプライン）

#### 機能概要
- 翻訳・分析の統合処理
- 並列処理による高速化
- 優先度に基づく処理順序制御
- パフォーマンス監視

#### API仕様

##### `process_articles(articles: List[Dict]) -> List[Article]`
記事の統合処理

**パラメータ:**
- `articles`: 処理対象記事のリスト

**戻り値:**
- 翻訳・分析済み記事のリスト

##### `process_high_priority_articles(articles: List[Article]) -> List[Article]`
高優先度記事の優先処理

##### `test_pipeline() -> Dict`
パイプラインテスト

**戻り値:**
```json
{
    "status": "success",
    "processed_count": 2,
    "processing_time": 12.5,
    "articles": [
        {
            "title": "Test Article",
            "translated_title": "テスト記事",
            "summary": "これはテスト記事の要約です...",
            "importance_score": 7,
            "keywords": ["テスト", "記事", "AI"],
            "processed": true
        }
    ]
}
```

## 分析結果データ構造

### Article オブジェクト

```python
class Article:
    # 基本情報
    title: str                      # 元タイトル
    content: str                    # 元本文
    url: str                        # 記事URL
    source: Dict                    # 配信元情報
    published_at: datetime          # 公開日時
    language: str                   # 言語
    category: str                   # カテゴリ
    
    # 翻訳情報
    title_translated: str           # 翻訳タイトル
    content_translated: str         # 翻訳本文
    detected_language: str          # 検出言語
    
    # 分析結果
    importance_score: int           # 重要度（1-10）
    summary: str                    # 要約（200-250文字）
    keywords: List[str]             # キーワード（最大5個）
    sentiment_score: float          # センチメント（-1.0〜1.0）
    is_urgent: bool                 # 緊急性
    impact_scope: str               # 影響範囲（local/national/international）
    reliability_score: int          # 信頼性（1-10）
    detailed_category: str          # 詳細カテゴリ
    risk_factors: List[str]         # リスク要因
    action_required: str            # 必要な対応
    analysis_reasoning: str         # 分析理由
    
    # 処理情報
    processed: bool                 # 処理完了フラグ
    analyzed_at: str                # 分析日時
```

## 設定パラメータ

### 翻訳設定

```json
{
    "translation": {
        "deepl": {
            "monthly_character_limit": 500000,
            "source_languages": ["en"],
            "target_language": "ja",
            "formality": "default"
        }
    }
}
```

### AI分析設定

```json
{
    "ai_analysis": {
        "claude": {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4096,
            "temperature": 0.3,
            "summary_length": {
                "min": 200,
                "max": 250
            },
            "max_keywords": 5,
            "importance_scale": {
                "min": 1,
                "max": 10
            }
        }
    }
}
```

### パイプライン設定

```json
{
    "pipeline": {
        "parallel_processing": true,
        "max_concurrent_translations": 5,
        "max_concurrent_analyses": 3,
        "batch_size": 10
    }
}
```

## エラーハンドリング

### エラータイプ

1. **翻訳エラー**
   - `TranslationError`: 翻訳処理失敗
   - `DeepLApiError`: DeepL API エラー
   - `CharacterLimitError`: 文字数制限超過

2. **分析エラー**
   - `AIAnalysisError`: AI分析処理失敗
   - `ClaudeApiError`: Claude API エラー
   - `RateLimitError`: レート制限超過

3. **パイプラインエラー**
   - `PipelineError`: パイプライン処理失敗
   - `ConfigurationError`: 設定エラー

### エラーレスポンス例

```json
{
    "status": "error",
    "error_type": "TranslationError",
    "message": "Translation failed for article",
    "details": {
        "article_url": "https://example.com/news",
        "error_code": "DEEPL_API_ERROR",
        "retry_possible": true
    }
}
```

## パフォーマンス仕様

### 処理時間目標

- 単一記事翻訳: 2秒以内
- 単一記事分析: 5秒以内
- バッチ処理（10記事）: 30秒以内
- 全体パイプライン（50記事）: 10分以内

### リソース使用量

- メモリ使用量: 最大2GB
- API呼び出し制限: 
  - DeepL: 月500,000文字
  - Claude: 日1,000リクエスト
- キャッシュサイズ: 最大1,000エントリ

## 使用例

### 基本的な使用方法

```python
from src.services.translation_analysis_pipeline import TranslationAnalysisPipeline

# パイプライン初期化
pipeline = TranslationAnalysisPipeline()

# 記事データ準備
articles = [
    {
        'title': 'AI Breakthrough in Medical Research',
        'content': 'Scientists have developed...',
        'url': 'https://example.com/news/1',
        'language': 'en',
        'category': 'tech'
    }
]

# 処理実行
processed_articles = await pipeline.process_articles(articles)

# 結果確認
for article in processed_articles:
    print(f"Title: {article.title}")
    print(f"Translated: {article.title_translated}")
    print(f"Summary: {article.summary}")
    print(f"Importance: {article.importance_score}")
    print(f"Keywords: {article.keywords}")
    print("---")

# 統計情報取得
stats = pipeline.get_pipeline_stats()
print(f"Processing stats: {stats}")
```

### 高優先度記事の処理

```python
# 緊急記事の優先処理
urgent_articles = [article for article in articles if article.get('is_urgent')]
priority_results = await pipeline.process_high_priority_articles(urgent_articles)
```

### パイプラインテスト

```python
# システムテスト実行
test_result = await pipeline.test_pipeline()
if test_result['status'] == 'success':
    print("Pipeline test passed")
    print(f"Processed {test_result['processed_count']} articles")
else:
    print(f"Pipeline test failed: {test_result['message']}")
```

## セキュリティ考慮事項

### APIキー管理
- 環境変数での安全な管理
- アクセス権限の最小限化
- 定期的なキーローテーション

### データ保護
- 処理中データの一時保存最小化
- 機密情報のログ出力禁止
- HTTPS通信の強制

### レート制限対応
- API呼び出し頻度の制御
- 適切な待機時間の設定
- エラー時の自動リトライ機能

## 監視・メトリクス

### 重要指標
- 処理成功率
- 平均処理時間
- API使用量
- キャッシュヒット率
- エラー発生率

### アラート条件
- エラー率 > 5%
- 平均処理時間 > 30秒
- API使用量 > 80%
- メモリ使用量 > 1.5GB

## トラブルシューティング

### よくある問題

1. **翻訳が遅い**
   - バッチサイズを小さくする
   - 並列処理数を調整する
   - キャッシュの確認

2. **分析精度が低い**
   - プロンプトの見直し
   - モデルパラメータ調整
   - 入力データの品質確認

3. **API制限エラー**
   - 使用量監視の強化
   - リトライ間隔の調整
   - 代替APIの検討

## バージョン履歴

- v1.0.0: 初期リリース
  - DeepL翻訳機能
  - Claude分析機能
  - 基本パイプライン

- v1.1.0: 機能強化
  - バッチ処理最適化
  - キャッシュ機能追加
  - パフォーマンス改善

- v1.2.0: 高度分析機能
  - 影響範囲評価
  - 信頼性スコア
  - リスク要因分析
  - 詳細カテゴリ分類