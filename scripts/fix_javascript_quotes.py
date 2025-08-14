#!/usr/bin/env python3
"""
Fix JavaScript quote issues in GitHub Actions workflows
"""

import re
from pathlib import Path

def fix_quotes(content):
    """Fix various quote issues in JavaScript"""
    
    # Replace curly quotes with straight quotes
    content = content.replace(''', "'")
    content = content.replace(''', "'")
    content = content.replace('"', '"')
    content = content.replace('"', '"')
    
    # Fix empty string concatenations with proper quotes
    content = re.sub(r"const content = '' \+ ([^;]+) \+ '';", r"const content = '' + \1 + '';", content)
    
    # Fix template literal syntax issues
    content = re.sub(r"'\\`\\`\\`'", r"'```'", content)
    content = re.sub(r"''\\`\\`", r"'```", content)
    content = re.sub(r"\\`\\`''", r"```'", content)
    
    # Fix JavaScript template issues in GitHub Actions context
    # Backticks in JavaScript strings inside YAML need to be handled carefully
    content = re.sub(r"'\\\\`", r"'`", content)
    content = re.sub(r"\\\\`'", r"`'", content)
    
    return content

def main():
    workflows_dir = Path('.github/workflows')
    
    for file_path in workflows_dir.glob('*.yml'):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        content = fix_quotes(content)
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修正完了: {file_path.name}")
        else:
            print(f"ℹ️ 修正不要: {file_path.name}")

if __name__ == "__main__":
    main()