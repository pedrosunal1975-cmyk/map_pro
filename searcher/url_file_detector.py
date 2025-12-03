"""
File: engines/searcher/url_file_detector.py
Path: engines/searcher/url_file_detector.py

URL File Detection
=================

Handles detection of file URLs and extension extraction.
Extracted from URLValidator to follow Single Responsibility Principle.
"""

from typing import Optional, List
from urllib.parse import urlparse

from core.system_logger import get_logger
from engines.searcher.url_constants import (
    URL_PATH_SEPARATOR,
    URL_EXTENSION_SEPARATOR
)

logger = get_logger(__name__, 'engine')


class URLFileDetector:
    """
    Detects downloadable files and extracts extensions from URLs.
    
    Responsibilities:
    - Identify downloadable file URLs
    - Extract file extensions
    - Validate extension format
    """
    
    def __init__(
        self, 
        downloadable_extensions: List[str],
        max_extension_length: int
    ) -> None:
        """
        Initialize file detector.
        
        Args:
            downloadable_extensions: List of file extensions that indicate downloadable files
            max_extension_length: Maximum valid extension length
        """
        self.downloadable_extensions = downloadable_extensions
        self.max_extension_length = max_extension_length
        
        logger.debug("URL file detector initialized")
    
    def get_file_extension(self, url: str) -> Optional[str]:
        """
        Extract file extension from URL.
        
        Args:
            url: URL to analyze
            
        Returns:
            File extension (including dot) or None if no valid extension found
        """
        if not url:
            return None
        
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            filename = self._extract_filename(path)
            extension = self._extract_extension(filename)
            
            if self._is_valid_extension(extension):
                return extension
            
            return None
            
        except (ValueError, AttributeError) as e:
            logger.error(f"Extension extraction failed for '{url}': {e}")
            return None
    
    def _extract_filename(self, path: str) -> str:
        """
        Extract filename from URL path.
        
        Args:
            path: URL path component
            
        Returns:
            Filename from path
        """
        if URL_PATH_SEPARATOR in path:
            return path.rsplit(URL_PATH_SEPARATOR, 1)[-1]
        return path
    
    def _extract_extension(self, filename: str) -> Optional[str]:
        """
        Extract extension from filename.
        
        Args:
            filename: Filename to extract extension from
            
        Returns:
            Extension with dot prefix or None
        """
        if URL_EXTENSION_SEPARATOR not in filename:
            return None
        
        extension_part = filename.rsplit(URL_EXTENSION_SEPARATOR, 1)[-1]
        return f'{URL_EXTENSION_SEPARATOR}{extension_part.lower()}'
    
    def _is_valid_extension(self, extension: Optional[str]) -> bool:
        """
        Validate extension format and length.
        
        Args:
            extension: Extension to validate
            
        Returns:
            True if extension is valid
        """
        if not extension:
            return False
        
        if len(extension) > self.max_extension_length:
            return False
        
        try:
            return extension.isascii()
        except AttributeError:
            return False
    
    def is_download_url(self, url: str) -> bool:
        """
        Check if URL appears to be a downloadable file.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to point to a downloadable file
        """
        if not url:
            return False
        
        url_lower = url.lower()
        
        return any(
            ext in url_lower 
            for ext in self.downloadable_extensions
        )