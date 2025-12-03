"""
Backup Coordinator
==================

Coordinates full backup operations across all components.

Save location: tools/maintenance/backup_coordinator.py

Responsibilities:
- Orchestrate full system backups
- Coordinate database and JSON backups
- Aggregate backup results
- Handle backup errors

Dependencies:
- datetime (timestamp generation)
- core.system_logger (logging)
- tools.maintenance.backup_config (configuration)
- tools.maintenance.backup_operations (database/JSON backup execution)
"""

from datetime import datetime, timezone
from typing import Dict, Any

from core.system_logger import get_logger
from tools.maintenance.backup_config import BackupConfig
from tools.maintenance.backup_operations import BackupOperations


logger = get_logger(__name__, 'maintenance')


class BackupCoordinator:
    """
    Coordinates full system backup operations.
    
    Orchestrates backup of all system components and aggregates results.
    
    Attributes:
        config: Backup configuration instance
        backup_ops: Backup operations handler
        logger: Logger instance for this coordinator
    """
    
    def __init__(self, config: BackupConfig, backup_ops: BackupOperations):
        """
        Initialize backup coordinator.
        
        Args:
            config: Backup configuration instance
            backup_ops: Backup operations handler
        """
        self.config = config
        self.backup_ops = backup_ops
        self.logger = logger
    
    def create_full_backup(self) -> Dict[str, Any]:
        """
        Create complete system backup.
        
        Backs up all databases and JSON data files, aggregating
        results and tracking errors.
        
        Returns:
            Dictionary containing:
                - backup_name: Name of this backup
                - timestamp: ISO format timestamp
                - success: Overall success flag
                - databases: Database backup results by name
                - json_data: JSON data backup results
                - errors: List of error messages
        """
        timestamp = self._generate_timestamp()
        backup_name = f"full_backup_{timestamp}"
        
        self.logger.info(f"Starting full system backup: {backup_name}")
        
        result = self._initialize_result(backup_name, timestamp)
        
        try:
            self._backup_databases(timestamp, result)
            self._backup_json_data(timestamp, result)
            result['success'] = len(result['errors']) == 0
            
            self._log_backup_completion(backup_name, result)
            
        except Exception as e:
            self.logger.error(f"Full backup failed: {e}", exc_info=True)
            result['errors'].append(str(e))
            result['success'] = False
        
        return result
    
    def _generate_timestamp(self) -> str:
        """
        Generate timestamp string for backup.
        
        Returns:
            Timestamp string in format YYYYMMDD_HHMMSS
        """
        return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    def _initialize_result(self, backup_name: str, timestamp: str) -> Dict[str, Any]:
        """
        Initialize backup result dictionary.
        
        Args:
            backup_name: Name of this backup
            timestamp: Backup timestamp
            
        Returns:
            Initialized result dictionary
        """
        return {
            'backup_name': backup_name,
            'timestamp': timestamp,
            'success': False,
            'databases': {},
            'json_data': {},
            'errors': []
        }
    
    def _backup_databases(self, timestamp: str, result: Dict[str, Any]) -> None:
        """
        Backup all configured databases.
        
        Args:
            timestamp: Backup timestamp for file naming
            result: Result dictionary to populate
        """
        for db_name in self.config.database_names:
            db_result = self.backup_ops.backup_database(db_name, timestamp)
            result['databases'][db_name] = db_result
            
            if not db_result['success']:
                error_msg = f"Database backup failed: {db_name}"
                result['errors'].append(error_msg)
                self.logger.warning(error_msg)
    
    def _backup_json_data(self, timestamp: str, result: Dict[str, Any]) -> None:
        """
        Backup JSON data files.
        
        Args:
            timestamp: Backup timestamp for file naming
            result: Result dictionary to populate
        """
        json_result = self.backup_ops.backup_json_data(timestamp)
        result['json_data'] = json_result
        
        if not json_result['success']:
            error_msg = "JSON data backup failed"
            result['errors'].append(error_msg)
            self.logger.warning(error_msg)
    
    def _log_backup_completion(
        self,
        backup_name: str,
        result: Dict[str, Any]
    ) -> None:
        """
        Log backup completion summary.
        
        Args:
            backup_name: Name of completed backup
            result: Backup result dictionary
        """
        if result['success']:
            self.logger.info(f"Full backup completed successfully: {backup_name}")
        else:
            self.logger.warning(
                f"Full backup completed with errors: {backup_name} "
                f"({len(result['errors'])} errors)"
            )


__all__ = ['BackupCoordinator']