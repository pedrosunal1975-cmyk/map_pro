"""
Map Pro Downloads Directory Analyzer
=====================================

Analyzes downloads directory for cleanup statistics.

Save location: tools/maintenance/downloads_directory_analyzer.py
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from .cleanup_statistics_config import CleanupStatisticsConfig

logger = get_logger(__name__, 'maintenance')


class DownloadsDirectoryAnalyzer:
    """
    Analyzes downloads directory contents.
    
    Responsibilities:
    - Calculate downloads directory size
    - Count download files
    - Track oldest and newest downloads
    """
    
    def __init__(self, downloads_root: Path) -> None:
        """
        Initialize downloads directory analyzer.
        
        Args:
            downloads_root: Path to downloads directory root
        """
        self.downloads_root = downloads_root
        self.logger = logger
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze downloads directory for cleanup statistics.
        
        Returns:
            Dictionary with downloads directory statistics
        """
        stats = self._initialize_stats()
        
        if not self.downloads_root.exists():
            return stats
        
        try:
            total_size = 0
            file_count = 0
            
            for item in self.downloads_root.rglob('*'):
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
                
                except (OSError, PermissionError) as e:
                    self.logger.debug(f"Skipping inaccessible item {item}: {e}")
                    continue
            
            stats['downloads_size_gb'] = self._bytes_to_gb(total_size)
            stats['download_files_count'] = file_count
            
        except Exception as e:
            self.logger.error(f"Error analyzing downloads directory: {e}")
        
        return stats
    
    def _initialize_stats(self) -> Dict[str, Any]:
        """
        Initialize statistics structure.
        
        Returns:
            Dictionary with default values
        """
        return {
            'downloads_size_gb': 0,
            'download_files_count': 0,
            'oldest_download': None,
            'newest_download': None
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
        if self._is_older_file(stats['oldest_download'], file_time):
            stats['oldest_download'] = file_info
        
        # Track newest file
        if self._is_newer_file(stats['newest_download'], file_time):
            stats['newest_download'] = file_info
    
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
            'path': str(item.relative_to(self.downloads_root)),
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
    
    def _bytes_to_gb(self, size_bytes: int) -> float:
        """
        Convert bytes to gigabytes.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Size in gigabytes
        """
        return size_bytes / CleanupStatisticsConfig.BYTES_PER_GB


__all__ = ['DownloadsDirectoryAnalyzer']