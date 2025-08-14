#!/usr/bin/env python3
"""
Comprehensive Email Delivery Testing System
本格的なメール配信テスト
"""

import asyncio
import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import asdict

# Change to parent directory and add to path
root_dir = Path(__file__).parent.parent
os.chdir(root_dir)
sys.path.insert(0, str(root_dir))

from src.services.email_delivery import GmailDeliveryService
from src.services.news_collector import NewsCollector
from src.services.report_generator import ReportGenerator
from src.models.article import Article, ArticleCategory, ArticleLanguage, DeliveryRecord
from src.utils.logger import setup_logger


class EmailDeliveryTester:
    """Comprehensive email delivery testing system"""
    
    def __init__(self):
        self.logger = setup_logger('email_delivery_tester')
        self.email_service = GmailDeliveryService()
        self.news_collector = NewsCollector()
        self.report_generator = ReportGenerator()
        
        # Test results
        self.test_results = []
        
    def create_test_articles(self) -> List[Article]:
        """Create sample articles for testing"""
        
        test_articles = [
            Article(
                title="Critical Security Vulnerability Discovered in Popular Framework",
                content="A critical security vulnerability with CVSS score 9.8 has been discovered...",
                url="https://example.com/security-alert-1",
                source="Test Security News",
                category=ArticleCategory.SECURITY,
                language=ArticleLanguage.ENGLISH,
                published_at=datetime.now() - timedelta(hours=2),
                cvss_score=9.8,
                cve_id="CVE-2024-12345",
                importance_score=10,
                is_urgent=True
            ),
            Article(
                title="AI技術の最新動向：次世代AIの可能性",
                content="人工知能技術の急速な発展により、次世代AIシステムの実用化が進んでいます...",
                url="https://example.com/ai-news-1",
                source="テクノロジーニュース",
                category=ArticleCategory.TECH,
                language=ArticleLanguage.JAPANESE,
                published_at=datetime.now() - timedelta(hours=1),
                importance_score=8
            ),
            Article(
                title="Global Economic Outlook: Market Analysis",
                content="International market analysis shows significant trends in global economics...",
                url="https://example.com/economy-news-1",
                source="Economic Times",
                category=ArticleCategory.INTERNATIONAL_ECONOMY,
                language=ArticleLanguage.ENGLISH,
                published_at=datetime.now() - timedelta(minutes=30),
                importance_score=7
            ),
            Article(
                title="国内経済政策の新たな展開",
                content="政府による新しい経済政策が発表され、国内経済への影響が注目されています...",
                url="https://example.com/domestic-economy-1",
                source="経済新聞",
                category=ArticleCategory.DOMESTIC_ECONOMY,
                language=ArticleLanguage.JAPANESE,
                published_at=datetime.now() - timedelta(minutes=15),
                importance_score=6
            ),
            Article(
                title="Breaking: International Diplomatic Development",
                content="Urgent diplomatic news with significant international implications...",
                url="https://example.com/breaking-news-1",
                source="International News",
                category=ArticleCategory.INTERNATIONAL_SOCIAL,
                language=ArticleLanguage.ENGLISH,
                published_at=datetime.now() - timedelta(minutes=5),
                importance_score=9,
                is_urgent=True
            )
        ]
        
        return test_articles
    
    async def test_daily_report_delivery(self) -> Dict[str, Any]:
        """Test daily report email delivery"""
        
        self.logger.info("Testing daily report delivery...")
        
        try:
            # Create test articles
            articles = self.create_test_articles()
            
            # Generate report files
            report_files = await self.report_generator.generate_daily_report(articles)
            
            # Count urgent articles
            urgent_count = sum(1 for article in articles if article.is_urgent)
            
            # Send daily report
            delivery_record = await self.email_service.send_daily_report(
                report_files, len(articles), urgent_count
            )
            
            result = {
                "test_name": "Daily Report Delivery",
                "status": "success",
                "delivery_record": asdict(delivery_record),
                "articles_count": len(articles),
                "urgent_count": urgent_count,
                "report_files": report_files,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info("Daily report delivery test completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Daily report delivery test failed: {e}")
            return {
                "test_name": "Daily Report Delivery",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_urgent_alert_delivery(self) -> Dict[str, Any]:
        """Test urgent alert email delivery"""
        
        self.logger.info("Testing urgent alert delivery...")
        
        try:
            # Create urgent articles only
            articles = self.create_test_articles()
            urgent_articles = [article for article in articles if article.is_urgent]
            
            # Generate urgent report
            report_files = await self.report_generator.generate_urgent_report(urgent_articles)
            
            # Send urgent alert
            delivery_record = await self.email_service.send_urgent_alert(
                report_files, len(urgent_articles)
            )
            
            result = {
                "test_name": "Urgent Alert Delivery",
                "status": "success",
                "delivery_record": asdict(delivery_record),
                "urgent_articles_count": len(urgent_articles),
                "report_files": report_files,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info("Urgent alert delivery test completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Urgent alert delivery test failed: {e}")
            return {
                "test_name": "Urgent Alert Delivery",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_custom_report_delivery(self) -> Dict[str, Any]:
        """Test custom report delivery"""
        
        self.logger.info("Testing custom report delivery...")
        
        try:
            # Create temporary report files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create HTML report
                html_file = temp_path / "test_report.html"
                html_content = """
                <!DOCTYPE html>
                <html>
                <head><title>Test Report</title></head>
                <body>
                    <h1>Custom Test Report</h1>
                    <p>This is a test report for email delivery validation.</p>
                    <p>Generated at: {}</p>
                </body>
                </html>
                """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                html_file.write_text(html_content, encoding='utf-8')
                
                # Create text report
                txt_file = temp_path / "test_report.txt"
                txt_content = f"""
                Custom Test Report
                ==================
                
                Test Description: Email delivery validation
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                This is a test report to validate email attachment functionality.
                """
                txt_file.write_text(txt_content)
                
                report_files = {
                    "html": str(html_file),
                    "text": str(txt_file)
                }
                
                # Send custom report
                delivery_record = await self.email_service.send_report(
                    report_files=report_files,
                    subject="Custom Test Report - Email Delivery Validation",
                    delivery_type="test"
                )
                
                result = {
                    "test_name": "Custom Report Delivery",
                    "status": "success",
                    "delivery_record": asdict(delivery_record),
                    "report_files": report_files,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.logger.info("Custom report delivery test completed successfully")
                return result
                
        except Exception as e:
            self.logger.error(f"Custom report delivery test failed: {e}")
            return {
                "test_name": "Custom Report Delivery",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def test_gmail_connection(self) -> Dict[str, Any]:
        """Test Gmail API connection"""
        
        self.logger.info("Testing Gmail API connection...")
        
        try:
            connection_ok = self.email_service.test_email_connection()
            quota_info = self.email_service.get_quota_info()
            
            result = {
                "test_name": "Gmail Connection Test",
                "status": "success" if connection_ok else "failed",
                "connection_ok": connection_ok,
                "quota_info": quota_info,
                "timestamp": datetime.now().isoformat()
            }
            
            if connection_ok:
                self.logger.info("Gmail connection test passed")
            else:
                self.logger.warning("Gmail connection test failed")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {e}")
            return {
                "test_name": "Gmail Connection Test",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_live_news_collection_and_delivery(self) -> Dict[str, Any]:
        """Test with live news collection and delivery"""
        
        self.logger.info("Testing live news collection and delivery...")
        
        try:
            # Collect live news
            articles = await self.news_collector.collect_all_news()
            
            if not articles:
                return {
                    "test_name": "Live News Collection and Delivery",
                    "status": "skipped",
                    "reason": "No articles collected",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Limit to first 5 articles for testing
            test_articles = articles[:5]
            
            # Generate report
            report_files = await self.report_generator.generate_daily_report(test_articles)
            
            # Send email
            urgent_count = sum(1 for article in test_articles if getattr(article, 'is_urgent', False))
            
            delivery_record = await self.email_service.send_daily_report(
                report_files, len(test_articles), urgent_count
            )
            
            result = {
                "test_name": "Live News Collection and Delivery",
                "status": "success",
                "delivery_record": asdict(delivery_record),
                "total_articles_collected": len(articles),
                "test_articles_sent": len(test_articles),
                "urgent_count": urgent_count,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Live news test completed: {len(test_articles)} articles sent")
            return result
            
        except Exception as e:
            self.logger.error(f"Live news collection and delivery test failed: {e}")
            return {
                "test_name": "Live News Collection and Delivery",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all email delivery tests"""
        
        print("=" * 80)
        print("📧 Comprehensive Email Delivery Testing")
        print("=" * 80)
        print(f"🕐 Test start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        tests = [
            ("Gmail Connection", self.test_gmail_connection),
            ("Daily Report Delivery", self.test_daily_report_delivery),
            ("Urgent Alert Delivery", self.test_urgent_alert_delivery),
            ("Custom Report Delivery", self.test_custom_report_delivery),
            ("Live News Collection and Delivery", self.test_live_news_collection_and_delivery)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"🧪 Running test: {test_name}")
            
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                results.append(result)
                
                status_icon = "✅" if result["status"] == "success" else "❌" if result["status"] == "failed" else "⏭️"
                print(f"{status_icon} {test_name}: {result['status'].upper()}")
                
                if result["status"] == "failed" and "error" in result:
                    print(f"   💥 Error: {result['error']}")
                
            except Exception as e:
                error_result = {
                    "test_name": test_name,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                results.append(error_result)
                print(f"💥 {test_name}: ERROR - {e}")
            
            print()
        
        # Summary
        successful_tests = sum(1 for r in results if r["status"] == "success")
        failed_tests = sum(1 for r in results if r["status"] == "failed")
        error_tests = sum(1 for r in results if r["status"] == "error")
        skipped_tests = sum(1 for r in results if r["status"] == "skipped")
        
        print("=" * 80)
        print("📊 Test Summary")
        print("=" * 80)
        print(f"✅ Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💥 Errors: {error_tests}")
        print(f"⏭️ Skipped: {skipped_tests}")
        print(f"📊 Total: {len(results)}")
        print()
        
        if successful_tests == len(results):
            print("🎉 All tests passed! Email delivery system is working correctly.")
        elif successful_tests >= len(results) * 0.8:
            print("⚠️  Most tests passed. Some issues need attention.")
        else:
            print("❌ Multiple tests failed. Email delivery system needs investigation.")
        
        print("=" * 80)
        
        # Save detailed results
        self.save_test_results(results)
        
        return results
    
    def save_test_results(self, results: List[Dict[str, Any]]):
        """Save test results to file"""
        
        try:
            # Create reports directory if it doesn't exist
            reports_dir = Path('reports')
            reports_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = reports_dir / f'email_delivery_test_results_{timestamp}.json'
            
            # Prepare detailed results
            detailed_results = {
                "test_session": {
                    "start_time": datetime.now().isoformat(),
                    "total_tests": len(results),
                    "successful": sum(1 for r in results if r["status"] == "success"),
                    "failed": sum(1 for r in results if r["status"] == "failed"),
                    "errors": sum(1 for r in results if r["status"] == "error"),
                    "skipped": sum(1 for r in results if r["status"] == "skipped")
                },
                "test_results": results,
                "system_info": {
                    "email_service_available": self.email_service.service is not None,
                    "configured_recipients": len(self.email_service.recipients),
                    "sender_email": self.email_service.sender_email
                }
            }
            
            # Save to file
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_results, f, indent=2, ensure_ascii=False)
            
            print(f"📄 Detailed test results saved to: {results_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save test results: {e}")


async def main():
    """Main testing function"""
    
    # Initialize tester
    tester = EmailDeliveryTester()
    
    # Run all tests
    results = await tester.run_all_tests()
    
    # Return exit code based on results
    successful_tests = sum(1 for r in results if r["status"] == "success")
    if successful_tests == len(results):
        return 0  # All tests passed
    elif successful_tests >= len(results) * 0.8:
        return 1  # Most tests passed
    else:
        return 2  # Many tests failed


if __name__ == "__main__":
    exit(asyncio.run(main()))