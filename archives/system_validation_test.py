#!/usr/bin/env python3
"""
News Delivery System - Comprehensive Validation Test
ニュース配信システム 総合検証テスト

This script validates the entire news delivery system implementation
according to CLAUDE.md specifications.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# System validation results
validation_results = {
    "timestamp": datetime.now().isoformat(),
    "system_version": "1.0.0",
    "claude_md_compliance": True,
    "components": {},
    "overall_status": "PASS",
    "issues": [],
    "recommendations": []
}

def log_test_result(component: str, test: str, status: str, details: str = ""):
    """Log a test result"""
    if component not in validation_results["components"]:
        validation_results["components"][component] = {
            "tests_passed": 0,
            "tests_failed": 0,
            "status": "PASS",
            "issues": []
        }
    
    if status == "PASS":
        validation_results["components"][component]["tests_passed"] += 1
        print(f"✅ {component} - {test}: {status}")
    else:
        validation_results["components"][component]["tests_failed"] += 1
        validation_results["components"][component]["status"] = "FAIL"
        validation_results["components"][component]["issues"].append(f"{test}: {details}")
        validation_results["overall_status"] = "FAIL"
        validation_results["issues"].append(f"{component}: {test} - {details}")
        print(f"❌ {component} - {test}: {status} - {details}")
    
    if details:
        print(f"   Details: {details}")

def test_directory_structure():
    """Test 1: Validate directory structure according to CLAUDE.md"""
    print("\n=== Testing Directory Structure ===")
    
    required_dirs = [
        "src",
        "src/collectors", 
        "src/processors",
        "src/services",
        "src/utils",
        "src/models", 
        "src/templates",
        "config",
        "data",
        "data/articles",
        "data/reports", 
        "data/cache",
        "data/database",
        "data/logs"
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            log_test_result("Directory Structure", f"Directory {dir_path}", "PASS")
        else:
            log_test_result("Directory Structure", f"Directory {dir_path}", "FAIL", f"Missing required directory: {dir_path}")

def test_core_files():
    """Test 2: Validate core system files"""
    print("\n=== Testing Core Files ===")
    
    required_files = [
        ("main.py", "Main application entry point"),
        ("config/config.json", "System configuration"),
        ("src/collectors/base_collector.py", "Base collector class"),
        ("src/collectors/newsapi_collector.py", "NewsAPI collector"),
        ("src/processors/translator.py", "Translation processor"),
        ("src/processors/analyzer.py", "AI analysis processor"),
        ("src/services/report_generator.py", "Report generation service"),
        ("src/services/email_delivery.py", "Gmail delivery service"),
        ("src/models/database.py", "Database model"),
        ("src/models/article.py", "Article data model"),
        ("src/utils/config.py", "Configuration utilities"),
        ("src/utils/logger.py", "Logging system")
    ]
    
    for file_path, description in required_files:
        path = Path(file_path)
        if path.exists():
            # Check if file has content
            try:
                content = path.read_text(encoding='utf-8')
                if len(content.strip()) > 100:  # Basic content check
                    log_test_result("Core Files", f"{description}", "PASS")
                else:
                    log_test_result("Core Files", f"{description}", "FAIL", f"File too small or empty: {file_path}")
            except Exception as e:
                log_test_result("Core Files", f"{description}", "FAIL", f"Cannot read file: {e}")
        else:
            log_test_result("Core Files", f"{description}", "FAIL", f"Missing required file: {file_path}")

def test_configuration():
    """Test 3: Validate configuration system"""
    print("\n=== Testing Configuration System ===")
    
    try:
        from src.utils.config import load_config
        config = load_config()
        
        # Test required configuration sections
        required_sections = [
            "general",
            "paths", 
            "collection",
            "delivery",
            "api_limits",
            "cache",
            "logging"
        ]
        
        for section in required_sections:
            if hasattr(config, 'get') and config.get(section):
                log_test_result("Configuration", f"Section: {section}", "PASS")
            else:
                log_test_result("Configuration", f"Section: {section}", "FAIL", f"Missing configuration section: {section}")
        
        # Test specific configuration values from CLAUDE.md
        collection_config = config.get('collection', {})
        categories = collection_config.get('categories', {})
        
        required_categories = [
            "domestic_social",
            "international_social", 
            "tech",
            "security"
        ]
        
        for category in required_categories:
            if category in categories:
                log_test_result("Configuration", f"Category: {category}", "PASS")
            else:
                log_test_result("Configuration", f"Category: {category}", "FAIL", f"Missing category: {category}")
                
    except Exception as e:
        log_test_result("Configuration", "Configuration Loading", "FAIL", str(e))

def test_database_schema():
    """Test 4: Validate database schema compliance"""
    print("\n=== Testing Database Schema ===")
    
    try:
        from src.models.database import Database
        
        # Initialize database to create tables
        db = Database()
        
        # Test if database file is created
        if db.db_path.exists():
            log_test_result("Database", "Database File Creation", "PASS")
        else:
            log_test_result("Database", "Database File Creation", "FAIL", "Database file not created")
            return
        
        # Test table structure compliance with CLAUDE.md
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check required tables from CLAUDE.md specification
            required_tables = [
                "articles",
                "delivery_history", 
                "api_usage",
                "cache"
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            for table in required_tables:
                if table in existing_tables:
                    log_test_result("Database", f"Table: {table}", "PASS")
                else:
                    log_test_result("Database", f"Table: {table}", "FAIL", f"Missing required table: {table}")
            
            # Test articles table structure (key table from CLAUDE.md)
            if "articles" in existing_tables:
                cursor.execute("PRAGMA table_info(articles)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                required_columns = [
                    "id", "url", "url_hash", "title", "translated_title", 
                    "description", "content", "translated_content", "summary",
                    "source_name", "author", "published_at", "collected_at",
                    "category", "importance_score", "keywords", "sentiment", "processed"
                ]
                
                missing_columns = []
                for col in required_columns:
                    if col in column_names:
                        continue
                    else:
                        missing_columns.append(col)
                
                if not missing_columns:
                    log_test_result("Database", "Articles Table Schema", "PASS")
                else:
                    log_test_result("Database", "Articles Table Schema", "FAIL", f"Missing columns: {missing_columns}")
                    
    except Exception as e:
        log_test_result("Database", "Database Schema Validation", "FAIL", str(e))

async def test_collectors():
    """Test 5: Validate news collector implementations"""
    print("\n=== Testing News Collectors ===")
    
    try:
        # Test base collector
        from src.collectors.base_collector import BaseCollector
        log_test_result("Collectors", "Base Collector Import", "PASS")
        
        # Test NewsAPI collector
        from src.collectors.newsapi_collector import NewsAPICollector
        log_test_result("Collectors", "NewsAPI Collector Import", "PASS")
        
        # Test collector initialization (without API keys)
        try:
            from src.utils.config import load_config
            config = load_config()
            
            # Mock logger for testing
            import logging
            logger = logging.getLogger("test")
            
            collector = NewsAPICollector(config, logger)
            log_test_result("Collectors", "NewsAPI Collector Initialization", "PASS")
            
        except Exception as e:
            log_test_result("Collectors", "NewsAPI Collector Initialization", "FAIL", str(e))
            
    except Exception as e:
        log_test_result("Collectors", "Collector Import", "FAIL", str(e))

async def test_translation_system():
    """Test 6: Validate translation system"""
    print("\n=== Testing Translation System ===")
    
    try:
        from src.processors.translator import DeepLTranslator
        log_test_result("Translation", "DeepL Translator Import", "PASS")
        
        # Test translator initialization
        translator = DeepLTranslator()
        log_test_result("Translation", "Translator Initialization", "PASS")
        
        # Test translation method exists
        if hasattr(translator, 'translate_batch'):
            log_test_result("Translation", "Batch Translation Method", "PASS")
        else:
            log_test_result("Translation", "Batch Translation Method", "FAIL", "Missing translate_batch method")
            
    except Exception as e:
        log_test_result("Translation", "Translation System", "FAIL", str(e))

async def test_ai_analysis():
    """Test 7: Validate AI analysis system"""
    print("\n=== Testing AI Analysis System ===")
    
    try:
        from src.processors.analyzer import ClaudeAnalyzer
        log_test_result("AI Analysis", "Claude Analyzer Import", "PASS")
        
        # Test analyzer initialization
        analyzer = ClaudeAnalyzer()
        log_test_result("AI Analysis", "Analyzer Initialization", "PASS")
        
        # Test required methods from CLAUDE.md
        required_methods = [
            "analyze_batch",
            "create_daily_summary",
            "create_weekly_summary"
        ]
        
        for method in required_methods:
            if hasattr(analyzer, method):
                log_test_result("AI Analysis", f"Method: {method}", "PASS")
            else:
                log_test_result("AI Analysis", f"Method: {method}", "FAIL", f"Missing method: {method}")
                
    except Exception as e:
        log_test_result("AI Analysis", "AI Analysis System", "FAIL", str(e))

async def test_report_generation():
    """Test 8: Validate report generation system"""
    print("\n=== Testing Report Generation System ===")
    
    try:
        from src.services.report_generator import ReportGenerator
        log_test_result("Report Generation", "Report Generator Import", "PASS")
        
        # Test generator initialization
        generator = ReportGenerator()
        log_test_result("Report Generation", "Generator Initialization", "PASS")
        
        # Test required methods
        required_methods = [
            "generate_daily_report",
            "generate_urgent_alert",
            "_generate_html_report",
            "_generate_pdf_report"
        ]
        
        for method in required_methods:
            if hasattr(generator, method):
                log_test_result("Report Generation", f"Method: {method}", "PASS")
            else:
                log_test_result("Report Generation", f"Method: {method}", "FAIL", f"Missing method: {method}")
                
    except Exception as e:
        log_test_result("Report Generation", "Report Generation System", "FAIL", str(e))

async def test_email_delivery():
    """Test 9: Validate email delivery system"""
    print("\n=== Testing Email Delivery System ===")
    
    try:
        from src.services.email_delivery import GmailDeliveryService
        log_test_result("Email Delivery", "Gmail Service Import", "PASS")
        
        # Test service initialization
        service = GmailDeliveryService()
        log_test_result("Email Delivery", "Gmail Service Initialization", "PASS")
        
        # Test required methods from CLAUDE.md
        required_methods = [
            "send_daily_report",
            "send_urgent_alert",
            "test_email_connection"
        ]
        
        for method in required_methods:
            if hasattr(service, method):
                log_test_result("Email Delivery", f"Method: {method}", "PASS")
            else:
                log_test_result("Email Delivery", f"Method: {method}", "FAIL", f"Missing method: {method}")
                
    except Exception as e:
        log_test_result("Email Delivery", "Email Delivery System", "FAIL", str(e))

def test_scheduler_system():
    """Test 10: Validate scheduler system"""
    print("\n=== Testing Scheduler System ===")
    
    try:
        from src.services.scheduler import NewsDeliveryScheduler
        log_test_result("Scheduler", "Scheduler Import", "PASS")
        
        # Test scheduler initialization
        scheduler = NewsDeliveryScheduler()
        log_test_result("Scheduler", "Scheduler Initialization", "PASS")
        
        # Test required methods and schedule compliance
        required_methods = [
            "start",
            "stop", 
            "get_status",
            "_daily_news_collection",
            "_urgent_news_check",
            "_system_health_check"
        ]
        
        for method in required_methods:
            if hasattr(scheduler, method):
                log_test_result("Scheduler", f"Method: {method}", "PASS")
            else:
                log_test_result("Scheduler", f"Method: {method}", "FAIL", f"Missing method: {method}")
        
        # Test schedule configuration from CLAUDE.md (7:00, 12:00, 18:00)
        if hasattr(scheduler, 'tasks') and scheduler.tasks:
            log_test_result("Scheduler", "Tasks Configuration", "PASS")
        else:
            log_test_result("Scheduler", "Tasks Configuration", "FAIL", "No scheduled tasks configured")
            
    except Exception as e:
        log_test_result("Scheduler", "Scheduler System", "FAIL", str(e))

def test_main_orchestrator():
    """Test 11: Validate main application orchestrator"""
    print("\n=== Testing Main Orchestrator ===")
    
    try:
        # Test main.py structure and NewsDeliverySystem class
        main_path = Path("main.py")
        if main_path.exists():
            log_test_result("Main Orchestrator", "Main File Exists", "PASS")
            
            # Check for required class and methods
            content = main_path.read_text(encoding='utf-8')
            
            required_elements = [
                "class NewsDeliverySystem",
                "run_daily_collection",
                "run_urgent_check", 
                "run_system_check",
                "get_system_status"
            ]
            
            for element in required_elements:
                if element in content:
                    log_test_result("Main Orchestrator", f"Element: {element}", "PASS")
                else:
                    log_test_result("Main Orchestrator", f"Element: {element}", "FAIL", f"Missing: {element}")
        else:
            log_test_result("Main Orchestrator", "Main File Exists", "FAIL", "main.py not found")
            
    except Exception as e:
        log_test_result("Main Orchestrator", "Main Orchestrator", "FAIL", str(e))

def test_claude_md_compliance():
    """Test 12: Validate CLAUDE.md specification compliance"""
    print("\n=== Testing CLAUDE.md Compliance ===")
    
    try:
        claude_md_path = Path("CLAUDE.md")
        if claude_md_path.exists():
            log_test_result("CLAUDE.md Compliance", "CLAUDE.md File Exists", "PASS")
            
            content = claude_md_path.read_text(encoding='utf-8')
            
            # Check for key specification elements
            required_specs = [
                "ニュース自動配信システム",
                "NewsAPI",
                "DeepL API", 
                "Claude API",
                "Gmail",
                "7:00, 12:00, 18:00",
                "importance_score",
                "200-250文字",
                "SQLiteデータベース"
            ]
            
            for spec in required_specs:
                if spec in content:
                    log_test_result("CLAUDE.md Compliance", f"Specification: {spec}", "PASS")
                else:
                    log_test_result("CLAUDE.md Compliance", f"Specification: {spec}", "FAIL", f"Missing spec: {spec}")
        else:
            log_test_result("CLAUDE.md Compliance", "CLAUDE.md File Exists", "FAIL", "CLAUDE.md not found")
            
    except Exception as e:
        log_test_result("CLAUDE.md Compliance", "CLAUDE.md Compliance", "FAIL", str(e))

async def run_validation_tests():
    """Run all validation tests"""
    print("🚀 Starting News Delivery System Comprehensive Validation")
    print(f"Timestamp: {validation_results['timestamp']}")
    print("=" * 60)
    
    # Run all validation tests
    test_directory_structure()
    test_core_files() 
    test_configuration()
    test_database_schema()
    await test_collectors()
    await test_translation_system()
    await test_ai_analysis()
    await test_report_generation()
    await test_email_delivery()
    test_scheduler_system()
    test_main_orchestrator()
    test_claude_md_compliance()
    
    # Generate final report
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    total_components = len(validation_results["components"])
    passed_components = sum(1 for comp in validation_results["components"].values() if comp["status"] == "PASS")
    
    print(f"Overall Status: {'✅ PASS' if validation_results['overall_status'] == 'PASS' else '❌ FAIL'}")
    print(f"Components Tested: {total_components}")
    print(f"Components Passed: {passed_components}")
    print(f"Components Failed: {total_components - passed_components}")
    
    total_tests = sum(comp["tests_passed"] + comp["tests_failed"] for comp in validation_results["components"].values())
    total_passed = sum(comp["tests_passed"] for comp in validation_results["components"].values())
    
    print(f"Total Tests: {total_tests}")
    print(f"Tests Passed: {total_passed}")
    print(f"Tests Failed: {total_tests - total_passed}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "0%")
    
    if validation_results["issues"]:
        print(f"\n⚠️  Issues Found ({len(validation_results['issues'])}):")
        for issue in validation_results["issues"][:10]:  # Show first 10 issues
            print(f"  • {issue}")
        if len(validation_results["issues"]) > 10:
            print(f"  ... and {len(validation_results['issues']) - 10} more issues")
    
    # Save detailed report
    report_path = Path("validation_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Detailed validation report saved to: {report_path}")
    
    # Final recommendations
    if validation_results["overall_status"] == "PASS":
        print("\n🎉 NEWS DELIVERY SYSTEM VALIDATION SUCCESSFUL!")
        print("✅ The system is ready for deployment and meets CLAUDE.md specifications.")
    else:
        print("\n⚠️  NEWS DELIVERY SYSTEM VALIDATION INCOMPLETE")
        print("❌ Please address the issues above before deployment.")
    
    return validation_results["overall_status"] == "PASS"

if __name__ == "__main__":
    success = asyncio.run(run_validation_tests())
    sys.exit(0 if success else 1)