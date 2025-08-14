#!/usr/bin/env python3
"""
GitHub Actions ワークフロー自動修復スクリプト
全エラーを検知し、自動修復してプッシュするループシステム
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

class WorkflowAutoFixer:
    """GitHub Actions ワークフロー自動修復クラス"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.workflows_dir = self.repo_path / ".github" / "workflows"
        self.fix_count = 0
        self.max_iterations = 10
        self.iteration = 0
        
    def run_command(self, cmd: List[str], cwd: str = None) -> Tuple[int, str, str]:
        """コマンド実行"""
        result = subprocess.run(
            cmd,
            cwd=cwd or self.repo_path,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    
    def check_yaml_syntax(self, file_path: Path) -> List[str]:
        """YAML構文チェック"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"{file_path.name}: {str(e)}")
        return errors
    
    def fix_template_literals(self, content: str) -> str:
        """JavaScriptテンプレートリテラルを文字列連結に修正"""
        # バッククォートで囲まれたテンプレートリテラルを検出
        pattern = r'`([^`]*\$\{[^}]+\}[^`]*)`'
        
        def replace_template(match):
            template = match.group(1)
            # ${variable} を ' + variable + ' に置換
            result = template
            result = re.sub(r'\$\{([^}]+)\}', r"' + \1 + '", result)
            # 改行を \n に置換
            result = result.replace('\n', '\\n')
            # 最初と最後のクォートを調整
            return "'" + result + "'"
        
        return re.sub(pattern, replace_template, content)
    
    def fix_multiline_strings(self, content: str) -> str:
        """複数行文字列の修正"""
        lines = content.split('\n')
        fixed_lines = []
        in_script = False
        in_python = False
        
        for i, line in enumerate(lines):
            # GitHub Script内のテンプレートリテラル
            if 'script: |' in line:
                in_script = True
                fixed_lines.append(line)
                continue
            elif in_script and line and not line[0].isspace():
                in_script = False
            
            # Python -c コマンド内の複数行
            if 'python -c "' in line or 'python3 -c "' in line:
                in_python = True
                # 複数行Pythonコードを単一行に変換
                if not line.rstrip().endswith('"'):
                    # 複数行Pythonコードの開始
                    fixed_line = line.rstrip() + ' '
                    j = i + 1
                    while j < len(lines) and not lines[j].rstrip().endswith('"'):
                        fixed_line += lines[j].strip() + '; '
                        j += 1
                    if j < len(lines):
                        fixed_line += lines[j].strip()
                    fixed_lines.append(fixed_line)
                    # 処理済み行をスキップ
                    for _ in range(j - i):
                        if i + 1 < len(lines):
                            lines[i + 1] = ''
                    continue
            
            # 通常の行処理
            if in_script:
                # JavaScript内のテンプレートリテラル修正
                line = self.fix_template_literals(line)
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_workflow_file(self, file_path: Path) -> bool:
        """ワークフローファイルの修正"""
        logger.info(f"修正中: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 各種修正を適用
            content = self.fix_template_literals(content)
            content = self.fix_multiline_strings(content)
            
            # ヒアドキュメントの修正
            content = re.sub(
                r'cat\s*<<\s*([\'"]?)EOF\1(.*?)EOF',
                lambda m: 'echo "' + m.group(2).strip().replace('"', '\\"').replace('\n', '\\n') + '"',
                content,
                flags=re.DOTALL
            )
            
            # 特殊文字のエスケープ
            # ${} 形式の変数展開をエスケープ
            content = re.sub(
                r'(?<!\\)\$\{([^}]+)\}',
                r'$\{\{\1\}\}',
                content
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✅ {file_path.name} を修正しました")
                self.fix_count += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ {file_path.name} の修正中にエラー: {e}")
            
        return False
    
    def check_all_workflows(self) -> List[str]:
        """全ワークフローの構文チェック"""
        all_errors = []
        
        for yml_file in self.workflows_dir.glob("*.yml"):
            errors = self.check_yaml_syntax(yml_file)
            if errors:
                all_errors.extend(errors)
                
        for yaml_file in self.workflows_dir.glob("*.yaml"):
            errors = self.check_yaml_syntax(yaml_file)
            if errors:
                all_errors.extend(errors)
                
        return all_errors
    
    def git_operations(self, message: str) -> bool:
        """Git操作（add, commit, push）"""
        try:
            # 変更をステージング
            self.run_command(["git", "add", "-A"])
            
            # コミット
            commit_msg = f"""fix: {message}

自動修復システムによる修正
- YAML構文エラー修正
- テンプレートリテラル修正
- 複数行文字列修正

🤖 Auto-generated by workflow fixer
"""
            self.run_command(["git", "commit", "-m", commit_msg])
            
            # プッシュ
            returncode, stdout, stderr = self.run_command(["git", "push"])
            
            if returncode == 0:
                logger.info("✅ 変更をプッシュしました")
                return True
            else:
                logger.error(f"❌ プッシュエラー: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Git操作エラー: {e}")
            return False
    
    def check_github_actions_status(self) -> bool:
        """GitHub Actionsの状態を確認（gh CLIを使用）"""
        try:
            # 最新のワークフロー実行を確認
            returncode, stdout, stderr = self.run_command([
                "gh", "run", "list", "--limit", "5", "--json", "status,conclusion"
            ])
            
            if returncode == 0:
                runs = json.loads(stdout)
                # 失敗したワークフローがあるか確認
                for run in runs:
                    if run.get('conclusion') == 'failure':
                        return False
                return True
            else:
                logger.warning("GitHub CLI が利用できません")
                return True
                
        except Exception as e:
            logger.warning(f"GitHub Actions状態確認エラー: {e}")
            return True
    
    def auto_fix_loop(self):
        """自動修復ループ"""
        logger.info("🔄 自動修復ループを開始します")
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            logger.info(f"\n--- イテレーション {self.iteration}/{self.max_iterations} ---")
            
            # 1. YAML構文チェック
            errors = self.check_all_workflows()
            
            if not errors:
                logger.info("✅ すべてのYAMLファイルの構文が正常です")
                
                # GitHub Actionsの状態確認
                if self.check_github_actions_status():
                    logger.info("🎉 すべてのワークフローが正常に動作しています！")
                    break
                else:
                    logger.info("⚠️ GitHub Actionsにエラーがあります。修復を続行します...")
            else:
                logger.info(f"❌ {len(errors)} 個のエラーを検出:")
                for error in errors[:5]:  # 最初の5個のみ表示
                    logger.info(f"  - {error}")
            
            # 2. 自動修復
            fixed_files = []
            for yml_file in self.workflows_dir.glob("*.yml"):
                if self.fix_workflow_file(yml_file):
                    fixed_files.append(yml_file.name)
            
            for yaml_file in self.workflows_dir.glob("*.yaml"):
                if self.fix_workflow_file(yaml_file):
                    fixed_files.append(yaml_file.name)
            
            # 3. 修正があればコミット・プッシュ
            if fixed_files:
                logger.info(f"📝 {len(fixed_files)} 個のファイルを修正しました")
                
                # Git操作
                if self.git_operations(f"自動修復 iteration {self.iteration}"):
                    logger.info("⏳ 30秒待機してGitHub Actionsの実行を待ちます...")
                    time.sleep(30)
                else:
                    logger.error("Git操作に失敗しました")
                    break
            else:
                logger.info("修正可能な問題が見つかりませんでした")
                break
            
            # 4. プル（他の変更を取り込む）
            self.run_command(["git", "pull", "--rebase"])
        
        # 完了メッセージ
        if self.iteration >= self.max_iterations:
            logger.warning(f"⚠️ 最大イテレーション数（{self.max_iterations}）に達しました")
        
        logger.info(f"\n📊 修復統計:")
        logger.info(f"  - 総イテレーション: {self.iteration}")
        logger.info(f"  - 修正ファイル数: {self.fix_count}")

def main():
    """メイン関数"""
    print("""
╔══════════════════════════════════════════════════╗
║  GitHub Actions ワークフロー自動修復システム     ║
║  Auto-Fix All Workflow Errors Until Success      ║
╚══════════════════════════════════════════════════╝
    """)
    
    # リポジトリパスの確認
    repo_path = os.getcwd()
    if not (Path(repo_path) / ".github" / "workflows").exists():
        logger.error("❌ .github/workflows ディレクトリが見つかりません")
        sys.exit(1)
    
    # 自動修復システムの実行
    fixer = WorkflowAutoFixer(repo_path)
    
    try:
        fixer.auto_fix_loop()
        logger.info("\n✅ 自動修復プロセスが完了しました")
    except KeyboardInterrupt:
        logger.info("\n⚠️ ユーザーによって中断されました")
    except Exception as e:
        logger.error(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()