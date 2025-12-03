# File: /map_pro/tools/cleanup_file_operations.py

"""
Cleanup File Operations
========================

Handles all file-related cleanup operations including temp files
and log file cleanup.

SAFETY FEATURES:
- Only operates on explicit temp and log directories
- Never touches data directories (entities, filings, taxonomies)
- Requires age threshold for deletions
- Handles permissions errors gracefully

Responsibilities:
- Clean temp files from explicit temp directory
- Clean old log files
- Track space freed
- Handle file system errors safely

Related Files:
- cleanup_orchestrator.py: Main orchestration
- database_cleanup.py: Entry point
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path

from core.data_paths import map_pro_paths


class FileAgeDefaults:
    """Default age thresholds for file cleanup."""
    TEMP_FILES_DAYS = 7
    LOG_FILES_DAYS = 30


class ByteConversion:
    """Constants for byte to megabyte conversion."""
    BYTES_PER_MB = 1024 * 1024


class CleanupFileOperations:
    """
    Handles file-related cleanup operations.
    
    This class provides safe methods for cleaning temp files and logs
    without touching protected data directories.
    """
    
    def __init__(self, logger, dry_run: bool = False):
        """
        Initialize file cleanup operations.
        
        Args:
            logger: Logger instance for operation logging
            dry_run: If True, preview changes without applying them
        """
        self.logger = logger
        self.dry_run = dry_run
    
    def cleanup_temp_files(self) -> Dict[str, Any]:
        """
        Clean ONLY temp files from /data/temp directory.
        
        This is safe because temp directories are explicitly for temporary data.
        Removes files older than 7 days by default.
        
        Returns:
            Dictionary with cleanup results containing:
                - files_removed (int): Number of files removed
                - space_freed_mb (float): Space freed in megabytes
                - summary (str): Summary of operation
                - errors (list): List of error messages if any
        """
        result = {
            'files_removed': 0,
            'space_freed_mb': 0.0,
            'summary': '',
            'errors': []
        }
        
        try:
            temp_root = map_pro_paths.data_temp
            
            if not temp_root.exists():
                result['summary'] = "Temp directory doesn't exist"
                return result
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=FileAgeDefaults.TEMP_FILES_DAYS
            )
            
            # Recursively find and remove old temp files
            for item in temp_root.rglob('*'):
                try:
                    if item.is_file():
                        file_mtime = datetime.fromtimestamp(
                            item.stat().st_mtime,
                            timezone.utc
                        )
                        if file_mtime < cutoff_date:
                            if not self.dry_run:
                                size_mb = item.stat().st_size / ByteConversion.BYTES_PER_MB
                                item.unlink()
                                result['space_freed_mb'] += size_mb
                            result['files_removed'] += 1
                
                except (OSError, PermissionError) as exception:
                    error_msg = f"Failed to remove {item}: {exception}"
                    result['errors'].append(error_msg)
                    self.logger.warning(error_msg)
            
            result['summary'] = (
                f"Removed {result['files_removed']} temp files "
                f"({result['space_freed_mb']:.2f} MB)"
            )
            
            self.logger.info(result['summary'])
            
        except Exception as exception:
            error_msg = f"Temp cleanup failed: {exception}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def cleanup_old_logs(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old log files.
        
        Removes rotated log files (*.log.*) older than the specified threshold.
        Current log files (*.log without extension) are preserved.
        
        Args:
            days_old: Age threshold in days (default: 30)
            
        Returns:
            Dictionary with cleanup results containing:
                - files_removed (int): Number of log files removed
                - space_freed_mb (float): Space freed in megabytes
                - summary (str): Summary of operation
                - errors (list): List of error messages if any
        """
        result = {
            'files_removed': 0,
            'space_freed_mb': 0.0,
            'summary': '',
            'errors': []
        }
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            logs_dir = map_pro_paths.logs_root
            
            if not logs_dir.exists():
                result['summary'] = "Logs directory doesn't exist"
                return result
            
            # Find and remove old rotated log files
            for log_file in logs_dir.rglob('*.log.*'):
                try:
                    file_mtime = datetime.fromtimestamp(
                        log_file.stat().st_mtime,
                        timezone.utc
                    )
                    if file_mtime < cutoff_date:
                        if not self.dry_run:
                            size_mb = log_file.stat().st_size / ByteConversion.BYTES_PER_MB
                            log_file.unlink()
                            result['space_freed_mb'] += size_mb
                        result['files_removed'] += 1
                
                except (OSError, PermissionError) as exception:
                    error_msg = f"Failed to remove log {log_file}: {exception}"
                    result['errors'].append(error_msg)
                    self.logger.warning(error_msg)
            
            result['summary'] = (
                f"Removed {result['files_removed']} old logs "
                f"({result['space_freed_mb']:.2f} MB)"
            )
            
            self.logger.info(result['summary'])
            
        except Exception as exception:
            error_msg = f"Log cleanup failed: {exception}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result


__all__ = ['CleanupFileOperations', 'FileAgeDefaults', 'ByteConversion']