"""
Filesystem Utilities
===================

File: engines/extractor/filesystem_utils.py

Common filesystem operations for validation.
Extracted to avoid duplication across validators.
Imported by extraction_validators.py
"""

import shutil
from pathlib import Path

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class FilesystemUtils:
    """
    Utility class for filesystem operations.
    
    Provides safe, reusable filesystem checks.
    """
    
    @staticmethod
    def is_readable(path: Path) -> bool:
        """
        Check if path is readable.
        
        Args:
            path: Path to check
            
        Returns:
            True if readable
        """
        try:
            path.stat()
            if path.is_file():
                with open(path, 'rb') as f:
                    f.read(1)
            return True
        except Exception:
            return False
    
    @staticmethod
    def is_writable(path: Path) -> bool:
        """
        Check if path is writable.
        
        Args:
            path: Path to check
            
        Returns:
            True if writable
        """
        try:
            if path.is_dir():
                test_file = path / '.write_test'
                test_file.touch()
                test_file.unlink()
                return True
            else:
                return False
        except Exception:
            return False
    
    @staticmethod
    def get_free_space_mb(path: Path) -> float:
        """
        Get free disk space in MB.
        
        Args:
            path: Path to check
            
        Returns:
            Free space in MB
        """
        try:
            # Get path that exists
            check_path = path if path.exists() else path.parent
            
            # Get disk usage
            stat = shutil.disk_usage(check_path)
            bytes_per_mb = 1024 * 1024
            return stat.free / bytes_per_mb
            
        except Exception as e:
            logger.warning(f"Failed to get free space: {e}")
            return float('inf')  # Assume sufficient space if check fails
    
    @staticmethod
    def get_file_size_mb(path: Path) -> float:
        """
        Get file size in megabytes.
        
        Args:
            path: Path to file
            
        Returns:
            Size in MB
        """
        try:
            size_bytes = path.stat().st_size
            bytes_per_mb = 1024 * 1024
            return size_bytes / bytes_per_mb
        except Exception as e:
            logger.warning(f"Failed to get file size: {e}")
            return 0.0
    
    @staticmethod
    def count_files(directory: Path) -> int:
        """
        Count files in directory recursively.
        
        Args:
            directory: Directory to scan
            
        Returns:
            Number of files
        """
        try:
            all_files = list(directory.rglob('*'))
            return sum(1 for f in all_files if f.is_file())
        except Exception as e:
            logger.warning(f"Failed to count files: {e}")
            return 0