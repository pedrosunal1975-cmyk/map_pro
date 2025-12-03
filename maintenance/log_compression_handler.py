# File: /map_pro/tools/maintenance/log_compression_handler.py

"""
Log Compression Handler
========================

Handles compression of log files using gzip.
Calculates space savings and manages compressed files.
"""

import gzip
import shutil
from pathlib import Path
from typing import Dict, Any

from core.system_logger import get_logger

from .log_rotation_constants import (
    COMPRESSED_EXTENSION,
    BYTES_PER_KILOBYTE,
    BYTES_PER_MEGABYTE
)

logger = get_logger(__name__, 'maintenance')


class LogCompressionHandler:
    """
    Handles log file compression.
    
    Responsibilities:
    - Compress log files using gzip
    - Calculate space savings
    - Remove original files after compression
    - Handle compression errors
    """
    
    def __init__(self):
        """Initialize log compression handler."""
        self.logger = logger
    
    def compress_log_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Compress a log file using gzip.
        
        Args:
            file_path: Path to log file
            
        Returns:
            Compression result dictionary with:
            - success: Boolean indicating success
            - space_saved_mb: Space saved in MB
            - error: Error message if failed
        """
        result = {
            'success': False,
            'space_saved_mb': 0,
            'error': None
        }
        
        try:
            compressed_path = self._get_compressed_path(file_path)
            
            # Skip if already compressed
            if compressed_path.exists():
                return result
            
            original_size = file_path.stat().st_size
            
            # Perform compression
            self._perform_compression(file_path, compressed_path)
            
            compressed_size = compressed_path.stat().st_size
            
            # Remove original file
            file_path.unlink()
            
            # Calculate savings
            space_saved = self._calculate_space_saved(original_size, compressed_size)
            
            result['success'] = True
            result['space_saved_mb'] = space_saved
            
            self._log_compression_success(file_path.name, original_size, compressed_size, space_saved)
            
        except Exception as exception:
            result['error'] = f"Failed to compress {file_path}: {exception}"
            self.logger.error(result['error'])
        
        return result
    
    def _get_compressed_path(self, file_path: Path) -> Path:
        """
        Get path for compressed file.
        
        Args:
            file_path: Original file path
            
        Returns:
            Path for compressed file
        """
        return Path(str(file_path) + COMPRESSED_EXTENSION)
    
    def _perform_compression(self, source: Path, destination: Path) -> None:
        """
        Perform gzip compression.
        
        Args:
            source: Source file path
            destination: Destination compressed file path
        """
        with open(source, 'rb') as f_in:
            with gzip.open(destination, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _calculate_space_saved(self, original_size: int, compressed_size: int) -> float:
        """
        Calculate space saved by compression.
        
        Args:
            original_size: Original file size in bytes
            compressed_size: Compressed file size in bytes
            
        Returns:
            Space saved in megabytes, rounded to 2 decimal places
        """
        space_saved_bytes = original_size - compressed_size
        space_saved_mb = space_saved_bytes / BYTES_PER_MEGABYTE
        return round(space_saved_mb, 2)
    
    def _log_compression_success(
        self,
        filename: str,
        original_size: int,
        compressed_size: int,
        space_saved: float
    ) -> None:
        """
        Log successful compression.
        
        Args:
            filename: Name of compressed file
            original_size: Original file size in bytes
            compressed_size: Compressed file size in bytes
            space_saved: Space saved in MB
        """
        original_kb = original_size / BYTES_PER_KILOBYTE
        compressed_kb = compressed_size / BYTES_PER_KILOBYTE
        
        self.logger.debug(
            f"Compressed {filename}: "
            f"{original_kb:.1f} KB -> {compressed_kb:.1f} KB "
            f"(saved {space_saved:.2f} MB)"
        )


__all__ = ['LogCompressionHandler']