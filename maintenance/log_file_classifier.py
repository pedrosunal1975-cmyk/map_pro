# File: /map_pro/tools/maintenance/log_file_classifier.py

"""
Log File Classifier
===================

Classifies log files for rotation and cleanup operations.
Determines if files should be compressed or removed.
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone

from core.system_logger import get_logger

from .log_rotation_constants import (
    COMPRESSED_EXTENSION,
    LOG_EXTENSION,
    LOG_SEPARATOR
)

logger = get_logger(__name__, 'maintenance')


class LogFileClassifier:
    """
    Classifies log files for processing.
    
    Responsibilities:
    - Identify rotated log files
    - Identify old log files
    - Check file age against retention policy
    """
    
    def __init__(self):
        """Initialize log file classifier."""
        self.logger = logger
    
    def is_rotated_log(self, file_path: Path) -> bool:
        """
        Check if file is a rotated log file.
        
        Rotated logs have pattern: .log.1, .log.2, etc.
        (not already compressed with .gz extension)
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is a rotated log that can be compressed
        """
        # Skip already compressed files
        if file_path.suffix == COMPRESSED_EXTENSION:
            return False
        
        # Check if filename contains .log. followed by a number
        name = file_path.name
        if LOG_SEPARATOR in name:
            parts = name.split(LOG_SEPARATOR)
            if len(parts) == 2 and parts[1].isdigit():
                return True
        
        return False
    
    def is_old_log(self, file_path: Path, retention_days: int) -> bool:
        """
        Check if log file is older than retention period.
        
        Args:
            file_path: Path to check
            retention_days: Number of days to retain logs
            
        Returns:
            True if file should be removed
        """
        # Only consider log files
        if not self._is_log_file(file_path):
            return False
        
        try:
            file_age = self._get_file_age(file_path)
            return file_age > retention_days
            
        except Exception as exception:
            self.logger.debug(f"Error checking file age {file_path}: {exception}")
            return False
    
    def _is_log_file(self, file_path: Path) -> bool:
        """
        Check if file is a log file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is a log file
        """
        return (
            file_path.suffix in [LOG_EXTENSION, COMPRESSED_EXTENSION] or 
            LOG_SEPARATOR in file_path.name
        )
    
    def _get_file_age(self, file_path: Path) -> int:
        """
        Get file age in days.
        
        Args:
            file_path: Path to file
            
        Returns:
            Age of file in days
        """
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        age_delta = now - mtime
        
        return age_delta.days


__all__ = ['LogFileClassifier']