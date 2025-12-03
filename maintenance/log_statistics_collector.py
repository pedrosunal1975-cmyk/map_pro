# File: /map_pro/tools/maintenance/log_statistics_collector.py

"""
Log Statistics Collector
=========================

Collects statistics about log files across directories.
Provides insights into log storage usage.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.system_logger import get_logger

from .log_rotation_constants import (
    LOG_EXTENSION,
    COMPRESSED_EXTENSION,
    LOG_SEPARATOR,
    BYTES_PER_MEGABYTE
)

logger = get_logger(__name__, 'maintenance')


class LogStatisticsCollector:
    """
    Collects log file statistics.
    
    Responsibilities:
    - Count log files by type
    - Calculate total storage usage
    - Track oldest and newest logs
    - Aggregate statistics by directory
    """
    
    def __init__(self):
        """Initialize log statistics collector."""
        self.logger = logger
    
    def collect_statistics(self, log_directories: List[Path]) -> Dict[str, Any]:
        """
        Get statistics about log files.
        
        Args:
            log_directories: List of log directory paths to analyze
            
        Returns:
            Dictionary with comprehensive log statistics
        """
        stats = self._initialize_statistics()
        
        try:
            date_tracker = DateTracker()
            
            for log_dir in log_directories:
                if not log_dir.exists():
                    continue
                
                dir_stats = self._collect_directory_statistics(log_dir, date_tracker)
                stats['by_directory'][log_dir.name] = dir_stats
            
            # Finalize statistics
            stats['total_size_mb'] = round(stats['total_size_mb'], 2)
            stats['oldest_log_date'] = date_tracker.get_oldest_iso()
            stats['newest_log_date'] = date_tracker.get_newest_iso()
            
        except Exception as exception:
            self.logger.error(f"Error gathering log statistics: {exception}")
        
        return stats
    
    def _initialize_statistics(self) -> Dict[str, Any]:
        """
        Initialize statistics dictionary.
        
        Returns:
            Statistics dictionary with default values
        """
        return {
            'total_log_files': 0,
            'total_size_mb': 0,
            'compressed_files': 0,
            'uncompressed_files': 0,
            'oldest_log_date': None,
            'newest_log_date': None,
            'by_directory': {}
        }
    
    def _collect_directory_statistics(
        self,
        log_dir: Path,
        date_tracker: 'DateTracker'
    ) -> Dict[str, Any]:
        """
        Collect statistics for a single directory.
        
        Args:
            log_dir: Directory path
            date_tracker: Date tracker for oldest/newest logs
            
        Returns:
            Directory statistics dictionary
        """
        dir_stats = {
            'count': 0,
            'size_mb': 0,
            'compressed': 0
        }
        
        for log_file in log_dir.rglob('*'):
            if not log_file.is_file():
                continue
            
            # Only count log files
            if not self._is_log_file(log_file):
                continue
            
            self._process_log_file(log_file, dir_stats, date_tracker)
        
        dir_stats['size_mb'] = round(dir_stats['size_mb'], 2)
        
        return dir_stats
    
    def _process_log_file(
        self,
        log_file: Path,
        dir_stats: Dict[str, Any],
        date_tracker: 'DateTracker'
    ) -> None:
        """
        Process a single log file for statistics.
        
        Args:
            log_file: Log file path
            dir_stats: Directory statistics to update
            date_tracker: Date tracker to update
        """
        file_stats = log_file.stat()
        file_size_mb = file_stats.st_size / BYTES_PER_MEGABYTE
        mtime = datetime.fromtimestamp(file_stats.st_mtime, tz=timezone.utc)
        
        # Update directory stats
        dir_stats['count'] += 1
        dir_stats['size_mb'] += file_size_mb
        
        if log_file.suffix == COMPRESSED_EXTENSION:
            dir_stats['compressed'] += 1
        
        # Update date tracker
        date_tracker.update(mtime)
    
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


class DateTracker:
    """
    Tracks oldest and newest dates.
    
    Helper class for statistics collection.
    """
    
    def __init__(self):
        """Initialize date tracker."""
        self.oldest: Optional[datetime] = None
        self.newest: Optional[datetime] = None
    
    def update(self, timestamp: datetime) -> None:
        """
        Update tracked dates with new timestamp.
        
        Args:
            timestamp: Datetime to consider
        """
        if self.oldest is None or timestamp < self.oldest:
            self.oldest = timestamp
        
        if self.newest is None or timestamp > self.newest:
            self.newest = timestamp
    
    def get_oldest_iso(self) -> Optional[str]:
        """
        Get oldest date in ISO format.
        
        Returns:
            ISO formatted date string or None
        """
        return self.oldest.isoformat() if self.oldest else None
    
    def get_newest_iso(self) -> Optional[str]:
        """
        Get newest date in ISO format.
        
        Returns:
            ISO formatted date string or None
        """
        return self.newest.isoformat() if self.newest else None


__all__ = ['LogStatisticsCollector', 'DateTracker']