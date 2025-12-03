"""
Map Pro Cleanup Statistics - Main Coordinator
==============================================

Coordinates statistics gathering and analysis for cleanup operations.

Save location: tools/maintenance/cleanup_statistics.py
"""

from typing import Dict, Any

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from core.database_coordinator import db_coordinator
from .cleanup_statistics_config import CleanupStatisticsConfig
from .temp_directory_analyzer import TempDirectoryAnalyzer
from .downloads_directory_analyzer import DownloadsDirectoryAnalyzer
from .logs_analyzer import LogsAnalyzer
from .database_statistics_collector import DatabaseStatisticsCollector
from .directory_breakdown_analyzer import DirectoryBreakdownAnalyzer

logger = get_logger(__name__, 'maintenance')


class CleanupStatistics:
    """
    Coordinates statistics gathering and analysis for cleanup planning.
    
    Responsibilities:
    - Coordinate statistics collection from various sources
    - Aggregate statistics from specialized analyzers
    - Provide unified statistics interface
    """
    
    def __init__(
        self,
        max_temp_size_gb: float = CleanupStatisticsConfig.DEFAULT_MAX_TEMP_SIZE_GB,
        max_log_size_gb: float = CleanupStatisticsConfig.DEFAULT_MAX_LOG_SIZE_GB
    ) -> None:
        """
        Initialize cleanup statistics coordinator.
        
        Args:
            max_temp_size_gb: Maximum allowed temp directory size in GB
            max_log_size_gb: Maximum allowed logs directory size in GB
        """
        self.logger = logger
        self.max_temp_size_gb = max_temp_size_gb
        self.max_log_size_gb = max_log_size_gb
        
        # Initialize analyzers
        self.temp_analyzer = TempDirectoryAnalyzer(
            temp_root=map_pro_paths.data_temp
        )
        self.downloads_analyzer = DownloadsDirectoryAnalyzer(
            downloads_root=map_pro_paths.data_root / 'downloads'
        )
        self.logs_analyzer = LogsAnalyzer(
            log_directories=[
                map_pro_paths.logs_engines,
                map_pro_paths.logs_system,
                map_pro_paths.logs_alerts,
                map_pro_paths.logs_integrations
            ]
        )
        self.db_collector = DatabaseStatisticsCollector(
            db_coordinator=db_coordinator
        )
        self.breakdown_analyzer = DirectoryBreakdownAnalyzer(
            map_pro_paths=map_pro_paths
        )
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """
        Get current system statistics for cleanup planning.
        
        Returns:
            Dictionary containing all cleanup statistics
        """
        stats = self._initialize_statistics_structure()
        
        try:
            # Collect from all sources
            stats.update(self.temp_analyzer.analyze())
            stats.update(self.downloads_analyzer.analyze())
            stats['logs_size_gb'] = self.logs_analyzer.get_total_size_gb()
            stats.update(self.db_collector.get_statistics())
            
        except Exception as e:
            self.logger.error(f"Error gathering cleanup statistics: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def get_directory_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed breakdown of directory sizes and contents.
        
        Returns:
            Dictionary with detailed analysis of each major directory
        """
        try:
            return self.breakdown_analyzer.analyze_all_directories()
        except Exception as e:
            self.logger.error(f"Error in directory breakdown: {e}")
            return {'error': str(e)}
    
    def _initialize_statistics_structure(self) -> Dict[str, Any]:
        """
        Initialize the statistics dictionary structure.
        
        Returns:
            Dictionary with default values for all statistics
        """
        return {
            'temp_directory_size_gb': 0,
            'downloads_size_gb': 0,
            'logs_size_gb': 0,
            'old_jobs_count': 0,
            'failed_jobs_count': 0,
            'temp_files_count': 0,
            'download_files_count': 0,
            'workspace_directories_count': 0,
            'oldest_temp_file': None,
            'oldest_download': None,
            'newest_temp_file': None,
            'newest_download': None,
            'by_directory': {}
        }


__all__ = ['CleanupStatistics']