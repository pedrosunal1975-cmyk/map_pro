"""
Backup Cleanup Manager
======================

Manages cleanup of old backups based on retention policies.

Save location: tools/maintenance/backup_cleanup_manager.py

Responsibilities:
- Remove backups older than retention period
- Track cleanup statistics (files removed, space freed)
- Handle cleanup errors gracefully
- Clean both database and JSON backups

Dependencies:
- pathlib (path handling)
- datetime (date calculations)
- core.system_logger (logging)
- tools.maintenance.backup_config (configuration)
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from core.system_logger import get_logger
from tools.maintenance.backup_config import BackupConfig, BYTES_PER_MB


logger = get_logger(__name__, 'maintenance')


class BackupCleanupManager:
    """
    Manages cleanup of old backup files.
    
    Removes backups that exceed the configured retention period,
    tracking cleanup statistics and handling errors.
    
    Attributes:
        config: Backup configuration instance
        logger: Logger instance for this manager
    """
    
    def __init__(self, config: BackupConfig):
        """
        Initialize cleanup manager.
        
        Args:
            config: Backup configuration instance
        """
        self.config = config
        self.logger = logger
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """
        Remove backups older than retention period.
        
        Scans all backup directories and removes files that are older
        than the configured retention period.
        
        Returns:
            Dictionary containing:
                - success: Overall success flag
                - files_removed: Count of files removed
                - space_freed_mb: Space freed in megabytes
                - errors: List of error messages
        """
        self.logger.info(
            f"Starting cleanup of backups older than {self.config.retention_days} days"
        )
        
        cutoff_date = self._calculate_cutoff_date()
        
        result = {
            'success': True,
            'files_removed': 0,
            'space_freed_mb': 0.0,
            'errors': []
        }
        
        try:
            # Cleanup database backups
            self._cleanup_database_backups(cutoff_date, result)
            
            # Cleanup JSON data backups
            self._cleanup_json_backups(cutoff_date, result)
            
            # Round space freed for readability
            result['space_freed_mb'] = round(result['space_freed_mb'], 2)
            
            self.logger.info(
                f"Cleanup complete: {result['files_removed']} files removed, "
                f"{result['space_freed_mb']} MB freed"
            )
            
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}", exc_info=True)
            result['success'] = False
            result['errors'].append(str(e))
        
        return result
    
    def _calculate_cutoff_date(self) -> datetime:
        """
        Calculate cutoff date for backup retention.
        
        Returns:
            Datetime before which backups should be removed
        """
        return datetime.now(timezone.utc) - timedelta(days=self.config.retention_days)
    
    def _cleanup_database_backups(
        self,
        cutoff_date: datetime,
        result: Dict[str, Any]
    ) -> None:
        """
        Cleanup database backup files.
        
        Args:
            cutoff_date: Date before which to remove backups
            result: Result dictionary to update with cleanup statistics
        """
        db_backup_dir = self.config.backup_root / 'databases'
        
        if not db_backup_dir.exists():
            self.logger.debug("Database backup directory does not exist, skipping")
            return
        
        for db_name in self.config.database_names:
            db_dir = self.config.get_database_backup_dir(db_name)
            
            if not db_dir.exists():
                continue
            
            self._cleanup_directory(db_dir, cutoff_date, result)
    
    def _cleanup_json_backups(
        self,
        cutoff_date: datetime,
        result: Dict[str, Any]
    ) -> None:
        """
        Cleanup JSON data backup files.
        
        Args:
            cutoff_date: Date before which to remove backups
            result: Result dictionary to update with cleanup statistics
        """
        json_backup_dir = self.config.get_json_backup_dir()
        
        if json_backup_dir.exists():
            self._cleanup_directory(json_backup_dir, cutoff_date, result)
    
    def _cleanup_directory(
        self,
        directory: Path,
        cutoff_date: datetime,
        result: Dict[str, Any]
    ) -> None:
        """
        Cleanup files in a specific directory.
        
        Args:
            directory: Directory to cleanup
            cutoff_date: Date before which to remove files
            result: Result dictionary to update
        """
        for backup_file in directory.iterdir():
            if not backup_file.is_file():
                continue
            
            try:
                if self._should_remove_file(backup_file, cutoff_date):
                    self._remove_file(backup_file, result)
                    
            except Exception as e:
                error_msg = f"Failed to process {backup_file}: {e}"
                result['errors'].append(error_msg)
                self.logger.error(error_msg)
    
    def _should_remove_file(self, file_path: Path, cutoff_date: datetime) -> bool:
        """
        Determine if file should be removed based on age.
        
        Args:
            file_path: Path to file to check
            cutoff_date: Cutoff date for removal
            
        Returns:
            True if file should be removed, False otherwise
        """
        mtime = datetime.fromtimestamp(
            file_path.stat().st_mtime,
            tz=timezone.utc
        )
        return mtime < cutoff_date
    
    def _remove_file(self, file_path: Path, result: Dict[str, Any]) -> None:
        """
        Remove a file and update statistics.
        
        Args:
            file_path: Path to file to remove
            result: Result dictionary to update
        """
        file_size = file_path.stat().st_size
        file_path.unlink()
        
        result['files_removed'] += 1
        result['space_freed_mb'] += file_size / BYTES_PER_MB
        
        self.logger.info(f"Removed old backup: {file_path.name}")


__all__ = ['BackupCleanupManager']