"""
Integration tests for news collectors
統合テスト - 実際のAPIを使用しない模擬統合テスト
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.collectors.newsapi_collector import NewsAPICollector
from src.collectors.gnews_collector import GNewsCollector
from src.collectors.nvd_collector import NVDCollector


@pytest.fixture
def mock_config():
    """統合テスト用モック設定"""
    config = Mock()
    config.get_api_key.side_effect = lambda service: f'{service}_test_key'
    config.get.return_value = 100  # デフォルト制限値
    config.is_service_enabled.return_value = True
    return config


@pytest.fixture
def mock_logger():
    """統合テスト用モックロガー"""
    return Mock()


class TestCollectorIntegration:
    """コレクター統合テスト"""
    
    @pytest.mark.asyncio
    async def test_all_collectors_initialization(self, mock_config, mock_logger):
        """全コレクターの初期化テスト"""
        # 全てのコレクターが正常に初期化できることを確認
        newsapi = NewsAPICollector(mock_config, mock_logger)
        gnews = GNewsCollector(mock_config, mock_logger)
        nvd = NVDCollector(mock_config, mock_logger)
        
        assert newsapi.service_name == 'newsapi'
        assert gnews.service_name == 'gnews'
        assert nvd.service_name == 'nvd'
        
        # APIキーが正しく設定されることを確認
        assert newsapi.api_key == 'newsapi_test_key'
        assert gnews.api_key == 'gnews_test_key'
        assert nvd.api_key == 'nvd_test_key'
    
    @pytest.mark.asyncio
    async def test_concurrent_collection(self, mock_config, mock_logger):
        """並行収集テスト"""
        # 各コレクターのモックレスポンス
        newsapi_response = {
            'status': 'ok',
            'totalResults': 1,
            'articles': [{
                'title': 'NewsAPI Article',
                'url': 'https://newsapi.example.com/1',
                'publishedAt': '2024-07-12T10:00:00Z',
                'source': {'name': 'NewsAPI Source'},
                'content': 'NewsAPI content'
            }]
        }
        
        gnews_response = {
            'totalArticles': 1,
            'articles': [{
                'title': 'GNews Article',
                'url': 'https://gnews.example.com/1',
                'publishedAt': '2024-07-12T11:00:00Z',
                'source': {'name': 'GNews Source'},
                'content': 'GNews content'
            }]
        }
        
        nvd_response = {
            'totalResults': 1,
            'vulnerabilities': [{
                'cve': {
                    'id': 'CVE-2024-1234',
                    'published': '2024-07-12T12:00:00Z',
                    'descriptions': [{'lang': 'en', 'value': 'Test vulnerability'}],
                    'metrics': {
                        'cvssMetricV31': [{
                            'cvssData': {
                                'baseScore': 8.5,
                                'baseSeverity': 'HIGH',
                                'vectorString': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N'
                            }
                        }]
                    }
                }
            }]
        }
        
        # コレクター作成
        newsapi = NewsAPICollector(mock_config, mock_logger)
        gnews = GNewsCollector(mock_config, mock_logger)
        nvd = NVDCollector(mock_config, mock_logger)
        
        # モックAPI呼び出し設定
        with patch.object(newsapi, 'fetch_with_cache', new_callable=AsyncMock, return_value=newsapi_response), \
             patch.object(gnews, 'fetch_with_cache', new_callable=AsyncMock, return_value=gnews_response), \
             patch.object(nvd, 'fetch_with_cache', new_callable=AsyncMock, return_value=nvd_response):
            
            # 並行実行
            tasks = [
                newsapi.collect(category='general', page_size=10),
                gnews.collect(category='world', max_results=10),
                nvd.collect(days_back=7)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果検証
            assert len(results) == 3
            
            # 各結果が例外でないことを確認
            for result in results:
                assert not isinstance(result, Exception)
            
            newsapi_articles, gnews_articles, nvd_articles = results
            
            # 各コレクターから記事が取得されることを確認
            assert len(newsapi_articles) == 1
            assert len(gnews_articles) == 1
            assert len(nvd_articles) == 1
            
            # 記事の基本フィールドを確認
            assert newsapi_articles[0].title == 'NewsAPI Article'
            assert gnews_articles[0].title == 'GNews Article'
            assert 'CVE-2024-1234' in nvd_articles[0].title
    
    @pytest.mark.asyncio
    async def test_error_handling_resilience(self, mock_config, mock_logger):
        """エラー処理の堅牢性テスト"""
        newsapi = NewsAPICollector(mock_config, mock_logger)
        gnews = GNewsCollector(mock_config, mock_logger)
        nvd = NVDCollector(mock_config, mock_logger)
        
        # 様々なエラーケースをテスト
        with patch.object(newsapi, 'fetch_with_cache', new_callable=AsyncMock, side_effect=Exception("API Error")), \
             patch.object(gnews, 'fetch_with_cache', new_callable=AsyncMock, return_value=None), \
             patch.object(nvd, 'fetch_with_cache', new_callable=AsyncMock, return_value={'vulnerabilities': []}):
            
            # エラーが発生しても他のコレクターに影響しないことを確認
            tasks = [
                newsapi.collect(),  # Exception発生
                gnews.collect(),    # None返却
                nvd.collect()       # 空のレスポンス
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # NewsAPIはエラーで空リスト、他は正常処理
            assert len(results[0]) == 0  # エラー時は空リスト
            assert len(results[1]) == 0  # None時は空リスト
            assert len(results[2]) == 0  # 空のvulnerabilities
    
    @pytest.mark.asyncio
    async def test_rate_limiting_coordination(self, mock_config, mock_logger):
        """レート制限の調整テスト"""
        collectors = [
            NewsAPICollector(mock_config, mock_logger),
            GNewsCollector(mock_config, mock_logger),
            NVDCollector(mock_config, mock_logger)
        ]
        
        # 各コレクターのレート制限状況をチェック
        for collector in collectors:
            status = collector.get_service_status()
            
            assert 'service' in status
            assert 'daily_limit' in status
            assert 'requests_made' in status
            assert 'remaining_requests' in status
            assert 'api_key_configured' in status
            
            # 初期状態では使用量は0
            assert status['requests_made'] == 0
            assert status['remaining_requests'] == status['daily_limit']
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, mock_config, mock_logger):
        """データ一貫性テスト"""
        newsapi = NewsAPICollector(mock_config, mock_logger)
        
        # 一貫した形式のレスポンスを確認
        mock_response = {
            'status': 'ok',
            'articles': [{
                'title': 'Consistency Test Article',
                'url': 'https://example.com/consistency',
                'publishedAt': '2024-07-12T10:00:00Z',
                'source': {'name': 'Test Source'},
                'content': 'Test content for consistency'
            }]
        }
        
        with patch.object(newsapi, 'fetch_with_cache', new_callable=AsyncMock, return_value=mock_response):
            articles = await newsapi.collect()
            
            # 記事オブジェクトの一貫性を確認
            assert len(articles) == 1
            article = articles[0]
            
            # 必須フィールドの存在確認
            assert hasattr(article, 'title')
            assert hasattr(article, 'url')
            assert hasattr(article, 'source')
            assert hasattr(article, 'category')
            assert hasattr(article, 'language')
            assert hasattr(article, 'published_at')
            assert hasattr(article, 'collected_at')
            
            # 日付形式の一貫性確認
            assert article.published_at is not None
            assert article.collected_at is not None
    
    @pytest.mark.asyncio
    async def test_cache_efficiency(self, mock_config, mock_logger):
        """キャッシュ効率性テスト"""
        newsapi = NewsAPICollector(mock_config, mock_logger)
        
        mock_response = {
            'status': 'ok',
            'articles': [{
                'title': 'Cache Test Article',
                'url': 'https://example.com/cache',
                'publishedAt': '2024-07-12T10:00:00Z',
                'source': {'name': 'Cache Source'},
                'content': 'Cache test content'
            }]
        }
        
        with patch.object(newsapi, 'fetch_with_cache', new_callable=AsyncMock, return_value=mock_response) as mock_fetch:
            # 同じパラメータで2回呼び出し
            await newsapi.collect(category='general', page_size=10)
            await newsapi.collect(category='general', page_size=10)
            
            # fetch_with_cacheが2回呼ばれることを確認（実際のキャッシュ効果は別途テスト）
            assert mock_fetch.call_count == 2
    
    def test_service_configuration(self, mock_config, mock_logger):
        """サービス設定テスト"""
        # 設定パラメータの確認
        collectors = [
            NewsAPICollector(mock_config, mock_logger),
            GNewsCollector(mock_config, mock_logger), 
            NVDCollector(mock_config, mock_logger)
        ]
        
        for collector in collectors:
            # 基本設定の確認
            assert collector.service_name in ['newsapi', 'gnews', 'nvd']
            assert collector.api_key is not None
            assert collector.max_retries >= 1
            assert collector.base_retry_delay >= 0
            
            # サービス固有設定の確認
            if hasattr(collector, 'daily_limit'):
                assert collector.daily_limit > 0
            if hasattr(collector, 'base_url'):
                assert collector.base_url.startswith('http')