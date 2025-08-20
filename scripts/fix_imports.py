#!/usr/bin/env python3
"""
Auto-fix import errors in Python files
インポートエラーの自動修正
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple

class ImportFixer:
    """インポート文の自動修正クラス"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.fixed_files = []
        self.errors = []
    
    def fix_all_files(self):
        """全Pythonファイルのインポートを修正"""
        python_files = list(self.src_path.rglob("*.py"))
        
        for file_path in python_files:
            try:
                self.fix_file(file_path)
            except Exception as e:
                self.errors.append((file_path, str(e)))
    
    def fix_file(self, file_path: Path):
        """単一ファイルのインポートを修正"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return  # 構文エラーがある場合はスキップ
        
        modified = False
        new_content = content
        
        # 相対インポートの修正
        if self._has_relative_imports(tree):
            new_content = self._fix_relative_imports(new_content, file_path)
            modified = True
        
        # 不足しているインポートの追加
        missing_imports = self._find_missing_imports(tree)
        if missing_imports:
            new_content = self._add_missing_imports(new_content, missing_imports)
            modified = True
        
        # 未使用インポートの削除
        unused_imports = self._find_unused_imports(tree, content)
        if unused_imports:
            new_content = self._remove_unused_imports(new_content, unused_imports)
            modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            self.fixed_files.append(file_path)
    
    def _has_relative_imports(self, tree: ast.AST) -> bool:
        """相対インポートの存在確認"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level > 0:  # 相対インポート
                    return True
        return False
    
    def _fix_relative_imports(self, content: str, file_path: Path) -> str:
        """相対インポートを絶対インポートに変換"""
        lines = content.split('\n')
        new_lines = []
        
        # ファイルの相対位置から絶対パスを計算
        relative_path = file_path.relative_to(self.src_path)
        package_path = str(relative_path.parent).replace(os.sep, '.')
        
        for line in lines:
            if line.strip().startswith('from .'):
                # 相対インポートを絶対インポートに変換
                parts = line.strip().split()
                if len(parts) >= 4:  # from . import something
                    level = len(parts[1]) - len(parts[1].lstrip('.'))
                    
                    if level == 1:
                        # 同じディレクトリ
                        if package_path:
                            new_line = line.replace('from .', f'from {package_path}.')
                        else:
                            new_line = line.replace('from .', 'from ')
                    else:
                        # 親ディレクトリ
                        parent_parts = package_path.split('.')
                        if len(parent_parts) >= level - 1:
                            parent_package = '.'.join(parent_parts[:-(level-1)])
                            new_line = line.replace(f'from {"." * level}', f'from {parent_package}.')
                        else:
                            new_line = line
                    
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def _find_missing_imports(self, tree: ast.AST) -> List[str]:
        """不足しているインポートを検出"""
        missing = []
        
        # 使用されているが定義されていない名前を探す
        defined_names = set()
        used_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names if hasattr(node, 'names') else []:
                    if isinstance(alias, ast.alias):
                        defined_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
        
        # 標準ライブラリで一般的に必要なもの
        standard_imports = {
            'Path': 'from pathlib import Path',
            'Dict': 'from typing import Dict',
            'List': 'from typing import List',
            'Optional': 'from typing import Optional',
            'Any': 'from typing import Any',
            'asyncio': 'import asyncio',
            'json': 'import json',
            'os': 'import os',
            'sys': 'import sys',
            'datetime': 'from datetime import datetime',
        }
        
        for name, import_stmt in standard_imports.items():
            if name in used_names and name not in defined_names:
                missing.append(import_stmt)
        
        return missing
    
    def _add_missing_imports(self, content: str, imports: List[str]) -> str:
        """不足しているインポートを追加"""
        lines = content.split('\n')
        
        # 最初のインポート文の位置を探す
        first_import_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                first_import_idx = i
                break
        
        # docstringの後にインポートを追加
        if first_import_idx == 0:
            for i, line in enumerate(lines):
                if not line.strip().startswith(('"""', "'''", '#')) and line.strip():
                    first_import_idx = i
                    break
        
        # インポートを挿入
        for imp in imports:
            if imp not in content:
                lines.insert(first_import_idx, imp)
                first_import_idx += 1
        
        return '\n'.join(lines)
    
    def _find_unused_imports(self, tree: ast.AST, content: str) -> Set[str]:
        """未使用のインポートを検出"""
        unused = set()
        
        imported_names = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names[name] = ast.get_source_segment(content, node)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names[name] = ast.get_source_segment(content, node)
        
        # 使用されている名前を収集
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)
        
        # 未使用のインポートを特定
        for name, import_line in imported_names.items():
            if name not in used_names and import_line:
                unused.add(import_line)
        
        return unused
    
    def _remove_unused_imports(self, content: str, unused: Set[str]) -> str:
        """未使用のインポートを削除"""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # 未使用のインポート行をスキップ
            if not any(unused_import in line for unused_import in unused):
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def report(self):
        """修正結果をレポート"""
        print(f"Fixed {len(self.fixed_files)} files")
        
        if self.fixed_files:
            print("\nFixed files:")
            for file in self.fixed_files:
                print(f"  - {file.relative_to(self.project_root)}")
        
        if self.errors:
            print(f"\nErrors in {len(self.errors)} files:")
            for file, error in self.errors:
                print(f"  - {file.relative_to(self.project_root)}: {error}")


def main():
    """メイン処理"""
    project_root = Path(__file__).parent.parent
    fixer = ImportFixer(project_root)
    
    print("Fixing import errors...")
    fixer.fix_all_files()
    fixer.report()
    
    return 0 if not fixer.errors else 1


if __name__ == "__main__":
    sys.exit(main())