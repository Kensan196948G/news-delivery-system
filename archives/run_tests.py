#!/usr/bin/env python3
"""
Enhanced Test Runner for News Delivery System
テスト自動実行システム - NEWS-Testerエージェント実装

Features:
- Pytest integration with async support
- Coverage reporting  
- Performance testing
- API testing
- Parallel execution
- Detailed reporting
"""

import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsTestRunner:
    """Advanced test runner for news delivery system"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def run_unit_tests(self, verbose: bool = True, coverage: bool = True) -> Dict[str, Any]:
        """Run unit tests with coverage"""
        logger.info("🔧 Running unit tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-m", "unit",
            "--tb=short",
            "-v" if verbose else "-q"
        ]
        
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/unit"
            ])
        
        result = self._execute_pytest(cmd, "unit_tests")
        return result
    
    def run_integration_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run integration tests"""
        logger.info("🔗 Running integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-m", "integration",
            "--tb=short",
            "-v" if verbose else "-q"
        ]
        
        result = self._execute_pytest(cmd, "integration_tests")
        return result
    
    def run_api_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run API endpoint tests"""
        logger.info("🌐 Running API tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-m", "api",
            "--tb=short",
            "-v" if verbose else "-q"
        ]
        
        result = self._execute_pytest(cmd, "api_tests")
        return result
    
    def run_performance_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run performance and benchmark tests"""
        logger.info("⚡ Running performance tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-m", "performance",
            "--tb=short",
            "--benchmark-only",
            "--benchmark-sort=mean",
            "-v" if verbose else "-q"
        ]
        
        result = self._execute_pytest(cmd, "performance_tests")
        return result
    
    def run_all_tests(self, 
                     parallel: bool = False, 
                     coverage: bool = True,
                     verbose: bool = True) -> Dict[str, Any]:
        """Run all tests with comprehensive reporting"""
        logger.info("🚀 Running comprehensive test suite...")
        self.start_time = datetime.now()
        
        cmd = [sys.executable, "-m", "pytest"]
        
        if parallel:
            # Use pytest-xdist for parallel execution
            cmd.extend(["-n", "auto"])
        
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing", 
                "--cov-report=html:htmlcov",
                "--cov-report=xml"
            ])
        
        cmd.extend([
            "--tb=short",
            "--durations=10",
            "-v" if verbose else "-q",
            "--json-report",
            f"--json-report-file={self.project_root}/test_results.json"
        ])
        
        result = self._execute_pytest(cmd, "all_tests")
        self.end_time = datetime.now()
        
        # Generate comprehensive report
        self._generate_comprehensive_report()
        
        return result
    
    def run_specific_tests(self, 
                          test_pattern: str, 
                          markers: List[str] = None,
                          verbose: bool = True) -> Dict[str, Any]:
        """Run tests matching specific pattern or markers"""
        logger.info(f"🎯 Running specific tests: {test_pattern}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_pattern,
            "--tb=short",
            "-v" if verbose else "-q"
        ]
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        result = self._execute_pytest(cmd, f"specific_tests_{test_pattern}")
        return result
    
    def _execute_pytest(self, cmd: List[str], test_type: str) -> Dict[str, Any]:
        """Execute pytest command and capture results"""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            test_result = {
                "test_type": test_type,
                "command": " ".join(cmd),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "success": result.returncode == 0,
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results[test_type] = test_result
            
            if result.returncode == 0:
                logger.info(f"✅ {test_type} completed successfully in {execution_time:.2f}s")
            else:
                logger.error(f"❌ {test_type} failed with return code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {test_type} timed out after 10 minutes")
            return {
                "test_type": test_type,
                "success": False,
                "error": "Timeout",
                "execution_time": 600,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"💥 {test_type} failed with exception: {e}")
            return {
                "test_type": test_type,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_comprehensive_report(self):
        """Generate detailed test execution report"""
        logger.info("📊 Generating comprehensive test report...")
        
        total_execution_time = 0
        successful_tests = 0
        failed_tests = 0
        
        for test_type, result in self.test_results.items():
            total_execution_time += result.get("execution_time", 0)
            if result.get("success", False):
                successful_tests += 1
            else:
                failed_tests += 1
        
        report = {
            "test_execution_summary": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "total_execution_time": total_execution_time,
                "total_test_suites": len(self.test_results),
                "successful_test_suites": successful_tests,
                "failed_test_suites": failed_tests,
                "overall_success_rate": successful_tests / len(self.test_results) * 100 if self.test_results else 0
            },
            "test_results_detail": self.test_results,
            "system_info": {
                "python_version": sys.version,
                "project_root": str(self.project_root),
                "test_runner_version": "1.0.0"
            },
            "coverage_info": self._extract_coverage_info(),
            "performance_metrics": self._extract_performance_metrics()
        }
        
        # Save comprehensive report
        report_path = self.project_root / "test_execution_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Comprehensive report saved: {report_path}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("🎯 TEST EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Total execution time: {total_execution_time:.2f}s")
        print(f"Test suites run: {len(self.test_results)}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {successful_tests / len(self.test_results) * 100:.1f}%" if self.test_results else "No tests run")
        print("=" * 80)
        
        return report
    
    def _extract_coverage_info(self) -> Dict[str, Any]:
        """Extract coverage information from reports"""
        coverage_info = {"status": "not_available"}
        
        coverage_xml = self.project_root / "coverage.xml"
        if coverage_xml.exists():
            coverage_info["xml_report"] = str(coverage_xml)
        
        htmlcov_dir = self.project_root / "htmlcov"
        if htmlcov_dir.exists():
            coverage_info["html_report"] = str(htmlcov_dir)
        
        return coverage_info
    
    def _extract_performance_metrics(self) -> Dict[str, Any]:
        """Extract performance testing metrics"""
        # Look for benchmark results
        benchmark_results = {}
        
        # This would be populated by pytest-benchmark
        # For now, return placeholder
        return {
            "benchmark_results": benchmark_results,
            "performance_tests_run": "performance" in self.test_results
        }
    
    def install_test_dependencies(self) -> bool:
        """Install testing dependencies"""
        logger.info("📦 Installing test dependencies...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "-r", str(self.project_root / "requirements-test.txt")
            ], check=True, capture_output=True, text=True)
            
            logger.info("✅ Test dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install test dependencies: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Perform system health check before tests"""
        logger.info("🏥 Performing system health check...")
        
        health_status = {
            "python_version": sys.version_info[:2],
            "project_structure": self._check_project_structure(),
            "dependencies": self._check_dependencies(),
            "configuration": self._check_configuration()
        }
        
        all_healthy = all([
            health_status["project_structure"],
            health_status["dependencies"],
            health_status["configuration"]
        ])
        
        health_status["overall_health"] = all_healthy
        
        if all_healthy:
            logger.info("✅ System health check passed")
        else:
            logger.warning("⚠️ System health check found issues")
        
        return health_status
    
    def _check_project_structure(self) -> bool:
        """Check if required project structure exists"""
        required_paths = [
            "src",
            "tests", 
            "config",
            "requirements.txt",
            "pytest.ini"
        ]
        
        for path in required_paths:
            if not (self.project_root / path).exists():
                logger.warning(f"Missing required path: {path}")
                return False
        
        return True
    
    def _check_dependencies(self) -> bool:
        """Check if core dependencies are available"""
        required_modules = [
            "pytest",
            "pytest_asyncio",
            "aiohttp",
            "anthropic"
        ]
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                logger.warning(f"Missing required module: {module}")
                return False
        
        return True
    
    def _check_configuration(self) -> bool:
        """Check if configuration is properly set up"""
        config_file = self.project_root / "config" / "config.json"
        return config_file.exists()


def main():
    """Main CLI interface for test runner"""
    parser = argparse.ArgumentParser(description="News Delivery System Test Runner")
    
    parser.add_argument("--type", choices=["unit", "integration", "api", "performance", "all"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--pattern", type=str, help="Specific test pattern to run")
    parser.add_argument("--markers", nargs="+", help="Test markers to filter by")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies first")
    parser.add_argument("--health-check", action="store_true", help="Perform health check only")
    
    args = parser.parse_args()
    
    runner = NewsTestRunner()
    
    # Install dependencies if requested
    if args.install_deps:
        if not runner.install_test_dependencies():
            sys.exit(1)
    
    # Health check
    if args.health_check:
        health = runner.health_check()
        print(json.dumps(health, indent=2))
        sys.exit(0 if health["overall_health"] else 1)
    
    # Run health check before tests
    health = runner.health_check()
    if not health["overall_health"]:
        logger.error("❌ Health check failed. Fix issues before running tests.")
        sys.exit(1)
    
    # Run tests based on type
    verbose = not args.quiet
    coverage = not args.no_coverage
    
    if args.pattern:
        result = runner.run_specific_tests(args.pattern, args.markers, verbose)
    elif args.type == "unit":
        result = runner.run_unit_tests(verbose, coverage)
    elif args.type == "integration":
        result = runner.run_integration_tests(verbose)
    elif args.type == "api":
        result = runner.run_api_tests(verbose)
    elif args.type == "performance":
        result = runner.run_performance_tests(verbose)
    else:  # all
        result = runner.run_all_tests(args.parallel, coverage, verbose)
    
    # Exit with appropriate code
    success = result.get("success", False) if isinstance(result, dict) else False
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()