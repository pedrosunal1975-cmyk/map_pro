"""
Map Pro Backup Manager
======================

Main backup manager coordinating all backup and restore operations.

Save location: tools/maintenance/backup_manager.py

Responsibilities:
- Coordinates backup operations for databases and JSON files
- Handles restore operations
- Manages retention policies
- Provides backup status and listing

This is the main facade/interface for backup operations. It delegates
to specialized managers for specific responsibilities:
- BackupConfig: Configuration management
- BackupDirectoryManager: Directory structure
- BackupCoordinator: Full backup orchestration
- BackupCleanupManager: Old backup removal
- BackupListingManager: Backup inventory
- BackupHistoryLogger: Operation history logging

Configuration:
- Uses .env for retention settings
- Backup location: /mnt/map_pro/databases/backups/

Dependencies:
- pathlib (path handling)
- core.system_logger (logging)
- tools.maintenance.backup_config (configuration)
- tools.maintenance.backup_directory_manager (directory management)
- tools.maintenance.backup_coordinator (backup orchestration)
- tools.maintenance.backup_cleanup_manager (cleanup operations)
- tools.maintenance.backup_listing_manager (backup listing)
- tools.maintenance.backup_history_logger (history logging)
- tools.maintenance.backup_operations (backup execution)
- tools.maintenance.restore_operations (restore execution)
"""

from pathlib import Path
from typing import Dict, Any

from core.system_logger import get_logger
from tools.maintenance.backup_config import BackupConfig
from tools.maintenance.backup_directory_manager import BackupDirectoryManager
from tools.maintenance.backup_coordinator import BackupCoordinator
from tools.maintenance.backup_cleanup_manager import BackupCleanupManager
from tools.maintenance.backup_listing_manager import BackupListingManager
from tools.maintenance.backup_history_logger import BackupHistoryLogger
from tools.maintenance.backup_operations import BackupOperations
from tools.maintenance.restore_operations import RestoreOperations


logger = get_logger(__name__, 'maintenance')


class BackupManager:
    """
    Main facade for backup system operations.
    
    Provides a unified interface for all backup-related operations,
    delegating to specialized managers for specific tasks.
    
    Attributes:
        config: Backup configuration
        directory_manager: Directory structure manager
        backup_coordinator: Full backup orchestrator
        cleanup_manager: Old backup cleanup handler
        listing_manager: Backup inventory manager
        history_logger: Backup history tracker
        restore_ops: Restore operations handler
        logger: Logger instance for this manager
    """
    
    def __init__(self):
        """
        Initialize backup manager with all component managers.
        
        Creates and configures all specialized managers required for
        backup operations.
        """
        self.logger = logger
        
        # Initialize configuration
        self.config = BackupConfig()
        
        # Initialize directory manager
        self.directory_manager = BackupDirectoryManager(self.config)
        
        # Initialize backup operations handler
        backup_ops = BackupOperations(
            self.config.backup_root,
            self.config.compress_backups
        )
        
        # Initialize specialized managers
        self.backup_coordinator = BackupCoordinator(self.config, backup_ops)
        self.cleanup_manager = BackupCleanupManager(self.config)
        self.listing_manager = BackupListingManager(self.config)
        self.history_logger = BackupHistoryLogger(self.config)
        
        # Initialize restore operations handler
        self.restore_ops = RestoreOperations()
        
        # Ensure backup directories exist
        self._initialize_directories()
        
        # Log initialization
        self._log_initialization()
    
    def _initialize_directories(self) -> None:
        """Initialize backup directory structure."""
        success, errors = self.directory_manager.ensure_backup_directories()
        
        if not success:
            self.logger.warning(
                f"Some backup directories could not be created: {len(errors)} errors"
            )
            for error in errors:
                self.logger.debug(error)
    
    def _log_initialization(self) -> None:
        """Log initialization information."""
        self.logger.info("Backup manager initialized")
        self.logger.info(f"Retention policy: {self.config.retention_days} days")
        self.logger.info(
            f"Compression: {'enabled' if self.config.compress_backups else 'disabled'}"
        )
        self.logger.info(f"Backup root: {self.config.backup_root}")
    
    def create_full_backup(self) -> Dict[str, Any]:
        """
        Create complete system backup.
        
        Orchestrates backup of all databases and JSON data files,
        logs the result to history, and returns the backup summary.
        
        Returns:
            Dictionary containing:
                - backup_name: Name of this backup
                - timestamp: ISO format timestamp
                - success: Overall success flag
                - databases: Database backup results by name
                - json_data: JSON data backup results
                - errors: List of error messages
        """
        result = self.backup_coordinator.create_full_backup()
        
        # Log to history
        self.history_logger.log_backup_result(result)
        
        return result
    
    def restore_database(
        self,
        db_name: str,
        backup_file: Path,
        drop_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Restore database from backup.
        
        Args:
            db_name: Database name to restore
            backup_file: Path to backup file
            drop_existing: Whether to drop existing database first
            
        Returns:
            Dictionary containing restore result:
                - success: Success flag
                - database: Database name restored
                - backup_file: Path to backup file used
                - error: Error message if failed
        """
        self.logger.info(f"Restoring database {db_name} from {backup_file}")
        
        result = self.restore_ops.restore_database(
            db_name,
            backup_file,
            drop_existing
        )
        
        if result.get('success', False):
            self.logger.info(f"Database {db_name} restored successfully")
        else:
            self.logger.error(f"Database {db_name} restore failed: {result.get('error')}")
        
        return result
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """
        Remove backups older than retention period.
        
        Delegates to cleanup manager to remove old backups and
        returns cleanup statistics.
        
        Returns:
            Dictionary containing:
                - success: Overall success flag
                - files_removed: Count of files removed
                - space_freed_mb: Space freed in megabytes
                - errors: List of error messages
        """
        return self.cleanup_manager.cleanup_old_backups()
    
    def list_backups(self) -> Dict[str, Any]:
        """
        List all available backups.
        
        Delegates to listing manager to provide inventory of all
        backup files with metadata.
        
        Returns:
            Dictionary containing:
                - databases: Dict mapping database names to backup lists
                - json_data: List of JSON data backups
                
            Each backup entry contains:
                - file: Filename
                - path: Full path string
                - size_mb: File size in megabytes
                - created: ISO format creation timestamp
        """
        return self.listing_manager.list_all_backups()
    
    def get_backup_status(self) -> Dict[str, Any]:
        """
        Get current backup system status.
        
        Provides overview of backup system configuration and
        available backup counts.
        
        Returns:
            Dictionary containing:
                - backup_directory: Root backup directory path
                - retention_days: Configured retention period
                - compression_enabled: Compression setting
                - available_backups: Count of backups by type
        """
        status = {
            'backup_directory': str(self.config.backup_root),
            'retention_days': self.config.retention_days,
            'compression_enabled': self.config.compress_backups,
            'available_backups': {}
        }
        
        try:
            status['available_backups'] = self.listing_manager.get_backup_counts()
            
        except Exception as e:
            status['error'] = str(e)
            self.logger.error(f"Failed to get backup status: {e}")
        
        return status
    
    def get_recent_backup_history(self, count: int = 10) -> list:
        """
        Get recent backup history entries.
        
        Args:
            count: Number of recent entries to retrieve (default: 10)
            
        Returns:
            List of recent backup result dictionaries
        """
        return self.history_logger.get_recent_backups(count)
    
    def get_failed_backups(self) -> list:
        """
        Get all failed backup entries from history.
        
        Returns:
            List of failed backup result dictionaries
        """
        return self.history_logger.get_failed_backups()


def create_backup() -> Dict[str, Any]:
    """
    Convenience function to create full system backup.
    
    Creates a BackupManager instance and executes a full backup.
    
    Returns:
        Dictionary with backup results
    """
    manager = BackupManager()
    return manager.create_full_backup()


__all__ = ['BackupManager', 'create_backup']