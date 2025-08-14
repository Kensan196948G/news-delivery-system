"""
Delivery Quality Testing and Validation System
配信品質検証・テストシステム - CLAUDE.md仕様準拠
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import time
import statistics

from utils.config import get_config
from utils.logger import setup_logger
from models.enhanced_article import Article, ArticleCategory
from .email_delivery import GmailDeliveryService
from .report_generator import ReportGenerator
from .emergency_alert_system import EmergencyAlertSystem
from .windows_task_scheduler import WindowsTaskScheduler


logger = logging.getLogger(__name__)


class TestSeverity(Enum):
    """Test result severity levels"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    CRITICAL = "critical"


@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    severity: TestSeverity
    success: bool
    message: str
    details: Dict[str, Any]
    execution_time: float
    timestamp: datetime
    
    @property
    def is_critical_failure(self) -> bool:
        """Check if this is a critical failure"""
        return self.severity == TestSeverity.CRITICAL and not self.success


@dataclass
class QualityReport:
    """Quality assessment report"""
    overall_score: float  # 0-100
    test_results: List[TestResult]
    recommendations: List[str]
    performance_metrics: Dict[str, Any]
    generated_at: datetime
    
    @property
    def has_critical_failures(self) -> bool:
        """Check if there are critical failures"""
        return any(result.is_critical_failure for result in self.test_results)
    
    @property
    def pass_rate(self) -> float:
        """Calculate test pass rate"""
        if not self.test_results:
            return 0.0
        passed = len([r for r in self.test_results if r.success])
        return (passed / len(self.test_results)) * 100


class DeliveryQualityTester:
    """Comprehensive delivery quality testing system"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.logger = setup_logger(__name__)
        
        # Initialize services for testing
        self.email_service = GmailDeliveryService(self.config)
        self.report_generator = ReportGenerator(self.config)
        self.emergency_alert_system = EmergencyAlertSystem(self.config)
        self.task_scheduler = WindowsTaskScheduler(self.config)
        
        # Quality thresholds - CLAUDE.md compliant
        self.quality_thresholds = {
            'delivery_success_rate': 95.0,      # CLAUDE.md: 95%以上
            'processing_time_limit': 600.0,     # CLAUDE.md: 10分以内
            'report_generation_time': 120.0,    # CLAUDE.md: 2分以内
            'email_delivery_time': 60.0,        # 1分以内
            'urgent_alert_time': 300.0,         # 5分以内
            'api_response_time': 30.0,          # 30秒以内
            'translation_accuracy': 85.0,       # 85%以上
            'analysis_completeness': 90.0       # 90%以上
        }
        
        # Test configuration
        self.test_timeouts = {
            'quick': 30,      # Quick tests (30 seconds)
            'standard': 120,  # Standard tests (2 minutes)
            'comprehensive': 600  # Comprehensive tests (10 minutes)
        }
    
    async def run_comprehensive_quality_test(self) -> QualityReport:
        """Run comprehensive quality assessment"""
        self.logger.info("Starting comprehensive delivery quality test")
        start_time = time.time()
        
        test_results = []
        
        try:
            # Core system tests
            test_results.extend(await self._test_system_components())
            
            # Email delivery tests
            test_results.extend(await self._test_email_delivery())
            
            # Report generation tests
            test_results.extend(await self._test_report_generation())
            
            # Emergency alert tests
            test_results.extend(await self._test_emergency_alerts())
            
            # Scheduling tests
            test_results.extend(await self._test_scheduling_system())
            
            # Performance tests
            test_results.extend(await self._test_performance())
            
            # Integration tests
            test_results.extend(await self._test_integration())
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(test_results)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(test_results)
            
            # Collect performance metrics
            performance_metrics = self._collect_performance_metrics(test_results)
            
            # Create quality report
            quality_report = QualityReport(
                overall_score=overall_score,
                test_results=test_results,
                recommendations=recommendations,
                performance_metrics=performance_metrics,
                generated_at=datetime.now()
            )
            
            execution_time = time.time() - start_time
            self.logger.info(f"Quality test completed in {execution_time:.2f}s. Overall score: {overall_score:.1f}%")
            
            # Save report
            await self._save_quality_report(quality_report)
            
            return quality_report
            
        except Exception as e:
            self.logger.error(f"Comprehensive quality test failed: {e}")
            # Return failed report
            failed_result = TestResult(
                test_name="comprehensive_test",
                severity=TestSeverity.CRITICAL,
                success=False,
                message=f"Quality test failed: {str(e)}",
                details={"error": str(e)},
                execution_time=time.time() - start_time,
                timestamp=datetime.now()
            )
            
            return QualityReport(
                overall_score=0.0,
                test_results=[failed_result],
                recommendations=["システムの緊急確認が必要です"],
                performance_metrics={},
                generated_at=datetime.now()
            )
    
    async def _test_system_components(self) -> List[TestResult]:
        """Test core system components"""
        results = []
        
        # Test configuration loading
        result = await self._test_configuration()
        results.append(result)
        
        # Test database connectivity
        result = await self._test_database_connection()
        results.append(result)
        
        # Test cache system
        result = await self._test_cache_system()
        results.append(result)
        
        # Test logging system
        result = await self._test_logging_system()
        results.append(result)
        
        # Test error notification
        result = await self._test_error_notification()
        results.append(result)
        
        return results
    
    async def _test_configuration(self) -> TestResult:
        """Test configuration system"""
        start_time = time.time()
        
        try:
            # Test config loading
            config_valid = True
            details = {}
            
            # Check required configuration sections
            required_sections = ['system', 'collection', 'delivery', 'api_limits']
            for section in required_sections:
                if not hasattr(self.config, section) and section not in self.config._config:
                    config_valid = False
                    details[f"missing_{section}"] = True
            
            # Check API keys
            api_keys = {
                'newsapi': self.config.get('api_keys', 'newsapi'),
                'deepl': self.config.get('api_keys', 'deepl'),
                'anthropic': self.config.get('api_keys', 'anthropic')
            }
            
            missing_keys = [name for name, key in api_keys.items() if not key]
            if missing_keys:
                details['missing_api_keys'] = missing_keys
            
            # Check storage paths
            storage_paths = {
                'data_root': self.config.get_storage_path('articles'),
                'reports': self.config.get_storage_path('reports'),
                'logs': self.config.get_storage_path('logs')
            }
            
            for path_name, path in storage_paths.items():
                if not path.exists():
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        details[f"created_{path_name}"] = str(path)
                    except Exception as e:
                        config_valid = False
                        details[f"path_error_{path_name}"] = str(e)
            
            execution_time = time.time() - start_time
            
            if config_valid:
                return TestResult(
                    test_name="configuration_test",
                    severity=TestSeverity.PASS,
                    success=True,
                    message="設定システム正常",
                    details=details,
                    execution_time=execution_time,
                    timestamp=datetime.now()
                )
            else:
                return TestResult(
                    test_name="configuration_test",
                    severity=TestSeverity.CRITICAL,
                    success=False,
                    message="設定システムエラー",
                    details=details,
                    execution_time=execution_time,
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="configuration_test",
                severity=TestSeverity.CRITICAL,
                success=False,
                message=f"設定テスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_database_connection(self) -> TestResult:
        """Test database connectivity and operations"""
        start_time = time.time()
        
        try:
            # Import database modules
            from models.database_orm import AsyncDatabase
            
            # Test database connection
            async with AsyncDatabase() as db:
                # Test basic operations
                test_article = Article(
                    url="https://test.example.com/quality-test",
                    title="Database Test Article",
                    source_name="Quality Test System",
                    category=ArticleCategory.TECH,
                    published_at=datetime.now(),
                    importance_score=5
                )
                
                # Test save operation
                saved_count = await db.save_articles_batch([test_article])
                
                # Test retrieval
                recent_articles = await db.get_recent_articles(limit=1)
                
                # Test statistics
                stats = await db.get_delivery_statistics()
                
                execution_time = time.time() - start_time
                
                details = {
                    "saved_articles": saved_count,
                    "retrieved_articles": len(recent_articles),
                    "stats_available": bool(stats),
                    "database_file_exists": True
                }
                
                return TestResult(
                    test_name="database_connection_test",
                    severity=TestSeverity.PASS,
                    success=True,
                    message="データベース接続正常",
                    details=details,
                    execution_time=execution_time,
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="database_connection_test",
                severity=TestSeverity.CRITICAL,
                success=False,
                message=f"データベース接続失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_cache_system(self) -> TestResult:
        """Test cache system functionality"""
        start_time = time.time()
        
        try:
            from utils.cache_manager import get_cache_manager
            
            cache = get_cache_manager()
            
            # Test cache operations
            test_key = "quality_test_key"
            test_value = {"test": "data", "timestamp": datetime.now().isoformat()}
            
            # Test set operation
            cache.set(test_key, test_value, expire=60)
            
            # Test get operation
            retrieved_value = cache.get(test_key)
            
            # Test delete operation
            cache.delete(test_key)
            
            # Test after delete
            after_delete = cache.get(test_key)
            
            execution_time = time.time() - start_time
            
            success = (
                retrieved_value == test_value and
                after_delete is None
            )
            
            details = {
                "set_operation": True,
                "get_operation": retrieved_value == test_value,
                "delete_operation": after_delete is None,
                "cache_type": type(cache).__name__
            }
            
            return TestResult(
                test_name="cache_system_test",
                severity=TestSeverity.PASS if success else TestSeverity.WARNING,
                success=success,
                message="キャッシュシステム正常" if success else "キャッシュシステム問題",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="cache_system_test",
                severity=TestSeverity.WARNING,
                success=False,
                message=f"キャッシュテスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_logging_system(self) -> TestResult:
        """Test logging system"""
        start_time = time.time()
        
        try:
            # Test logger creation and basic operations
            test_logger = logging.getLogger("quality_test")
            
            # Test log levels
            test_logger.debug("Debug test message")
            test_logger.info("Info test message")
            test_logger.warning("Warning test message")
            test_logger.error("Error test message")
            
            # Check log directory exists
            logs_dir = self.config.get_storage_path('logs')
            log_files_exist = logs_dir.exists() and any(logs_dir.glob('*.log'))
            
            execution_time = time.time() - start_time
            
            details = {
                "logger_created": True,
                "log_directory_exists": logs_dir.exists(),
                "log_files_exist": log_files_exist,
                "log_directory": str(logs_dir)
            }
            
            return TestResult(
                test_name="logging_system_test",
                severity=TestSeverity.PASS,
                success=True,
                message="ログシステム正常",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="logging_system_test",
                severity=TestSeverity.WARNING,
                success=False,
                message=f"ログテスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_error_notification(self) -> TestResult:
        """Test error notification system"""
        start_time = time.time()
        
        try:
            from utils.error_notifier import get_error_notifier
            
            error_notifier = get_error_notifier()
            
            # Test error handling
            test_error = Exception("Quality test error")
            error_key = await error_notifier.handle_error(
                test_error,
                context="quality_test",
                severity=error_notifier.ErrorSeverity.LOW
            )
            
            # Test summary
            summary = error_notifier.get_error_summary()
            
            execution_time = time.time() - start_time
            
            details = {
                "error_handled": bool(error_key),
                "summary_available": bool(summary),
                "admin_email_configured": bool(error_notifier.admin_email),
                "error_count": summary.get('total_errors', 0)
            }
            
            return TestResult(
                test_name="error_notification_test",
                severity=TestSeverity.PASS,
                success=True,
                message="エラー通知システム正常",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="error_notification_test",
                severity=TestSeverity.WARNING,
                success=False,
                message=f"エラー通知テスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_email_delivery(self) -> List[TestResult]:
        """Test email delivery system"""
        results = []
        
        # Test Gmail connection
        result = await self._test_gmail_connection()
        results.append(result)
        
        # Test email formatting
        result = await self._test_email_formatting()
        results.append(result)
        
        # Test attachment handling
        result = await self._test_attachment_handling()
        results.append(result)
        
        return results
    
    async def _test_gmail_connection(self) -> TestResult:
        """Test Gmail API connection"""
        start_time = time.time()
        
        try:
            # Test connection
            connection_test = self.email_service.test_email_connection()
            
            # Test quota info
            quota_info = self.email_service.get_quota_info()
            
            execution_time = time.time() - start_time
            
            details = {
                "connection_successful": connection_test,
                "service_available": quota_info.get('service_available', False),
                "configured_recipients": quota_info.get('configured_recipients', 0),
                "sender_email": quota_info.get('sender_email', 'Not configured')
            }
            
            success = connection_test and quota_info.get('service_available', False)
            
            return TestResult(
                test_name="gmail_connection_test",
                severity=TestSeverity.CRITICAL if not success else TestSeverity.PASS,
                success=success,
                message="Gmail接続正常" if success else "Gmail接続エラー",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="gmail_connection_test",
                severity=TestSeverity.CRITICAL,
                success=False,
                message=f"Gmail接続テスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_email_formatting(self) -> TestResult:
        """Test email formatting and template rendering"""
        start_time = time.time()
        
        try:
            # Create test articles
            test_articles = [
                Article(
                    url="https://test1.example.com",
                    title="Test Article 1",
                    source_name="Test Source",
                    category=ArticleCategory.TECH,
                    published_at=datetime.now(),
                    importance_score=7
                ),
                Article(
                    url="https://test2.example.com",
                    title="Test Urgent Article",
                    source_name="Test Source",
                    category=ArticleCategory.SECURITY,
                    published_at=datetime.now(),
                    importance_score=10,
                    cvss_score=9.5
                )
            ]
            
            # Test HTML content generation
            daily_html = self.email_service._create_daily_html_content(
                len(test_articles), 1, {}
            )
            
            urgent_html = self.email_service._create_urgent_html_content(
                1, {}
            )
            
            execution_time = time.time() - start_time
            
            details = {
                "daily_html_generated": bool(daily_html and len(daily_html) > 0),
                "urgent_html_generated": bool(urgent_html and len(urgent_html) > 0),
                "daily_html_length": len(daily_html) if daily_html else 0,
                "urgent_html_length": len(urgent_html) if urgent_html else 0
            }
            
            success = bool(daily_html and urgent_html)
            
            return TestResult(
                test_name="email_formatting_test",
                severity=TestSeverity.PASS if success else TestSeverity.FAIL,
                success=success,
                message="メールフォーマット正常" if success else "メールフォーマットエラー",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="email_formatting_test",
                severity=TestSeverity.FAIL,
                success=False,
                message=f"メールフォーマットテスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_attachment_handling(self) -> TestResult:
        """Test attachment handling"""
        start_time = time.time()
        
        try:
            # Test report generation for attachment
            test_articles = [
                Article(
                    url="https://test.example.com",
                    title="Attachment Test Article",
                    source_name="Test Source",
                    category=ArticleCategory.TECH,
                    published_at=datetime.now(),
                    importance_score=6
                )
            ]
            
            # Generate test reports
            report_files = await self.report_generator.generate_daily_report(test_articles)
            
            execution_time = time.time() - start_time
            
            details = {
                "reports_generated": len(report_files),
                "html_report": 'html' in report_files,
                "pdf_report": 'pdf' in report_files,
                "report_files": list(report_files.keys())
            }
            
            # Check if files actually exist
            files_exist = all(
                Path(file_path).exists() 
                for file_path in report_files.values()
            )
            
            details["files_exist"] = files_exist
            
            success = len(report_files) > 0 and files_exist
            
            return TestResult(
                test_name="attachment_handling_test",
                severity=TestSeverity.PASS if success else TestSeverity.FAIL,
                success=success,
                message="添付ファイル処理正常" if success else "添付ファイル処理エラー",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="attachment_handling_test",
                severity=TestSeverity.FAIL,
                success=False,
                message=f"添付ファイルテスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_report_generation(self) -> List[TestResult]:
        """Test report generation functionality"""
        results = []
        
        # Test HTML report generation
        result = await self._test_html_report_generation()
        results.append(result)
        
        # Test PDF report generation
        result = await self._test_pdf_report_generation()
        results.append(result)
        
        return results
    
    async def _test_html_report_generation(self) -> TestResult:
        """Test HTML report generation"""
        start_time = time.time()
        
        try:
            # Create test articles
            test_articles = [
                Article(
                    url=f"https://test{i}.example.com",
                    title=f"Test Article {i}",
                    source_name="Test Source",
                    category=ArticleCategory.TECH,
                    published_at=datetime.now() - timedelta(hours=i),
                    importance_score=5 + i
                )
                for i in range(5)
            ]
            
            # Generate HTML report
            report_files = await self.report_generator.generate_daily_report(test_articles)
            
            execution_time = time.time() - start_time
            
            # Check if HTML was generated
            html_generated = 'html' in report_files
            html_file_exists = False
            html_file_size = 0
            
            if html_generated:
                html_path = Path(report_files['html'])
                html_file_exists = html_path.exists()
                if html_file_exists:
                    html_file_size = html_path.stat().st_size
            
            details = {
                "html_in_report": html_generated,
                "html_file_exists": html_file_exists,
                "html_file_size": html_file_size,
                "articles_processed": len(test_articles),
                "generation_time": execution_time
            }
            
            success = html_generated and html_file_exists and html_file_size > 0
            
            # Check if within time threshold
            within_time_limit = execution_time <= self.quality_thresholds['report_generation_time']
            if not within_time_limit:
                details["time_limit_exceeded"] = True
            
            severity = TestSeverity.PASS if success and within_time_limit else TestSeverity.WARNING
            
            return TestResult(
                test_name="html_report_generation_test",
                severity=severity,
                success=success,
                message="HTMLレポート生成正常" if success else "HTMLレポート生成問題",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="html_report_generation_test",
                severity=TestSeverity.FAIL,
                success=False,
                message=f"HTMLレポート生成失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_pdf_report_generation(self) -> TestResult:
        """Test PDF report generation"""
        start_time = time.time()
        
        try:
            # Create test articles
            test_articles = [
                Article(
                    url=f"https://test{i}.example.com",
                    title=f"PDF Test Article {i}",
                    source_name="Test Source",
                    category=ArticleCategory.SECURITY,
                    published_at=datetime.now() - timedelta(hours=i),
                    importance_score=6 + i
                )
                for i in range(3)
            ]
            
            # Generate PDF report
            report_files = await self.report_generator.generate_daily_report(test_articles)
            
            execution_time = time.time() - start_time
            
            # Check if PDF was generated
            pdf_generated = 'pdf' in report_files
            pdf_file_exists = False
            pdf_file_size = 0
            
            if pdf_generated:
                pdf_path = Path(report_files['pdf'])
                pdf_file_exists = pdf_path.exists()
                if pdf_file_exists:
                    pdf_file_size = pdf_path.stat().st_size
            
            details = {
                "pdf_in_report": pdf_generated,
                "pdf_file_exists": pdf_file_exists,
                "pdf_file_size": pdf_file_size,
                "articles_processed": len(test_articles),
                "generation_time": execution_time
            }
            
            success = pdf_generated and pdf_file_exists and pdf_file_size > 0
            
            # Check if within time threshold
            within_time_limit = execution_time <= self.quality_thresholds['report_generation_time']
            if not within_time_limit:
                details["time_limit_exceeded"] = True
            
            severity = TestSeverity.PASS if success and within_time_limit else TestSeverity.WARNING
            
            return TestResult(
                test_name="pdf_report_generation_test",
                severity=severity,
                success=success,
                message="PDFレポート生成正常" if success else "PDFレポート生成問題",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="pdf_report_generation_test",
                severity=TestSeverity.WARNING,  # PDF generation might fail due to missing dependencies
                success=False,
                message=f"PDFレポート生成失敗: {str(e)}",
                details={"error": str(e), "note": "PDF generation dependencies may be missing"},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_emergency_alerts(self) -> List[TestResult]:
        """Test emergency alert system"""
        results = []
        
        # Test alert criteria detection
        result = await self._test_alert_detection()
        results.append(result)
        
        # Test alert generation
        result = await self._test_alert_generation()
        results.append(result)
        
        return results
    
    async def _test_alert_detection(self) -> TestResult:
        """Test emergency alert detection"""
        start_time = time.time()
        
        try:
            # Create test articles with emergency criteria
            test_articles = [
                # Critical CVSS score
                Article(
                    url="https://test-critical.example.com",
                    title="Critical Security Vulnerability",
                    source_name="Security Test",
                    category=ArticleCategory.SECURITY,
                    published_at=datetime.now(),
                    importance_score=8,
                    cvss_score=9.5
                ),
                # High importance score
                Article(
                    url="https://test-important.example.com",
                    title="Critical News Alert",
                    source_name="News Test",
                    category=ArticleCategory.DOMESTIC_SOCIAL,
                    published_at=datetime.now(),
                    importance_score=10
                ),
                # Normal article (should not trigger)
                Article(
                    url="https://test-normal.example.com",
                    title="Normal Article",
                    source_name="News Test",
                    category=ArticleCategory.TECH,
                    published_at=datetime.now(),
                    importance_score=5
                )
            ]
            
            # Test alert detection
            emergency_articles = self.emergency_alert_system._filter_emergency_articles(test_articles)
            
            execution_time = time.time() - start_time
            
            details = {
                "total_articles": len(test_articles),
                "emergency_articles": len(emergency_articles),
                "cvss_detection": any(a.cvss_score and a.cvss_score >= 9.0 for a in emergency_articles),
                "importance_detection": any(a.importance_score >= 10 for a in emergency_articles)
            }
            
            # Should detect 2 emergency articles
            success = len(emergency_articles) == 2
            
            return TestResult(
                test_name="alert_detection_test",
                severity=TestSeverity.PASS if success else TestSeverity.FAIL,
                success=success,
                message="緊急アラート検出正常" if success else "緊急アラート検出問題",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="alert_detection_test",
                severity=TestSeverity.FAIL,
                success=False,
                message=f"アラート検出テスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_alert_generation(self) -> TestResult:
        """Test alert generation process"""
        start_time = time.time()
        
        try:
            # Create emergency test article
            emergency_article = Article(
                url="https://test-emergency.example.com",
                title="Emergency Alert Test",
                source_name="Emergency Test",
                category=ArticleCategory.SECURITY,
                published_at=datetime.now(),
                importance_score=10,
                cvss_score=9.8
            )
            
            # Test alert creation
            alerts = await self.emergency_alert_system._create_emergency_alerts([emergency_article])
            
            execution_time = time.time() - start_time
            
            details = {
                "alerts_created": len(alerts),
                "alert_has_id": bool(alerts[0].alert_id) if alerts else False,
                "alert_priority": alerts[0].priority.value if alerts else None,
                "alert_criteria": alerts[0].criteria_met if alerts else [],
                "is_security_related": alerts[0].is_security_related if alerts else False
            }
            
            success = len(alerts) > 0 and bool(alerts[0].alert_id)
            
            return TestResult(
                test_name="alert_generation_test",
                severity=TestSeverity.PASS if success else TestSeverity.FAIL,
                success=success,
                message="アラート生成正常" if success else "アラート生成問題",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="alert_generation_test",
                severity=TestSeverity.FAIL,
                success=False,
                message=f"アラート生成テスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_scheduling_system(self) -> List[TestResult]:
        """Test scheduling system"""
        results = []
        
        # Test Windows Task Scheduler validation
        result = await self._test_windows_scheduler()
        results.append(result)
        
        return results
    
    async def _test_windows_scheduler(self) -> TestResult:
        """Test Windows Task Scheduler integration"""
        start_time = time.time()
        
        try:
            # Test environment validation
            validation = self.task_scheduler.validate_windows_environment()
            
            execution_time = time.time() - start_time
            
            details = validation.copy()
            
            success = validation.get('overall_ready', False)
            severity = TestSeverity.PASS if success else TestSeverity.WARNING
            
            return TestResult(
                test_name="windows_scheduler_test",
                severity=severity,
                success=success,
                message="Windowsスケジューラ準備完了" if success else "Windowsスケジューラ設定要",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="windows_scheduler_test",
                severity=TestSeverity.WARNING,
                success=False,
                message=f"スケジューラテスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_performance(self) -> List[TestResult]:
        """Test system performance"""
        results = []
        
        # Test processing time
        result = await self._test_processing_time()
        results.append(result)
        
        # Test memory usage
        result = await self._test_memory_usage()
        results.append(result)
        
        return results
    
    async def _test_processing_time(self) -> TestResult:
        """Test overall processing time"""
        start_time = time.time()
        
        try:
            # Create test articles for performance test
            test_articles = [
                Article(
                    url=f"https://perf-test-{i}.example.com",
                    title=f"Performance Test Article {i}",
                    source_name="Performance Test",
                    category=ArticleCategory.TECH,
                    published_at=datetime.now() - timedelta(minutes=i),
                    importance_score=5 + (i % 5)
                )
                for i in range(20)  # Test with 20 articles
            ]
            
            # Test report generation time
            report_start = time.time()
            report_files = await self.report_generator.generate_daily_report(test_articles)
            report_time = time.time() - report_start
            
            execution_time = time.time() - start_time
            
            details = {
                "articles_processed": len(test_articles),
                "report_generation_time": report_time,
                "total_processing_time": execution_time,
                "report_time_limit": self.quality_thresholds['report_generation_time'],
                "processing_time_limit": self.quality_thresholds['processing_time_limit'],
                "reports_generated": len(report_files)
            }
            
            # Check performance thresholds
            report_within_limit = report_time <= self.quality_thresholds['report_generation_time']
            processing_within_limit = execution_time <= self.quality_thresholds['processing_time_limit']
            
            success = report_within_limit and processing_within_limit
            
            if not report_within_limit:
                details["report_time_exceeded"] = True
            if not processing_within_limit:
                details["processing_time_exceeded"] = True
            
            severity = TestSeverity.PASS if success else TestSeverity.WARNING
            
            return TestResult(
                test_name="processing_time_test",
                severity=severity,
                success=success,
                message="処理時間正常" if success else "処理時間超過",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="processing_time_test",
                severity=TestSeverity.WARNING,
                success=False,
                message=f"処理時間テスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_memory_usage(self) -> TestResult:
        """Test memory usage"""
        start_time = time.time()
        
        try:
            import psutil
            import os
            
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Get memory info before test
            memory_before = process.memory_info()
            
            # Create memory-intensive test
            test_data = []
            for i in range(100):
                article = Article(
                    url=f"https://memory-test-{i}.example.com",
                    title=f"Memory Test Article {i}" * 10,  # Make it longer
                    source_name="Memory Test Source",
                    category=ArticleCategory.TECH,
                    published_at=datetime.now(),
                    description="Memory test description " * 50,
                    importance_score=5
                )
                test_data.append(article)
            
            # Get memory info after test
            memory_after = process.memory_info()
            
            execution_time = time.time() - start_time
            
            # Calculate memory usage
            memory_diff = memory_after.rss - memory_before.rss
            memory_mb = memory_diff / (1024 * 1024)
            
            details = {
                "memory_before_mb": memory_before.rss / (1024 * 1024),
                "memory_after_mb": memory_after.rss / (1024 * 1024),
                "memory_diff_mb": memory_mb,
                "articles_created": len(test_data),
                "cpu_percent": process.cpu_percent()
            }
            
            # Memory usage should be reasonable (less than 100MB for this test)
            success = memory_mb < 100
            severity = TestSeverity.PASS if success else TestSeverity.WARNING
            
            return TestResult(
                test_name="memory_usage_test",
                severity=severity,
                success=success,
                message="メモリ使用量正常" if success else "メモリ使用量注意",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except ImportError:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="memory_usage_test",
                severity=TestSeverity.WARNING,
                success=False,
                message="psutilが利用できません",
                details={"error": "psutil module not available"},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="memory_usage_test",
                severity=TestSeverity.WARNING,
                success=False,
                message=f"メモリテスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def _test_integration(self) -> List[TestResult]:
        """Test system integration"""
        results = []
        
        # Test end-to-end workflow
        result = await self._test_end_to_end_workflow()
        results.append(result)
        
        return results
    
    async def _test_end_to_end_workflow(self) -> TestResult:
        """Test complete end-to-end workflow"""
        start_time = time.time()
        
        try:
            # Create test articles
            test_articles = [
                Article(
                    url="https://e2e-test.example.com",
                    title="End-to-End Test Article",
                    source_name="E2E Test Source",
                    category=ArticleCategory.SECURITY,
                    published_at=datetime.now(),
                    description="Test article for end-to-end workflow validation",
                    importance_score=8,
                    cvss_score=7.5
                )
            ]
            
            workflow_steps = {}
            
            # Step 1: Report generation
            try:
                report_files = await self.report_generator.generate_daily_report(test_articles)
                workflow_steps["report_generation"] = bool(report_files)
            except Exception as e:
                workflow_steps["report_generation"] = False
                workflow_steps["report_error"] = str(e)
            
            # Step 2: Emergency alert check
            try:
                alerts = await self.emergency_alert_system.check_and_send_alerts(test_articles)
                workflow_steps["emergency_check"] = True
                workflow_steps["alerts_generated"] = len(alerts)
            except Exception as e:
                workflow_steps["emergency_check"] = False
                workflow_steps["emergency_error"] = str(e)
            
            # Step 3: Database operations
            try:
                from models.database_orm import AsyncDatabase
                async with AsyncDatabase() as db:
                    saved_count = await db.save_articles_batch(test_articles)
                    workflow_steps["database_operations"] = saved_count > 0
            except Exception as e:
                workflow_steps["database_operations"] = False
                workflow_steps["database_error"] = str(e)
            
            execution_time = time.time() - start_time
            
            # Calculate success
            successful_steps = sum(1 for step, success in workflow_steps.items() 
                                 if isinstance(success, bool) and success)
            total_steps = len([v for v in workflow_steps.values() if isinstance(v, bool)])
            
            success = successful_steps >= (total_steps * 0.8)  # 80% success rate
            
            details = workflow_steps.copy()
            details.update({
                "successful_steps": successful_steps,
                "total_steps": total_steps,
                "success_rate": (successful_steps / total_steps * 100) if total_steps > 0 else 0,
                "execution_time": execution_time
            })
            
            severity = TestSeverity.PASS if success else TestSeverity.FAIL
            
            return TestResult(
                test_name="end_to_end_workflow_test",
                severity=severity,
                success=success,
                message="エンドツーエンド正常" if success else "エンドツーエンド問題",
                details=details,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name="end_to_end_workflow_test",
                severity=TestSeverity.CRITICAL,
                success=False,
                message=f"エンドツーエンドテスト失敗: {str(e)}",
                details={"error": str(e)},
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def _calculate_overall_score(self, test_results: List[TestResult]) -> float:
        """Calculate overall quality score"""
        if not test_results:
            return 0.0
        
        # Weight different test types
        weights = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4
        }
        
        total_weight = 0
        weighted_score = 0
        
        for result in test_results:
            # Determine test weight based on name and severity
            weight = 1.0
            if "connection" in result.test_name or "database" in result.test_name:
                weight = weights["critical"]
            elif "email" in result.test_name or "alert" in result.test_name:
                weight = weights["high"]
            elif "report" in result.test_name or "performance" in result.test_name:
                weight = weights["medium"]
            else:
                weight = weights["low"]
            
            # Calculate score for this test
            test_score = 100 if result.success else 0
            
            # Apply severity penalty
            if result.severity == TestSeverity.CRITICAL and not result.success:
                test_score = 0
            elif result.severity == TestSeverity.FAIL and not result.success:
                test_score = 0
            elif result.severity == TestSeverity.WARNING and not result.success:
                test_score = 30
            
            weighted_score += test_score * weight
            total_weight += weight
        
        return (weighted_score / total_weight) if total_weight > 0 else 0.0
    
    def _generate_recommendations(self, test_results: List[TestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [r for r in test_results if not r.success]
        critical_failures = [r for r in test_results if r.is_critical_failure]
        
        if critical_failures:
            recommendations.append("🚨 重大な問題が検出されました。即座の対応が必要です。")
        
        # Specific recommendations based on failed tests
        for result in failed_tests:
            if "gmail" in result.test_name:
                recommendations.append("📧 Gmail API接続を確認してください。認証情報とネットワーク接続を点検してください。")
            elif "database" in result.test_name:
                recommendations.append("🗄️ データベース接続を確認してください。ファイルアクセス権限を点検してください。")
            elif "pdf" in result.test_name:
                recommendations.append("📄 PDF生成ツール（wkhtmltopdf/WeasyPrint）をインストールしてください。")
            elif "memory" in result.test_name:
                recommendations.append("💾 メモリ使用量を監視してください。バッチサイズの調整を検討してください。")
            elif "performance" in result.test_name:
                recommendations.append("⚡ パフォーマンス最適化を検討してください。処理の並列化や最適化を実装してください。")
        
        # Performance recommendations
        slow_tests = [r for r in test_results if r.execution_time > 60]
        if slow_tests:
            recommendations.append("🏃 処理時間の最適化を検討してください。キャッシュの活用や非同期処理の改善を行ってください。")
        
        # General recommendations
        pass_rate = len([r for r in test_results if r.success]) / len(test_results) * 100
        if pass_rate < 80:
            recommendations.append("🔧 システム全体の安定性向上が必要です。エラーハンドリングとリトライ機能を強化してください。")
        elif pass_rate < 95:
            recommendations.append("✅ システムは概ね正常ですが、警告項目の改善を推奨します。")
        else:
            recommendations.append("🎉 システムは良好な状態です。定期的な監視を継続してください。")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _collect_performance_metrics(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Collect performance metrics from test results"""
        execution_times = [r.execution_time for r in test_results]
        
        metrics = {
            "total_tests": len(test_results),
            "passed_tests": len([r for r in test_results if r.success]),
            "failed_tests": len([r for r in test_results if not r.success]),
            "critical_failures": len([r for r in test_results if r.is_critical_failure]),
            "avg_execution_time": statistics.mean(execution_times) if execution_times else 0,
            "max_execution_time": max(execution_times) if execution_times else 0,
            "min_execution_time": min(execution_times) if execution_times else 0,
            "total_execution_time": sum(execution_times)
        }
        
        # Add specific test metrics
        for result in test_results:
            test_type = result.test_name.replace("_test", "")
            metrics[f"{test_type}_time"] = result.execution_time
            metrics[f"{test_type}_success"] = result.success
        
        return metrics
    
    async def _save_quality_report(self, quality_report: QualityReport):
        """Save quality report to file"""
        try:
            # Create reports directory
            reports_dir = self.config.get_storage_path('reports')
            reports_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = quality_report.generated_at.strftime('%Y%m%d_%H%M%S')
            report_file = reports_dir / f"quality_report_{timestamp}.json"
            
            # Convert to serializable format
            report_data = {
                "overall_score": quality_report.overall_score,
                "has_critical_failures": quality_report.has_critical_failures,
                "pass_rate": quality_report.pass_rate,
                "generated_at": quality_report.generated_at.isoformat(),
                "test_results": [
                    {
                        "test_name": r.test_name,
                        "severity": r.severity.value,
                        "success": r.success,
                        "message": r.message,
                        "details": r.details,
                        "execution_time": r.execution_time,
                        "timestamp": r.timestamp.isoformat()
                    }
                    for r in quality_report.test_results
                ],
                "recommendations": quality_report.recommendations,
                "performance_metrics": quality_report.performance_metrics
            }
            
            # Save to file
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Quality report saved: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save quality report: {e}")
    
    async def run_quick_test(self) -> QualityReport:
        """Run quick quality test (essential checks only)"""
        self.logger.info("Starting quick quality test")
        start_time = time.time()
        
        test_results = []
        
        try:
            # Quick essential tests
            test_results.append(await self._test_configuration())
            test_results.append(await self._test_gmail_connection())
            test_results.append(await self._test_database_connection())
            
            # Calculate results
            overall_score = self._calculate_overall_score(test_results)
            recommendations = self._generate_recommendations(test_results)
            performance_metrics = self._collect_performance_metrics(test_results)
            
            quality_report = QualityReport(
                overall_score=overall_score,
                test_results=test_results,
                recommendations=recommendations,
                performance_metrics=performance_metrics,
                generated_at=datetime.now()
            )
            
            execution_time = time.time() - start_time
            self.logger.info(f"Quick test completed in {execution_time:.2f}s. Score: {overall_score:.1f}%")
            
            return quality_report
            
        except Exception as e:
            self.logger.error(f"Quick quality test failed: {e}")
            return QualityReport(
                overall_score=0.0,
                test_results=test_results,
                recommendations=["クイックテストが失敗しました"],
                performance_metrics={},
                generated_at=datetime.now()
            )


# Global quality tester instance
_quality_tester = None


def get_quality_tester() -> DeliveryQualityTester:
    """Get global quality tester instance"""
    global _quality_tester
    if _quality_tester is None:
        _quality_tester = DeliveryQualityTester()
    return _quality_tester


# CLI interface for quality testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Delivery Quality Testing System')
    parser.add_argument('--comprehensive', action='store_true', help='Run comprehensive quality test')
    parser.add_argument('--quick', action='store_true', help='Run quick quality test')
    parser.add_argument('--output', type=str, help='Output file for report')
    
    args = parser.parse_args()
    
    async def main():
        tester = DeliveryQualityTester()
        
        if args.comprehensive:
            print("Running comprehensive quality test...")
            report = await tester.run_comprehensive_quality_test()
        else:
            print("Running quick quality test...")
            report = await tester.run_quick_test()
        
        # Display results
        print(f"\n📊 Quality Assessment Results")
        print(f"Overall Score: {report.overall_score:.1f}%")
        print(f"Pass Rate: {report.pass_rate:.1f}%")
        print(f"Tests: {len(report.test_results)} total")
        
        if report.has_critical_failures:
            print("🚨 CRITICAL FAILURES DETECTED")
        
        print(f"\n📋 Recommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({
                    "overall_score": report.overall_score,
                    "pass_rate": report.pass_rate,
                    "test_results": [r.__dict__ for r in report.test_results],
                    "recommendations": report.recommendations,
                    "performance_metrics": report.performance_metrics
                }, f, indent=2, ensure_ascii=False)
            print(f"\nReport saved to: {args.output}")
    
    asyncio.run(main())