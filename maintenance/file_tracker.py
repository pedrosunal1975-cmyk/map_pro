"""
Map Pro File Tracker Utilities
===============================

Utility classes for tracking file information during analysis.

Save location: tools/maintenance/file_tracker.py
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from .cleanup_statistics_config import CleanupStatisticsConfig


class FileTracker:
    """Base class for file tracking utilities."""
    
    pass


class FileAgeCategorizer:
    """
    Categorizes files by age.
    
    Responsibilities:
    - Categorize files into age buckets
    - Provide age distribution statistics
    """
    
    def __init__(self) -> None:
        """Initialize file age categorizer."""
        self.distribution = {
            'last_day': 0,
            'last_week': 0,
            'last_month': 0,
            'older': 0
        }
    
    def categorize(self, file_time: datetime) -> None:
        """
        Categorize a file by its age.
        
        Args:
            file_time: File modification time
        """
        now = datetime.now(file_time.tzinfo)
        age = now - file_time
        
        if age <= CleanupStatisticsConfig.AGE_THRESHOLD_DAY:
            self.distribution['last_day'] += 1
        elif age <= CleanupStatisticsConfig.AGE_THRESHOLD_WEEK:
            self.distribution['last_week'] += 1
        elif age <= CleanupStatisticsConfig.AGE_THRESHOLD_MONTH:
            self.distribution['last_month'] += 1
        else:
            self.distribution['older'] += 1
    
    def get_distribution(self) -> Dict[str, int]:
        """
        Get age distribution.
        
        Returns:
            Dictionary with counts for each age category
        """
        return self.distribution.copy()


class FileTypeTracker:
    """
    Tracks file types distribution.
    
    Responsibilities:
    - Count files by extension
    - Provide file type statistics
    """
    
    def __init__(self) -> None:
        """Initialize file type tracker."""
        self.file_types: Dict[str, int] = {}
    
    def add_file(self, file_path: Path) -> None:
        """
        Add a file to type tracking.
        
        Args:
            file_path: Path to file
        """
        suffix = file_path.suffix.lower()
        if not suffix:
            suffix = CleanupStatisticsConfig.NO_EXTENSION_LABEL
        
        self.file_types[suffix] = self.file_types.get(suffix, 0) + 1
    
    def get_file_types(self) -> Dict[str, int]:
        """
        Get file types distribution.
        
        Returns:
            Dictionary mapping file extensions to counts
        """
        return self.file_types.copy()


class LargestFilesTracker:
    """
    Tracks largest files in a directory.
    
    Responsibilities:
    - Maintain list of largest files
    - Sort and limit results
    """
    
    def __init__(self, max_files: int) -> None:
        """
        Initialize largest files tracker.
        
        Args:
            max_files: Maximum number of files to track
        """
        self.max_files = max_files
        self.files: List[Dict[str, Any]] = []
    
    def add_file(self, path: Path, size_bytes: int) -> None:
        """
        Add a file to largest files tracking.
        
        Args:
            path: File path (relative)
            size_bytes: File size in bytes
        """
        self.files.append({
            'path': str(path),
            'size_mb': size_bytes / CleanupStatisticsConfig.BYTES_PER_MB
        })
    
    def get_largest_files(self) -> List[Dict[str, Any]]:
        """
        Get list of largest files.
        
        Returns:
            List of largest files, sorted by size descending
        """
        # Sort by size descending and take top N
        sorted_files = sorted(
            self.files,
            key=lambda x: x['size_mb'],
            reverse=True
        )
        return sorted_files[:self.max_files]


__all__ = [
    'FileTracker',
    'FileAgeCategorizer',
    'FileTypeTracker',
    'LargestFilesTracker'
]