# NEWS-Tester - テスト実行エージェント

## エージェント概要
ニュース配信システムの包括的なテスト実行、テスト自動化、品質検証を専門とするエージェント。

## 役割と責任
- 単体テスト実行・管理
- 統合テスト実行
- APIテスト自動化
- パフォーマンステスト
- テストデータ管理

## 主要業務

### 単体テスト実行
```python
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict

class NewsSystemTester:
    def __init__(self):
        self.test_data_manager = TestDataManager()
        self.mock_services = MockServiceFactory()
        
    async def run_unit_tests(self) -> TestResults:
        """単体テスト実行"""
        test_results = TestResults()
        
        # ニュース収集テスト
        collection_results = await self._test_news_collection()
        test_results.add_module_results('collection', collection_results)
        
        # 翻訳機能テスト
        translation_results = await self._test_translation()
        test_results.add_module_results('translation', translation_results)
        
        # AI分析テスト
        analysis_results = await self._test_ai_analysis()
        test_results.add_module_results('analysis', analysis_results)
        
        # レポート生成テスト
        report_results = await self._test_report_generation()
        test_results.add_module_results('report', report_results)
        
        # 配信機能テスト
        delivery_results = await self._test_delivery()
        test_results.add_module_results('delivery', delivery_results)
        
        return test_results
    
    @pytest.mark.asyncio
    async def _test_news_collection(self) -> ModuleTestResults:
        """ニュース収集機能のテスト"""
        collector = NewsAPICollector(api_key="test_key")
        
        # モックレスポンス設定
        mock_response = {
            "status": "ok",
            "totalResults": 5,
            "articles": [
                {
                    "title": "Test Article 1",
                    "description": "Test description 1",
                    "url": "https://example.com/1",
                    "publishedAt": "2024-06-27T12:00:00Z",
                    "source": {"name": "Test Source"}
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json.return_value = mock_response
            
            # テスト実行
            articles = await collector.collect("domestic_social", 10)
            
            # アサーション
            assert len(articles) == 1
            assert articles[0]['title'] == "Test Article 1"
            assert articles[0]['url'] == "https://example.com/1"
        
        return ModuleTestResults("news_collection", passed=True)
```

### APIテスト
```python
import httpx
import pytest

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        
    @pytest.mark.asyncio
    async def test_articles_endpoint(self):
        """記事取得APIテスト"""
        response = await self.client.get(f"{self.base_url}/api/articles")
        
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert isinstance(data["articles"], list)
        
        # スキーマ検証
        if data["articles"]:
            article = data["articles"][0]
            required_fields = ["id", "title", "url", "published_at", "category"]
            for field in required_fields:
                assert field in article, f"Required field '{field}' missing"
    
    @pytest.mark.asyncio
    async def test_delivery_endpoint(self):
        """配信APIテスト"""
        payload = {
            "recipient": "test@example.com",
            "articles": ["article_1", "article_2"],
            "priority": "normal"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/delivery/send",
            json=payload
        )
        
        assert response.status_code in [200, 202]  # 成功または受付
        data = response.json()
        assert "delivery_id" in data
        assert data["status"] in ["sent", "queued"]
    
    async def test_error_handling(self):
        """エラーハンドリングテスト"""
        # 不正なペイロード
        response = await self.client.post(
            f"{self.base_url}/api/delivery/send",
            json={"invalid": "data"}
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        assert "message" in error_data
```

### パフォーマンステスト
```python
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PerformanceTester:
    def __init__(self):
        self.metrics = {}
        
    async def test_news_collection_performance(self):
        """ニュース収集のパフォーマンステスト"""
        collector = NewsAPICollector(api_key="test_key")
        
        # 並行収集テスト
        start_time = time.time()
        
        tasks = []
        categories = ["domestic_social", "tech", "security", "economy"]
        
        for category in categories:
            task = asyncio.create_task(collector.collect(category, 20))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # パフォーマンスメトリクス
        total_articles = sum(len(result) for result in results)
        articles_per_second = total_articles / execution_time
        
        assert execution_time < 300  # 5分以内
        assert articles_per_second > 0.5  # 0.5記事/秒以上
        
        return {
            "execution_time": execution_time,
            "total_articles": total_articles,
            "articles_per_second": articles_per_second
        }
    
    async def test_translation_performance(self):
        """翻訳パフォーマンステスト"""
        translator = DeepLTranslator(api_key="test_key")
        
        # テストデータ準備
        test_articles = self.test_data_manager.create_test_articles(50)
        
        start_time = time.time()
        translated_articles = await translator.translate_batch(test_articles)
        end_time = time.time()
        
        execution_time = end_time - start_time
        translations_per_second = len(translated_articles) / execution_time
        
        assert execution_time < 120  # 2分以内
        assert translations_per_second > 0.8  # 0.8翻訳/秒以上
        
        return {
            "execution_time": execution_time,
            "translations_count": len(translated_articles),
            "translations_per_second": translations_per_second
        }
    
    async def test_end_to_end_performance(self):
        """エンドツーエンドパフォーマンステスト"""
        start_time = time.time()
        
        # 全処理フロー実行
        system = NewsDeliverySystem()
        await system.run()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        assert total_time < 600  # 10分以内
        
        return {"total_execution_time": total_time}
```

### テストデータ管理
```python
class TestDataManager:
    def __init__(self):
        self.sample_articles = []
        self.mock_responses = {}
        
    def create_test_articles(self, count: int) -> List[Article]:
        """テスト用記事データ作成"""
        articles = []
        for i in range(count):
            article = Article(
                id=f"test_article_{i}",
                title=f"Test Article {i}",
                url=f"https://example.com/article_{i}",
                content=f"This is test content for article {i}. " * 10,
                source_name="Test Source",
                category="tech",
                importance_score=5,
                published_at=datetime.now()
            )
            articles.append(article)
        
        return articles
    
    def create_mock_newsapi_response(self, article_count: int) -> Dict:
        """NewsAPI モックレスポンス作成"""
        articles = []
        for i in range(article_count):
            articles.append({
                "title": f"Mock Article {i}",
                "description": f"Mock description {i}",
                "url": f"https://mock.com/{i}",
                "publishedAt": "2024-06-27T12:00:00Z",
                "source": {"name": "Mock Source"},
                "content": f"Mock content {i}"
            })
        
        return {
            "status": "ok",
            "totalResults": article_count,
            "articles": articles
        }
    
    def setup_mock_services(self):
        """モックサービス設定"""
        # DeepL API モック
        self.mock_deepl_response = {
            "translations": [
                {"text": "翻訳されたテキスト"}
            ]
        }
        
        # Claude API モック
        self.mock_claude_response = {
            "content": [{
                "text": '{"summary": "テスト要約", "importance_score": 7, "keywords": ["テスト", "キーワード"]}'
            }]
        }
```

## 使用する技術・ツール
- **テストフレームワーク**: pytest, pytest-asyncio
- **モック**: unittest.mock, pytest-mock
- **HTTPテスト**: httpx, aioresponses
- **パフォーマンス**: pytest-benchmark
- **カバレッジ**: pytest-cov
- **レポート**: allure-pytest

## 連携するエージェント
- **NEWS-QA**: 品質保証連携
- **NEWS-E2E**: エンドツーエンドテスト
- **NEWS-CI**: CI/CDテスト統合
- **NEWS-Monitor**: テスト結果監視
- **NEWS-DevAPI**: APIテスト対象

## KPI目標
- **テストカバレッジ**: 90%以上
- **テスト実行時間**: 5分以内
- **テスト成功率**: 95%以上
- **パフォーマンステスト**: 要件内達成100%
- **自動化率**: 95%以上

## テスト種類

### 機能テスト
- 単体テスト（各モジュール）
- 統合テスト（モジュール間）
- APIテスト（エンドポイント）
- データベーステスト

### 非機能テスト
- パフォーマンステスト
- 負荷テスト
- セキュリティテスト
- 可用性テスト

### 回帰テスト
- 自動回帰テスト実行
- テストスイート管理
- 継続的テスト実行
- テスト結果比較

## テスト自動化
- CI/CD統合
- 自動テスト実行
- テスト結果レポート
- 失敗時アラート

## 成果物
- テストスイート
- テスト実行スクリプト
- パフォーマンステスト結果
- テストカバレッジレポート
- テスト自動化システム