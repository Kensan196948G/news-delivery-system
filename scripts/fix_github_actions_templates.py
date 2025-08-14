#!/usr/bin/env python3
"""
GitHub Actions テンプレート変数修正スクリプト
"""

import re
import sys
from pathlib import Path

def fix_templates(file_path):
    """テンプレート変数を修正"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. 誤ったエスケープ $\{\{{ → ${{
    content = re.sub(r'\$\\?\{\\?\{\{', r'${{', content)
    
    # 2. 誤ったエスケープ \}\}} → }}
    content = re.sub(r'\\?\}\\?\}\}', r'}}', content)
    
    # 3. Bash内の配列変数修正 "$\{\{array[@]\}\}" → "${array[@]}"
    content = re.sub(r'"\$\{\{([^}]+\[@\])\}\}"', r'"${\\1}"', content)
    
    # 4. Bash内の変数修正 $\{\{#array[@]\}\} → ${#array[@]}
    content = re.sub(r'\$\{\{#([^}]+\[@\])\}\}', r'${#\\1}', content)
    
    # 5. Bash内の配列要素参照 $\{\{array[*]\}\} → ${array[*]}
    content = re.sub(r'\$\{\{([^}]+\[\*\])\}\}', r'${\\1}', content)
    
    # 6. JavaScript内の誤った構文 ' + { var + '} → ${{ var }}
    content = re.sub(r"' \+ \{ ([^}]+) \+ '\}", r"${{ \\1 }}", content)
    
    # 7. JavaScript内の誤った構文 ' + #array[@] + ' → ${#array[@]}
    content = re.sub(r"' \+ #([^[]+\[@\]) \+ '", r"${#\\1}", content)
    
    # 8. JavaScript内の誤った構文 ' + array[*] + ' → ${array[*]}
    content = re.sub(r"' \+ ([^[]+\[\*\]) \+ '", r"${\\1}", content)
    
    # 9. バッククォートの修正 ''`` → \`\`\`
    content = re.sub(r"''\`\`", r"'\\`\\`\\`", content)
    
    # 10. バッククォートの修正 \`\`' → \`\`\`'
    content = re.sub(r"\`\`'", r"\\`\\`\\`'", content)
    
    # 11. バッククォートの修正 ''`' → '\`\`\`'
    content = re.sub(r"''\`'", r"'\\`\\`\\`'", content)
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    workflows_dir = Path('.github/workflows')
    
    files_to_fix = [
        'auto-flow-complete.yml',
        'issue-automation.yml'
    ]
    
    for file_name in files_to_fix:
        file_path = workflows_dir / file_name
        if file_path.exists():
            if fix_templates(file_path):
                print(f"✅ 修正完了: {file_name}")
            else:
                print(f"ℹ️ 修正不要: {file_name}")
        else:
            print(f"❌ ファイルなし: {file_name}")

if __name__ == "__main__":
    main()