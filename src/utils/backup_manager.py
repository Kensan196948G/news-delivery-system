"""
Backup Manager for News Delivery System
バックアップマネージャー - データベースとファイルのバックアップ機能
"""

import os
import shutil
import sqlite3
import logging
import gzip
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

from .config import get_config
from .logger import setup_logger


logger = setup_logger(__name__)


class BackupManager:
    """バックアップマネージャー - データベースとファイルのバックアップ"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.backup_dir = Path(self.config.get('paths.backup', '/media/kensan/LinuxHDD/news-delivery-system/data/backup'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # バックアップ設定
        self.max_generations = self.config.get('data_retention.backup_generations', 7)
        self.compression_enabled = True
        
        logger.info(f"Backup manager initialized: {self.backup_dir}")
    
    def create_full_backup(self) -> Dict[str, str]:
        """完全バックアップの作成"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"news_system_full_{timestamp}"
            backup_path = self.backup_dir / f"{backup_name}.tar.gz"
            
            logger.info(f"Creating full backup: {backup_name}")
            
            # バックアップするディレクトリ
            source_dirs = [
                self.config.get('paths.database', '/media/kensan/LinuxHDD/news-delivery-system/data/database'),
                self.config.get('paths.articles', '/media/kensan/LinuxHDD/news-delivery-system/data/articles'),
                self.config.get('paths.reports', '/media/kensan/LinuxHDD/news-delivery-system/data/reports'),
                self.config.get('paths.cache', '/media/kensan/LinuxHDD/news-delivery-system/data/cache'),
                '/media/kensan/LinuxHDD/news-delivery-system/config'
            ]
            
            # tarファイル作成
            with tarfile.open(backup_path, 'w:gz') as tar:
                for source_dir in source_dirs:
                    source_path = Path(source_dir)
                    if source_path.exists():
                        tar.add(source_path, arcname=source_path.name)
                        logger.debug(f"Added to backup: {source_path}")
                    else:
                        logger.warning(f"Source directory not found: {source_path}")
            
            # バックアップ情報を記録
            backup_info = {
                'type': 'full',
                'name': backup_name,
                'path': str(backup_path),
                'size_mb': backup_path.stat().st_size / (1024 * 1024),
                'created_at': timestamp,
                'source_dirs': [str(d) for d in source_dirs]
            }
            
            # バックアップ情報ファイル作成
            info_path = self.backup_dir / f"{backup_name}.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Full backup created: {backup_path} ({backup_info['size_mb']:.1f}MB)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create full backup: {e}")
            raise
    
    def create_database_backup(self) -> Dict[str, str]:
        """データベースのバックアップ"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"news_database_{timestamp}"
            
            # データベースパス
            db_path = Path(self.config.get('paths.database', '/media/kensan/LinuxHDD/news-delivery-system/data/database')) / 'news_system.db'
            
            if not db_path.exists():
                logger.warning(f"Database not found: {db_path}")
                return {}
            
            # バックアップファイルパス
            backup_path = self.backup_dir / f"{backup_name}.db.gz"
            
            logger.info(f"Creating database backup: {backup_name}")
            
            # データベースをgzip圧縮してバックアップ
            with open(db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # バックアップ情報
            backup_info = {
                'type': 'database',
                'name': backup_name,
                'path': str(backup_path),
                'size_mb': backup_path.stat().st_size / (1024 * 1024),
                'created_at': timestamp,
                'source_db': str(db_path)
            }
            
            # バックアップ情報ファイル作成
            info_path = self.backup_dir / f"{backup_name}.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Database backup created: {backup_path} ({backup_info['size_mb']:.1f}MB)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            raise
    
    def restore_database(self, backup_path: str) -> bool:
        """データベースの復元"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # 復元先データベースパス
            db_path = Path(self.config.get('paths.database', '/media/kensan/LinuxHDD/news-delivery-system/data/database')) / 'news_system.db'
            
            # 現在のデータベースをバックアップ
            if db_path.exists():
                backup_current = db_path.parent / f"news_system_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(db_path, backup_current)
                logger.info(f"Current database backed up to: {backup_current}")
            
            # gzip圧縮されたバックアップを復元
            with gzip.open(backup_file, 'rb') as f_in:
                with open(db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            return False
    
    def cleanup_old_backups(self) -> int:
        """古いバックアップの削除"""
        try:
            # バックアップファイル一覧取得
            backup_files = []
            
            for file_path in self.backup_dir.glob("*.tar.gz"):
                try:
                    # ファイル名から日時を抽出
                    name_parts = file_path.stem.split('_')
                    if len(name_parts) >= 3:
                        date_str = name_parts[-2] + '_' + name_parts[-1]
                        created_at = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                        backup_files.append((file_path, created_at))
                except ValueError:
                    logger.warning(f"Could not parse backup date from: {file_path}")
                    continue
            
            # データベースバックアップも含める
            for file_path in self.backup_dir.glob("*.db.gz"):
                try:
                    name_parts = file_path.stem.split('_')
                    if len(name_parts) >= 3:
                        date_str = name_parts[-2] + '_' + name_parts[-1].replace('.db', '')
                        created_at = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                        backup_files.append((file_path, created_at))
                except ValueError:
                    logger.warning(f"Could not parse backup date from: {file_path}")
                    continue
            
            # 日時でソート（新しい順）
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 古いファイルを削除
            deleted_count = 0
            for i, (file_path, created_at) in enumerate(backup_files):
                if i >= self.max_generations:
                    try:
                        file_path.unlink()
                        
                        # 対応するJSONファイルも削除
                        json_path = file_path.with_suffix('.json')
                        if json_path.exists():
                            json_path.unlink()
                        
                        logger.debug(f"Deleted old backup: {file_path}")
                        deleted_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to delete backup {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backup files")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0
    
    def get_backup_list(self) -> List[Dict]:
        """バックアップファイル一覧取得"""
        try:
            backups = []
            
            # JSONファイルから情報を読み取り
            for json_file in self.backup_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                    
                    # ファイルが実際に存在するかチェック
                    backup_path = Path(backup_info['path'])
                    if backup_path.exists():
                        backup_info['exists'] = True
                        backup_info['current_size_mb'] = backup_path.stat().st_size / (1024 * 1024)
                    else:
                        backup_info['exists'] = False
                    
                    backups.append(backup_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to read backup info from {json_file}: {e}")
                    continue
            
            # 作成日時でソート（新しい順）
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to get backup list: {e}")
            return []
    
    def verify_backup(self, backup_path: str) -> bool:
        """バックアップファイルの整合性確認"""
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # ファイル拡張子に応じて検証
            if backup_path.endswith('.tar.gz'):
                # tarファイルの整合性確認
                with tarfile.open(backup_file, 'r:gz') as tar:
                    # ファイル一覧を取得して確認
                    members = tar.getmembers()
                    logger.debug(f"Backup contains {len(members)} files/directories")
                    return True
                    
            elif backup_path.endswith('.db.gz'):
                # gzipファイルの整合性確認
                with gzip.open(backup_file, 'rb') as f:
                    # ファイルを読んで整合性確認
                    f.read(1024)  # 最初の1KBを読んで確認
                    return True
            
            else:
                logger.warning(f"Unknown backup format: {backup_path}")
                return False
                
        except Exception as e:
            logger.error(f"Backup verification failed for {backup_path}: {e}")
            return False
    
    def get_backup_statistics(self) -> Dict:
        """バックアップ統計情報"""
        try:
            backups = self.get_backup_list()
            
            total_backups = len(backups)
            total_size_mb = sum(b.get('current_size_mb', 0) for b in backups if b.get('exists', False))
            
            # タイプ別統計
            type_stats = {}
            for backup in backups:
                backup_type = backup.get('type', 'unknown')
                if backup_type not in type_stats:
                    type_stats[backup_type] = {'count': 0, 'size_mb': 0}
                
                type_stats[backup_type]['count'] += 1
                if backup.get('exists', False):
                    type_stats[backup_type]['size_mb'] += backup.get('current_size_mb', 0)
            
            # 最新・最古バックアップ
            latest_backup = backups[0] if backups else None
            oldest_backup = backups[-1] if backups else None
            
            return {
                'total_backups': total_backups,
                'total_size_mb': total_size_mb,
                'type_statistics': type_stats,
                'latest_backup': latest_backup,
                'oldest_backup': oldest_backup,
                'backup_directory': str(self.backup_dir),
                'max_generations': self.max_generations
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup statistics: {e}")
            return {}
    
    def schedule_auto_backup(self, backup_type: str = 'database') -> bool:
        """自動バックアップのスケジュール実行"""
        try:
            logger.info(f"Starting scheduled {backup_type} backup")
            
            if backup_type == 'full':
                backup_info = self.create_full_backup()
            else:  # database
                backup_info = self.create_database_backup()
            
            if backup_info:
                # 古いバックアップのクリーンアップ
                cleaned_count = self.cleanup_old_backups()
                
                logger.info(f"Scheduled backup completed: {backup_info['name']} "
                           f"({backup_info['size_mb']:.1f}MB), cleaned {cleaned_count} old files")
                return True
            else:
                logger.error("Scheduled backup failed")
                return False
                
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
            return False


# グローバルバックアップマネージャーインスタンス
_backup_manager_instance = None


def get_backup_manager() -> BackupManager:
    """グローバルバックアップマネージャー取得"""
    global _backup_manager_instance
    if _backup_manager_instance is None:
        _backup_manager_instance = BackupManager()
    return _backup_manager_instance