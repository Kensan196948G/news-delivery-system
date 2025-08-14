"""
Basic system tests for News Delivery System
"""

import unittest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.config import get_config
from src.models.article import Article, ArticleCategory, ArticleLanguage
from src.utils.rate_limiter import RateLimiter


class TestSystemComponents(unittest.TestCase):
    """Test basic system components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
    
    def test_config_loading(self):
        """Test configuration loading"""
        self.assertIsNotNone(self.config)
        self.assertIsInstance(self.config.config_data, dict)
    
    def test_article_model(self):
        """Test Article model creation and validation"""
        from datetime import datetime
        
        article = Article(
            title="Test Article",
            content="This is a test article content.",
            url="https://example.com/test",
            source="Test Source",
            category=ArticleCategory.TECH,
            language=ArticleLanguage.ENGLISH,
            published_at=datetime.now()
        )
        
        self.assertEqual(article.title, "Test Article")
        self.assertEqual(article.category, ArticleCategory.TECH)
        self.assertEqual(article.language, ArticleLanguage.ENGLISH)
        self.assertFalse(article.is_urgent)
        
        # Test urgency determination
        article.importance_score = 10
        article.__post_init__()
        self.assertTrue(article.is_urgent)
    
    def test_article_serialization(self):
        """Test Article to/from dict conversion"""
        from datetime import datetime
        
        original_article = Article(
            title="Test Article",
            content="Test content",
            url="https://example.com",
            source="Test",
            category=ArticleCategory.SECURITY,
            language=ArticleLanguage.JAPANESE,
            published_at=datetime.now(),
            importance_score=8,
            keywords=["test", "article"]
        )
        
        # Convert to dict
        article_dict = original_article.to_dict()
        self.assertIsInstance(article_dict, dict)
        self.assertEqual(article_dict['title'], "Test Article")
        self.assertEqual(article_dict['importance_score'], 8)
        
        # Convert back from dict
        restored_article = Article.from_dict(article_dict)
        self.assertEqual(restored_article.title, original_article.title)
        self.assertEqual(restored_article.importance_score, original_article.importance_score)
        self.assertEqual(restored_article.category, original_article.category)
    
    def test_rate_limiter(self):
        """Test rate limiter functionality"""
        rate_limiter = RateLimiter()
        
        # Test service configuration
        self.assertIn('newsapi', rate_limiter.limits)
        self.assertIn('deepl', rate_limiter.limits)
        self.assertIn('claude', rate_limiter.limits)
        
        # Test request recording
        remaining_before = rate_limiter.get_remaining_requests('newsapi')
        rate_limiter.record_request('newsapi')
        remaining_after = rate_limiter.get_remaining_requests('newsapi')
        
        self.assertIsNotNone(remaining_before)
        self.assertIsNotNone(remaining_after)
        if remaining_before is not None and remaining_after is not None:
            self.assertEqual(remaining_before - 1, remaining_after)


class TestAsyncComponents(unittest.TestCase):
    """Test async components"""
    
    def setUp(self):
        """Set up async test fixtures"""
        self.config = get_config()
    
    def test_rate_limiter_async(self):
        """Test async rate limiter functionality"""
        async def async_test():
            rate_limiter = RateLimiter()
            
            # Test async wait functionality
            result = await rate_limiter.wait_if_needed('newsapi')
            self.assertTrue(result)
            
            # Test status
            status = rate_limiter.get_status()
            self.assertIsInstance(status, dict)
            self.assertIn('newsapi', status)
        
        asyncio.run(async_test())


class TestMockServices(unittest.TestCase):
    """Test services with mocked dependencies"""
    
    @patch.dict('os.environ', {
        'NEWSAPI_KEY': 'test_key',
        'DEEPL_API_KEY': 'test_key',
        'ANTHROPIC_API_KEY': 'test_key'
    })
    def test_service_initialization(self):
        """Test service initialization with mocked API keys"""
        # Test news collector
        from src.services.news_collector import NewsCollector
        
        with patch('src.services.news_collector.NewsApiClient'):
            collector = NewsCollector()
            self.assertIsNotNone(collector)
        
        # Test translation service
        from src.services.translation import TranslationService
        
        with patch('deepl.Translator'):
            translator = TranslationService()
            self.assertIsNotNone(translator)
        
        # Test AI analyzer
        from src.services.ai_analyzer import ClaudeAnalyzer
        
        with patch('anthropic.Anthropic'):
            analyzer = ClaudeAnalyzer()
            self.assertIsNotNone(analyzer)


class TestDatabaseOperations(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.config = get_config()
        
        # Use in-memory database for testing
        with patch.object(self.config, 'get_data_path') as mock_path:
            mock_path.return_value = Path(':memory:')
            from src.models.database import Database
            self.db = Database(self.config)
    
    def test_database_initialization(self):
        """Test database initialization"""
        self.assertIsNotNone(self.db)
        
        # Test connection
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # Check that required tables exist
            table_names = [table[0] for table in tables]
            self.assertIn('articles', table_names)
            self.assertIn('delivery_history', table_names)
            self.assertIn('api_usage', table_names)


class TestUtilities(unittest.TestCase):
    """Test utility functions"""
    
    def test_config_environment_loading(self):
        """Test configuration with environment variables"""
        with patch.dict('os.environ', {'TEST_ENV_VAR': 'test_value'}):
            config = get_config()
            env_value = config.get_env('TEST_ENV_VAR')
            self.assertEqual(env_value, 'test_value')
    
    def test_config_data_path_generation(self):
        """Test data path generation"""
        config = get_config()
        
        # Test different path types
        cache_path = config.get_data_path('cache_dir')
        logs_path = config.get_data_path('logs_dir')
        
        self.assertIsInstance(cache_path, Path)
        self.assertIsInstance(logs_path, Path)


def run_tests():
    """Run all tests"""
    print("Running News Delivery System Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestSystemComponents,
        TestAsyncComponents,
        TestMockServices,
        TestDatabaseOperations,
        TestUtilities
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print results
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall result: {'PASS' if success else 'FAIL'}")
    
    return success


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)