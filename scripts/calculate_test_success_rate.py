#!/usr/bin/env python3
"""
テスト成功率とメトリクスの計算
"""
import xml.etree.ElementTree as ET
import json
import glob
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestMetricsCalculator:
    def __init__(self):
        self.metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'error_tests': 0,
            'success_rate': 0.0,
            'execution_time': 0.0,
            'test_files': [],
            'coverage': {
                'line_coverage': 0.0,
                'branch_coverage': 0.0,
                'function_coverage': 0.0
            }
        }
    
    def parse_junit_xml(self, xml_file: str) -> bool:
        """JUnit XML形式のテスト結果を解析"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            if root.tag == 'testsuites':
                # pytest-junit形式
                self.metrics['total_tests'] += int(root.get('tests', 0))
                self.metrics['failed_tests'] += int(root.get('failures', 0))
                self.metrics['error_tests'] += int(root.get('errors', 0))
                self.metrics['skipped_tests'] += int(root.get('skipped', 0))
                
                # 実行時間
                time_attr = root.get('time')
                if time_attr:
                    self.metrics['execution_time'] += float(time_attr)
                
                # 各テストスイートの詳細
                for testsuite in root.findall('testsuite'):
                    suite_name = testsuite.get('name', 'unknown')
                    suite_tests = int(testsuite.get('tests', 0))
                    suite_failures = int(testsuite.get('failures', 0))
                    suite_errors = int(testsuite.get('errors', 0))
                    suite_skipped = int(testsuite.get('skipped', 0))
                    
                    self.metrics['test_files'].append({
                        'name': suite_name,
                        'tests': suite_tests,
                        'failures': suite_failures,
                        'errors': suite_errors,
                        'skipped': suite_skipped,
                        'success_rate': ((suite_tests - suite_failures - suite_errors) / suite_tests * 100) if suite_tests > 0 else 0
                    })
                
            elif root.tag == 'testsuite':
                # 単一テストスイート形式
                self.metrics['total_tests'] += int(root.get('tests', 0))
                self.metrics['failed_tests'] += int(root.get('failures', 0))
                self.metrics['error_tests'] += int(root.get('errors', 0))
                self.metrics['skipped_tests'] += int(root.get('skipped', 0))
                
                time_attr = root.get('time')
                if time_attr:
                    self.metrics['execution_time'] += float(time_attr)
            
            logger.info(f"Parsed XML file: {xml_file}")
            return True
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML file {xml_file}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing XML file {xml_file}: {e}")
            return False
    
    def parse_coverage_xml(self, xml_file: str) -> bool:
        """カバレッジXMLファイルを解析"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            if root.tag == 'coverage':
                # line-rate（行カバレッジ）
                line_rate = float(root.get('line-rate', 0))
                self.metrics['coverage']['line_coverage'] = round(line_rate * 100, 2)
                
                # branch-rate（分岐カバレッジ）
                branch_rate = float(root.get('branch-rate', 0))
                self.metrics['coverage']['branch_coverage'] = round(branch_rate * 100, 2)
                
                # 関数カバレッジ（利用可能な場合）
                for package in root.findall('.//package'):
                    for class_elem in package.findall('classes/class'):
                        methods = class_elem.findall('methods/method')
                        if methods:
                            total_methods = len(methods)
                            covered_methods = len([m for m in methods if float(m.get('line-rate', 0)) > 0])
                            function_coverage = (covered_methods / total_methods * 100) if total_methods > 0 else 0
                            self.metrics['coverage']['function_coverage'] = max(
                                self.metrics['coverage']['function_coverage'], 
                                function_coverage
                            )
            
            logger.info(f"Parsed coverage file: {xml_file}")
            return True
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse coverage XML file {xml_file}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing coverage XML file {xml_file}: {e}")
            return False
    
    def calculate_success_rate(self):
        """成功率を計算"""
        total = self.metrics['total_tests']
        if total > 0:
            passed = total - self.metrics['failed_tests'] - self.metrics['error_tests']
            self.metrics['passed_tests'] = passed
            self.metrics['success_rate'] = round((passed / total) * 100, 2)
    
    def find_test_results(self) -> list:
        """テスト結果ファイルを検索"""
        patterns = [
            'test-results.xml',
            'pytest-results.xml',
            'junit.xml',
            '**/test-results.xml',
            '**/pytest-results.xml',
            '**/junit.xml'
        ]
        
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))
        
        return list(set(files))  # 重複除去
    
    def find_coverage_files(self) -> list:
        """カバレッジファイルを検索"""
        patterns = [
            'coverage.xml',
            '**/coverage.xml'
        ]
        
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))
        
        return list(set(files))
    
    def save_metrics(self, output_file: str = 'metrics/test-metrics.json'):
        """メトリクスをJSONファイルに保存"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2, ensure_ascii=False)
            logger.info(f"Metrics saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            return False
    
    def generate_summary_report(self) -> str:
        """サマリーレポートを生成"""
        report = f"""
# 📊 Test Metrics Summary

**Timestamp**: {self.metrics['timestamp']}

## 🧪 Test Results
- **Total Tests**: {self.metrics['total_tests']}
- **Passed**: {self.metrics['passed_tests']}
- **Failed**: {self.metrics['failed_tests']}
- **Errors**: {self.metrics['error_tests']}
- **Skipped**: {self.metrics['skipped_tests']}
- **Success Rate**: {self.metrics['success_rate']}%
- **Execution Time**: {self.metrics['execution_time']:.2f}s

## 📈 Coverage
- **Line Coverage**: {self.metrics['coverage']['line_coverage']}%
- **Branch Coverage**: {self.metrics['coverage']['branch_coverage']}%
- **Function Coverage**: {self.metrics['coverage']['function_coverage']}%

## 📁 Test Files
"""
        
        for test_file in self.metrics['test_files']:
            report += f"- **{test_file['name']}**: {test_file['success_rate']:.1f}% "
            report += f"({test_file['tests'] - test_file['failures'] - test_file['errors']}/{test_file['tests']})\n"
        
        return report
    
    def run_calculation(self):
        """メトリクス計算の実行"""
        logger.info("Starting test metrics calculation...")
        
        # テスト結果ファイルを検索・解析
        test_files = self.find_test_results()
        logger.info(f"Found test result files: {test_files}")
        
        for test_file in test_files:
            self.parse_junit_xml(test_file)
        
        # カバレッジファイルを検索・解析
        coverage_files = self.find_coverage_files()
        logger.info(f"Found coverage files: {coverage_files}")
        
        for coverage_file in coverage_files:
            self.parse_coverage_xml(coverage_file)
        
        # 成功率計算
        self.calculate_success_rate()
        
        # メトリクス保存
        self.save_metrics()
        
        # サマリーレポート生成
        report = self.generate_summary_report()
        print(report)
        
        # レポートをファイルに保存
        with open('metrics/test-summary.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        # GitHub Actions用の出力
        print(f"::set-output name=success_rate::{self.metrics['success_rate']}")
        print(f"::set-output name=total_tests::{self.metrics['total_tests']}")
        print(f"::set-output name=passed_tests::{self.metrics['passed_tests']}")
        print(f"::set-output name=coverage::{self.metrics['coverage']['line_coverage']}")
        
        logger.info("Test metrics calculation completed")

def main():
    calculator = TestMetricsCalculator()
    calculator.run_calculation()

if __name__ == "__main__":
    main()