#!/usr/bin/env python3
"""
Auto-fix type hints in Python files
型ヒントの自動修正
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

class TypeHintFixer:
    """型ヒントの自動修正クラス"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.fixed_files = []
        self.errors = []
        
        # 一般的な型マッピング
        self.type_mappings = {
            'dict': 'Dict',
            'list': 'List',
            'tuple': 'Tuple',
            'set': 'Set',
            'str': 'str',
            'int': 'int',
            'float': 'float',
            'bool': 'bool',
            'None': 'None',
        }
    
    def fix_all_files(self):
        """全Pythonファイルの型ヒントを修正"""
        python_files = list(self.src_path.rglob("*.py"))
        
        for file_path in python_files:
            try:
                self.fix_file(file_path)
            except Exception as e:
                self.errors.append((file_path, str(e)))
    
    def fix_file(self, file_path: Path):
        """単一ファイルの型ヒントを修正"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return  # 構文エラーがある場合はスキップ
        
        modified = False
        new_content = content
        
        # 関数の型ヒントを修正
        new_content, func_modified = self._fix_function_hints(new_content, tree)
        modified = modified or func_modified
        
        # 変数の型ヒントを修正
        new_content, var_modified = self._fix_variable_hints(new_content, tree)
        modified = modified or var_modified
        
        # typing インポートを追加
        if modified:
            new_content = self._ensure_typing_imports(new_content)
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            self.fixed_files.append(file_path)
    
    def _fix_function_hints(self, content: str, tree: ast.AST) -> Tuple[str, bool]:
        """関数の型ヒントを修正"""
        modified = False
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 戻り値の型が不足している場合
                if not node.returns and not node.name.startswith('_'):
                    # 関数の内容から戻り値の型を推測
                    return_type = self._infer_return_type(node)
                    if return_type:
                        # 関数定義行を探す
                        for i, line in enumerate(lines):
                            if f'def {node.name}(' in line and '->' not in line:
                                # コロンの前に型ヒントを追加
                                lines[i] = line.replace(':', f' -> {return_type}:', 1)
                                modified = True
                                break
                
                # 引数の型が不足している場合
                for arg in node.args.args:
                    if not arg.annotation and arg.arg != 'self':
                        # 引数の型を推測
                        arg_type = self._infer_argument_type(node, arg.arg)
                        if arg_type:
                            for i, line in enumerate(lines):
                                if f'{arg.arg}' in line and f'{arg.arg}:' not in line:
                                    # 引数に型ヒントを追加
                                    pattern = f'\\b{arg.arg}\\b(?!:)'
                                    replacement = f'{arg.arg}: {arg_type}'
                                    lines[i] = re.sub(pattern, replacement, lines[i], count=1)
                                    modified = True
                                    break
        
        return '\n'.join(lines), modified
    
    def _fix_variable_hints(self, content: str, tree: ast.AST) -> Tuple[str, bool]:
        """変数の型ヒントを修正"""
        modified = False
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                # すでに型注釈がある場合はスキップ
                continue
            elif isinstance(node, ast.Assign):
                # 代入文から型を推測
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_type = self._infer_variable_type(node.value)
                        if var_type and var_type != 'Any':
                            # 型注釈を追加できる場合
                            for i, line in enumerate(lines):
                                if target.id in line and ':' not in line:
                                    # クラス変数やグローバル変数の場合のみ型ヒントを追加
                                    if line.strip().startswith('self.'):
                                        continue
                                    pattern = f'\\b{target.id}\\s*='
                                    replacement = f'{target.id}: {var_type} ='
                                    if re.search(pattern, line):
                                        lines[i] = re.sub(pattern, replacement, line, count=1)
                                        modified = True
                                        break
        
        return '\n'.join(lines), modified
    
    def _infer_return_type(self, func_node: ast.FunctionDef) -> Optional[str]:
        """関数の戻り値の型を推測"""
        returns = []
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Return):
                if node.value is None:
                    returns.append('None')
                elif isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, str):
                        returns.append('str')
                    elif isinstance(node.value.value, int):
                        returns.append('int')
                    elif isinstance(node.value.value, float):
                        returns.append('float')
                    elif isinstance(node.value.value, bool):
                        returns.append('bool')
                elif isinstance(node.value, ast.Dict):
                    returns.append('Dict[str, Any]')
                elif isinstance(node.value, ast.List):
                    returns.append('List[Any]')
                elif isinstance(node.value, ast.Tuple):
                    returns.append('Tuple[Any, ...]')
        
        if not returns:
            return 'None'
        elif len(set(returns)) == 1:
            return returns[0]
        elif 'None' in returns:
            other_types = [t for t in returns if t != 'None']
            if other_types:
                return f'Optional[{other_types[0]}]'
        
        return 'Any'
    
    def _infer_argument_type(self, func_node: ast.FunctionDef, arg_name: str) -> Optional[str]:
        """引数の型を推測"""
        # 引数の使用方法から型を推測
        for node in ast.walk(func_node):
            if isinstance(node, ast.Name) and node.id == arg_name:
                parent = self._get_parent_node(func_node, node)
                if parent:
                    return self._infer_type_from_usage(parent)
        
        # デフォルトで Any を返す
        return 'Any'
    
    def _infer_variable_type(self, value_node: ast.AST) -> Optional[str]:
        """変数の型を推測"""
        if isinstance(value_node, ast.Constant):
            if isinstance(value_node.value, str):
                return 'str'
            elif isinstance(value_node.value, int):
                return 'int'
            elif isinstance(value_node.value, float):
                return 'float'
            elif isinstance(value_node.value, bool):
                return 'bool'
            elif value_node.value is None:
                return 'None'
        elif isinstance(value_node, ast.Dict):
            return 'Dict[str, Any]'
        elif isinstance(value_node, ast.List):
            return 'List[Any]'
        elif isinstance(value_node, ast.Set):
            return 'Set[Any]'
        elif isinstance(value_node, ast.Tuple):
            return 'Tuple[Any, ...]'
        elif isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                func_name = value_node.func.id
                if func_name == 'dict':
                    return 'Dict[Any, Any]'
                elif func_name == 'list':
                    return 'List[Any]'
                elif func_name == 'set':
                    return 'Set[Any]'
                elif func_name == 'tuple':
                    return 'Tuple[Any, ...]'
                elif func_name in ['Path', 'pathlib.Path']:
                    return 'Path'
        
        return None
    
    def _get_parent_node(self, tree: ast.AST, target: ast.AST) -> Optional[ast.AST]:
        """ASTノードの親ノードを取得"""
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                if child == target:
                    return node
        return None
    
    def _infer_type_from_usage(self, node: ast.AST) -> str:
        """使用方法から型を推測"""
        if isinstance(node, ast.Call):
            if hasattr(node.func, 'attr'):
                attr = node.func.attr
                if attr in ['split', 'strip', 'upper', 'lower', 'replace']:
                    return 'str'
                elif attr in ['append', 'extend', 'pop']:
                    return 'List[Any]'
                elif attr in ['keys', 'values', 'items', 'get']:
                    return 'Dict[Any, Any]'
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                return 'Union[int, float]'
        elif isinstance(node, ast.Compare):
            return 'Any'
        
        return 'Any'
    
    def _ensure_typing_imports(self, content: str) -> str:
        """必要なtypingインポートを追加"""
        lines = content.split('\n')
        
        # 使用されている型を検出
        used_types = set()
        for line in lines:
            for type_name in ['Dict', 'List', 'Optional', 'Tuple', 'Set', 'Any', 'Union']:
                if type_name in line:
                    used_types.add(type_name)
        
        if not used_types:
            return content
        
        # 既存のtypingインポートを確認
        has_typing_import = False
        typing_import_line = -1
        
        for i, line in enumerate(lines):
            if 'from typing import' in line:
                has_typing_import = True
                typing_import_line = i
                break
        
        if has_typing_import:
            # 既存のインポートに追加
            import_line = lines[typing_import_line]
            for type_name in used_types:
                if type_name not in import_line:
                    # インポート行の末尾に追加
                    import_line = import_line.rstrip()
                    if import_line.endswith(')'):
                        import_line = import_line[:-1] + f', {type_name})'
                    else:
                        import_line += f', {type_name}'
            lines[typing_import_line] = import_line
        else:
            # 新しいインポートを追加
            import_statement = f'from typing import {", ".join(sorted(used_types))}'
            
            # 適切な位置を探す
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('#'):
                    if line.strip().startswith(('"""', "'''")):
                        # docstringをスキップ
                        in_docstring = True
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip().endswith(('"""', "'''")):
                                insert_pos = j + 1
                                break
                    elif line.strip().startswith(('import ', 'from ')):
                        insert_pos = i
                        break
                    else:
                        insert_pos = i
                        break
            
            lines.insert(insert_pos, import_statement)
        
        return '\n'.join(lines)
    
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
    fixer = TypeHintFixer(project_root)
    
    print("Fixing type hints...")
    fixer.fix_all_files()
    fixer.report()
    
    return 0 if not fixer.errors else 1


if __name__ == "__main__":
    sys.exit(main())