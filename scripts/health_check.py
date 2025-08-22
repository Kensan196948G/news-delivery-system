#!/usr/bin/env python3
"""
システムヘルスチェックスクリプト
デプロイ後の動作確認とシステム状態の検証
"""
import sys
import subprocess
import requests
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import importlib.util
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.checks = []
        self.results = {}
        self.start_time = datetime.now()
        
    def add_check(self, name: str, func, *args, **kwargs):
        """ヘルスチェック項目を追加"""
        self.checks.append({
            'name': name,
            'function': func,
            'args': args,
            'kwargs': kwargs
        })
    
    def check_python_environment(self) -> Dict[str, Any]:
        """Python環境のチェック"""
        result = {'status': 'OK', 'details': {}}
        
        try:
            # Pythonバージョン
            result['details']['python_version'] = sys.version
            
            # 必要なモジュールのインポートテスト
            required_modules = [
                'aiohttp', 'anthropic', 'pytest', 'jinja2', 
                'requests', 'beautifulsoup4'
            ]
            
            missing_modules = []
            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
            
            if missing_modules:
                result['status'] = 'WARNING'
                result['details']['missing_modules'] = missing_modules
            else:
                result['details']['all_modules_available'] = True
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['details']['error'] = str(e)
        
        return result
    
    def check_file_structure(self) -> Dict[str, Any]:
        """ファイル構造のチェック"""
        result = {'status': 'OK', 'details': {}}
        
        required_paths = [
            'src/',
            'src/main.py',
            'src/collectors/',
            'src/processors/',
            'src/generators/',
            'src/notifiers/',
            'src/utils/',
            'tests/',
            'config/',
            'requirements.txt'
        ]
        
        missing_paths = []
        existing_paths = []
        
        for path_str in required_paths:
            path = Path(path_str)
            if path.exists():
                existing_paths.append(path_str)
            else:
                missing_paths.append(path_str)
        
        result['details']['existing_paths'] = existing_paths
        
        if missing_paths:
            result['status'] = 'WARNING'
            result['details']['missing_paths'] = missing_paths
        
        return result
    
    def check_configuration(self) -> Dict[str, Any]:
        """設定ファイルのチェック"""
        result = {'status': 'OK', 'details': {}}
        
        try:
            # config.json の存在確認
            config_path = Path('config/config.json')
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                result['details']['config_loaded'] = True
                result['details']['config_keys'] = list(config.keys())
            else:
                result['status'] = 'WARNING'
                result['details']['config_file_missing'] = True
            
            # .env ファイルの確認
            env_path = Path('config/.env')
            if env_path.exists():
                result['details']['env_file_exists'] = True
            else:
                result['status'] = 'WARNING'
                result['details']['env_file_missing'] = True
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['details']['error'] = str(e)
        
        return result
    
    def check_dependencies(self) -> Dict[str, Any]:
        """依存関係のチェック"""
        result = {'status': 'OK', 'details': {}}
        
        try:
            # requirements.txt の確認
            req_path = Path('requirements.txt')
            if req_path.exists():
                with open(req_path) as f:
                    requirements = f.read().splitlines()
                result['details']['requirements_count'] = len([r for r in requirements if r.strip() and not r.startswith('#')])
            
            # pip list の実行
            pip_result = subprocess.run(['pip', 'list', '--format=json'], 
                                      capture_output=True, text=True)
            if pip_result.returncode == 0:
                installed_packages = json.loads(pip_result.stdout)
                result['details']['installed_packages_count'] = len(installed_packages)
            
        except Exception as e:
            result['status'] = 'WARNING'
            result['details']['error'] = str(e)
        
        return result
    
    def check_database_connectivity(self) -> Dict[str, Any]:
        """データベース接続のチェック"""
        result = {'status': 'OK', 'details': {}}
        
        try:
            import sqlite3
            
            # データベースファイルの確認
            db_paths = [
                Path('E:/NewsDeliverySystem/database/news.db'),
                Path('database/news.db'),
                Path('news.db')
            ]
            
            db_found = False
            for db_path in db_paths:
                if db_path.exists():
                    try:
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        conn.close()
                        
                        result['details']['database_path'] = str(db_path)
                        result['details']['tables'] = [table[0] for table in tables]
                        result['details']['table_count'] = len(tables)
                        db_found = True
                        break
                        
                    except Exception as e:
                        result['details'][f'db_error_{db_path.name}'] = str(e)
            
            if not db_found:
                result['status'] = 'WARNING'
                result['details']['database_not_found'] = True
                
        except ImportError:
            result['status'] = 'ERROR'
            result['details']['sqlite3_not_available'] = True
        except Exception as e:
            result['status'] = 'ERROR'
            result['details']['error'] = str(e)
        
        return result
    
    def check_api_connectivity(self) -> Dict[str, Any]:
        """外部API接続のチェック（簡易版）"""
        result = {'status': 'OK', 'details': {}}
        
        # 基本的なインターネット接続確認
        test_urls = [
            'https://httpbin.org/get',
            'https://api.github.com',
            'https://www.google.com'
        ]
        
        connectivity_results = {}
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=10)
                connectivity_results[url] = {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                connectivity_results[url] = {
                    'error': str(e)
                }
        
        result['details']['connectivity_tests'] = connectivity_results
        
        # 失敗したテストをチェック
        failed_tests = [url for url, test in connectivity_results.items() 
                       if 'error' in test or test.get('status_code', 0) >= 400]
        
        if failed_tests:
            result['status'] = 'WARNING'
            result['details']['failed_connectivity_tests'] = failed_tests
        
        return result
    
    def check_basic_functionality(self) -> Dict[str, Any]:
        """基本機能のチェック"""
        result = {'status': 'OK', 'details': {}}
        
        try:
            # メインモジュールのインポートテスト
            src_path = Path('src')
            if src_path.exists():
                sys.path.insert(0, str(src_path))
                
                # 主要モジュールのインポートテスト
                modules_to_test = [
                    'utils.config',
                    'utils.logger',
                    'models.article',
                ]
                
                import_results = {}
                for module_name in modules_to_test:
                    try:
                        spec = importlib.util.find_spec(module_name)
                        if spec is not None:
                            import_results[module_name] = 'OK'
                        else:
                            import_results[module_name] = 'Module not found'
                    except Exception as e:
                        import_results[module_name] = f'Error: {str(e)}'
                
                result['details']['module_imports'] = import_results
                
                # 失敗したインポートをチェック
                failed_imports = [mod for mod, status in import_results.items() 
                                if status != 'OK']
                
                if failed_imports:
                    result['status'] = 'WARNING'
                    result['details']['failed_imports'] = failed_imports
                    
        except Exception as e:
            result['status'] = 'ERROR'
            result['details']['error'] = str(e)
        
        return result
    
    def check_disk_space(self) -> Dict[str, Any]:
        """ディスク容量のチェック"""
        result = {'status': 'OK', 'details': {}}
        
        try:
            import shutil
            
            # 現在のディレクトリの容量
            total, used, free = shutil.disk_usage('.')
            
            result['details']['current_dir'] = {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'usage_percent': round((used / total) * 100, 2)
            }
            
            # 外付けHDDの確認（Eドライブ）
            if Path('E:/').exists():
                total_e, used_e, free_e = shutil.disk_usage('E:/')
                result['details']['external_hdd'] = {
                    'total_gb': round(total_e / (1024**3), 2),
                    'used_gb': round(used_e / (1024**3), 2),
                    'free_gb': round(free_e / (1024**3), 2),
                    'usage_percent': round((used_e / total_e) * 100, 2)
                }
            
            # 容量警告
            if result['details']['current_dir']['usage_percent'] > 90:
                result['status'] = 'WARNING'
                result['details']['disk_space_warning'] = 'Current directory is over 90% full'
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['details']['error'] = str(e)
        
        return result
    
    def run_all_checks(self) -> Dict[str, Any]:
        """全チェックの実行"""
        logger.info("Starting health check...")
        
        # デフォルトのチェック項目を追加
        self.add_check("Python Environment", self.check_python_environment)
        self.add_check("File Structure", self.check_file_structure)
        self.add_check("Configuration", self.check_configuration)
        self.add_check("Dependencies", self.check_dependencies)
        self.add_check("Database Connectivity", self.check_database_connectivity)
        self.add_check("API Connectivity", self.check_api_connectivity)
        self.add_check("Basic Functionality", self.check_basic_functionality)
        self.add_check("Disk Space", self.check_disk_space)
        
        # 各チェックを実行
        for check in self.checks:
            check_name = check['name']
            logger.info(f"Running check: {check_name}")
            
            try:
                start_time = time.time()
                result = check['function'](*check['args'], **check['kwargs'])
                end_time = time.time()
                
                result['execution_time'] = round(end_time - start_time, 3)
                self.results[check_name] = result
                
                status = result['status']
                logger.info(f"Check '{check_name}' completed: {status}")
                
            except Exception as e:
                logger.error(f"Check '{check_name}' failed: {str(e)}")
                self.results[check_name] = {
                    'status': 'ERROR',
                    'details': {'exception': str(e)}
                }
        
        # 全体的な結果をまとめる
        total_checks = len(self.results)
        ok_checks = len([r for r in self.results.values() if r['status'] == 'OK'])
        warning_checks = len([r for r in self.results.values() if r['status'] == 'WARNING'])
        error_checks = len([r for r in self.results.values() if r['status'] == 'ERROR'])
        
        overall_status = 'OK'
        if error_checks > 0:
            overall_status = 'ERROR'
        elif warning_checks > 0:
            overall_status = 'WARNING'
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'total_checks': total_checks,
            'ok_checks': ok_checks,
            'warning_checks': warning_checks,
            'error_checks': error_checks,
            'execution_time': round((datetime.now() - self.start_time).total_seconds(), 3),
            'detailed_results': self.results
        }
        
        return summary
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """ヘルスチェックレポートの生成"""
        report = f"""
# 🏥 System Health Check Report

**Timestamp**: {results['timestamp']}
**Overall Status**: {results['overall_status']}
**Execution Time**: {results['execution_time']}s

## 📊 Summary
- **Total Checks**: {results['total_checks']}
- **✅ OK**: {results['ok_checks']}
- **⚠️ Warnings**: {results['warning_checks']}
- **❌ Errors**: {results['error_checks']}

## 📋 Detailed Results

"""
        
        for check_name, result in results['detailed_results'].items():
            status_emoji = {
                'OK': '✅',
                'WARNING': '⚠️',
                'ERROR': '❌'
            }.get(result['status'], '❓')
            
            report += f"### {status_emoji} {check_name}\n"
            report += f"**Status**: {result['status']}\n"
            report += f"**Execution Time**: {result.get('execution_time', 'N/A')}s\n"
            
            if result.get('details'):
                report += "**Details**:\n"
                for key, value in result['details'].items():
                    if isinstance(value, (list, dict)):
                        report += f"- {key}: {json.dumps(value, indent=2)}\n"
                    else:
                        report += f"- {key}: {value}\n"
            
            report += "\n"
        
        return report

def main():
    """メイン関数"""
    checker = HealthChecker()
    results = checker.run_all_checks()
    
    # レポート生成
    report = checker.generate_report(results)
    print(report)
    
    # 結果をファイルに保存
    output_dir = Path('health-check-reports')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = output_dir / f'health-check-{timestamp}.md'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # JSON形式でも保存
    json_file = output_dir / f'health-check-{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Health check completed. Reports saved to {output_dir}")
    
    # 終了コード
    if results['overall_status'] == 'ERROR':
        sys.exit(1)
    elif results['overall_status'] == 'WARNING':
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()