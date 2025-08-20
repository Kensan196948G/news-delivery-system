"""
Cross-platform Path Resolution Module
クロスプラットフォーム対応パス解決モジュール

Windows/Linux環境の違いを吸収し、動的にパスを解決
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Union
import json


class PathResolver:
    """環境に依存しないパス解決クラス"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.is_windows = self.platform == 'windows'
        self.is_linux = self.platform == 'linux'
        self.is_mac = self.platform == 'darwin'
        
        # プロジェクトルートの自動検出
        self.project_root = self._detect_project_root()
        
        # 外付けストレージパスの自動検出
        self.external_storage = self._detect_external_storage()
        
        # データディレクトリの決定
        self.data_root = self._determine_data_root()
        
    def _detect_project_root(self) -> Path:
        """プロジェクトルートを自動検出"""
        # 現在のファイルから2階層上がプロジェクトルート
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        
        # CLAUDE.mdファイルの存在でプロジェクトルートを確認
        if (project_root / "CLAUDE.md").exists():
            return project_root
        
        # 環境変数から取得を試みる
        env_root = os.getenv('NEWS_PROJECT_ROOT')
        if env_root:
            return Path(env_root)
        
        # フォールバック
        return project_root
    
    def _detect_external_storage(self) -> Optional[Path]:
        """外付けストレージを自動検出"""
        # 環境変数から優先的に取得
        env_storage = os.getenv('EXTERNAL_STORAGE_PATH')
        if env_storage:
            path = Path(env_storage)
            if path.exists():
                return path
        
        # Windows環境での検出
        if self.is_windows:
            # E:ドライブをチェック（CLAUDE.md仕様）
            e_drive = Path("E:/")
            if e_drive.exists():
                news_path = e_drive / "NewsDeliverySystem"
                if news_path.exists():
                    return news_path
                # 存在しない場合は作成を試みる
                try:
                    news_path.mkdir(parents=True, exist_ok=True)
                    return news_path
                except:
                    pass
            
            # D:ドライブもチェック
            d_drive = Path("D:/")
            if d_drive.exists():
                news_path = d_drive / "NewsDeliverySystem"
                if news_path.exists():
                    return news_path
        
        # Linux環境での検出
        if self.is_linux:
            # 現在のマウントされた外付けHDDをチェック
            linux_mount = Path("/mnt/Linux-ExHDD/news-delivery-system")
            if linux_mount.exists():
                data_path = linux_mount / "data"
                if data_path.exists():
                    return data_path
                
            # 汎用的なマウントポイントをチェック
            mount_points = [
                "/mnt/external",
                "/media/external",
                "/external",
                f"/media/{os.getenv('USER', 'user')}/external"
            ]
            
            for mount in mount_points:
                mount_path = Path(mount)
                if mount_path.exists():
                    news_path = mount_path / "NewsDeliverySystem"
                    if news_path.exists():
                        return news_path
        
        return None
    
    def _determine_data_root(self) -> Path:
        """データルートディレクトリを決定"""
        # 外付けストレージが利用可能な場合
        if self.external_storage:
            return self.external_storage
        
        # プロジェクトルート内のdataディレクトリをフォールバック
        data_dir = self.project_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def get_data_path(self, *paths: str) -> Path:
        """データディレクトリ内のパスを取得"""
        full_path = self.data_root
        for path in paths:
            full_path = full_path / path
        
        # ディレクトリの場合は作成
        if not full_path.suffix:  # 拡張子がない = ディレクトリと判定
            full_path.mkdir(parents=True, exist_ok=True)
        else:
            # ファイルの場合は親ディレクトリを作成
            full_path.parent.mkdir(parents=True, exist_ok=True)
        
        return full_path
    
    def get_config_path(self, filename: str = "config.json") -> Path:
        """設定ファイルのパスを取得"""
        config_dir = self.project_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / filename
    
    def get_template_path(self, template_name: str) -> Path:
        """テンプレートファイルのパスを取得"""
        template_dir = self.project_root / "src" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        return template_dir / template_name
    
    def get_log_path(self, log_name: Optional[str] = None) -> Path:
        """ログファイルのパスを取得"""
        log_dir = self.get_data_path("logs")
        if log_name:
            return log_dir / log_name
        return log_dir
    
    def get_database_path(self, db_name: str = "news_system.db") -> Path:
        """データベースファイルのパスを取得"""
        db_dir = self.get_data_path("database")
        return db_dir / db_name
    
    def get_cache_path(self, cache_name: Optional[str] = None) -> Path:
        """キャッシュディレクトリのパスを取得"""
        cache_dir = self.get_data_path("cache")
        if cache_name:
            return cache_dir / cache_name
        return cache_dir
    
    def get_report_path(self, report_type: str = "daily") -> Path:
        """レポートディレクトリのパスを取得"""
        return self.get_data_path("reports", report_type)
    
    def get_article_path(self, article_type: str = "raw") -> Path:
        """記事データディレクトリのパスを取得"""
        return self.get_data_path("articles", article_type)
    
    def get_backup_path(self) -> Path:
        """バックアップディレクトリのパスを取得"""
        return self.get_data_path("backup")
    
    def convert_windows_path(self, path: str) -> Path:
        """Windows形式のパスをクロスプラットフォーム形式に変換"""
        # E:\NewsDeliverySystem\ 形式を処理
        if self.is_linux and path.startswith("E:\\"):
            # Linux環境でWindows形式のパスを変換
            relative_path = path.replace("E:\\NewsDeliverySystem\\", "").replace("\\", "/")
            return self.data_root / relative_path
        
        # C:\NewsDeliverySystem\ 形式を処理
        if self.is_linux and path.startswith("C:\\"):
            relative_path = path.replace("C:\\NewsDeliverySystem\\", "").replace("\\", "/")
            return self.project_root / relative_path
        
        return Path(path)
    
    def resolve_path(self, path: Union[str, Path]) -> Path:
        """任意のパスを環境に応じて解決"""
        if isinstance(path, str):
            # Windows形式のパスを変換
            if "\\" in path:
                path = self.convert_windows_path(path)
            else:
                path = Path(path)
        
        # 相対パスの場合はプロジェクトルートからの相対パスとして解決
        if not path.is_absolute():
            path = self.project_root / path
        
        return path
    
    def get_platform_info(self) -> dict:
        """プラットフォーム情報を取得"""
        return {
            "platform": self.platform,
            "is_windows": self.is_windows,
            "is_linux": self.is_linux,
            "is_mac": self.is_mac,
            "project_root": str(self.project_root),
            "data_root": str(self.data_root),
            "external_storage": str(self.external_storage) if self.external_storage else None,
            "python_version": sys.version,
        }
    
    def validate_paths(self) -> dict:
        """重要なパスの存在を検証"""
        paths_to_check = {
            "project_root": self.project_root,
            "data_root": self.data_root,
            "config": self.get_config_path(),
            "database": self.get_database_path(),
            "logs": self.get_log_path(),
            "cache": self.get_cache_path(),
            "reports": self.get_report_path(),
        }
        
        validation_results = {}
        for name, path in paths_to_check.items():
            validation_results[name] = {
                "path": str(path),
                "exists": path.exists() if path.suffix else path.is_dir(),
                "writable": os.access(path.parent if path.suffix else path, os.W_OK) if path.exists() else False
            }
        
        return validation_results


# グローバルインスタンス
_path_resolver_instance = None


def get_path_resolver() -> PathResolver:
    """PathResolverのシングルトンインスタンスを取得"""
    global _path_resolver_instance
    if _path_resolver_instance is None:
        _path_resolver_instance = PathResolver()
    return _path_resolver_instance


# 便利関数
def resolve_path(path: Union[str, Path]) -> Path:
    """パスを解決する便利関数"""
    resolver = get_path_resolver()
    return resolver.resolve_path(path)


def get_data_path(*paths: str) -> Path:
    """データパスを取得する便利関数"""
    resolver = get_path_resolver()
    return resolver.get_data_path(*paths)


def get_project_root() -> Path:
    """プロジェクトルートを取得する便利関数"""
    resolver = get_path_resolver()
    return resolver.project_root