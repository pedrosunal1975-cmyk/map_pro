"""
Map Pro Logs Analyzer
======================

Analyzes log directories for cleanup statistics.

Save location: tools/maintenance/logs_analyzer.py
"""

from pathlib import Path
from typing import List

from core.system_logger import get_logger
from .cleanup_statistics_config import CleanupStatisticsConfig

logger = get_logger(__name__, 'maintenance')


class LogsAnalyzer:
    """
    Analyzes log directories.
    
    Responsibilities:
    - Calculate total logs directory size
    - Handle multiple log directories
    """
    
    def __init__(self, log_directories: List[Path]) -> None:
        """
        Initialize logs analyzer.
        
        Args:
            log_directories: List of log directory paths to analyze
        """
        self.log_directories = log_directories
        self.logger = logger
    
    def get_total_size_gb(self) -> float:
        """
        Calculate total logs directory size in GB.
        
        Returns:
            Total size of all log directories in gigabytes
        """
        try:
            total_size = 0
            
            for log_dir in self.log_directories:
                total_size += self._get_directory_size_bytes(log_dir)
            
            return total_size / CleanupStatisticsConfig.BYTES_PER_GB
        
        except Exception as e:
            self.logger.error(f"Error calculating logs size: {e}")
            return 0.0
    
    def _get_directory_size_bytes(self, directory: Path) -> int:
        """
        Calculate size of a directory in bytes.
        
        Args:
            directory: Directory to calculate size for
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        
        if not directory.exists():
            return total_size
        
        for item in directory.rglob('*'):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                except (OSError, PermissionError) as e:
                    self.logger.debug(f"Skipping inaccessible file {item}: {e}")
                    continue
        
        return total_size


__all__ = ['LogsAnalyzer']