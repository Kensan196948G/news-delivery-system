#!/usr/bin/env python3
"""
Weekly Backup Script for News Delivery System
ニュース配信システムの週次バックアップ
"""

import os
import shutil
import sqlite3
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

class NewsSystemBackup:
    def __init__(self):
        self.project_root = Path("/media/kensan/LinuxHDD/news-delivery-system")
        self.backup_root = self.project_root / "backups"
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def create_backup(self):
        """Complete system backup"""
        print(f"🗄️ Starting backup: {self.timestamp}")
        
        # Create backup directory
        backup_dir = self.backup_root / f"backup_{self.timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Backup database
            self.backup_database(backup_dir)
            
            # Backup reports
            self.backup_reports(backup_dir)
            
            # Backup logs (last 30 days)
            self.backup_recent_logs(backup_dir)
            
            # Backup configuration
            self.backup_configuration(backup_dir)
            
            # Create backup summary
            self.create_backup_summary(backup_dir)
            
            # Cleanup old backups (keep last 12 weeks)
            self.cleanup_old_backups()
            
            print(f"✅ Backup completed: {backup_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def backup_database(self, backup_dir):
        """Backup SQLite database"""
        db_path = self.project_root / "data" / "database" / "news.db"
        
        if db_path.exists():
            # Create compressed backup
            backup_path = backup_dir / "database_backup.db.gz"
            
            with open(db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Create readable SQL dump
            sql_dump_path = backup_dir / "database_dump.sql"
            
            with sqlite3.connect(str(db_path)) as conn:
                with open(sql_dump_path, 'w') as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")
            
            print(f"✅ Database backed up")
        else:
            print("⚠️ Database not found")
    
    def backup_reports(self, backup_dir):
        """Backup recent reports (last 30 days)"""
        reports_dir = self.project_root / "data" / "reports"
        
        if reports_dir.exists():
            backup_reports_dir = backup_dir / "reports"
            backup_reports_dir.mkdir(exist_ok=True)
            
            # Get reports from last 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for report_file in reports_dir.rglob("*.html"):
                if report_file.stat().st_mtime > cutoff_date.timestamp():
                    relative_path = report_file.relative_to(reports_dir)
                    backup_path = backup_reports_dir / relative_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(report_file, backup_path)
            
            print("✅ Reports backed up")
    
    def backup_recent_logs(self, backup_dir):
        """Backup logs from last 30 days"""
        logs_dir = self.project_root / "logs"
        
        if logs_dir.exists():
            backup_logs_dir = backup_dir / "logs"
            backup_logs_dir.mkdir(exist_ok=True)
            
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for log_file in logs_dir.rglob("*.log"):
                if log_file.stat().st_mtime > cutoff_date.timestamp():
                    relative_path = log_file.relative_to(logs_dir)
                    backup_path = backup_logs_dir / relative_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Compress log files
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
            
            print("✅ Logs backed up")
    
    def backup_configuration(self, backup_dir):
        """Backup configuration files"""
        config_files = [
            ".env",
            "config/config.json",
            "requirements.txt"
        ]
        
        config_backup_dir = backup_dir / "config"
        config_backup_dir.mkdir(exist_ok=True)
        
        for config_file in config_files:
            source_path = self.project_root / config_file
            if source_path.exists():
                backup_path = config_backup_dir / source_path.name
                shutil.copy2(source_path, backup_path)
        
        print("✅ Configuration backed up")
    
    def create_backup_summary(self, backup_dir):
        """Create backup summary report"""
        summary = {
            "backup_timestamp": self.timestamp,
            "backup_date": datetime.now().isoformat(),
            "project_path": str(self.project_root),
            "backup_contents": {
                "database": (backup_dir / "database_backup.db.gz").exists(),
                "database_dump": (backup_dir / "database_dump.sql").exists(),
                "reports": len(list((backup_dir / "reports").rglob("*.*"))) if (backup_dir / "reports").exists() else 0,
                "logs": len(list((backup_dir / "logs").rglob("*.*"))) if (backup_dir / "logs").exists() else 0,
                "config_files": len(list((backup_dir / "config").rglob("*.*"))) if (backup_dir / "config").exists() else 0
            },
            "system_info": {
                "python_version": os.sys.version,
                "backup_size_mb": sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()) / (1024*1024)
            }
        }
        
        summary_path = backup_dir / "backup_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Backup summary: {summary['backup_contents']}")
    
    def cleanup_old_backups(self):
        """Remove backups older than 12 weeks"""
        cutoff_date = datetime.now() - timedelta(weeks=12)
        
        if self.backup_root.exists():
            for backup_folder in self.backup_root.glob("backup_*"):
                if backup_folder.is_dir():
                    folder_time = datetime.fromtimestamp(backup_folder.stat().st_mtime)
                    if folder_time < cutoff_date:
                        shutil.rmtree(backup_folder)
                        print(f"🗑️ Removed old backup: {backup_folder.name}")

def main():
    """Main execution"""
    print("🗄️ News Delivery System - Weekly Backup")
    print("=" * 50)
    
    backup_system = NewsSystemBackup()
    
    if backup_system.create_backup():
        print("\n✅ Backup completed successfully!")
    else:
        print("\n❌ Backup failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())