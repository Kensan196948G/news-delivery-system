#!/usr/bin/env python3
"""
自動修復機能のテストスクリプト
意図的にコード品質の問題を作成し、自動修復をテストする
"""
import tempfile
import subprocess
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoRepairTester:
    def __init__(self):
        self.test_files = []
        self.temp_dir = None
    
    def setup_test_environment(self):
        """テスト環境のセットアップ"""
        self.temp_dir = tempfile.mkdtemp(prefix="auto_repair_test_")
        logger.info(f"Test environment created: {self.temp_dir}")
        return self.temp_dir
    
    def create_problematic_code(self):
        """問題のあるコードサンプルを作成"""
        problems = []
        
        # 1. Import順序の問題
        import_problem = """import os
import sys
import json
import asyncio
import aiohttp
import requests
"""
        
        # 2. コードフォーマットの問題
        format_problem = """
def bad_function(x,y,z):
    if x>0:
        result=x+y*z
        return result
    else:
        return None

class BadClass:
    def __init__(self,name,value):
        self.name=name
        self.value=value
    
    def process(self):
        data={'key':self.value,'name':self.name}
        return data
"""
        
        # 3. 未使用importの問題
        unused_import_problem = """
import os
import sys
import json
import unused_module_that_does_not_exist
from typing import Dict, List, Optional, Any, Union, Tuple
import logging

def simple_function():
    return "Hello, World!"
"""
        
        # 4. トレーリングカンマの問題
        trailing_comma_problem = """
data = {
    'key1': 'value1',
    'key2': 'value2',
    'key3': 'value3'
}

items = [
    'item1',
    'item2',
    'item3'
]

def function_with_args(
    arg1,
    arg2,
    arg3
):
    pass
"""
        
        # テストファイルを作成
        test_files = [
            ('import_problem.py', import_problem),
            ('format_problem.py', format_problem),
            ('unused_import_problem.py', unused_import_problem),
            ('trailing_comma_problem.py', trailing_comma_problem)
        ]
        
        for filename, content in test_files:
            file_path = Path(self.temp_dir) / filename
            with open(file_path, 'w') as f:
                f.write(content)
            self.test_files.append(file_path)
            problems.append(f"Created problematic file: {filename}")
        
        return problems
    
    def run_quality_checks(self, fix_issues=False):
        """コード品質チェックの実行"""
        results = {}
        
        # 現在のディレクトリを一時的に変更
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)
        
        try:
            # 1. isort チェック
            cmd = ['isort', '--check-only', '--diff', '.'] if not fix_issues else ['isort', '.']
            result = subprocess.run(cmd, capture_output=True, text=True)
            results['isort'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # 2. black チェック
            cmd = ['black', '--check', '--diff', '.'] if not fix_issues else ['black', '.']
            result = subprocess.run(cmd, capture_output=True, text=True)
            results['black'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # 3. autoflake チェック（未使用import）
            if fix_issues:
                cmd = ['autoflake', '--remove-all-unused-imports', '--recursive', '--in-place', '.']
                result = subprocess.run(cmd, capture_output=True, text=True)
                results['autoflake'] = {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            
            # 4. flake8 チェック（情報のみ）
            result = subprocess.run(['flake8', '.', '--max-line-length=100'], capture_output=True, text=True)
            results['flake8'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except FileNotFoundError as e:
            logger.warning(f"Tool not found: {e}")
        finally:
            os.chdir(original_dir)
        
        return results
    
    def analyze_results(self, results_before, results_after):
        """修復前後の結果を比較分析"""
        analysis = {
            'improvements': [],
            'remaining_issues': [],
            'tools_used': []
        }
        
        for tool in ['isort', 'black', 'autoflake', 'flake8']:
            if tool in results_before and tool in results_after:
                before = results_before[tool]['returncode']
                after = results_after[tool]['returncode']
                
                if before != 0 and after == 0:
                    analysis['improvements'].append(f"{tool}: Fixed (return code {before} → {after})")
                    analysis['tools_used'].append(tool)
                elif before != 0 and after != 0:
                    analysis['remaining_issues'].append(f"{tool}: Still has issues (return code {after})")
                elif before == 0 and after == 0:
                    analysis['improvements'].append(f"{tool}: Already good")
        
        return analysis
    
    def show_file_diff(self, file_path):
        """ファイルの修復前後の差分を表示"""
        logger.info(f"\n=== File: {file_path.name} ===")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            print(content)
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
    
    def cleanup(self):
        """テスト環境のクリーンアップ"""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up test environment: {self.temp_dir}")
    
    def run_test(self):
        """自動修復テストの実行"""
        logger.info("🧪 Starting Auto-Repair Test")
        
        # 1. テスト環境のセットアップ
        self.setup_test_environment()
        
        # 2. 問題のあるコードを作成
        problems = self.create_problematic_code()
        logger.info(f"Created {len(problems)} problematic files")
        
        # 3. 修復前の品質チェック
        logger.info("Running quality checks BEFORE auto-repair...")
        results_before = self.run_quality_checks(fix_issues=False)
        
        # 4. 修復前のファイル内容を表示
        logger.info("\n📝 Files BEFORE auto-repair:")
        for file_path in self.test_files:
            self.show_file_diff(file_path)
        
        # 5. 自動修復を実行
        logger.info("\n🔧 Running auto-repair...")
        results_after = self.run_quality_checks(fix_issues=True)
        
        # 6. 修復後の品質チェック
        logger.info("Running quality checks AFTER auto-repair...")
        results_final = self.run_quality_checks(fix_issues=False)
        
        # 7. 修復後のファイル内容を表示
        logger.info("\n📝 Files AFTER auto-repair:")
        for file_path in self.test_files:
            self.show_file_diff(file_path)
        
        # 8. 結果の分析
        analysis = self.analyze_results(results_before, results_final)
        
        # 9. レポート生成
        self.generate_report(results_before, results_final, analysis)
        
        # 10. クリーンアップ
        self.cleanup()
        
        return analysis
    
    def generate_report(self, results_before, results_after, analysis):
        """テストレポートの生成"""
        report = f"""
# 🔧 Auto-Repair Test Report

## 📊 Summary
- **Improvements**: {len(analysis['improvements'])}
- **Remaining Issues**: {len(analysis['remaining_issues'])}
- **Tools Used**: {', '.join(analysis['tools_used'])}

## ✅ Improvements Made
"""
        
        for improvement in analysis['improvements']:
            report += f"- {improvement}\n"
        
        report += "\n## ⚠️ Remaining Issues\n"
        for issue in analysis['remaining_issues']:
            report += f"- {issue}\n"
        
        report += "\n## 📋 Detailed Results\n"
        
        for tool in ['isort', 'black', 'autoflake', 'flake8']:
            if tool in results_before and tool in results_after:
                before_code = results_before[tool]['returncode']
                after_code = results_after[tool]['returncode']
                
                report += f"\n### {tool.title()}\n"
                report += f"- Before: Return code {before_code}\n"
                report += f"- After: Return code {after_code}\n"
                
                if results_after[tool]['stdout']:
                    report += f"- Output: {results_after[tool]['stdout'][:200]}...\n"
        
        print(report)
        
        # ファイルにも保存
        with open('auto-repair-test-report.md', 'w') as f:
            f.write(report)
        
        logger.info("Test report saved to: auto-repair-test-report.md")

def main():
    """メイン実行関数"""
    tester = AutoRepairTester()
    
    try:
        analysis = tester.run_test()
        
        # 成功判定
        if len(analysis['improvements']) > 0:
            logger.info("✅ Auto-repair test PASSED - Issues were successfully fixed")
            return 0
        else:
            logger.warning("⚠️ Auto-repair test PARTIAL - Some issues remain")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Auto-repair test FAILED: {e}")
        return 2
    finally:
        tester.cleanup()

if __name__ == "__main__":
    exit(main())