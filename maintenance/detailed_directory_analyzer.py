"""
Map Pro Detailed Directory Analyzer
====================================

Provides detailed analysis of individual directories.

Save location: tools/maintenance/detailed_directory_analyzer.py
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

from core.system_logger import get_logger
from .cleanup_statistics_config import CleanupStatisticsConfig
from .file_tracker import FileAgeCategorizer, FileTypeTracker, LargestFilesTracker

logger = get_logger(__name__, 'maintenance')


class DetailedDirectoryAnalyzer:
    """
    Provides detailed analysis of a directory.
    
    Responsibilities:
    - Calculate directory size and counts
    - Track file types distribution
    - Track largest files
    - Categorize files by age
    """
    
    def __init__(self) -> None:
        """Initialize detailed directory analyzer."""
        self.logger = logger
    
    def analyze(self, directory: Path) -> Dict[str, Any]:
        """
        Perform detailed analysis of a specific directory.
        
        Args:
            directory: Directory path to analyze
            
        Returns:
            Dictionary with detailed analysis results
        """
        analysis = self._initialize_analysis_structure()
        
        if not directory.exists():
            return analysis
        
        analysis['exists'] = True
        
        try:
            self._analyze_directory_contents(
                directory=directory,
                analysis=analysis
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing directory {directory}: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _initialize_analysis_structure(self) -> Dict[str, Any]:
        """
        Initialize analysis result structure.
        
        Returns:
            Dictionary with default values
        """
        return {
            'exists': False,
            'total_size_gb': 0,
            'file_count': 0,
            'directory_count': 0,
            'largest_files': [],
            'file_types': {},
            'age_distribution': {
                'last_day': 0,
                'last_week': 0,
                'last_month': 0,
                'older': 0
            }
        }
    
    def _analyze_directory_contents(
        self,
        directory: Path,
        analysis: Dict[str, Any]
    ) -> None:
        """
        Analyze directory contents.
        
        Args:
            directory: Directory to analyze
            analysis: Analysis dictionary to populate
        """
        total_size = 0
        file_count = 0
        dir_count = 0
        
        # Initialize trackers
        age_categorizer = FileAgeCategorizer()
        type_tracker = FileTypeTracker()
        largest_tracker = LargestFilesTracker(
            max_files=CleanupStatisticsConfig.MAX_LARGEST_FILES_TO_TRACK
        )
        
        for item in directory.rglob('*'):
            try:
                if item.is_file():
                    file_size = item.stat().st_size
                    total_size += file_size
                    file_count += 1
                    
                    # Track largest files
                    largest_tracker.add_file(
                        path=item.relative_to(directory),
                        size_bytes=file_size
                    )
                    
                    # Track file types
                    type_tracker.add_file(item)
                    
                    # Categorize by age
                    file_time = datetime.fromtimestamp(
                        item.stat().st_mtime,
                        timezone.utc
                    )
                    age_categorizer.categorize(file_time)
                
                elif item.is_dir():
                    dir_count += 1
            
            except (OSError, PermissionError) as e:
                self.logger.debug(f"Skipping inaccessible item {item}: {e}")
                continue
        
        # Populate analysis results
        analysis['total_size_gb'] = total_size / CleanupStatisticsConfig.BYTES_PER_GB
        analysis['file_count'] = file_count
        analysis['directory_count'] = dir_count
        analysis['largest_files'] = largest_tracker.get_largest_files()
        analysis['file_types'] = type_tracker.get_file_types()
        analysis['age_distribution'] = age_categorizer.get_distribution()


__all__ = ['DetailedDirectoryAnalyzer']