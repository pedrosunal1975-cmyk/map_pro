# File: /map_pro/tools/maintenance/log_rotator.py

"""
Map Pro Log Rotation System
============================

Manages log file rotation, compression, and cleanup.

Responsibilities:
- Orchestrate log rotation workflow
- Coordinate specialized handlers

This module has been refactored into:
- log_rotator.py (this file) - Main orchestration
- log_rotation_config.py - Configuration management
- log_file_classifier.py - Log file classification
- log_compression_handler.py - File compression
- log_cleanup_handler.py - Old log removal
- log_statistics_collector.py - Statistics gathering
- log_rotation_constants.py - Constants and magic numbers

Save location: tools/maintenance/log_rotator.py
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

from .log_rotation_config import LogRotationConfig
from .log_file_classifier import LogFileClassifier
from .log_compression_handler import LogCompressionHandler
from .log_cleanup_handler import LogCleanupHandler
from .log_statistics_collector import LogStatisticsCollector

logger = get_logger(__name__, 'maintenance')


class LogRotator:
    """
    Manages log file rotation, compression, and cleanup.
    
    Works alongside Python's RotatingFileHandler to:
    - Compress rotated log files
    - Clean up old logs based on retention policy
    - Monitor log directory sizes
    
    Configuration:
    - MAP_PRO_LOG_RETENTION_DAYS: Days to keep logs (default: 30)
    - MAP_PRO_COMPRESS_LOGS: Enable compression (default: true)
    """
    
    def __init__(
        self,
        config: Optional[LogRotationConfig] = None,
        classifier: Optional[LogFileClassifier] = None,
        compression_handler: Optional[LogCompressionHandler] = None,
        cleanup_handler: Optional[LogCleanupHandler] = None,
        statistics_collector: Optional[LogStatisticsCollector] = None
    ):
        """
        Initialize log rotator with optional dependencies.
        
        Args:
            config: Configuration manager (created if None)
            classifier: File classifier (created if None)
            compression_handler: Compression handler (created if None)
            cleanup_handler: Cleanup handler (created if None)
            statistics_collector: Statistics collector (created if None)
        """
        self.config = config or LogRotationConfig()
        self.classifier = classifier or LogFileClassifier()
        self.compression_handler = compression_handler or LogCompressionHandler()
        self.cleanup_handler = cleanup_handler or LogCleanupHandler(
            retention_days=self.config.retention_days
        )
        self.statistics_collector = statistics_collector or LogStatisticsCollector()
        
        self.logger = logger
        
        # Define log directories to manage
        self.log_directories = [
            map_pro_paths.logs_engines,
            map_pro_paths.logs_system,
            map_pro_paths.logs_alerts,
            map_pro_paths.logs_integrations
        ]
        
        self._log_initialization()
    
    def _log_initialization(self) -> None:
        """Log initialization details."""
        self.logger.info("Log rotator initialized")
        self.logger.info(f"Retention policy: {self.config.retention_days} days")
        
        compression_status = 'enabled' if self.config.compress_logs else 'disabled'
        self.logger.info(f"Compression: {compression_status}")
    
    def rotate_all_logs(self) -> Dict[str, Any]:
        """
        Execute full log rotation cycle.
        
        Returns:
            Dictionary with rotation results
        """
        self.logger.info("Starting log rotation cycle")
        
        results = self._initialize_results()
        
        try:
            for log_dir in self.log_directories:
                if not log_dir.exists():
                    self.logger.debug(f"Log directory does not exist: {log_dir}")
                    continue
                
                dir_result = self._process_directory(log_dir)
                self._aggregate_results(results, dir_result)
            
            results['success'] = len(results['errors']) == 0
            self._log_completion(results)
            
        except Exception as exception:
            self._handle_rotation_error(results, exception)
        
        return results
    
    def _initialize_results(self) -> Dict[str, Any]:
        """
        Initialize results dictionary.
        
        Returns:
            Results dictionary with default values
        """
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': False,
            'directories_processed': 0,
            'files_compressed': 0,
            'files_removed': 0,
            'space_freed_mb': 0,
            'space_saved_mb': 0,
            'errors': []
        }
    
    def _aggregate_results(
        self,
        results: Dict[str, Any],
        dir_result: Dict[str, Any]
    ) -> None:
        """
        Aggregate directory results into overall results.
        
        Args:
            results: Overall results dictionary to update
            dir_result: Directory processing results
        """
        results['directories_processed'] += 1
        results['files_compressed'] += dir_result['files_compressed']
        results['files_removed'] += dir_result['files_removed']
        results['space_freed_mb'] += dir_result['space_freed_mb']
        results['space_saved_mb'] += dir_result['space_saved_mb']
        results['errors'].extend(dir_result['errors'])
    
    def _log_completion(self, results: Dict[str, Any]) -> None:
        """
        Log rotation completion summary.
        
        Args:
            results: Rotation results
        """
        self.logger.info(
            f"Log rotation complete: {results['files_compressed']} compressed, "
            f"{results['files_removed']} removed, "
            f"{results['space_freed_mb']:.2f} MB freed, "
            f"{results['space_saved_mb']:.2f} MB saved"
        )
    
    def _handle_rotation_error(
        self,
        results: Dict[str, Any],
        exception: Exception
    ) -> None:
        """
        Handle rotation error.
        
        Args:
            results: Results dictionary to update
            exception: Exception that occurred
        """
        self.logger.error(f"Log rotation failed: {exception}", exc_info=True)
        results['errors'].append(str(exception))
        results['success'] = False
    
    def _process_directory(self, directory: Path) -> Dict[str, Any]:
        """
        Process a single log directory.
        
        Args:
            directory: Path to log directory
            
        Returns:
            Processing results dictionary
        """
        result = {
            'files_compressed': 0,
            'files_removed': 0,
            'space_freed_mb': 0,
            'space_saved_mb': 0,
            'errors': []
        }
        
        try:
            for log_file in directory.rglob('*'):
                if not log_file.is_file():
                    continue
                
                # Process compression
                if self._should_compress_file(log_file):
                    self._process_compression(log_file, result)
                
                # Process cleanup
                if self._should_remove_file(log_file):
                    self._process_removal(log_file, result)
        
        except Exception as exception:
            self._handle_directory_error(directory, result, exception)
        
        return result
    
    def _should_compress_file(self, log_file: Path) -> bool:
        """
        Check if file should be compressed.
        
        Args:
            log_file: Path to check
            
        Returns:
            True if file should be compressed
        """
        return (
            self.classifier.is_rotated_log(log_file) and 
            self.config.compress_logs
        )
    
    def _should_remove_file(self, log_file: Path) -> bool:
        """
        Check if file should be removed.
        
        Args:
            log_file: Path to check
            
        Returns:
            True if file should be removed
        """
        return self.classifier.is_old_log(log_file, self.config.retention_days)
    
    def _process_compression(
        self,
        log_file: Path,
        result: Dict[str, Any]
    ) -> None:
        """
        Process file compression.
        
        Args:
            log_file: File to compress
            result: Results dictionary to update
        """
        compress_result = self.compression_handler.compress_log_file(log_file)
        
        if compress_result['success']:
            result['files_compressed'] += 1
            result['space_saved_mb'] += compress_result['space_saved_mb']
        else:
            result['errors'].append(compress_result['error'])
    
    def _process_removal(
        self,
        log_file: Path,
        result: Dict[str, Any]
    ) -> None:
        """
        Process file removal.
        
        Args:
            log_file: File to remove
            result: Results dictionary to update
        """
        remove_result = self.cleanup_handler.remove_old_log(log_file)
        
        if remove_result['success']:
            result['files_removed'] += 1
            result['space_freed_mb'] += remove_result['size_mb']
        else:
            result['errors'].append(remove_result['error'])
    
    def _handle_directory_error(
        self,
        directory: Path,
        result: Dict[str, Any],
        exception: Exception
    ) -> None:
        """
        Handle directory processing error.
        
        Args:
            directory: Directory being processed
            result: Results dictionary to update
            exception: Exception that occurred
        """
        self.logger.error(f"Error processing directory {directory}: {exception}")
        result['errors'].append(f"Directory processing error: {exception}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about log files.
        
        Returns:
            Dictionary with log statistics
        """
        return self.statistics_collector.collect_statistics(self.log_directories)
    
    def cleanup_logs_by_age(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Remove logs older than specified days.
        
        Args:
            days: Number of days to retain (uses configured retention if None)
            
        Returns:
            Cleanup results
        """
        retention = days if days is not None else self.config.retention_days
        original_retention = self.config.retention_days
        
        try:
            self.config.retention_days = retention
            self.cleanup_handler.retention_days = retention
            
            self.logger.info(f"Cleaning up logs older than {retention} days")
            
            result = self.rotate_all_logs()
            return result
            
        finally:
            self.config.retention_days = original_retention
            self.cleanup_handler.retention_days = original_retention


def rotate_logs() -> Dict[str, Any]:
    """
    Convenience function to rotate logs.
    
    Returns:
        Rotation results
    """
    rotator = LogRotator()
    return rotator.rotate_all_logs()


__all__ = ['LogRotator', 'rotate_logs']