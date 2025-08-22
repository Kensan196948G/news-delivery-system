#!/usr/bin/env python3
"""
CI/CDセットアップの検証スクリプト
新しいワークフローファイルと関連ファイルの整合性をチェック
"""
import yaml
import json
from pathlib import Path
import logging
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CISetupValidator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.validation_results = []
        
    def validate_workflow_files(self):
        """ワークフローファイルの検証"""
        workflows_dir = self.project_root / ".github" / "workflows"
        
        if not workflows_dir.exists():
            self.validation_results.append({
                'category': 'Workflows',
                'status': 'ERROR',
                'message': 'Workflows directory not found'
            })
            return
        
        # 必要なワークフローファイルをチェック
        required_workflows = [
            'automated-news-system.yml',
            'main-ci-cd.yml',
            'quality-gate.yml'
        ]
        
        for workflow_file in required_workflows:
            workflow_path = workflows_dir / workflow_file
            
            if not workflow_path.exists():
                self.validation_results.append({
                    'category': 'Workflows',
                    'status': 'WARNING',
                    'message': f'Workflow file missing: {workflow_file}'
                })
                continue
            
            # YAML構文チェック
            try:
                with open(workflow_path) as f:
                    yaml.safe_load(f)
                
                self.validation_results.append({
                    'category': 'Workflows',
                    'status': 'OK',
                    'message': f'Workflow file valid: {workflow_file}'
                })
                
            except yaml.YAMLError as e:
                self.validation_results.append({
                    'category': 'Workflows',
                    'status': 'ERROR',
                    'message': f'Invalid YAML in {workflow_file}: {e}'
                })
    
    def validate_script_files(self):
        """スクリプトファイルの検証"""
        scripts_dir = self.project_root / "scripts"
        
        required_scripts = [
            'compare_benchmarks.py',
            'update_readme_badges.py',
            'calculate_test_success_rate.py',
            'health_check.py',
            'update_metrics_dashboard.py',
            'test_auto_repair.py',
            'validate_ci_setup.py'
        ]
        
        for script_file in required_scripts:
            script_path = scripts_dir / script_file
            
            if not script_path.exists():
                self.validation_results.append({
                    'category': 'Scripts',
                    'status': 'ERROR',
                    'message': f'Required script missing: {script_file}'
                })
                continue
            
            # Python構文チェック
            try:
                with open(script_path) as f:
                    compile(f.read(), script_path, 'exec')
                
                self.validation_results.append({
                    'category': 'Scripts',
                    'status': 'OK',
                    'message': f'Script syntax valid: {script_file}'
                })
                
            except SyntaxError as e:
                self.validation_results.append({
                    'category': 'Scripts',
                    'status': 'ERROR',
                    'message': f'Syntax error in {script_file}: {e}'
                })
            
            # 実行権限チェック
            if not script_path.stat().st_mode & 0o111:
                self.validation_results.append({
                    'category': 'Scripts',
                    'status': 'WARNING',
                    'message': f'Script not executable: {script_file}'
                })
    
    def validate_github_templates(self):
        """GitHubテンプレートファイルの検証"""
        github_dir = self.project_root / ".github"
        
        # Pull Request テンプレート
        pr_template = github_dir / "pull_request_template.md"
        if pr_template.exists():
            self.validation_results.append({
                'category': 'Templates',
                'status': 'OK',
                'message': 'Pull request template found'
            })
        else:
            self.validation_results.append({
                'category': 'Templates',
                'status': 'WARNING',
                'message': 'Pull request template missing'
            })
        
        # CODEOWNERS
        codeowners = github_dir / "CODEOWNERS"
        if codeowners.exists():
            self.validation_results.append({
                'category': 'Templates',
                'status': 'OK',
                'message': 'CODEOWNERS file found'
            })
        else:
            self.validation_results.append({
                'category': 'Templates',
                'status': 'WARNING',
                'message': 'CODEOWNERS file missing'
            })
    
    def validate_directory_structure(self):
        """ディレクトリ構造の検証"""
        required_dirs = [
            'src',
            'tests',
            'config',
            'scripts',
            'metrics',
            'metrics/charts',
            'metrics/reports',
            '.github',
            '.github/workflows'
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            
            if full_path.exists() and full_path.is_dir():
                self.validation_results.append({
                    'category': 'Structure',
                    'status': 'OK',
                    'message': f'Directory exists: {dir_path}'
                })
            else:
                self.validation_results.append({
                    'category': 'Structure',
                    'status': 'WARNING',
                    'message': f'Directory missing: {dir_path}'
                })
    
    def validate_dependencies(self):
        """依存関係の検証"""
        # requirements.txt の存在確認
        requirements_file = self.project_root / "requirements.txt"
        
        if requirements_file.exists():
            self.validation_results.append({
                'category': 'Dependencies',
                'status': 'OK',
                'message': 'requirements.txt found'
            })
            
            # 必要なパッケージの確認
            required_packages = [
                'pytest', 'flake8', 'black', 'isort', 'bandit',
                'aiohttp', 'requests', 'jinja2'
            ]
            
            try:
                with open(requirements_file) as f:
                    requirements_content = f.read()
                
                missing_packages = []
                for package in required_packages:
                    if package not in requirements_content:
                        missing_packages.append(package)
                
                if missing_packages:
                    self.validation_results.append({
                        'category': 'Dependencies',
                        'status': 'WARNING',
                        'message': f'Missing packages in requirements.txt: {missing_packages}'
                    })
                else:
                    self.validation_results.append({
                        'category': 'Dependencies',
                        'status': 'OK',
                        'message': 'All required packages found in requirements.txt'
                    })
                    
            except Exception as e:
                self.validation_results.append({
                    'category': 'Dependencies',
                    'status': 'ERROR',
                    'message': f'Error reading requirements.txt: {e}'
                })
        else:
            self.validation_results.append({
                'category': 'Dependencies',
                'status': 'ERROR',
                'message': 'requirements.txt not found'
            })
    
    def validate_ci_tools(self):
        """CI/CDツールの可用性確認"""
        tools_to_check = [
            'python', 'pip', 'pytest', 'flake8', 'black', 'isort'
        ]
        
        for tool in tools_to_check:
            try:
                result = subprocess.run([tool, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.validation_results.append({
                        'category': 'CI Tools',
                        'status': 'OK',
                        'message': f'{tool} available: {result.stdout.strip().split()[0] if result.stdout else "version unknown"}'
                    })
                else:
                    self.validation_results.append({
                        'category': 'CI Tools',
                        'status': 'WARNING',
                        'message': f'{tool} command failed'
                    })
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.validation_results.append({
                    'category': 'CI Tools',
                    'status': 'WARNING',
                    'message': f'{tool} not found or not available'
                })
    
    def validate_workflow_syntax(self):
        """新しいワークフローファイルの詳細構文チェック"""
        main_workflow = self.project_root / ".github" / "workflows" / "automated-news-system.yml"
        
        if not main_workflow.exists():
            self.validation_results.append({
                'category': 'Workflow Syntax',
                'status': 'ERROR',
                'message': 'Main automated workflow file not found'
            })
            return
        
        try:
            with open(main_workflow) as f:
                workflow_data = yaml.safe_load(f)
            
            # 必要なセクションの確認
            required_sections = ['name', 'jobs']
            # 'on' は True として解釈される場合があるため、特別に処理
            has_on_trigger = 'on' in workflow_data or True in workflow_data
            missing_sections = [section for section in required_sections 
                              if section not in workflow_data]
            if not has_on_trigger:
                missing_sections.append('on')
            
            if missing_sections:
                self.validation_results.append({
                    'category': 'Workflow Syntax',
                    'status': 'ERROR',
                    'message': f'Missing workflow sections: {missing_sections}'
                })
            else:
                self.validation_results.append({
                    'category': 'Workflow Syntax',
                    'status': 'OK',
                    'message': 'All required workflow sections present'
                })
            
            # ジョブの確認
            jobs = workflow_data.get('jobs', {})
            expected_jobs = [
                'setup', 'quality-gate', 'test-matrix', 'auto-repair',
                'security-scan', 'performance-test', 'docs-automation',
                'notification', 'deploy', 'monitoring'
            ]
            
            missing_jobs = [job for job in expected_jobs if job not in jobs]
            
            if missing_jobs:
                self.validation_results.append({
                    'category': 'Workflow Syntax',
                    'status': 'WARNING',
                    'message': f'Missing workflow jobs: {missing_jobs}'
                })
            else:
                self.validation_results.append({
                    'category': 'Workflow Syntax',
                    'status': 'OK',
                    'message': 'All expected workflow jobs present'
                })
                
        except yaml.YAMLError as e:
            self.validation_results.append({
                'category': 'Workflow Syntax',
                'status': 'ERROR',
                'message': f'YAML syntax error in main workflow: {e}'
            })
        except Exception as e:
            self.validation_results.append({
                'category': 'Workflow Syntax',
                'status': 'ERROR',
                'message': f'Error validating workflow syntax: {e}'
            })
    
    def run_validation(self):
        """全検証の実行"""
        logger.info("🔍 Starting CI/CD setup validation...")
        
        validation_methods = [
            self.validate_workflow_files,
            self.validate_script_files,
            self.validate_github_templates,
            self.validate_directory_structure,
            self.validate_dependencies,
            self.validate_ci_tools,
            self.validate_workflow_syntax
        ]
        
        for method in validation_methods:
            try:
                method()
            except Exception as e:
                self.validation_results.append({
                    'category': 'Validation',
                    'status': 'ERROR',
                    'message': f'Validation method {method.__name__} failed: {e}'
                })
        
        return self.generate_report()
    
    def generate_report(self):
        """検証レポートの生成"""
        # 結果をカテゴリ別に集計
        summary = {}
        for result in self.validation_results:
            category = result['category']
            status = result['status']
            
            if category not in summary:
                summary[category] = {'OK': 0, 'WARNING': 0, 'ERROR': 0}
            summary[category][status] += 1
        
        # 全体的な評価
        total_errors = sum(cat['ERROR'] for cat in summary.values())
        total_warnings = sum(cat['WARNING'] for cat in summary.values())
        total_ok = sum(cat['OK'] for cat in summary.values())
        
        overall_status = 'PASS'
        if total_errors > 0:
            overall_status = 'FAIL'
        elif total_warnings > 0:
            overall_status = 'PARTIAL'
        
        # レポート生成
        report = f"""
# 🔍 CI/CD Setup Validation Report

**Overall Status**: {overall_status}
**Total Checks**: {len(self.validation_results)}
- ✅ OK: {total_ok}
- ⚠️ Warnings: {total_warnings}
- ❌ Errors: {total_errors}

## 📊 Summary by Category

| Category | ✅ OK | ⚠️ Warning | ❌ Error |
|----------|-------|------------|----------|
"""
        
        for category, counts in summary.items():
            report += f"| {category} | {counts['OK']} | {counts['WARNING']} | {counts['ERROR']} |\n"
        
        report += "\n## 📋 Detailed Results\n\n"
        
        current_category = None
        for result in self.validation_results:
            if result['category'] != current_category:
                current_category = result['category']
                report += f"\n### {current_category}\n\n"
            
            status_emoji = {'OK': '✅', 'WARNING': '⚠️', 'ERROR': '❌'}[result['status']]
            report += f"- {status_emoji} {result['message']}\n"
        
        report += f"""

## 🎯 Next Steps

{"### ✅ All validations passed! Your CI/CD setup is ready." if overall_status == 'PASS' else ""}
{"### ⚠️ Some warnings found. Consider addressing them before deployment." if overall_status == 'PARTIAL' else ""}
{"### ❌ Critical errors found. Please fix them before using the CI/CD pipeline." if overall_status == 'FAIL' else ""}

## 🚀 Recommended Actions

1. **Fix any ERROR status items** - These will prevent the CI/CD pipeline from working
2. **Address WARNING status items** - These may cause issues or suboptimal performance
3. **Test the workflow** - Create a test PR to verify the automated pipeline works
4. **Monitor the first few runs** - Watch for any unexpected issues

---
*Generated by CI/CD Setup Validator*
"""
        
        print(report)
        
        # レポートをファイルに保存
        with open('ci-cd-validation-report.md', 'w') as f:
            f.write(report)
        
        logger.info("Validation report saved to: ci-cd-validation-report.md")
        
        return {
            'overall_status': overall_status,
            'total_checks': len(self.validation_results),
            'summary': summary,
            'results': self.validation_results
        }

def main():
    """メイン実行関数"""
    validator = CISetupValidator()
    
    try:
        results = validator.run_validation()
        
        # 終了コード
        if results['overall_status'] == 'PASS':
            logger.info("✅ CI/CD setup validation PASSED")
            return 0
        elif results['overall_status'] == 'PARTIAL':
            logger.warning("⚠️ CI/CD setup validation PARTIAL - warnings found")
            return 1
        else:
            logger.error("❌ CI/CD setup validation FAILED - errors found")
            return 2
            
    except Exception as e:
        logger.error(f"❌ Validation failed with exception: {e}")
        return 3

if __name__ == "__main__":
    sys.exit(main())