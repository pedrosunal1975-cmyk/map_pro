# File: /map_pro/tools/maintenance/cleanup_executor.py

"""
Cleanup Executor
================

Executes cleanup operations based on configuration.

Responsibilities:
- Execute full cleanup workflow
- Execute targeted cleanup operations
- Aggregate cleanup results
- Handle cleanup operation errors
- Track space freed across operations

Related Files:
- cleanup_scheduler.py: Main scheduler
- cleanup_operations.py: Individual cleanup operations
- cleanup_config.py: Configuration management
- connection_pool_manager.py: Connection pool operations
"""

from datetime import datetime
from typing import Dict, Any, List


class CleanupType:
    """Constants for cleanup type identifiers."""
    TEMP = 'temp'
    DOWNLOADS = 'downloads'
    DATABASE = 'database'
    CONNECTIONS = 'connections'
    LOGS = 'logs'


class ResultKeys:
    """Constants for result dictionary keys."""
    CLEANUP_NAME = 'cleanup_name'
    TIMESTAMP = 'timestamp'
    SUCCESS = 'success'
    TEMP_CLEANUP = 'temp_cleanup'
    DOWNLOAD_CLEANUP = 'download_cleanup'
    DATABASE_CLEANUP = 'database_cleanup'
    CONNECTION_CLEANUP = 'connection_cleanup'
    LOG_CLEANUP = 'log_cleanup'
    TOTAL_SPACE_FREED_MB = 'total_space_freed_mb'
    ERRORS = 'errors'
    CLEANUP_TYPES = 'cleanup_types'


class CleanupExecutor:
    """
    Executes cleanup operations and aggregates results.
    
    This class handles the actual execution of cleanup operations,
    result aggregation, and error collection.
    """
    
    def __init__(
        self,
        cleanup_ops,
        connection_pool_manager,
        config,
        logger
    ):
        """
        Initialize cleanup executor.
        
        Args:
            cleanup_ops: CleanupOperations instance
            connection_pool_manager: ConnectionPoolManager instance
            config: CleanupConfig instance
            logger: Logger instance
        """
        self.cleanup_ops = cleanup_ops
        self.connection_pool_manager = connection_pool_manager
        self.config = config
        self.logger = logger
    
    def execute_full_cleanup(
        self,
        cleanup_name: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute complete system cleanup with all enabled operations.
        
        Args:
            cleanup_name: Unique cleanup identifier
            start_time: Cleanup start timestamp
            
        Returns:
            Dictionary with comprehensive cleanup results
        """
        results = self._initialize_results(cleanup_name, start_time)
        
        # Execute each cleanup type if enabled
        if self.config.cleanup_temp_files:
            self._execute_temp_cleanup(results)
        
        if self.config.cleanup_downloads:
            self._execute_download_cleanup(results)
        
        if self.config.cleanup_database:
            self._execute_database_cleanup(results)
        
        if self.config.cleanup_connections:
            self._execute_connection_cleanup(results)
        
        if self.config.cleanup_logs:
            self._execute_log_cleanup(results)
        
        # Set overall success status
        results[ResultKeys.SUCCESS] = len(results[ResultKeys.ERRORS]) == 0
        
        return results
    
    def execute_targeted_cleanup(
        self,
        cleanup_name: str,
        start_time: datetime,
        cleanup_types: List[str]
    ) -> Dict[str, Any]:
        """
        Execute specific types of cleanup operations.
        
        Args:
            cleanup_name: Unique cleanup identifier
            start_time: Cleanup start timestamp
            cleanup_types: List of cleanup type identifiers
            
        Returns:
            Dictionary with cleanup results for specified types
        """
        results = self._initialize_results(cleanup_name, start_time)
        results[ResultKeys.CLEANUP_TYPES] = cleanup_types
        
        # Execute requested cleanup types
        if CleanupType.TEMP in cleanup_types:
            self._execute_temp_cleanup(results)
        
        if CleanupType.DOWNLOADS in cleanup_types:
            self._execute_download_cleanup(results)
        
        if CleanupType.DATABASE in cleanup_types:
            self._execute_database_cleanup(results)
        
        if CleanupType.CONNECTIONS in cleanup_types:
            self._execute_connection_cleanup(results)
        
        if CleanupType.LOGS in cleanup_types:
            self._execute_log_cleanup(results)
        
        # Set overall success status
        results[ResultKeys.SUCCESS] = len(results[ResultKeys.ERRORS]) == 0
        
        return results
    
    def _initialize_results(
        self,
        cleanup_name: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Initialize results dictionary with default values.
        
        Args:
            cleanup_name: Unique cleanup identifier
            start_time: Cleanup start timestamp
            
        Returns:
            Initialized results dictionary
        """
        return {
            ResultKeys.CLEANUP_NAME: cleanup_name,
            ResultKeys.TIMESTAMP: start_time.isoformat(),
            ResultKeys.SUCCESS: True,
            ResultKeys.TEMP_CLEANUP: {},
            ResultKeys.DOWNLOAD_CLEANUP: {},
            ResultKeys.DATABASE_CLEANUP: {},
            ResultKeys.CONNECTION_CLEANUP: {},
            ResultKeys.LOG_CLEANUP: {},
            ResultKeys.TOTAL_SPACE_FREED_MB: 0,
            ResultKeys.ERRORS: []
        }
    
    def _execute_temp_cleanup(self, results: Dict[str, Any]) -> None:
        """
        Execute temporary files cleanup and update results.
        
        Args:
            results: Results dictionary to update
        """
        try:
            temp_result = self.cleanup_ops.cleanup_temp_files()
            results[ResultKeys.TEMP_CLEANUP] = temp_result
            results[ResultKeys.TOTAL_SPACE_FREED_MB] += temp_result.get(
                'space_freed_mb', 0
            )
            
            if not temp_result.get('success', False):
                results[ResultKeys.ERRORS].append("Temporary files cleanup failed")
        
        except Exception as exception:
            error_msg = f"Temp cleanup exception: {exception}"
            results[ResultKeys.ERRORS].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
    
    def _execute_download_cleanup(self, results: Dict[str, Any]) -> None:
        """
        Execute downloads cleanup and update results.
        
        Args:
            results: Results dictionary to update
        """
        try:
            download_result = self.cleanup_ops.cleanup_old_downloads()
            results[ResultKeys.DOWNLOAD_CLEANUP] = download_result
            results[ResultKeys.TOTAL_SPACE_FREED_MB] += download_result.get(
                'space_freed_mb', 0
            )
            
            if not download_result.get('success', False):
                results[ResultKeys.ERRORS].append("Downloads cleanup failed")
        
        except Exception as exception:
            error_msg = f"Download cleanup exception: {exception}"
            results[ResultKeys.ERRORS].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
    
    def _execute_database_cleanup(self, results: Dict[str, Any]) -> None:
        """
        Execute database cleanup and update results.
        
        Args:
            results: Results dictionary to update
        """
        try:
            db_result = self.cleanup_ops.cleanup_database()
            results[ResultKeys.DATABASE_CLEANUP] = db_result
            
            if not db_result.get('success', False):
                results[ResultKeys.ERRORS].append("Database cleanup failed")
        
        except Exception as exception:
            error_msg = f"Database cleanup exception: {exception}"
            results[ResultKeys.ERRORS].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
    
    def _execute_connection_cleanup(self, results: Dict[str, Any]) -> None:
        """
        Execute connection pool cleanup and update results.
        
        Args:
            results: Results dictionary to update
        """
        try:
            connection_result = self.connection_pool_manager.cleanup_idle_connections()
            results[ResultKeys.CONNECTION_CLEANUP] = connection_result
            
            if not connection_result.get('success', False):
                results[ResultKeys.ERRORS].append("Connection pool cleanup failed")
            else:
                terminated = connection_result.get('connections_terminated', 0)
                if terminated > 0:
                    self.logger.info(
                        f"Terminated {terminated} idle database connections"
                    )
        
        except Exception as exception:
            error_msg = f"Connection cleanup exception: {exception}"
            results[ResultKeys.ERRORS].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
    
    def _execute_log_cleanup(self, results: Dict[str, Any]) -> None:
        """
        Execute log cleanup and update results.
        
        Args:
            results: Results dictionary to update
        """
        try:
            log_result = self.cleanup_ops.cleanup_old_logs()
            results[ResultKeys.LOG_CLEANUP] = log_result
            results[ResultKeys.TOTAL_SPACE_FREED_MB] += log_result.get(
                'space_freed_mb', 0
            )
            
            if not log_result.get('success', False):
                results[ResultKeys.ERRORS].append("Log cleanup failed")
        
        except Exception as exception:
            error_msg = f"Log cleanup exception: {exception}"
            results[ResultKeys.ERRORS].append(error_msg)
            self.logger.error(error_msg, exc_info=True)


__all__ = ['CleanupExecutor', 'CleanupType', 'ResultKeys']