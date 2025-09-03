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
from src.processors.analyzer import ClaudeAnalyzer, AnalysisResult, SentimentType


class TestSystemComponents(unittest.TestCase):
    """Test basic system components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
    
    def test_config_loading(self):
        """Test configuration loading"""
        self.assertIsNotNone(self.config)
        # Check if config has data (different attribute names possible)
        config_has_data = hasattr(self.config, 'config_data') or hasattr(self.config, 'data') or hasattr(self.config, 'config')
        self.assertTrue(config_has_data)
    
    def test_article_model(self):
        """Test Article model creation and validation"""
        from datetime import datetime
        
        article = Article(
            title="Test Article",
            content="This is a test article content.",
            url="https://example.com/test",
            source_name="Test Source",
            category="tech",
            language=ArticleLanguage.ENGLISH,
            published_at=datetime.now()
        )
        
        self.assertEqual(article.title, "Test Article")
        self.assertEqual(article.category, "tech")
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
            source_name="Test",
            category="security",
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
        
        with patch('src.collectors.newsapi_collector.NewsAPICollector'), \
             patch('asyncio.create_task') as mock_create_task:
            collector = NewsCollector()
            self.assertIsNotNone(collector)
            # Verify that async task creation was attempted
            mock_create_task.assert_called()
        
        # Test translation service
        from src.services.translation import TranslationService
        
        with patch('deepl.Translator'):
            translator = TranslationService()
            self.assertIsNotNone(translator)
        
        # Test AI analyzer
        from src.processors.analyzer import ClaudeAnalyzer
        
        with patch('anthropic.AsyncAnthropic'):
            analyzer = ClaudeAnalyzer()
            self.assertIsNotNone(analyzer)
            
            # Test Claude 4 configuration
            self.assertEqual(analyzer.model_name, "claude-4-sonnet-20250514")
            self.assertIn("claude-3-5-sonnet-20241022", analyzer.fallback_models)
            self.assertTrue(analyzer.enhanced_reasoning)


class TestDatabaseOperations(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.config = get_config()
        
        # Use in-memory database for testing
        with patch.object(self.config, 'get_storage_path') as mock_path:
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


class TestClaudeEnhancedAnalyzer(unittest.TestCase):
    """Test Claude 4 Sonnet enhanced analyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('anthropic.AsyncAnthropic'):
            self.analyzer = ClaudeAnalyzer()
    
    def test_enhanced_analysis_result(self):
        """Test enhanced AnalysisResult with new features"""
        result = AnalysisResult(
            importance_score=8,
            summary="Enhanced summary with more detailed analysis and context",
            keywords=["claude4", "enhancement", "analysis", "sentiment", "trends"],
            sentiment=SentimentType.MIXED,  # New sentiment type
            sentiment_score=0.3,
            key_points=["Enhanced reasoning", "Better context understanding", "Improved accuracy"],
            risk_factors=["Model complexity", "API costs"],
            impact_assessment="Significant improvement in analysis quality",
            confidence_score=0.9,
            category_analysis={"urgency": "medium", "scope": "technical"},
            # New enhanced features
            emotional_context="Mixed emotions with optimism about improvements",
            bias_assessment="Slight technical bias toward new features",
            opportunity_factors=["Better user experience", "More accurate insights"],
            model_used="claude-4-sonnet-20250514"
        )
        
        # Test basic functionality
        self.assertEqual(result.importance_score, 8)
        self.assertEqual(result.sentiment, SentimentType.MIXED)
        
        # Test new enhanced features
        self.assertIn("improvements", result.emotional_context.lower())
        self.assertIn("bias", result.bias_assessment.lower())
        self.assertEqual(len(result.opportunity_factors), 2)
        self.assertEqual(result.model_used, "claude-4-sonnet-20250514")
        
        # Test post-init defaults
        self.assertIsInstance(result.trend_indicators, dict)
        self.assertIsInstance(result.stakeholder_analysis, dict)
    
    def test_fallback_mechanisms(self):
        """Test enhanced fallback analysis"""
        from datetime import datetime
        
        # Test article with security content
        security_article = Article(
            title="Critical Security Vulnerability CVE-2024-1234",
            content="A critical vulnerability has been discovered that affects multiple systems.",
            url="https://example.com/security-alert",
            source_name="Security Alert",
            category="security",
            language=ArticleLanguage.ENGLISH,
            published_at=datetime.now()
        )
        
        fallback_data = self.analyzer._perform_basic_fallback_analysis(security_article)
        
        # Should detect security context and assign higher importance
        self.assertGreaterEqual(fallback_data.get('importance_score', 5), 7)
        keywords = [k.lower() for k in fallback_data.get('keywords', [])]
        self.assertTrue(any('vulnerability' in k or 'security' in k or 'cve' in k for k in keywords))
    
    def test_validation_enhancements(self):
        """Test enhanced data validation"""
        test_data = {
            'importance_score': 15,  # Over limit
            'summary': 'Too short',  # Under enhanced limit
            'keywords': ['k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'k7', 'k8', 'k9'],  # Over enhanced limit
            'sentiment': 'mixed',  # New sentiment type
            'sentiment_score': -2.0,  # Under limit
            'emotional_context': 'Complex emotional landscape',
            'bias_assessment': 'Minimal bias detected',
            'opportunity_factors': ['Growth', 'Innovation', 'Efficiency'],
            'trend_indicators': {'rising': ['AI', 'automation']},
            'stakeholder_analysis': {'primary': ['developers', 'users']}
        }
        
        validated = self.analyzer._validate_and_normalize_analysis(test_data)
        
        # Test boundary enforcement
        self.assertLessEqual(validated['importance_score'], 10)
        self.assertGreaterEqual(validated['importance_score'], 1)
        self.assertLessEqual(len(validated['keywords']), 7)
        self.assertEqual(validated['sentiment'], 'mixed')
        self.assertGreaterEqual(validated['sentiment_score'], -1.0)
        
        # Test new field preservation
        self.assertEqual(validated['emotional_context'], 'Complex emotional landscape')
        self.assertEqual(validated['bias_assessment'], 'Minimal bias detected')
        self.assertIsInstance(validated['opportunity_factors'], list)
        self.assertIsInstance(validated['trend_indicators'], dict)
    
    def test_model_fallback_sequence(self):
        """Test model fallback sequence"""
        self.assertEqual(self.analyzer.model_name, "claude-4-sonnet-20250514")
        self.assertIsInstance(self.analyzer.fallback_models, list)
        self.assertIn("claude-3-5-sonnet-20241022", self.analyzer.fallback_models)
        self.assertIn("claude-3-haiku-20240307", self.analyzer.fallback_models)
    
    def test_enhanced_statistics(self):
        """Test enhanced statistics reporting"""
        stats = self.analyzer.get_analysis_statistics()
        
        # Test basic stats exist
        required_stats = ['total_requests', 'api_calls', 'cache_hits', 'cache_hit_rate']
        for stat in required_stats:
            self.assertIn(stat, stats)
        
        # Test enhanced features
        self.assertIn('primary_model', stats)
        self.assertIn('fallback_models', stats)
        self.assertIn('enhanced_features', stats)
        
        enhanced_features = stats['enhanced_features']
        self.assertTrue(enhanced_features['trend_analysis'])
        self.assertTrue(enhanced_features['sentiment_enhancement'])
        self.assertTrue(enhanced_features['stakeholder_analysis'])
        self.assertTrue(enhanced_features['bias_assessment'])


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
        cache_path = config.get_storage_path('cache')
        logs_path = config.get_storage_path('logs')
        
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
        TestClaudeEnhancedAnalyzer,
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