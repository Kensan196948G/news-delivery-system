#!/usr/bin/env python3
"""
Auto-fix dependency issues
依存関係の自動修正
"""

import subprocess
import sys
import re
from pathlib import Path
from typing import List, Set, Dict, Tuple

class DependencyFixer:
    """依存関係の自動修正クラス"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.requirements_file = project_root / "requirements.txt"
        self.requirements_dev_file = project_root / "requirements-dev.txt"
        self.fixed_dependencies = []
        self.errors = []
    
    def fix_all(self):
        """全ての依存関係問題を修正"""
        print("Analyzing dependencies...")
        
        # 1. インポートエラーから不足パッケージを検出
        missing_packages = self._find_missing_packages()
        if missing_packages:
            self._add_missing_packages(missing_packages)
        
        # 2. バージョン競合を解決
        conflicts = self._find_version_conflicts()
        if conflicts:
            self._resolve_conflicts(conflicts)
        
        # 3. 廃止されたパッケージを更新
        deprecated = self._find_deprecated_packages()
        if deprecated:
            self._update_deprecated(deprecated)
        
        # 4. requirements.txtを最適化
        self._optimize_requirements()
        
        # 5. 依存関係を検証
        self._validate_dependencies()
    
    def _find_missing_packages(self) -> Set[str]:
        """不足しているパッケージを検出"""
        missing = set()
        
        # Pythonファイルからインポートを抽出
        imports = self._extract_imports()
        
        # 現在インストールされているパッケージ
        installed = self._get_installed_packages()
        
        # requirements.txtのパッケージ
        required = self._get_required_packages()
        
        # パッケージ名のマッピング
        package_mapping = {
            'cv2': 'opencv-python',
            'PIL': 'Pillow',
            'sklearn': 'scikit-learn',
            'yaml': 'PyYAML',
            'dotenv': 'python-dotenv',
            'googleapiclient': 'google-api-python-client',
            'bs4': 'beautifulsoup4',
            'httpx': 'httpx',
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
            'pydantic': 'pydantic',
            'jwt': 'PyJWT',
            'redis': 'redis',
            'celery': 'celery',
            'sqlalchemy': 'SQLAlchemy',
            'alembic': 'alembic',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'matplotlib': 'matplotlib',
            'seaborn': 'seaborn',
            'plotly': 'plotly',
            'anthropic': 'anthropic',
            'openai': 'openai',
            'pdfkit': 'pdfkit',
            'wkhtmltopdf': 'pdfkit',  # pdfkitの依存
            'deepl': 'deepl',
            'newsapi': 'newsapi-python',
            'psutil': 'psutil',
            'aiohttp': 'aiohttp',
            'jinja2': 'Jinja2',
            'pytest': 'pytest',
            'pytest_asyncio': 'pytest-asyncio',
            'pytest_cov': 'pytest-cov',
            'mypy': 'mypy',
            'black': 'black',
            'ruff': 'ruff',
            'isort': 'isort',
            'bandit': 'bandit',
            'safety': 'safety',
        }
        
        # インポートされているが不足しているパッケージを特定
        for import_name in imports:
            base_name = import_name.split('.')[0]
            
            # 標準ライブラリは除外
            if base_name in self._get_stdlib_modules():
                continue
            
            # パッケージ名を変換
            package_name = package_mapping.get(base_name, base_name)
            
            # インストールされていない、かつrequirementsにもない
            if package_name not in installed and package_name not in required:
                missing.add(package_name)
        
        return missing
    
    def _extract_imports(self) -> Set[str]:
        """Pythonファイルからインポートを抽出"""
        imports = set()
        
        src_path = self.project_root / "src"
        for py_file in src_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # import文を抽出
                import_pattern = r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)'
                from_pattern = r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)'
                
                for match in re.finditer(import_pattern, content, re.MULTILINE):
                    imports.add(match.group(1))
                
                for match in re.finditer(from_pattern, content, re.MULTILINE):
                    imports.add(match.group(1))
            
            except Exception as e:
                self.errors.append((py_file, str(e)))
        
        return imports
    
    def _get_installed_packages(self) -> Set[str]:
        """インストールされているパッケージを取得"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
                capture_output=True,
                text=True,
                check=True
            )
            
            packages = set()
            for line in result.stdout.split('\n'):
                if '==' in line:
                    package_name = line.split('==')[0].lower()
                    packages.add(package_name)
            
            return packages
        
        except subprocess.CalledProcessError:
            return set()
    
    def _get_required_packages(self) -> Set[str]:
        """requirements.txtのパッケージを取得"""
        packages = set()
        
        for req_file in [self.requirements_file, self.requirements_dev_file]:
            if req_file.exists():
                with open(req_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # パッケージ名を抽出
                            if '==' in line:
                                package_name = line.split('==')[0]
                            elif '>=' in line:
                                package_name = line.split('>=')[0]
                            elif '<=' in line:
                                package_name = line.split('<=')[0]
                            else:
                                package_name = line.split()[0]
                            
                            packages.add(package_name.lower())
        
        return packages
    
    def _get_stdlib_modules(self) -> Set[str]:
        """Python標準ライブラリのモジュール一覧"""
        return {
            'abc', 'aifc', 'argparse', 'array', 'ast', 'asyncio', 'atexit',
            'base64', 'bdb', 'binascii', 'bisect', 'builtins',
            'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code',
            'codecs', 'codeop', 'collections', 'colorsys', 'compileall',
            'concurrent', 'configparser', 'contextlib', 'copy', 'copyreg',
            'cProfile', 'crypt', 'csv', 'ctypes', 'curses',
            'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis',
            'distutils', 'doctest',
            'email', 'encodings', 'enum', 'errno',
            'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
            'fractions', 'ftplib', 'functools', 'future',
            'gc', 'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip',
            'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib',
            'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress',
            'itertools',
            'json',
            'keyword',
            'lib2to3', 'linecache', 'locale', 'logging', 'lzma',
            'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes', 'mmap',
            'modulefinder', 'multiprocessing',
            'netrc', 'nis', 'nntplib', 'numbers',
            'operator', 'optparse', 'os', 'ossaudiodev',
            'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes',
            'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'pprint',
            'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr',
            'pydoc', 'pyexpat',
            'queue', 'quopri',
            'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
            'runpy',
            'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex',
            'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr',
            'socket', 'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat',
            'statistics', 'string', 'stringprep', 'struct', 'subprocess',
            'sunau', 'symbol', 'symtable', 'sys', 'sysconfig', 'syslog',
            'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios',
            'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter',
            'token', 'tokenize', 'trace', 'traceback', 'tracemalloc', 'tty',
            'turtle', 'types', 'typing',
            'unicodedata', 'unittest', 'urllib', 'uu', 'uuid',
            'venv',
            'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound',
            'wsgiref',
            'xdrlib', 'xml', 'xmlrpc',
            'zipapp', 'zipfile', 'zipimport', 'zlib'
        }
    
    def _add_missing_packages(self, packages: Set[str]):
        """不足しているパッケージを追加"""
        if not packages:
            return
        
        print(f"Adding {len(packages)} missing packages...")
        
        # requirements.txtに追加
        with open(self.requirements_file, 'a') as f:
            for package in sorted(packages):
                # バージョンを取得
                version = self._get_latest_version(package)
                if version:
                    line = f"{package}=={version}"
                else:
                    line = package
                
                f.write(f"\n{line}")
                self.fixed_dependencies.append(('added', package))
                print(f"  Added: {line}")
    
    def _get_latest_version(self, package: str) -> str:
        """パッケージの最新バージョンを取得"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'index', 'versions', package],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # バージョン情報を解析
            if 'Available versions:' in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Available versions:' in line:
                        versions = line.split(':')[1].strip().split(',')
                        if versions:
                            return versions[0].strip()
        except:
            pass
        
        return ''
    
    def _find_version_conflicts(self) -> List[Tuple[str, str, str]]:
        """バージョン競合を検出"""
        conflicts = []
        
        # pip checkを実行
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'check'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # 競合を解析
                for line in result.stdout.split('\n'):
                    if 'requires' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            conflicts.append((parts[0], parts[2], parts[3]))
        except:
            pass
        
        return conflicts
    
    def _resolve_conflicts(self, conflicts: List[Tuple[str, str, str]]):
        """バージョン競合を解決"""
        print(f"Resolving {len(conflicts)} version conflicts...")
        
        for package, required_by, version in conflicts:
            print(f"  Fixing: {package} (required by {required_by})")
            
            # requirements.txtを更新
            self._update_package_version(package, version)
            self.fixed_dependencies.append(('updated', f"{package}=={version}"))
    
    def _update_package_version(self, package: str, version: str):
        """パッケージのバージョンを更新"""
        if not self.requirements_file.exists():
            return
        
        lines = []
        updated = False
        
        with open(self.requirements_file, 'r') as f:
            for line in f:
                if line.strip().startswith(package):
                    lines.append(f"{package}=={version}\n")
                    updated = True
                else:
                    lines.append(line)
        
        if not updated:
            lines.append(f"{package}=={version}\n")
        
        with open(self.requirements_file, 'w') as f:
            f.writelines(lines)
    
    def _find_deprecated_packages(self) -> Dict[str, str]:
        """廃止されたパッケージを検出"""
        deprecated_mapping = {
            'pycryptodome': 'cryptography',
            'nose': 'pytest',
            'mock': 'unittest.mock',  # Python 3.3+では標準ライブラリ
            'futures': 'concurrent.futures',  # Python 3.2+では標準ライブラリ
        }
        
        deprecated = {}
        
        if self.requirements_file.exists():
            with open(self.requirements_file, 'r') as f:
                for line in f:
                    for old_package, new_package in deprecated_mapping.items():
                        if old_package in line:
                            deprecated[old_package] = new_package
        
        return deprecated
    
    def _update_deprecated(self, deprecated: Dict[str, str]):
        """廃止されたパッケージを更新"""
        print(f"Updating {len(deprecated)} deprecated packages...")
        
        for old_package, new_package in deprecated.items():
            print(f"  Replacing: {old_package} -> {new_package}")
            self._replace_package(old_package, new_package)
            self.fixed_dependencies.append(('replaced', f"{old_package} -> {new_package}"))
    
    def _replace_package(self, old_package: str, new_package: str):
        """パッケージを置き換え"""
        if not self.requirements_file.exists():
            return
        
        lines = []
        
        with open(self.requirements_file, 'r') as f:
            for line in f:
                if old_package in line:
                    if not new_package.startswith('unittest') and not new_package.startswith('concurrent'):
                        # 標準ライブラリでない場合は置き換え
                        version = self._get_latest_version(new_package)
                        if version:
                            lines.append(f"{new_package}=={version}\n")
                        else:
                            lines.append(f"{new_package}\n")
                else:
                    lines.append(line)
        
        with open(self.requirements_file, 'w') as f:
            f.writelines(lines)
    
    def _optimize_requirements(self):
        """requirements.txtを最適化"""
        if not self.requirements_file.exists():
            return
        
        print("Optimizing requirements.txt...")
        
        # 重複を削除し、ソート
        packages = {}
        
        with open(self.requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '==' in line:
                        name, version = line.split('==')
                        packages[name] = version
                    else:
                        packages[line] = ''
        
        # ソートして書き戻し
        with open(self.requirements_file, 'w') as f:
            f.write("# News Delivery System Dependencies\n")
            f.write("# Auto-generated and optimized\n\n")
            
            for name in sorted(packages.keys()):
                if packages[name]:
                    f.write(f"{name}=={packages[name]}\n")
                else:
                    f.write(f"{name}\n")
    
    def _validate_dependencies(self):
        """依存関係を検証"""
        print("Validating dependencies...")
        
        try:
            # pip checkを実行
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'check'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ All dependencies are valid")
            else:
                print("⚠️  Some dependency issues remain:")
                print(result.stdout)
        except Exception as e:
            print(f"❌ Validation failed: {e}")
    
    def report(self):
        """修正結果をレポート"""
        print(f"\nFixed {len(self.fixed_dependencies)} dependency issues")
        
        if self.fixed_dependencies:
            print("\nChanges made:")
            for action, detail in self.fixed_dependencies:
                print(f"  - {action}: {detail}")
        
        if self.errors:
            print(f"\nErrors encountered: {len(self.errors)}")
            for file, error in self.errors:
                print(f"  - {file}: {error}")


def main():
    """メイン処理"""
    project_root = Path(__file__).parent.parent
    fixer = DependencyFixer(project_root)
    
    print("Fixing dependencies...")
    fixer.fix_all()
    fixer.report()
    
    return 0 if not fixer.errors else 1


if __name__ == "__main__":
    sys.exit(main())