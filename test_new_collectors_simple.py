#!/usr/bin/env python3
"""
Simple test for new collectors
新しいコレクターの簡単なテスト
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.collectors.reuters_collector import ReutersCollector
from src.collectors.bbc_collector import BBCCollector


class MockConfig:
    def get_api_key(self, service):
        return f"mock_{service}_key"


class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")


async def test_collectors():
    """新しいコレクターのテスト"""
    
    config = MockConfig()
    logger = MockLogger()
    
    print("=== Testing Reuters Collector ===")
    try:
        async with ReutersCollector(config, logger) as reuters_collector:
            # ソース情報の取得
            source_info = reuters_collector.get_source_info()
            print(f"Reuters Source: {source_info['name']}")
            print(f"Reliability: {source_info['reliability']}")
            print(f"Available Feeds: {len(source_info['feeds_available'])}")
            
            # カテゴリ判定テスト
            category = reuters_collector._determine_category(
                "AI Technology Breakthrough", 
                "Artificial intelligence research", 
                "technology"
            )
            print(f"Category determination test: {category}")
            
            # 重要度計算テスト
            importance = reuters_collector._calculate_importance(
                "Breaking: Cybersecurity Alert", 
                "Security researchers discover vulnerability", 
                "cybersecurity"
            )
            print(f"Importance calculation test: {importance}")
            
            print("✓ Reuters collector tests passed")
    
    except Exception as e:
        print(f"✗ Reuters collector test failed: {e}")
    
    print("\n=== Testing BBC Collector ===")
    try:
        async with BBCCollector(config, logger) as bbc_collector:
            # ソース情報の取得
            source_info = bbc_collector.get_source_info()
            print(f"BBC Source: {source_info['name']}")
            print(f"Reliability: {source_info['reliability']}")
            print(f"Available Feeds: {len(source_info['feeds_available'])}")
            
            # コンテンツクリーニングテスト
            dirty_content = '<p>This is <strong>important</strong> news &amp; information.</p>'
            clean_content = bbc_collector._clean_description(dirty_content)
            print(f"Content cleaning test: '{clean_content[:50]}...'")
            
            # カテゴリ判定テスト
            category = bbc_collector._determine_category(
                "Technology Innovation", 
                "AI and machine learning advances", 
                "technology"
            )
            print(f"Category determination test: {category}")
            
            print("✓ BBC collector tests passed")
            
    except Exception as e:
        print(f"✗ BBC collector test failed: {e}")
    
    print("\n=== Testing Collection Manager Integration ===")
    try:
        # Collection Manager の基本テスト
        from src.collectors.collection_manager import CollectionManager
        
        class ExtendedMockConfig(MockConfig):
            def get(self, *args, **kwargs):
                default = kwargs.get('default', None)
                path_mappings = {
                    ('news_sources', 'reuters', 'enabled'): True,
                    ('news_sources', 'bbc', 'enabled'): True,
                    ('news_sources', 'newsapi', 'enabled'): False,
                    ('news_sources', 'gnews', 'enabled'): False,
                    ('news_sources', 'nvd', 'enabled'): False,
                    ('collection', 'max_concurrent'): 2,
                    ('collection', 'timeout_seconds'): 60,
                    ('collection', 'targets'): [],
                }
                return path_mappings.get(args, default)
        
        extended_config = ExtendedMockConfig()
        manager = CollectionManager(extended_config)
        
        print(f"Initialized collectors: {list(manager.collectors.keys())}")
        
        # 新しいコレクターが含まれているか確認
        assert 'reuters' in manager.collectors, "Reuters collector not found"
        assert 'bbc' in manager.collectors, "BBC collector not found"
        
        print("✓ Collection Manager integration test passed")
        
        # クリーンアップ
        await manager.cleanup()
        
    except Exception as e:
        print(f"✗ Collection Manager test failed: {e}")
    
    print("\n=== All Tests Completed ===")


if __name__ == "__main__":
    asyncio.run(test_collectors())