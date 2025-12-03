"""
Backup Configuration Module
============================

Manages backup system configuration and settings.

Save location: tools/maintenance/backup_config.py

Responsibilities:
- Load and validate backup configuration from environment
- Provide configuration access to backup components
- Define backup-related constants
- Manage retention policies

Dependencies:
- os (environment variables)
- pathlib (path handling)
- core.data_paths (system paths)
"""

import os
from pathlib import Path
from typing import List

from core.data_paths import map_pro_paths


# Backup retention constants
DEFAULT_RETENTION_DAYS = 30
MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 365

# Backup history constants
MAX_BACKUP_HISTORY_ENTRIES = 100

# File size constants
BYTES_PER_MB = 1024 * 1024

# Environment variable keys
ENV_RETENTION_DAYS = 'MAP_PRO_BACKUP_RETENTION_DAYS'
ENV_COMPRESS_BACKUPS = 'MAP_PRO_COMPRESS_BACKUPS'


class BackupConfig:
    """
    Configuration manager for backup system.
    
    Loads configuration from environment variables and provides
    validated access to backup settings.
    
    Attributes:
        backup_root: Root directory for all backups
        retention_days: Number of days to retain backups
        compress_backups: Whether to compress backup files
        database_names: List of database names to backup
    """
    
    def __init__(self):
        """Initialize backup configuration from environment."""
        self.backup_root: Path = map_pro_paths.database_backups
        self.retention_days: int = self._load_retention_days()
        self.compress_backups: bool = self._load_compression_setting()
        self.database_names: List[str] = ['core', 'parsed', 'library', 'mapped']
    
    def _load_retention_days(self) -> int:
        """
        Load and validate retention days from environment.
        
        Returns:
            Validated retention days value
            
        Raises:
            ValueError: If retention days is outside valid range
        """
        try:
            retention_str = os.getenv(ENV_RETENTION_DAYS, str(DEFAULT_RETENTION_DAYS))
            retention = int(retention_str)
            
            if retention < MIN_RETENTION_DAYS or retention > MAX_RETENTION_DAYS:
                raise ValueError(
                    f"Retention days must be between {MIN_RETENTION_DAYS} "
                    f"and {MAX_RETENTION_DAYS}"
                )
            
            return retention
            
        except ValueError as e:
            raise ValueError(f"Invalid retention days configuration: {e}")
    
    def _load_compression_setting(self) -> bool:
        """
        Load compression setting from environment.
        
        Returns:
            True if compression is enabled, False otherwise
        """
        compress_str = os.getenv(ENV_COMPRESS_BACKUPS, 'true')
        return compress_str.lower() == 'true'
    
    def get_database_backup_dir(self, database_name: str) -> Path:
        """
        Get backup directory for specific database.
        
        Args:
            database_name: Name of the database
            
        Returns:
            Path to database backup directory
        """
        return self.backup_root / 'databases' / database_name
    
    def get_json_backup_dir(self) -> Path:
        """
        Get directory for JSON data backups.
        
        Returns:
            Path to JSON backup directory
        """
        return self.backup_root / 'json_data'
    
    def get_log_dir(self) -> Path:
        """
        Get directory for backup logs.
        
        Returns:
            Path to backup log directory
        """
        return self.backup_root / 'logs'
    
    def get_backup_directories(self) -> List[Path]:
        """
        Get all backup directory paths.
        
        Returns:
            List of all backup directory paths
        """
        return [
            self.backup_root,
            self.backup_root / 'databases',
            self.get_json_backup_dir(),
            self.get_log_dir()
        ]


__all__ = [
    'BackupConfig',
    'DEFAULT_RETENTION_DAYS',
    'MIN_RETENTION_DAYS',
    'MAX_RETENTION_DAYS',
    'MAX_BACKUP_HISTORY_ENTRIES',
    'BYTES_PER_MB'
]