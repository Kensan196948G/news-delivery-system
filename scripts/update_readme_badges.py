#!/usr/bin/env python3
"""
READMEファイルのバッジとメトリクスを自動更新
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import Dict, Optional
import subprocess
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReadmeBadgeUpdater:
    def __init__(self, readme_path: str = "README.md"):
        self.readme_path = Path(readme_path)
        self.metrics = {}
        
    def extract_test_results(self) -> Dict[str, any]:
        """テスト結果からメトリクスを抽出"""
        metrics = {
            'test_success_rate': 0,
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'coverage': 0
        }
        
        # pytest結果XMLファイルを探す
        xml_files = list(Path('.').glob('**/test-results.xml')) + list(Path('.').glob('**/pytest-results.xml'))
        
        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                
                # JUnit XML形式から統計情報を抽出
                if root.tag == 'testsuites':
                    total = int(root.get('tests', 0))
                    failures = int(root.get('failures', 0))
                    errors = int(root.get('errors', 0))
                    skipped = int(root.get('skipped', 0))
                    
                    passed = total - failures - errors - skipped
                    success_rate = (passed / total * 100) if total > 0 else 0
                    
                    metrics.update({
                        'total_tests': total,
                        'passed_tests': passed,
                        'failed_tests': failures + errors,
                        'test_success_rate': round(success_rate, 1)
                    })
                    
                    logger.info(f"Extracted test metrics: {metrics}")
                    break
                    
            except ET.ParseError as e:
                logger.warning(f"Failed to parse XML file {xml_file}: {e}")
                continue
                
        return metrics
    
    def extract_coverage_info(self) -> float:
        """カバレッジ情報を抽出"""
        coverage = 0
        
        # coverage.xml ファイルを探す
        coverage_files = list(Path('.').glob('**/coverage.xml'))
        
        for coverage_file in coverage_files:
            try:
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                
                # coverage XMLから総合カバレッジを取得
                if root.tag == 'coverage':
                    line_rate = float(root.get('line-rate', 0))
                    coverage = round(line_rate * 100, 1)
                    logger.info(f"Extracted coverage: {coverage}%")
                    break
                    
            except (ET.ParseError, ValueError) as e:
                logger.warning(f"Failed to parse coverage file {coverage_file}: {e}")
                continue
                
        return coverage
    
    def get_git_info(self) -> Dict[str, str]:
        """Git情報を取得"""
        info = {}
        
        try:
            # 最新コミットのハッシュ
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                info['commit'] = result.stdout.strip()
                
            # ブランチ名
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                info['branch'] = result.stdout.strip()
                
            # コミット数
            result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                info['commits'] = result.stdout.strip()
                
        except Exception as e:
            logger.warning(f"Failed to get git info: {e}")
            
        return info
    
    def get_code_stats(self) -> Dict[str, int]:
        """コード統計を取得"""
        stats = {'lines_of_code': 0, 'files': 0}
        
        try:
            # Pythonファイルの行数をカウント
            python_files = list(Path('src').glob('**/*.py')) if Path('src').exists() else []
            total_lines = 0
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = len([line for line in f if line.strip() and not line.strip().startswith('#')])
                        total_lines += lines
                except Exception:
                    continue
                    
            stats['lines_of_code'] = total_lines
            stats['files'] = len(python_files)
            
        except Exception as e:
            logger.warning(f"Failed to get code stats: {e}")
            
        return stats
    
    def generate_badge_url(self, label: str, message: str, color: str = 'blue') -> str:
        """shields.ioバッジURLを生成"""
        # スペースや特殊文字をエンコード
        label = label.replace(' ', '%20').replace('-', '--')
        message = str(message).replace(' ', '%20').replace('-', '--')
        
        return f"https://img.shields.io/badge/{label}-{message}-{color}"
    
    def get_color_for_percentage(self, percentage: float) -> str:
        """パーセンテージに基づいて色を決定"""
        if percentage >= 90:
            return 'brightgreen'
        elif percentage >= 75:
            return 'green'
        elif percentage >= 60:
            return 'yellow'
        elif percentage >= 40:
            return 'orange'
        else:
            return 'red'
    
    def update_badges(self) -> bool:
        """READMEファイルのバッジを更新"""
        if not self.readme_path.exists():
            logger.error(f"README file not found: {self.readme_path}")
            return False
            
        # メトリクス収集
        test_metrics = self.extract_test_results()
        coverage = self.extract_coverage_info()
        git_info = self.get_git_info()
        code_stats = self.get_code_stats()
        
        # READMEファイルを読み込み
        try:
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read README: {e}")
            return False
        
        # バッジURLを生成
        badges = {}
        
        # テスト成功率バッジ
        if test_metrics['test_success_rate'] > 0:
            color = self.get_color_for_percentage(test_metrics['test_success_rate'])
            badges['test-success'] = self.generate_badge_url(
                'Tests', f"{test_metrics['test_success_rate']}%25", color
            )
        
        # カバレッジバッジ
        if coverage > 0:
            color = self.get_color_for_percentage(coverage)
            badges['coverage'] = self.generate_badge_url(
                'Coverage', f"{coverage}%25", color
            )
        
        # コードライン数バッジ
        if code_stats['lines_of_code'] > 0:
            badges['lines'] = self.generate_badge_url(
                'Lines', f"{code_stats['lines_of_code']}", 'blue'
            )
        
        # Python バージョンバッジ
        badges['python'] = self.generate_badge_url(
            'Python', '3.11+-blue'
        )
        
        # ライセンスバッジ
        badges['license'] = self.generate_badge_url(
            'License', 'MIT-green'
        )
        
        # バッジセクションを作成
        badge_section = "<!-- Badges -->\n"
        for key, url in badges.items():
            badge_section += f"![{key.title()}]({url})\n"
        badge_section += "<!-- /Badges -->\n"
        
        # 既存のバッジセクションを置換または追加
        badge_pattern = r'<!-- Badges -->.*?<!-- /Badges -->\n'
        
        if re.search(badge_pattern, content, re.DOTALL):
            # 既存のバッジセクションを置換
            content = re.sub(badge_pattern, badge_section, content, flags=re.DOTALL)
        else:
            # タイトルの後にバッジセクションを追加
            title_pattern = r'(# [^\n]+\n)'
            if re.search(title_pattern, content):
                content = re.sub(title_pattern, r'\1\n' + badge_section, content, count=1)
            else:
                content = badge_section + content
        
        # 統計情報セクションを更新
        stats_section = f"""
<!-- Statistics -->
## 📊 プロジェクト統計

| メトリクス | 値 |
|-----------|-----|
| テスト成功率 | {test_metrics['test_success_rate']}% ({test_metrics['passed_tests']}/{test_metrics['total_tests']}) |
| コードカバレッジ | {coverage}% |
| コード行数 | {code_stats['lines_of_code']} |
| ファイル数 | {code_stats['files']} |
| 最新コミット | {git_info.get('commit', 'N/A')} |
| ブランチ | {git_info.get('branch', 'N/A')} |

*最終更新: {self.get_current_datetime()}*
<!-- /Statistics -->
"""
        
        # 既存の統計セクションを置換または追加
        stats_pattern = r'<!-- Statistics -->.*?<!-- /Statistics -->\n'
        
        if re.search(stats_pattern, content, re.DOTALL):
            content = re.sub(stats_pattern, stats_section, content, flags=re.DOTALL)
        else:
            content += stats_section
        
        # ファイルに書き戻し
        try:
            with open(self.readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("README badges updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to write README: {e}")
            return False
    
    def get_current_datetime(self) -> str:
        """現在の日時を取得"""
        from datetime import datetime
        return datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')

def main():
    """メイン関数"""
    updater = ReadmeBadgeUpdater()
    success = updater.update_badges()
    
    if success:
        print("✅ README badges updated successfully")
    else:
        print("❌ Failed to update README badges")
        exit(1)

if __name__ == "__main__":
    main()