# File: engines/extractor/format_detectors.py

"""
Map Pro Format Detectors
========================

Detects archive format from files using multiple detection methods.
Provides robust format identification for various archive types.

Architecture: Multi-method format detection with fallback strategies.
"""

import zipfile
import tarfile
import gzip
from pathlib import Path
from typing import Optional

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class FormatDetector:
    """
    Detects archive format using multiple detection methods.
    
    Detection strategies (in order):
    1. Magic number detection (file headers)
    2. File extension
    3. Content validation
    
    Responsibilities:
    - Detect archive format from file
    - Handle edge cases and corrupted files
    - Provide fallback detection methods
    """
    
    MAGIC_NUMBERS = {
        b'PK\x03\x04': 'zip',
        b'PK\x05\x06': 'zip',
        b'PK\x07\x08': 'zip',
        b'\x1f\x8b': 'gz',
        b'BZh': 'tar.bz2',
        b'\xfd7zXZ\x00': 'tar.xz'
    }
    
    TAR_MAGIC = [
        b'ustar\x00',
        b'ustar  \x00'
    ]
    
    def __init__(self):
        self.logger = get_logger(__name__, 'engine')
    
    def detect_format(self, file_path: Path) -> Optional[str]:
        """
        Detect archive format from file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Format string ('zip', 'tar', 'gz', etc.) or None if detection fails
        """
        format_from_magic = self._detect_by_magic_number(file_path)
        if format_from_magic:
            self.logger.debug(f"Detected format by magic number: {format_from_magic}")
            return format_from_magic
        
        format_from_extension = self._detect_by_extension(file_path)
        if format_from_extension:
            if self._validate_format(file_path, format_from_extension):
                self.logger.debug(f"Detected format by extension: {format_from_extension}")
                return format_from_extension
        
        format_from_content = self._detect_by_content_validation(file_path)
        if format_from_content:
            self.logger.debug(f"Detected format by content: {format_from_content}")
            return format_from_content
        
        self.logger.warning(f"Could not detect format for {file_path}")
        return None
    
    def _detect_by_magic_number(self, file_path: Path) -> Optional[str]:
        """
        Detect format by reading file magic number.
        
        Args:
            file_path: Path to file
            
        Returns:
            Format string or None
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                
                for magic, format_type in self.MAGIC_NUMBERS.items():
                    if header.startswith(magic):
                        return format_type
                
                f.seek(257)
                tar_magic = f.read(8)
                for magic in self.TAR_MAGIC:
                    if tar_magic.startswith(magic):
                        return 'tar'
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Magic number detection failed: {e}")
            return None
    
    def _detect_by_extension(self, file_path: Path) -> Optional[str]:
        """
        Detect format by file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            Format string or None
        """
        full_suffix = ''.join(file_path.suffixes).lower()
        
        extension_map = {
            '.zip': 'zip',
            '.tar': 'tar',
            '.tar.gz': 'tar.gz',
            '.tgz': 'tar.gz',
            '.tar.bz2': 'tar.bz2',
            '.tbz2': 'tar.bz2',
            '.tar.xz': 'tar.xz',
            '.txz': 'tar.xz',
            '.gz': 'gz',
            '.bz2': 'tar.bz2',
            '.xz': 'tar.xz'
        }
        
        return extension_map.get(full_suffix)
    
    def _detect_by_content_validation(self, file_path: Path) -> Optional[str]:
        """
        Detect format by attempting to open as each type.
        
        Args:
            file_path: Path to file
            
        Returns:
            Format string or None
        """
        try:
            if zipfile.is_zipfile(file_path):
                return 'zip'
        except Exception as e:
            self.logger.debug(f"ZIP validation failed for {file_path}: {e}")
        
        try:
            if tarfile.is_tarfile(file_path):
                with tarfile.open(file_path, 'r:*') as tar:
                    if hasattr(tar, 'compression'):
                        if 'gz' in str(tar.compression).lower():
                            return 'tar.gz'
                        elif 'bz2' in str(tar.compression).lower():
                            return 'tar.bz2'
                return 'tar'
        except Exception as e:
            self.logger.debug(f"TAR validation failed for {file_path}: {e}")
        
        try:
            with gzip.open(file_path, 'rb') as gz:
                gz.read(1)
            return 'gz'
        except Exception as e:
            self.logger.debug(f"GZIP validation failed for {file_path}: {e}")
        
        return None
    
    def _validate_format(self, file_path: Path, format_type: str) -> bool:
        """
        Validate that file matches the specified format.
        
        Args:
            file_path: Path to file
            format_type: Format to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if format_type == 'zip':
                return zipfile.is_zipfile(file_path)
            
            elif format_type in ['tar', 'tar.gz', 'tar.bz2', 'tar.xz']:
                return tarfile.is_tarfile(file_path)
            
            elif format_type == 'gz':
                try:
                    with gzip.open(file_path, 'rb') as gz:
                        gz.read(1)
                    return True
                except Exception as e:
                    self.logger.debug(f"GZIP validation check failed: {e}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Format validation failed: {e}")
            return False
    
    def get_format_info(self, file_path: Path) -> dict:
        """
        Get detailed format information about file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with format details
        """
        detected_format = self.detect_format(file_path)
        
        info = {
            'format': detected_format,
            'is_compressed': detected_format in ['zip', 'gz', 'tar.gz', 'tar.bz2', 'tar.xz'],
            'is_archive': detected_format in ['zip', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz'],
            'requires_extraction': detected_format is not None,
            'file_size_bytes': file_path.stat().st_size if file_path.exists() else None
        }
        
        return info