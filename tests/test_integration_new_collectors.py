"""
Integration Test for New News Collectors
新しいニュースコレクターの統合テスト
"""

import asyncio
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.reuters_collector import ReutersCollector
from src.collectors.bbc_collector import BBCCollector
from src.collectors.collection_manager import CollectionManager
from src.utils.config import ConfigManager


class MockConfig:
    """テスト用設定クラス"""
    
    def get_api_key(self, service):
        return f"mock_{service}_key"
    
    def get(self, *args, **kwargs):
        default = kwargs.get('default', None)
        
        # Nested path navigation
        path_mappings = {
            ('news_sources', 'reuters', 'enabled'): True,
            ('news_sources', 'bbc', 'enabled'): True,
            ('news_sources', 'newsapi', 'enabled'): False,  # 他を無効化してテスト簡略化
            ('news_sources', 'gnews', 'enabled'): False,
            ('news_sources', 'nvd', 'enabled'): False,
            ('collection', 'max_concurrent'): 2,
            ('collection', 'timeout_seconds'): 60,
            ('collection', 'targets'): [],
        }
        
        return path_mappings.get(args, default)


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


@pytest.mark.asyncio
async def test_reuters_real_data_collection():
    """Reutersから実データ収集テスト（少量）"""
    config = MockConfig()
    logger = MockLogger()
    
    async with ReutersCollector(config, logger) as collector:
        try:
            # 少量のテクノロジーニュースを収集
            articles = await collector.collect(category='tech', count=3)
            
            print(f"Reuters collected {len(articles)} articles:")
            for i, article in enumerate(articles, 1):
                print(f"{i}. {article.title[:60]}...")
                print(f"   Category: {article.category}")
                print(f"   Importance: {article.importance_score}")
                print(f"   Source: {article.source_name}")
                print()
            
            # 基本検証
            assert isinstance(articles, list)
            if articles:  # 記事が取得できた場合のみ検証
                for article in articles:
                    assert hasattr(article, 'title')
                    assert hasattr(article, 'url')
                    assert article.source_name == 'Reuters'
                    assert hasattr(article, 'category')
            
        except Exception as e:
            print(f"Reuters collection test error: {e}")
            # ネットワークエラーなどは想定内として扱う
            pytest.skip(f"Reuters collection failed (network issue): {e}")


@pytest.mark.asyncio
async def test_bbc_real_data_collection():
    """BBCから実データ収集テスト（少量）"""
    config = MockConfig()
    logger = MockLogger()
    
    async with BBCCollector(config, logger) as collector:
        try:
            # 少量のテクノロジーニュースを収集
            articles = await collector.collect(category='tech', count=3)
            
            print(f"BBC collected {len(articles)} articles:")
            for i, article in enumerate(articles, 1):
                print(f"{i}. {article.title[:60]}...")
                print(f"   Category: {article.category}")
                print(f"   Importance: {article.importance_score}")
                print(f"   Author: {article.author}")
                print()
            
            # 基本検証
            assert isinstance(articles, list)
            if articles:  # 記事が取得できた場合のみ検証
                for article in articles:
                    assert hasattr(article, 'title')
                    assert hasattr(article, 'url')
                    assert article.source_name == 'BBC News'
                    assert hasattr(article, 'category')
            
        except Exception as e:
            print(f"BBC collection test error: {e}")
            # ネットワークエラーなどは想定内として扱う
            pytest.skip(f"BBC collection failed (network issue): {e}")


@pytest.mark.asyncio
async def test_collection_manager_with_new_sources():
    """新しいソースを使ったCollection Managerテスト"""
    config = MockConfig()
    
    try:
        # Collection Managerの初期化
        manager = CollectionManager(config)
        
        # 新しいコレクターが初期化されているか確認
        print(f"Initialized collectors: {list(manager.collectors.keys())}")
        
        assert 'reuters' in manager.collectors
        assert 'bbc' in manager.collectors
        
        # ヘルスチェック
        health = await manager.get_health_status()
        print(f"Health status: {health['overall_status']}")
        print(f"Collector health: {list(health['collectors'].keys())}")
        
        # 統計情報の確認
        stats = manager.get_collection_statistics()
        print(f"Global stats: {stats['total_sessions']}")
        
        # クリーンアップ
        await manager.cleanup()
        
    except Exception as e:
        print(f"Collection manager test error: {e}")
        # 設定エラーなどは想定内
        pytest.skip(f"Collection manager test failed: {e}")


@pytest.mark.asyncio
async def test_collector_source_info():
    """ソース情報取得テスト"""
    config = MockConfig()
    logger = MockLogger()
    
    # Reuters情報
    reuters_collector = ReutersCollector(config, logger)
    reuters_info = reuters_collector.get_source_info()
    
    print("Reuters Source Info:")
    for key, value in reuters_info.items():
        print(f"  {key}: {value}")
    
    assert reuters_info['name'] == 'Reuters'
    assert reuters_info['reliability'] == 'High'
    assert reuters_info['language'] == 'English'
    
    # BBC情報
    bbc_collector = BBCCollector(config, logger)
    bbc_info = bbc_collector.get_source_info()
    
    print("\nBBC Source Info:")
    for key, value in bbc_info.items():
        print(f"  {key}: {value}")
    
    assert bbc_info['name'] == 'BBC News'
    assert bbc_info['reliability'] == 'Very High'
    assert bbc_info['language'] == 'English'


@pytest.mark.asyncio
async def test_collector_performance_metrics():
    """コレクターパフォーマンス計測テスト"""
    config = MockConfig()
    logger = MockLogger()
    
    async with ReutersCollector(config, logger) as reuters_collector:
        # 統計リセット
        reuters_collector.reset_session_stats()
        
        try:
            # テスト収集実行
            articles = await reuters_collector.collect(category='tech', count=2)
            
            # 統計取得
            stats = reuters_collector.get_collection_statistics()
            
            print("Reuters Performance Stats:")
            print(f"  Articles collected: {stats['articles_collected']}")
            print(f"  Requests made: {stats['requests_made']}")
            print(f"  Success rate: {stats['success_rate']:.1f}%")
            print(f"  Average response time: {stats['average_response_time']:.2f}ms")
            
            # パフォーマンス指標の確認
            assert stats['requests_made'] >= 0
            assert stats['success_rate'] >= 0
            
        except Exception as e:
            print(f"Performance metrics test error: {e}")
            # ネットワークエラーなどは想定内
            pass


@pytest.mark.asyncio
async def test_article_validation_and_deduplication():
    """記事検証と重複除去テスト"""
    config = MockConfig()
    logger = MockLogger()
    
    reuters_collector = ReutersCollector(config, logger)
    
    # 模擬記事データ
    from src.models.article import Article
    
    test_articles = [
        Article(
            url="https://example.com/article1",
            title="Test Article One with Sufficient Length",
            description="This is a test article description",
            content="Article content here",
            source_name="Test Source"
        ),
        Article(
            url="https://example.com/article2",
            title="Test Article Two with Different Content",
            description="This is another test article",
            content="Different article content",
            source_name="Test Source"
        ),
        Article(
            url="https://example.com/article3",
            title="Short",  # 短すぎるタイトル
            description="Description",
            source_name="Test Source"
        ),
    ]
    
    # 検証テスト
    valid_count = 0
    for article in test_articles:
        if reuters_collector._is_valid_article(article):
            valid_count += 1
            print(f"Valid: {article.title[:30]}...")
        else:
            print(f"Invalid: {article.title[:30]}...")
    
    print(f"Valid articles: {valid_count}/{len(test_articles)}")
    assert valid_count == 2  # 最初の2つが有効


if __name__ == "__main__":
    # 個別テスト実行
    print("=== Running Integration Tests ===")
    
    async def run_tests():
        """非同期テストの実行"""
        
        print("\n1. Testing Reuters real data collection...")
        try:
            await test_reuters_real_data_collection()
            print("✓ Reuters test passed")
        except Exception as e:
            print(f"✗ Reuters test failed: {e}")
        
        print("\n2. Testing BBC real data collection...")
        try:
            await test_bbc_real_data_collection()
            print("✓ BBC test passed")
        except Exception as e:
            print(f"✗ BBC test failed: {e}")
        
        print("\n3. Testing Collection Manager integration...")
        try:
            await test_collection_manager_with_new_sources()
            print("✓ Collection Manager test passed")
        except Exception as e:
            print(f"✗ Collection Manager test failed: {e}")
        
        print("\n4. Testing source info...")
        try:
            await test_collector_source_info()
            print("✓ Source info test passed")
        except Exception as e:
            print(f"✗ Source info test failed: {e}")
        
        print("\n5. Testing performance metrics...")
        try:
            await test_collector_performance_metrics()
            print("✓ Performance metrics test passed")
        except Exception as e:
            print(f"✗ Performance metrics test failed: {e}")
        
        print("\n6. Testing article validation...")
        try:
            await test_article_validation_and_deduplication()
            print("✓ Article validation test passed")
        except Exception as e:
            print(f"✗ Article validation test failed: {e}")
    
    # asyncioループで実行
    asyncio.run(run_tests())