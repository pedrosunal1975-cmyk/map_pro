"""
Map Pro Temp Directory Analyzer
================================

Analyzes temporary directory for cleanup statistics.

Save location: tools/maintenance/temp_directory_analyzer.py
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from .cleanup_statistics_config import CleanupStatisticsConfig
from .file_tracker import FileTracker

logger = get_logger(__name__, 'maintenance')


class TempDirectoryAnalyzer:
    """
    Analyzes temporary directory contents.
    
    Responsibilities:
    - Calculate temp directory size
    - Count temp files and directories
    - Track oldest and newest temp files
    - Count workspace directories
    """
    
    def __init__(self, temp_root: Path) -> None:
        """
        Initialize temp directory analyzer.
        
        Args:
            temp_root: Path to temporary directory root
        """
        self.temp_root = temp_root
        self.logger = logger
        self.file_tracker = FileTracker()
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze temporary directory for cleanup statistics.
        
        Returns:
            Dictionary with temp directory statistics
        """
        stats = self._initialize_stats()
        
        if not self.temp_root.exists():
            return stats
        
        try:
            total_size = 0
            file_count = 0
            workspace_count = 0
            
            for item in self.temp_root.rglob('*'):
                try:
                    if item.is_file():
                        file_size = item.stat().st_size
                        total_size += file_size
                        file_count += 1
                        
                        self._track_file_age(
                            item=item,
                            file_size=file_size,
                            stats=stats
                        )
                    
                    elif self._is_workspace_directory(item):
                        workspace_count += 1
                
                except (OSError, PermissionError) as e:
                    self.logger.debug(f"Skipping inaccessible item {item}: {e}")
                    continue
            
            stats['temp_directory_size_gb'] = self._bytes_to_gb(total_size)
            stats['temp_files_count'] = file_count
            stats['workspace_directories_count'] = workspace_count
            
        except Exception as e:
            self.logger.error(f"Error analyzing temp directory: {e}")
        
        return stats
    
    def _initialize_stats(self) -> Dict[str, Any]:
        """
        Initialize statistics structure.
        
        Returns:
            Dictionary with default values
        """
        return {
            'temp_directory_size_gb': 0,
            'temp_files_count': 0,
            'workspace_directories_count': 0,
            'oldest_temp_file': None,
            'newest_temp_file': None
        }
    
    def _track_file_age(
        self,
        item: Path,
        file_size: int,
        stats: Dict[str, Any]
    ) -> None:
        """
        Track oldest and newest files.
        
        Args:
            item: File path
            file_size: File size in bytes
            stats: Statistics dictionary to update
        """
        file_time = datetime.fromtimestamp(
            item.stat().st_mtime,
            timezone.utc
        )
        
        file_info = self._create_file_info(
            item=item,
            file_size=file_size,
            file_time=file_time
        )
        
        # Track oldest file
        if self._is_older_file(stats['oldest_temp_file'], file_time):
            stats['oldest_temp_file'] = file_info
        
        # Track newest file
        if self._is_newer_file(stats['newest_temp_file'], file_time):
            stats['newest_temp_file'] = file_info
    
    def _create_file_info(
        self,
        item: Path,
        file_size: int,
        file_time: datetime
    ) -> Dict[str, Any]:
        """
        Create file information dictionary.
        
        Args:
            item: File path
            file_size: File size in bytes
            file_time: File modification time
            
        Returns:
            Dictionary with file information
        """
        return {
            'path': str(item.relative_to(self.temp_root)),
            'size_mb': file_size / CleanupStatisticsConfig.BYTES_PER_MB,
            'modified': file_time.isoformat()
        }
    
    def _is_older_file(
        self,
        current_oldest: Optional[Dict[str, Any]],
        file_time: datetime
    ) -> bool:
        """
        Check if file is older than current oldest.
        
        Args:
            current_oldest: Current oldest file info or None
            file_time: Time to compare
            
        Returns:
            True if file is older
        """
        if current_oldest is None:
            return True
        
        current_time = datetime.fromisoformat(current_oldest['modified'])
        return file_time < current_time
    
    def _is_newer_file(
        self,
        current_newest: Optional[Dict[str, Any]],
        file_time: datetime
    ) -> bool:
        """
        Check if file is newer than current newest.
        
        Args:
            current_newest: Current newest file info or None
            file_time: Time to compare
            
        Returns:
            True if file is newer
        """
        if current_newest is None:
            return True
        
        current_time = datetime.fromisoformat(current_newest['modified'])
        return file_time > current_time
    
    def _is_workspace_directory(self, item: Path) -> bool:
        """
        Check if directory is a workspace directory.
        
        Args:
            item: Path to check
            
        Returns:
            True if item is a workspace directory
        """
        return (
            item.is_dir() and
            item != self.temp_root and
            CleanupStatisticsConfig.WORKSPACE_DIRECTORY_IDENTIFIER in item.name.lower()
        )
    
    def _bytes_to_gb(self, size_bytes: int) -> float:
        """
        Convert bytes to gigabytes.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Size in gigabytes
        """
        return size_bytes / CleanupStatisticsConfig.BYTES_PER_GB


__all__ = ['TempDirectoryAnalyzer']