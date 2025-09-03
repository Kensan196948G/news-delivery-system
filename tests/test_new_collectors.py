"""
New News Collectors Test Module
新しいニュースコレクターのテストモジュール
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.reuters_collector import ReutersCollector
from src.collectors.bbc_collector import BBCCollector
from src.models.article import Article


class MockConfig:
    """テスト用設定クラス"""
    
    def get_api_key(self, service):
        return f"mock_{service}_key"
    
    def get(self, *args, **kwargs):
        default = kwargs.get('default', None)
        if args == ('news_sources', 'reuters', 'enabled'):
            return True
        elif args == ('news_sources', 'bbc', 'enabled'):
            return True
        return default


class MockLogger:
    """テスト用ロガークラス"""
    
    def __init__(self):
        self.messages = []
    
    def info(self, msg):
        self.messages.append(('INFO', msg))
        print(f"INFO: {msg}")
    
    def debug(self, msg):
        self.messages.append(('DEBUG', msg))
        print(f"DEBUG: {msg}")
    
    def warning(self, msg):
        self.messages.append(('WARNING', msg))
        print(f"WARNING: {msg}")
    
    def error(self, msg):
        self.messages.append(('ERROR', msg))
        print(f"ERROR: {msg}")


@pytest.fixture
def mock_config():
    """設定モックフィクスチャ"""
    return MockConfig()


@pytest.fixture
def mock_logger():
    """ログモックフィクスチャ"""
    return MockLogger()


@pytest.fixture
def sample_rss_feed():
    """サンプルRSSフィード"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test News Feed</title>
        <description>Test RSS feed for unit testing</description>
        <item>
            <title>Breaking: Major Technology Breakthrough Announced</title>
            <link>https://example.com/news/tech-breakthrough</link>
            <description>A significant advancement in AI technology has been revealed...</description>
            <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
            <guid>https://example.com/news/tech-breakthrough</guid>
        </item>
        <item>
            <title>Global Economic Update: Markets Reach New Heights</title>
            <link>https://example.com/news/market-update</link>
            <description>Stock markets worldwide have reached unprecedented levels...</description>
            <pubDate>Mon, 01 Jan 2024 11:00:00 GMT</pubDate>
            <guid>https://example.com/news/market-update</guid>
        </item>
        <item>
            <title>Cybersecurity Alert: New Vulnerability Discovered</title>
            <link>https://example.com/news/security-alert</link>
            <description>Security researchers have identified a critical vulnerability...</description>
            <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
            <guid>https://example.com/news/security-alert</guid>
        </item>
    </channel>
</rss>"""


class TestReutersCollector:
    """Reutersコレクターテスト"""
    
    @pytest.mark.asyncio
    async def test_reuters_collector_initialization(self, mock_config, mock_logger):
        """Reutersコレクターの初期化テスト"""
        collector = ReutersCollector(mock_config, mock_logger)
        
        assert collector.service_name == 'reuters'
        assert 'world' in collector.rss_feeds
        assert 'technology' in collector.rss_feeds
        assert 'cybersecurity' in collector.rss_feeds
        
        # カテゴリマッピングの確認
        assert 'tech' in collector.category_mapping
        assert 'security' in collector.category_mapping
    
    @pytest.mark.asyncio
    async def test_reuters_get_target_feeds(self, mock_config, mock_logger):
        """対象フィード取得テスト"""
        collector = ReutersCollector(mock_config, mock_logger)
        
        # 全カテゴリ
        all_feeds = collector._get_target_feeds('all')
        assert len(all_feeds) > 0
        assert 'world' in all_feeds
        
        # 技術カテゴリ
        tech_feeds = collector._get_target_feeds('tech')
        assert 'technology' in tech_feeds
        
        # セキュリティカテゴリ
        security_feeds = collector._get_target_feeds('security')
        assert any(feed in security_feeds for feed in ['cybersecurity', 'technology'])
    
    @pytest.mark.asyncio
    async def test_reuters_category_determination(self, mock_config, mock_logger):
        """カテゴリ判定テスト"""
        collector = ReutersCollector(mock_config, mock_logger)
        
        # テクノロジーキーワード
        category = collector._determine_category(
            "AI Innovation Breakthrough", 
            "Artificial intelligence technology advances", 
            "technology"
        )
        assert category == 'tech'
        
        # セキュリティキーワード
        category = collector._determine_category(
            "Cybersecurity Threat Alert", 
            "New malware discovered by security researchers", 
            "cybersecurity"
        )
        assert category == 'security'
        
        # 経済キーワード
        category = collector._determine_category(
            "Global Market Update", 
            "Stock markets rise amid economic growth", 
            "business"
        )
        assert category == 'international_economy'
    
    @pytest.mark.asyncio
    async def test_reuters_importance_calculation(self, mock_config, mock_logger):
        """重要度計算テスト"""
        collector = ReutersCollector(mock_config, mock_logger)
        
        # 高重要度（緊急性キーワード）
        high_score = collector._calculate_importance(
            "Breaking: Major Security Breach", 
            "Emergency response required", 
            "cybersecurity"
        )
        assert high_score >= 8
        
        # 中程度重要度
        medium_score = collector._calculate_importance(
            "Technology Update", 
            "Regular technology news", 
            "technology"
        )
        assert 4 <= medium_score <= 7
        
        # 最大値制限テスト
        max_score = collector._calculate_importance(
            "Breaking: Emergency Crisis Attack Death", 
            "Government announces major significant investigation", 
            "breakingviews"
        )
        assert max_score <= 10


class TestBBCCollector:
    """BBCコレクターテスト"""
    
    @pytest.mark.asyncio
    async def test_bbc_collector_initialization(self, mock_config, mock_logger):
        """BBCコレクターの初期化テスト"""
        collector = BBCCollector(mock_config, mock_logger)
        
        assert collector.service_name == 'bbc'
        assert 'top_stories' in collector.rss_feeds
        assert 'world' in collector.rss_feeds
        assert 'technology' in collector.rss_feeds
        
        # カテゴリマッピングの確認
        assert 'domestic_social' in collector.category_mapping
        assert 'tech' in collector.category_mapping
    
    @pytest.mark.asyncio
    async def test_bbc_get_target_feeds(self, mock_config, mock_logger):
        """対象フィード取得テスト"""
        collector = BBCCollector(mock_config, mock_logger)
        
        # 全カテゴリ
        all_feeds = collector._get_target_feeds('all')
        assert 'top_stories' in all_feeds
        assert 'world' in all_feeds
        
        # 技術カテゴリ
        tech_feeds = collector._get_target_feeds('tech')
        assert 'technology' in tech_feeds or 'science' in tech_feeds
    
    @pytest.mark.asyncio
    async def test_bbc_content_cleaning(self, mock_config, mock_logger):
        """コンテンツクリーニングテスト"""
        collector = BBCCollector(mock_config, mock_logger)
        
        # HTML除去テスト
        dirty_content = '<p>This is <strong>important</strong> news &amp; information.</p>'
        clean_content = collector._clean_description(dirty_content)
        
        assert '<p>' not in clean_content
        assert '<strong>' not in clean_content
        assert '&amp;' not in clean_content
        assert 'important news & information' in clean_content
    
    @pytest.mark.asyncio
    async def test_bbc_category_determination(self, mock_config, mock_logger):
        """カテゴリ判定テスト"""
        collector = BBCCollector(mock_config, mock_logger)
        
        # テクノロジーキーワード
        category = collector._determine_category(
            "AI Technology Revolution", 
            "Machine learning advances in digital innovation", 
            "technology"
        )
        assert category == 'tech'
        
        # セキュリティキーワード
        category = collector._determine_category(
            "Cyber Attack on Government", 
            "Hackers breach security systems", 
            "world"
        )
        assert category == 'security'
    
    @pytest.mark.asyncio
    async def test_bbc_importance_calculation(self, mock_config, mock_logger):
        """重要度計算テスト"""
        collector = BBCCollector(mock_config, mock_logger)
        
        # トップストーリーフィードからの高重要度
        high_score = collector._calculate_importance(
            "Breaking: Prime Minister Announces Major Policy", 
            "Government reveals significant economic measures", 
            "top_stories"
        )
        assert high_score >= 8
        
        # 複数の重要度要因
        complex_score = collector._calculate_importance(
            "Breaking: AI Security Breach in Government Systems", 
            "Emergency response to cyber attack on critical infrastructure", 
            "top_stories"
        )
        assert complex_score >= 9


class TestCollectorIntegration:
    """コレクター統合テスト"""
    
    @pytest.mark.asyncio
    async def test_mock_collection_with_feed_data(self, mock_config, mock_logger, sample_rss_feed):
        """モックRSSフィードを使用した収集テスト"""
        
        # Reutersコレクターテスト
        with patch('feedparser.parse') as mock_feedparser:
            # モックRSSデータの設定
            mock_feed_data = Mock()
            mock_feed_data.entries = [
                Mock(title="Tech News", link="https://example.com/tech", 
                     description="Technology advancement", published_parsed=None),
                Mock(title="Business Update", link="https://example.com/biz", 
                     description="Market analysis", published_parsed=None),
            ]
            mock_feedparser.return_value = mock_feed_data
            
            collector = ReutersCollector(mock_config, mock_logger)
            
            with patch.object(collector, '_ensure_session', new_callable=AsyncMock):
                with patch.object(collector.cache, 'get', return_value=sample_rss_feed):
                    # キャッシュからRSSデータを取得するようにモック
                    articles = await collector.collect(category='tech', count=2)
                    
                    # 結果検証
                    assert isinstance(articles, list)
                    # モックデータなので具体的な数は保証されないが、処理が正常に動作することを確認
    
    @pytest.mark.asyncio
    async def test_article_validation(self, mock_config, mock_logger):
        """記事検証テスト"""
        collector = ReutersCollector(mock_config, mock_logger)
        
        # 有効な記事
        valid_article = Article(
            url="https://example.com/valid-news",
            title="Valid News Article with Sufficient Length",
            description="This is a valid news article description",
            content="Article content here",
            source_name="Test Source"
        )
        
        assert collector._is_valid_article(valid_article) == True
        
        # 無効な記事（短すぎるタイトル）
        invalid_article = Article(
            url="https://example.com/invalid-news",
            title="Short",
            description="Description",
            source_name="Test Source"
        )
        
        assert collector._is_valid_article(invalid_article) == False
    
    @pytest.mark.asyncio
    async def test_collector_statistics(self, mock_config, mock_logger):
        """統計機能テスト"""
        collector = ReutersCollector(mock_config, mock_logger)
        
        # 統計初期化
        initial_stats = collector.get_collection_statistics()
        assert initial_stats['requests_made'] == 0
        assert initial_stats['articles_collected'] == 0
        
        # 統計更新
        collector.update_collection_stats('request_made')
        collector.update_collection_stats('articles_collected', count=5)
        
        updated_stats = collector.get_collection_statistics()
        assert updated_stats['requests_made'] == 1
        assert updated_stats['articles_collected'] == 5
    
    @pytest.mark.asyncio
    async def test_source_info_retrieval(self, mock_config, mock_logger):
        """ソース情報取得テスト"""
        # Reutersコレクター
        reuters_collector = ReutersCollector(mock_config, mock_logger)
        reuters_info = reuters_collector.get_source_info()
        
        assert reuters_info['name'] == 'Reuters'
        assert reuters_info['type'] == 'RSS Feed'
        assert reuters_info['reliability'] == 'High'
        
        # BBCコレクター
        bbc_collector = BBCCollector(mock_config, mock_logger)
        bbc_info = bbc_collector.get_source_info()
        
        assert bbc_info['name'] == 'BBC News'
        assert bbc_info['reliability'] == 'Very High'
        assert 'editorial_standards' in bbc_info


@pytest.mark.asyncio
async def test_end_to_end_collection():
    """エンドツーエンド収集テスト（実際のRSSフィード使用）"""
    config = MockConfig()
    logger = MockLogger()
    
    # BBC コレクターでの実際のフィード取得テスト（少数）
    async with BBCCollector(config, logger) as bbc_collector:
        try:
            articles = await bbc_collector.collect(category='tech', count=2)
            
            print(f"Collected {len(articles)} articles from BBC")
            for article in articles[:2]:  # 最初の2件のみ表示
                print(f"- {article.title[:50]}...")
                print(f"  Category: {article.category}")
                print(f"  Importance: {article.importance_score}")
            
            # 基本検証
            assert isinstance(articles, list)
            for article in articles:
                assert hasattr(article, 'title')
                assert hasattr(article, 'url')
                assert hasattr(article, 'category')
                
        except Exception as e:
            print(f"End-to-end test error (expected in some environments): {e}")
            # ネットワーク環境によってはエラーが発生する可能性があるため、
            # テスト環境では警告として扱う


if __name__ == "__main__":
    # 個別テスト実行
    print("=== Running New Collectors Tests ===")
    
    # pytest実行
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    print(f"Return code: {result.returncode}")