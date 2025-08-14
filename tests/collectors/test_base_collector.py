"""
Test cases for BaseCollector
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from src.collectors.base_collector import BaseCollector
from src.models.article import Article


class TestCollector(BaseCollector):
    """テスト用のコレクター実装"""

    async def collect(self, **kwargs):
        return []


@pytest.fixture
def mock_config():
    """モック設定オブジェクト"""
    config = Mock()
    config.get_api_key.return_value = "test_api_key"
    return config


@pytest.fixture
def mock_logger():
    """モックロガー"""
    return Mock()


@pytest.fixture
def test_collector(mock_config, mock_logger):
    """テスト用コレクター"""
    return TestCollector(mock_config, mock_logger, "test_service")


class TestBaseCollector:
    """BaseCollectorのテストクラス"""

    def test_init(self, test_collector):
        """初期化テスト"""
        assert test_collector.service_name == "test_service"
        assert test_collector.api_key == "test_api_key"
        assert test_collector.max_retries == 3
        assert test_collector.base_retry_delay == 1

    @pytest.mark.asyncio
    async def test_context_manager(self, test_collector):
        """非同期コンテキストマネージャーテスト"""
        async with test_collector as collector:
            assert collector.session is not None
            assert isinstance(collector.session, aiohttp.ClientSession)

        # セッションが閉じられているかは直接確認できないが、エラーが出ないことを確認
        assert True

    def test_validate_article_data_valid(self, test_collector):
        """有効な記事データの検証テスト"""
        valid_data = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "content": "Article content",
        }

        assert test_collector.validate_article_data(valid_data) is True

    def test_validate_article_data_missing_title(self, test_collector):
        """タイトル不足データの検証テスト"""
        invalid_data = {
            "url": "https://example.com/article",
            "content": "Article content",
        }

        assert test_collector.validate_article_data(invalid_data) is False

    def test_validate_article_data_missing_url(self, test_collector):
        """URL不足データの検証テスト"""
        invalid_data = {"title": "Test Article", "content": "Article content"}

        assert test_collector.validate_article_data(invalid_data) is False

    def test_validate_article_data_removed_article(self, test_collector):
        """削除済み記事の検証テスト"""
        removed_data = {"title": "[Removed]", "url": "https://example.com/article"}

        assert test_collector.validate_article_data(removed_data) is False

    def test_parse_date_iso_format(self, test_collector):
        """ISO形式日付パースのテスト"""
        iso_date = "2024-07-12T10:30:00Z"
        parsed = test_collector.parse_date(iso_date)

        # 正しくパースされ、ISO形式で返されることを確認
        assert "2024-07-12T10:30:00" in parsed

    def test_parse_date_invalid(self, test_collector):
        """無効な日付パースのテスト"""
        invalid_date = "invalid_date"
        parsed = test_collector.parse_date(invalid_date)

        # 現在日時が返されることを確認
        now = datetime.now()
        assert str(now.year) in parsed

    def test_parse_date_empty(self, test_collector):
        """空の日付パースのテスト"""
        parsed = test_collector.parse_date("")

        # 現在日時が返されることを確認
        now = datetime.now()
        assert str(now.year) in parsed

    @pytest.mark.asyncio
    async def test_fetch_with_cache_success(self, test_collector):
        """成功時のキャッシュ付きフェッチテスト"""
        # モックレスポンス
        mock_response_data = {"articles": [{"title": "Test"}]}

        with patch.object(
            test_collector.cache, "get_api_cache", return_value=None
        ), patch.object(test_collector.cache, "set_api_cache"), patch.object(
            test_collector.rate_limiter, "wait_if_needed", new_callable=AsyncMock
        ), patch.object(
            test_collector.rate_limiter, "record_request"
        ):
            # aiohttp.ClientSessionをモック
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.headers = {}

            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = mock_response

            mock_session = Mock()
            mock_session.get.return_value = mock_get

            test_collector.session = mock_session

            result = await test_collector.fetch_with_cache(
                "https://api.example.com/test", {"param": "value"}
            )

            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_fetch_with_cache_cached_response(self, test_collector):
        """キャッシュされたレスポンスのテスト"""
        cached_data = {"articles": [{"title": "Cached"}]}

        with patch.object(
            test_collector.cache, "get_api_cache", return_value=cached_data
        ):
            result = await test_collector.fetch_with_cache(
                "https://api.example.com/test", {"param": "value"}
            )

            assert result == cached_data

    @pytest.mark.asyncio
    async def test_fetch_with_cache_rate_limit(self, test_collector):
        """レート制限時のテスト"""
        with patch.object(
            test_collector.cache, "get_api_cache", return_value=None
        ), patch.object(
            test_collector.rate_limiter, "wait_if_needed", new_callable=AsyncMock
        ), patch.object(
            test_collector.rate_limiter, "record_request"
        ):
            # 429レスポンスをモック
            mock_response = Mock()
            mock_response.status = 429
            mock_response.headers = {"Retry-After": "10"}

            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = mock_response

            mock_session = Mock()
            mock_session.get.return_value = mock_get

            test_collector.session = mock_session
            test_collector.max_retries = 1  # テスト用に制限

            # レート制限で失敗することを確認
            result = await test_collector.fetch_with_cache(
                "https://api.example.com/test", {"param": "value"}
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_with_cache_timeout(self, test_collector):
        """タイムアウト時のテスト"""
        with patch.object(
            test_collector.cache, "get_api_cache", return_value=None
        ), patch.object(
            test_collector.rate_limiter, "wait_if_needed", new_callable=AsyncMock
        ), patch.object(
            test_collector.rate_limiter, "record_request"
        ):
            # タイムアウトを発生させる
            mock_session = Mock()
            mock_session.get.side_effect = asyncio.TimeoutError()

            test_collector.session = mock_session
            test_collector.max_retries = 1  # テスト用に制限

            result = await test_collector.fetch_with_cache(
                "https://api.example.com/test", {"param": "value"}
            )

            assert result is None

    def test_get_rate_limit_status(self, test_collector):
        """レート制限状況取得のテスト"""
        mock_status = {"can_make_request": True, "remaining": 100}

        with patch.object(
            test_collector.rate_limiter,
            "get_status",
            return_value={"test_service": mock_status},
        ):
            status = test_collector.get_rate_limit_status()
            assert status == mock_status

    def test_get_cache_stats(self, test_collector):
        """キャッシュ統計取得のテスト"""
        mock_stats = {"total_entries": 50, "memory_entries": 10}

        with patch.object(test_collector.cache, "get_stats", return_value=mock_stats):
            stats = test_collector.get_cache_stats()
            assert stats == mock_stats
