# File: /map_pro/tools/maintenance/log_cleanup_handler.py

"""
Log Cleanup Handler
===================

Handles removal of old log files based on retention policy.
"""

from pathlib import Path
from typing import Dict, Any

from core.system_logger import get_logger

from .log_rotation_constants import BYTES_PER_MEGABYTE

logger = get_logger(__name__, 'maintenance')


class LogCleanupHandler:
    """
    Handles old log file removal.
    
    Responsibilities:
    - Remove old log files
    - Track space freed
    - Handle removal errors
    """
    
    def __init__(self, retention_days: int):
        """
        Initialize log cleanup handler.
        
        Args:
            retention_days: Number of days to retain logs
        """
        self.retention_days = retention_days
        self.logger = logger
    
    def remove_old_log(self, file_path: Path) -> Dict[str, Any]:
        """
        Remove an old log file.
        
        Args:
            file_path: Path to log file
            
        Returns:
            Removal result dictionary with:
            - success: Boolean indicating success
            - size_mb: Size of removed file in MB
            - error: Error message if failed
        """
        result = {
            'success': False,
            'size_mb': 0,
            'error': None
        }
        
        try:
            file_size_mb = self._get_file_size_mb(file_path)
            
            file_path.unlink()
            
            result['success'] = True
            result['size_mb'] = file_size_mb
            
            self._log_removal_success(file_path.name, file_size_mb)
            
        except Exception as exception:
            result['error'] = f"Failed to remove {file_path}: {exception}"
            self.logger.error(result['error'])
        
        return result
    
    def _get_file_size_mb(self, file_path: Path) -> float:
        """
        Get file size in megabytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in MB, rounded to 2 decimal places
        """
        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / BYTES_PER_MEGABYTE
        return round(size_mb, 2)
    
    def _log_removal_success(self, filename: str, size_mb: float) -> None:
        """
        Log successful removal.
        
        Args:
            filename: Name of removed file
            size_mb: Size of removed file in MB
        """
        self.logger.debug(f"Removed old log: {filename} ({size_mb:.2f} MB)")


__all__ = ['LogCleanupHandler']