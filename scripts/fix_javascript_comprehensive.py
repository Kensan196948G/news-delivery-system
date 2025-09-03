#!/usr/bin/env python3
"""
Comprehensive JavaScript fix for GitHub Actions workflows
"""

import re
from pathlib import Path

def fix_javascript_in_yaml(content):
    """Fix JavaScript code inside YAML files"""
    
    # Fix pattern: '```'\\n\\n' → '\\`\\`\\`\\n\\n'
    # Backticks in JavaScript strings need proper escaping
    content = re.sub(r"'```'\\\\n", r"'\\`\\`\\`\\n", content)
    
    # Fix pattern: ``' → \\`\\`\\`'
    content = re.sub(r"``'\\\\n", r"\\`\\`\\`'\\n", content)
    
    # Fix empty string concatenation issues
    # const content = '' + title + ' ' + body + ''; should work fine
    # But let's ensure proper escaping
    
    # Fix JavaScript template literal patterns
    # In YAML, backticks need to be escaped in JavaScript strings
    content = re.sub(r"'```\\\\n' \+", r"'\\`\\`\\`\\n' +", content)
    content = re.sub(r"'``\\\\n' \+", r"'\\`\\`\\n' +", content)
    
    # Fix closing backtick patterns
    content = re.sub(r"\\\\n```' \+", r"\\n\\`\\`\\`' +", content)
    
    # Fix standalone backtick patterns in strings
    content = re.sub(r"'```'", r"'\\`\\`\\`'", content)
    
    return content

def main():
    workflows_dir = Path('.github/workflows')
    
    files_to_fix = [
        'auto-flow-complete.yml',
        'docs-automation.yml',
        'issue-automation.yml',
        'self-heal.yml'
    ]
    
    for file_name in files_to_fix:
        file_path = workflows_dir / file_name
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            content = fix_javascript_in_yaml(content)
            
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