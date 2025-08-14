#!/usr/bin/env python3
"""
Bash配列構文修正スクリプト
GitHub Actions内のBash配列変数を正しい形式に修正
"""

import re
from pathlib import Path

def fix_bash_arrays(content):
    """Bash配列構文を修正"""
    
    # パターン1: "$\{\{array[@]\}\}" → "${array[@]}"
    content = re.sub(r'\$\\?\{\\?\{([a-zA-Z_][a-zA-Z0-9_]*\[@\])\\?\}\\?\}', r'${\\1}', content)
    
    # パターン2: $\{\{#array[@]\}\} → ${#array[@]}
    content = re.sub(r'\$\\?\{\\?\{#([a-zA-Z_][a-zA-Z0-9_]*\[@\])\\?\}\\?\}', r'${#\\1}', content)
    
    # パターン3: $\{\{array[*]\}\} → ${array[*]}
    content = re.sub(r'\$\\?\{\\?\{([a-zA-Z_][a-zA-Z0-9_]*\[\*\])\\?\}\\?\}', r'${\\1}', content)
    
    # パターン4: エスケープが残っている場合の処理
    content = re.sub(r'\\"?\$\\?\{\\?\{([^}]+\[@\])\\?\}\\?\}\\"?', r'"${\\1}"', content)
    content = re.sub(r'\$\\?\{\\?\{#([^}]+\[@\])\\?\}\\?\}', r'${#\\1}', content)
    content = re.sub(r'\$\\?\{\\?\{([^}]+\[\*\])\\?\}\\?\}', r'${\\1}', content)
    
    return content

def main():
    workflows_dir = Path('.github/workflows')
    
    for file_path in workflows_dir.glob('*.yml'):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = fix_bash_arrays(content)
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修正完了: {file_path.name}")
        else:
            print(f"ℹ️ 修正不要: {file_path.name}")

if __name__ == "__main__":
    main()