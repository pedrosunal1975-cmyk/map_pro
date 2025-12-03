"""
Backup Listing Manager
======================

Manages listing and inventory of available backups.

Save location: tools/maintenance/backup_listing_manager.py

Responsibilities:
- List all available backup files
- Provide backup metadata (size, creation date)
- Organize backup listings by type
- Calculate backup statistics

Dependencies:
- pathlib (path handling)
- datetime (date handling)
- core.system_logger (logging)
- tools.maintenance.backup_config (configuration)
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

from core.system_logger import get_logger
from tools.maintenance.backup_config import BackupConfig, BYTES_PER_MB


logger = get_logger(__name__, 'maintenance')


class BackupListingManager:
    """
    Manages listing of available backups.
    
    Provides inventory and metadata for all backup files in the system.
    
    Attributes:
        config: Backup configuration instance
        logger: Logger instance for this manager
    """
    
    def __init__(self, config: BackupConfig):
        """
        Initialize listing manager.
        
        Args:
            config: Backup configuration instance
        """
        self.config = config
        self.logger = logger
    
    def list_all_backups(self) -> Dict[str, Any]:
        """
        List all available backups.
        
        Returns:
            Dictionary containing:
                - databases: Dict mapping database names to backup lists
                - json_data: List of JSON data backups
        """
        backups = {
            'databases': {},
            'json_data': []
        }
        
        try:
            self._list_database_backups(backups)
            self._list_json_backups(backups)
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}", exc_info=True)
        
        return backups
    
    def _list_database_backups(self, backups: Dict[str, Any]) -> None:
        """
        List all database backup files.
        
        Args:
            backups: Backups dictionary to populate
        """
        db_backup_dir = self.config.backup_root / 'databases'
        
        for db_name in self.config.database_names:
            db_dir = self.config.get_database_backup_dir(db_name)
            
            if not db_dir.exists():
                backups['databases'][db_name] = []
                continue
            
            db_backups = self._get_directory_backups(db_dir)
            backups['databases'][db_name] = db_backups
    
    def _list_json_backups(self, backups: Dict[str, Any]) -> None:
        """
        List all JSON data backup files.
        
        Args:
            backups: Backups dictionary to populate
        """
        json_backup_dir = self.config.get_json_backup_dir()
        
        if json_backup_dir.exists():
            backups['json_data'] = self._get_directory_backups(json_backup_dir)
    
    def _get_directory_backups(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Get backup file information for a directory.
        
        Args:
            directory: Directory to scan for backups
            
        Returns:
            List of backup file information dictionaries
        """
        backups = []
        
        try:
            for backup_file in sorted(directory.iterdir(), reverse=True):
                if not backup_file.is_file():
                    continue
                
                backup_info = self._get_file_info(backup_file)
                backups.append(backup_info)
                
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return backups
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get metadata for a backup file.
        
        Args:
            file_path: Path to backup file
            
        Returns:
            Dictionary with file metadata:
                - file: Filename
                - path: Full path string
                - size_mb: File size in megabytes
                - created: ISO format creation timestamp
        """
        file_stat = file_path.stat()
        file_size_mb = file_stat.st_size / BYTES_PER_MB
        
        mtime = datetime.fromtimestamp(
            file_stat.st_mtime,
            tz=timezone.utc
        )
        
        return {
            'file': file_path.name,
            'path': str(file_path),
            'size_mb': round(file_size_mb, 2),
            'created': mtime.isoformat()
        }
    
    def get_backup_counts(self) -> Dict[str, int]:
        """
        Get count of backups by type.
        
        Returns:
            Dictionary mapping backup types to counts
        """
        backups = self.list_all_backups()
        counts = {}
        
        for db_name in self.config.database_names:
            counts[db_name] = len(backups['databases'].get(db_name, []))
        
        counts['json_data'] = len(backups['json_data'])
        
        return counts


__all__ = ['BackupListingManager']