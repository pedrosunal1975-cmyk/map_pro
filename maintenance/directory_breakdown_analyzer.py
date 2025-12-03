"""
Map Pro Directory Breakdown Analyzer
=====================================

Provides detailed breakdown of directory sizes and contents.

Save location: tools/maintenance/directory_breakdown_analyzer.py
"""

from pathlib import Path
from typing import Dict, Any, Tuple, List

from core.system_logger import get_logger
from .detailed_directory_analyzer import DetailedDirectoryAnalyzer

logger = get_logger(__name__, 'maintenance')


class DirectoryBreakdownAnalyzer:
    """
    Analyzes multiple directories for detailed breakdown.
    
    Responsibilities:
    - Coordinate analysis of major system directories
    - Provide unified breakdown report
    """
    
    def __init__(self, map_pro_paths) -> None:
        """
        Initialize directory breakdown analyzer.
        
        Args:
            map_pro_paths: Map Pro paths configuration object
        """
        self.map_pro_paths = map_pro_paths
        self.logger = logger
        self.directory_analyzer = DetailedDirectoryAnalyzer()
    
    def analyze_all_directories(self) -> Dict[str, Any]:
        """
        Get detailed breakdown of all major directories.
        
        Returns:
            Dictionary with analysis for each directory
        """
        breakdown = {}
        
        try:
            directories = self._get_directories_to_analyze()
            
            for name, path in directories:
                breakdown[name] = self.directory_analyzer.analyze(path)
            
        except Exception as e:
            self.logger.error(f"Error in directory breakdown: {e}")
            breakdown['error'] = str(e)
        
        return breakdown
    
    def _get_directories_to_analyze(self) -> List[Tuple[str, Path]]:
        """
        Get list of directories to analyze.
        
        Returns:
            List of tuples (directory_name, directory_path)
        """
        return [
            ('temp', self.map_pro_paths.data_temp),
            ('downloads', self.map_pro_paths.data_root / 'downloads'),
            ('logs_engines', self.map_pro_paths.logs_engines),
            ('logs_system', self.map_pro_paths.logs_system),
            ('logs_alerts', self.map_pro_paths.logs_alerts),
            ('logs_integrations', self.map_pro_paths.logs_integrations),
            ('entities', self.map_pro_paths.data_entities),
            ('parsed_facts', self.map_pro_paths.data_parsed_facts),
            ('mapped_statements', self.map_pro_paths.data_mapped_statements),
        ]


__all__ = ['DirectoryBreakdownAnalyzer']