#!/usr/bin/env python3
"""
GitHub Actions ワークフロー自動修復システム v2
エラーが完全になくなるまで自動修復・コミット・プッシュを繰り返す
"""

import os
import sys
import json
import yaml
import time
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkflowAutoFixerV2:
    """GitHub Actions ワークフロー自動修復クラス v2"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.workflows_dir = self.repo_path / ".github" / "workflows"
        self.fix_count = 0
        self.max_iterations = 20  # 最大イテレーション数を増やす
        self.iteration = 0
        self.total_fixes = 0
        
    def run_command(self, cmd: List[str], cwd: str = None) -> Tuple[int, str, str]:
        """コマンド実行"""
        result = subprocess.run(
            cmd,
            cwd=cwd or self.repo_path,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    
    def check_yaml_syntax(self, file_path: Path) -> List[Dict]:
        """YAML構文チェック（詳細なエラー情報を返す）"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            error_info = {
                'file': file_path.name,
                'error': str(e),
                'line': None,
                'column': None
            }
            
            # エラーメッセージから行番号を抽出
            line_match = re.search(r'line (\d+)', str(e))
            if line_match:
                error_info['line'] = int(line_match.group(1))
            
            col_match = re.search(r'column (\d+)', str(e))
            if col_match:
                error_info['column'] = int(col_match.group(1))
                
            errors.append(error_info)
            
        return errors
    
    def fix_yaml_file(self, file_path: Path, error_info: Dict) -> bool:
        """YAMLファイルの特定のエラーを修正"""
        logger.info(f"🔧 修正中: {file_path.name} (Line {error_info.get('line', '?')})")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            error_line = error_info.get('line')
            
            if error_line and error_line > 0:
                # エラー行周辺を詳しく調査
                start = max(0, error_line - 5)
                end = min(len(lines), error_line + 5)
                
                logger.debug(f"エラー行周辺のコンテキスト (行 {start+1}-{end}):")
                for i in range(start, end):
                    if i == error_line - 1:
                        logger.debug(f">>> {i+1}: {lines[i].rstrip()}")
                    else:
                        logger.debug(f"    {i+1}: {lines[i].rstrip()}")
            
            # ファイル全体の修正
            new_lines = []
            in_script_block = False
            in_python_block = False
            python_block_indent = 0
            
            for i, line in enumerate(lines):
                line_num = i + 1
                
                # script: | ブロックの検出
                if 'script: |' in line:
                    in_script_block = True
                    new_lines.append(line)
                    continue
                elif in_script_block and line.strip() and not line[0].isspace():
                    in_script_block = False
                
                # python -c " ブロックの検出と修正
                if re.search(r'python3?\s+-c\s+"', line):
                    in_python_block = True
                    python_block_indent = len(line) - len(line.lstrip())
                    
                    # 複数行Pythonコードを単一行に変換
                    if error_line and abs(line_num - error_line) <= 5:
                        logger.info(f"  📝 Python複数行コードを修正 (行 {line_num})")
                        
                        # 複数行を収集
                        python_lines = [line.rstrip()]
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j]
                            # クォートで終わるまで続ける
                            if '"' in next_line and not next_line.strip().startswith('#'):
                                python_lines.append(next_line.rstrip())
                                break
                            python_lines.append(next_line.rstrip())
                            j += 1
                        
                        # 単一行に結合
                        single_line = python_lines[0]
                        for pl in python_lines[1:]:
                            stripped = pl.strip()
                            if stripped and not stripped.startswith('#'):
                                single_line += ' ' + stripped
                        
                        new_lines.append(single_line + '\n')
                        
                        # 処理済みの行をスキップ
                        for _ in range(j - i):
                            if i + 1 < len(lines):
                                lines[i + 1] = ''
                        
                        modified = True
                        continue
                
                # JavaScriptテンプレートリテラルの修正
                if in_script_block:
                    # バッククォートをシングルクォートに変換
                    if '`' in line:
                        logger.info(f"  📝 テンプレートリテラル修正 (行 {line_num})")
                        line = line.replace('`', "'")
                        modified = True
                    
                    # ${variable} を ' + variable + ' に変換
                    if '${' in line and '}' in line:
                        logger.info(f"  📝 変数展開修正 (行 {line_num})")
                        line = re.sub(r'\$\{([^}]+)\}', r"' + \1 + '", line)
                        modified = True
                
                # 三連バッククォートの修正
                if '```' in line and error_line and abs(line_num - error_line) <= 2:
                    logger.info(f"  📝 三連バッククォート修正 (行 {line_num})")
                    line = line.replace('```', '\\`\\`\\`')
                    modified = True
                
                # エラー行周辺での特殊処理
                if error_line and abs(line_num - error_line) <= 2:
                    # 不正な文字列連結の修正
                    if "' +" in line and not line.strip().endswith('+'):
                        if not line.rstrip().endswith("'"):
                            logger.info(f"  📝 文字列連結修正 (行 {line_num})")
                            line = line.rstrip() + " +\n"
                            modified = True
                    
                    # カンマエラーの修正
                    if ',' in line and 'expected <block end>' in str(error_info.get('error', '')):
                        # JavaScriptオブジェクトのカンマ問題
                        if line.strip().endswith(',') and not line.strip().endswith("',"):
                            logger.info(f"  📝 末尾カンマ削除 (行 {line_num})")
                            line = line.rstrip()[:-1] + '\n'
                            modified = True
                
                new_lines.append(line)
            
            if modified:
                # ファイルを書き戻す
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
                logger.info(f"✅ {file_path.name} を修正しました")
                self.total_fixes += 1
                return True
            else:
                logger.info(f"ℹ️ {file_path.name} に修正可能な問題が見つかりませんでした")
                
        except Exception as e:
            logger.error(f"❌ {file_path.name} の修正中にエラー: {e}")
            
        return False
    
    def aggressive_fix(self, file_path: Path) -> bool:
        """より積極的な修正を試みる"""
        logger.info(f"🔨 積極的修正モード: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 1. すべてのテンプレートリテラルを文字列連結に変換
            content = re.sub(r'`([^`]*)`', lambda m: "'" + m.group(1).replace('\n', '\\n').replace('${', "' + ").replace('}', " + '") + "'", content)
            
            # 2. Pythonの複数行文字列を単一行に
            content = re.sub(
                r'python3?\s+-c\s+"([^"]*)"',
                lambda m: 'python3 -c "' + m.group(1).replace('\n', '; ').replace('  ', ' ') + '"',
                content,
                flags=re.DOTALL
            )
            
            # 3. 三連バッククォートのエスケープ
            content = re.sub(r'```(?!\w)', r'\\`\\`\\`', content)
            
            # 4. 不正な改行の修正
            lines = content.split('\n')
            fixed_lines = []
            for i, line in enumerate(lines):
                if i > 0 and lines[i-1].rstrip().endswith('+') and line.strip().startswith("'"):
                    # 文字列連結の継続
                    fixed_lines.append('              ' + line.strip())
                else:
                    fixed_lines.append(line)
            content = '\n'.join(fixed_lines)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✅ {file_path.name} を積極的に修正しました")
                self.total_fixes += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ 積極的修正中にエラー: {e}")
            
        return False
    
    def git_operations(self, message: str) -> bool:
        """Git操作（add, commit, push）"""
        try:
            # 変更をステージング
            returncode, stdout, stderr = self.run_command(["git", "add", "-A"])
            if returncode != 0:
                logger.error(f"Git add failed: {stderr}")
                return False
            
            # 変更があるか確認
            returncode, stdout, stderr = self.run_command(["git", "status", "--porcelain"])
            if not stdout.strip():
                logger.info("変更なし - コミット不要")
                return False
            
            # コミット
            commit_msg = f"""fix: {message} (iteration {self.iteration})

自動修復システムによる修正
- YAML構文エラー修正 ({self.total_fixes} fixes)
- テンプレートリテラル修正
- Python複数行コード修正
- 文字列連結エラー修正

🤖 Auto-generated by workflow fixer v2"""
            
            returncode, stdout, stderr = self.run_command(["git", "commit", "-m", commit_msg])
            if returncode != 0:
                logger.error(f"Git commit failed: {stderr}")
                return False
            
            logger.info("✅ 変更をコミットしました")
            
            # プッシュ
            returncode, stdout, stderr = self.run_command(["git", "push"])
            if returncode == 0:
                logger.info("✅ 変更をプッシュしました")
                return True
            else:
                logger.error(f"❌ プッシュエラー: {stderr}")
                # プッシュ失敗時はpullしてリトライ
                self.run_command(["git", "pull", "--rebase"])
                returncode, stdout, stderr = self.run_command(["git", "push"])
                if returncode == 0:
                    logger.info("✅ リトライ後プッシュ成功")
                    return True
                    
        except Exception as e:
            logger.error(f"Git操作エラー: {e}")
            
        return False
    
    def auto_fix_loop(self):
        """自動修復ループ - エラーがなくなるまで続ける"""
        logger.info("🔄 自動修復ループを開始します (エラーがなくなるまで継続)")
        
        consecutive_no_fix = 0  # 連続で修正なしの回数
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 イテレーション {self.iteration}/{self.max_iterations}")
            logger.info(f"{'='*60}")
            
            # 1. エラー検出
            all_errors = []
            for yml_file in self.workflows_dir.glob("*.yml"):
                errors = self.check_yaml_syntax(yml_file)
                for error in errors:
                    error['file_path'] = yml_file
                    all_errors.append(error)
            
            for yaml_file in self.workflows_dir.glob("*.yaml"):
                errors = self.check_yaml_syntax(yaml_file)
                for error in errors:
                    error['file_path'] = yaml_file
                    all_errors.append(error)
            
            if not all_errors:
                logger.info("🎉 すべてのYAMLファイルの構文が正常です！")
                logger.info("✨ エラーゼロ達成！")
                break
            
            logger.info(f"❌ {len(all_errors)} 個のエラーを検出:")
            for error in all_errors:
                logger.info(f"  - {error['file']}: Line {error.get('line', '?')}")
                logger.debug(f"    {error['error'][:100]}...")
            
            # 2. エラーごとに修正を試みる
            fixes_in_iteration = 0
            
            for error in all_errors:
                file_path = error['file_path']
                
                # まず通常の修正を試みる
                if self.fix_yaml_file(file_path, error):
                    fixes_in_iteration += 1
                else:
                    # 通常の修正が失敗したら積極的修正
                    if self.aggressive_fix(file_path):
                        fixes_in_iteration += 1
            
            # 3. 修正があればコミット・プッシュ
            if fixes_in_iteration > 0:
                logger.info(f"📝 {fixes_in_iteration} 個の修正を適用しました")
                consecutive_no_fix = 0
                
                if self.git_operations(f"YAMLエラー修正 ({fixes_in_iteration} fixes)"):
                    logger.info("⏳ 30秒待機してGitHub Actionsの実行を待ちます...")
                    time.sleep(30)
                else:
                    logger.warning("Git操作に失敗しましたが、続行します")
            else:
                consecutive_no_fix += 1
                logger.warning(f"⚠️ 修正可能な問題が見つかりませんでした (連続 {consecutive_no_fix} 回)")
                
                if consecutive_no_fix >= 3:
                    logger.error("❌ 3回連続で修正できません。手動介入が必要です。")
                    logger.info("\n🔍 残存エラーの詳細:")
                    for error in all_errors:
                        logger.info(f"\nファイル: {error['file']}")
                        logger.info(f"エラー: {error['error']}")
                    break
                
                # 少し異なるアプローチを試みる
                logger.info("🔄 別のアプローチを試みます...")
                time.sleep(5)
        
        # 最終チェック
        final_errors = []
        for yml_file in self.workflows_dir.glob("*.yml"):
            errors = self.check_yaml_syntax(yml_file)
            final_errors.extend(errors)
        
        # 完了メッセージ
        logger.info(f"\n{'='*60}")
        logger.info("📊 最終修復統計:")
        logger.info(f"  - 総イテレーション: {self.iteration}")
        logger.info(f"  - 総修正数: {self.total_fixes}")
        logger.info(f"  - 残存エラー: {len(final_errors)}")
        
        if len(final_errors) == 0:
            logger.info("✅ 🎉 完全修復成功！すべてのエラーが解決されました！")
        else:
            logger.warning(f"⚠️ {len(final_errors)} 個のエラーが残っています")
            logger.info("手動での修正が必要な可能性があります")

def main():
    """メイン関数"""
    print("""
╔══════════════════════════════════════════════════╗
║  GitHub Actions ワークフロー自動修復システム v2  ║
║  Auto-Fix Until All Errors Are Resolved          ║
╚══════════════════════════════════════════════════╝
    """)
    
    # リポジトリパスの確認
    repo_path = os.getcwd()
    if not (Path(repo_path) / ".github" / "workflows").exists():
        logger.error("❌ .github/workflows ディレクトリが見つかりません")
        sys.exit(1)
    
    # 自動修復システムの実行
    fixer = WorkflowAutoFixerV2(repo_path)
    
    try:
        fixer.auto_fix_loop()
        logger.info("\n✅ 自動修復プロセスが完了しました")
    except KeyboardInterrupt:
        logger.info("\n⚠️ ユーザーによって中断されました")
    except Exception as e:
        logger.error(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()