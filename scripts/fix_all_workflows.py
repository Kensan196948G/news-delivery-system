#!/usr/bin/env python3
"""
完全なGitHub Actionsワークフロー修正スクリプト
全ての構文エラーを修正
"""

import re
import sys
from pathlib import Path

def fix_auto_flow_complete(content):
    """auto-flow-complete.yml専用の修正"""
    
    # 1. Bash配列変数の修正 "${critical_files[@]}" が正しい形式
    content = re.sub(r'\$\\{\\{{(critical_files\[@\])\\}\\}', r'${\\1}', content)
    content = re.sub(r'\$\\{\\{{#(DETECTION_RESULTS\[@\])\\}\\}', r'${#\\1}', content)
    content = re.sub(r'\$\\{\\{{(DETECTION_RESULTS\[\*\])\\}\\}', r'${\\1}', content)
    content = re.sub(r'\$\\{\\{{(DETECTION_RESULTS\[@\])\\}\\}', r'${\\1}', content)
    
    # 2. GitHub Actions変数の修正 - 間違った構文を修正
    # ' + { var + '} → ${{ var }}
    content = re.sub(r"' \+ \{ steps\.repair\.outputs\.repair_successful\s+\+ '\}", r"${{ steps.repair.outputs.repair_successful }}", content)
    content = re.sub(r"' \+ \{ steps\.repair\.outputs\.repair_summary\s+\+ '\}", r"${{ steps.repair.outputs.repair_summary }}", content)
    content = re.sub(r"' \+ \{ steps\.create-pr\.outputs\.pr_number\s+\+ '\}", r"${{ steps.create-pr.outputs.pr_number }}", content)
    content = re.sub(r"' \+ \{ steps\.create-pr\.outputs\.pr_url\s+\+ '\}", r"${{ steps.create-pr.outputs.pr_url }}", content)
    content = re.sub(r"' \+ \{ secrets\.GITHUB_TOKEN\s+\+ '\}", r"${{ secrets.GITHUB_TOKEN }}", content)
    content = re.sub(r"' \+ \{ env\.REPAIR_BRANCH\s+\+ '\}", r"${{ env.REPAIR_BRANCH }}", content)
    content = re.sub(r"' \+ \{ env\.NOTIFICATION_EMAIL\s+\+ '\}", r"${{ env.NOTIFICATION_EMAIL }}", content)
    
    # needs.*の変数
    content = re.sub(r"' \+ \{ needs\.auto-issue-creation\.outputs\.issue_number\s+\+ '\}", r"${{ needs.auto-issue-creation.outputs.issue_number }}", content)
    content = re.sub(r"' \+ \{ needs\.auto-detection\.outputs\.detection_summary\s+\+ '\}", r"${{ needs.auto-detection.outputs.detection_summary }}", content)
    content = re.sub(r"' \+ \{ needs\.auto-repair\.outputs\.repair_summary\s+\+ '\}", r"${{ needs.auto-repair.outputs.repair_summary }}", content)
    content = re.sub(r"' \+ \{ needs\.auto-pr-creation\.outputs\.pr_number\s+\+ '\}", r"${{ needs.auto-pr-creation.outputs.pr_number }}", content)
    content = re.sub(r"' \+ \{ needs\.auto-pr-creation\.outputs\.pr_url\s+\+ '\}", r"${{ needs.auto-pr-creation.outputs.pr_url }}", content)
    
    # 3. Bash配列の長さの修正
    content = re.sub(r"' \+ #REPAIR_ACTIONS\[@\] \+ '", r"${#REPAIR_ACTIONS[@]}", content)
    content = re.sub(r"' \+ REPAIR_ACTIONS\[\*\] \+ '", r"${REPAIR_ACTIONS[*]}", content)
    
    # 4. バッククォートの修正
    content = re.sub(r"''``", r"'```", content)
    content = re.sub(r"``'", r"```'", content)
    content = re.sub(r"''`'", r"'```'", content)
    
    return content

def fix_docs_automation(content):
    """docs-automation.yml専用の修正"""
    
    # Bash配列変数の修正
    content = re.sub(r'\$\\{\\{{(required_sections\[@\])\\}\\}', r'${\\1}', content)
    content = re.sub(r'\$\\{\\{{#(missing_sections\[@\])\\}\\}', r'${#\\1}', content)
    content = re.sub(r'\$\\{\\{{(missing_sections\[\*\])\\}\\}', r'${\\1}', content)
    
    # GitHub Actions変数の修正
    content = re.sub(r"'\$\\{\\{{ (steps\.[^}]+) \\}\\}}'", r"'${{ \\1 }}'", content)
    
    return content

def fix_security_automation(content):
    """security-automation.yml専用の修正"""
    
    # JavaScript内のテンプレート変数修正
    content = re.sub(r"'\$\\{\\{{(issue\.[^}]+)\\}\\}:\$\\{\\{{(issue\.[^}]+)\\}\\}'\\'", r"' + \\1 + ':' + \\2 + '\\'", content)
    
    return content

def fix_issue_automation(content):
    """issue-automation.yml専用の修正 (現在は問題なし)"""
    return content

def main():
    workflows_dir = Path('.github/workflows')
    
    fixes = {
        'auto-flow-complete.yml': fix_auto_flow_complete,
        'docs-automation.yml': fix_docs_automation,
        'security-automation.yml': fix_security_automation,
        'issue-automation.yml': fix_issue_automation
    }
    
    for file_name, fix_func in fixes.items():
        file_path = workflows_dir / file_name
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            content = fix_func(content)
            
            if content != original:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修正完了: {file_name}")
            else:
                print(f"ℹ️ 修正不要: {file_name}")
        else:
            print(f"❌ ファイルなし: {file_name}")

if __name__ == "__main__":
    main()