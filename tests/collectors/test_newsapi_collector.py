"""
Test cases for NewsAPICollector
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.collectors.newsapi_collector import NewsAPICollector
from src.models.article import Article, ArticleCategory, ArticleLanguage


@pytest.fixture
def mock_config():
    """モック設定オブジェクト"""
    config = Mock()
    config.get_api_key.return_value = 'test_newsapi_key'
    config.get.return_value = 1000  # daily_limit
    return config


@pytest.fixture
def mock_logger():
    """モックロガー"""
    return Mock()


@pytest.fixture
def newsapi_collector(mock_config, mock_logger):
    """NewsAPICollectorインスタンス"""
    return NewsAPICollector(mock_config, mock_logger)


class TestNewsAPICollector:
    """NewsAPICollectorのテストクラス"""
    
    def test_init(self, newsapi_collector):
        """初期化テスト"""
        assert newsapi_collector.service_name == 'newsapi'
        assert newsapi_collector.base_url == 'https://newsapi.org/v2'
        assert newsapi_collector.daily_limit == 1000
        assert newsapi_collector.request_count == 0
    
    def test_category_mapping(self, newsapi_collector):
        """カテゴリマッピングテスト"""
        assert newsapi_collector.category_mapping['general'] == ArticleCategory.DOMESTIC_SOCIAL
        assert newsapi_collector.category_mapping['technology'] == ArticleCategory.TECH
        assert newsapi_collector.category_mapping['business'] == ArticleCategory.DOMESTIC_ECONOMY
    
    @pytest.mark.asyncio
    async def test_collect_success(self, newsapi_collector):
        """正常なニュース収集テスト"""
        # モックAPIレスポンス
        mock_api_response = {
            'status': 'ok',
            'totalResults': 2,
            'articles': [
                {
                    'title': 'Test Article 1',
                    'description': 'Test description 1',
                    'url': 'https://example.com/article1',
                    'urlToImage': 'https://example.com/image1.jpg',
                    'publishedAt': '2024-07-12T10:30:00Z',
                    'source': {'name': 'Test Source 1'},
                    'author': 'Test Author 1',
                    'content': 'Test content 1'
                },
                {
                    'title': 'Test Article 2', 
                    'description': 'Test description 2',
                    'url': 'https://example.com/article2',
                    'publishedAt': '2024-07-12T11:30:00Z',
                    'source': {'name': 'Test Source 2'},
                    'content': 'Test content 2'
                }
            ]
        }
        
        with patch.object(newsapi_collector, 'fetch_with_cache', 
                         new_callable=AsyncMock, return_value=mock_api_response):
            
            articles = await newsapi_collector.collect(
                category='general',
                country='jp',
                language='ja',
                page_size=50
            )
            
            assert len(articles) == 2
            assert newsapi_collector.request_count == 1
            
            # 最初の記事を詳細チェック
            article1 = articles[0]
            assert article1.title == 'Test Article 1'
            assert article1.url == 'https://example.com/article1'
            assert article1.source == 'Test Source 1'
            assert article1.category == ArticleCategory.DOMESTIC_SOCIAL
            assert article1.language == ArticleLanguage.JAPANESE
    
    @pytest.mark.asyncio
    async def test_collect_daily_limit_reached(self, newsapi_collector):
        """日次制限到達時のテスト"""
        newsapi_collector.request_count = newsapi_collector.daily_limit
        
        articles = await newsapi_collector.collect()
        
        assert len(articles) == 0
        assert newsapi_collector.request_count == newsapi_collector.daily_limit
    
    @pytest.mark.asyncio
    async def test_collect_api_failure(self, newsapi_collector):
        """API失敗時のテスト"""
        with patch.object(newsapi_collector, 'fetch_with_cache',
                         new_callable=AsyncMock, return_value=None):
            
            articles = await newsapi_collector.collect()
            
            assert len(articles) == 0
            assert newsapi_collector.request_count == 0  # 失敗時はカウントしない
    
    @pytest.mark.asyncio
    async def test_collect_everything_search(self, newsapi_collector):
        """Everything API検索テスト"""
        mock_api_response = {
            'status': 'ok',
            'totalResults': 1,
            'articles': [
                {
                    'title': 'AI Technology News',
                    'description': 'Latest AI developments',
                    'url': 'https://example.com/ai-news',
                    'publishedAt': '2024-07-12T12:00:00Z',
                    'source': {'name': 'Tech Source'},
                    'content': 'AI technology content'
                }
            ]
        }
        
        with patch.object(newsapi_collector, 'fetch_with_cache',
                         new_callable=AsyncMock, return_value=mock_api_response):
            
            articles = await newsapi_collector.collect_everything(
                query='artificial intelligence',
                language='en'
            )
            
            assert len(articles) == 1
            assert newsapi_collector.request_count == 1
            
            article = articles[0]
            assert 'AI Technology' in article.title
            assert article.category == ArticleCategory.TECH  # tech推定
    
    def test_create_article_success(self, newsapi_collector):
        """記事オブジェクト作成成功テスト"""
        article_data = {
            'title': 'Test Article',
            'description': 'Test description',
            'content': 'Test content',
            'url': 'https://example.com/test',
            'publishedAt': '2024-07-12T10:00:00Z',
            'source': {'name': 'Test Source'},
            'author': 'Test Author',
            'urlToImage': 'https://example.com/image.jpg'
        }
        
        article = newsapi_collector._create_article(article_data, 'general', 'jp')
        
        assert article is not None
        assert article.title == 'Test Article'
        assert article.content == 'Test content'
        assert article.url == 'https://example.com/test'
        assert article.source == 'Test Source'
        assert article.author == 'Test Author'
        assert article.category == ArticleCategory.DOMESTIC_SOCIAL
        assert article.language == ArticleLanguage.JAPANESE
    
    def test_create_article_missing_data(self, newsapi_collector):
        """必要データ不足時の記事作成テスト"""
        article_data = {
            'title': '',  # 空のタイトル
            'url': 'https://example.com/test'
        }
        
        article = newsapi_collector._create_article(article_data, 'general', 'jp')
        
        # 空のタイトルでも記事は作成されるが、バリデーションで弾かれるはず
        assert article is not None
        assert article.title == ''
    
    def test_infer_category_from_query(self, newsapi_collector):
        """クエリからのカテゴリ推定テスト"""
        # テクノロジー関連
        assert newsapi_collector._infer_category_from_query('artificial intelligence') == 'technology'
        assert newsapi_collector._infer_category_from_query('machine learning AI') == 'technology'
        
        # ビジネス関連
        assert newsapi_collector._infer_category_from_query('business market economy') == 'business'
        assert newsapi_collector._infer_category_from_query('finance stock market') == 'business'
        
        # ヘルス関連
        assert newsapi_collector._infer_category_from_query('healthcare medical') == 'health'
        
        # セキュリティ関連（テクノロジーに分類）
        assert newsapi_collector._infer_category_from_query('cybersecurity vulnerability') == 'technology'
        
        # 一般
        assert newsapi_collector._infer_category_from_query('general news') == 'general'
    
    def test_process_articles_with_validation(self, newsapi_collector):
        """記事処理とバリデーションテスト"""
        articles_data = [
            {
                'title': 'Valid Article',
                'url': 'https://example.com/valid',
                'content': 'Valid content',
                'publishedAt': '2024-07-12T10:00:00Z',
                'source': {'name': 'Test Source'}
            },
            {
                'title': '[Removed]',  # 除外されるべき
                'url': 'https://example.com/removed',
                'content': 'Removed content'
            },
            {
                'title': '',  # 無効なタイトル
                'url': 'https://example.com/invalid',
                'content': 'Invalid content'
            }
        ]
        
        with patch.object(newsapi_collector, 'validate_article_data') as mock_validate:
            # 最初の記事のみ有効とする
            mock_validate.side_effect = [True, False, False]
            
            processed = newsapi_collector._process_articles(articles_data, 'general', 'jp')
            
            assert len(processed) == 1
            assert processed[0].title == 'Valid Article'
    
    def test_get_remaining_requests(self, newsapi_collector):
        """残りリクエスト数取得テスト"""
        newsapi_collector.request_count = 100
        remaining = newsapi_collector.get_remaining_requests()
        assert remaining == 900  # 1000 - 100
        
        # 制限超過時
        newsapi_collector.request_count = 1500
        remaining = newsapi_collector.get_remaining_requests()
        assert remaining == 0
    
    def test_get_service_status(self, newsapi_collector):
        """サービス状況取得テスト"""
        newsapi_collector.request_count = 150
        
        with patch.object(newsapi_collector, 'get_rate_limit_status', 
                         return_value={'can_make_request': True}):
            
            status = newsapi_collector.get_service_status()
            
            assert status['service'] == 'newsapi'
            assert status['daily_limit'] == 1000
            assert status['requests_made'] == 150
            assert status['remaining_requests'] == 850
            assert status['api_key_configured'] is True
    
    @pytest.mark.asyncio
    async def test_collect_parameter_validation(self, newsapi_collector):
        """パラメータ検証テスト"""
        mock_response = {
            'status': 'ok',
            'totalResults': 0,
            'articles': []
        }
        
        with patch.object(newsapi_collector, 'fetch_with_cache',
                         new_callable=AsyncMock, return_value=mock_response) as mock_fetch:
            
            await newsapi_collector.collect(
                category='technology',
                country='us',
                language='en',
                page_size=150  # 制限値を超える
            )
            
            # fetch_with_cacheが呼ばれた引数を確認
            args, kwargs = mock_fetch.call_args
            url, params = args
            
            assert url == 'https://newsapi.org/v2/top-headlines'
            assert params['category'] == 'technology'
            assert params['country'] == 'us'
            assert params['language'] == 'en'
            assert params['pageSize'] == 100  # 100に制限されているはず
            assert params['apiKey'] == 'test_newsapi_key'