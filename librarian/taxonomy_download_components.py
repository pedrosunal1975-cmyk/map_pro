"""
Map Pro Taxonomy Download Components
====================================

Core components for taxonomy downloading and extraction.
Contains specialized classes for download, extraction, validation, and analysis.

File: /map_pro/engines/librarian/taxonomy_download_components.py
"""

import os
import asyncio
import zipfile
import tarfile
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

import aiohttp
import aiofiles

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class ArchiveType(Enum):
    """Supported archive types."""
    ZIP = "zip"
    TAR = "tar"
    SINGLE_FILE = "single_file"


@dataclass
class ExtractionResult:
    """Result of archive extraction."""
    success: bool
    error: Optional[str] = None


# =============================================================================
# AUTHENTICATION
# =============================================================================

class AuthenticationProvider:
    """
    Single Responsibility: Provide authentication credentials.
    
    Handles retrieving credentials from environment variables
    or other secure sources.
    """
    
    def get_credentials(self, url: str, requires_auth: bool) -> Optional[Tuple[str, str]]:
        """
        Get authentication credentials if required.
        
        Args:
            url: Target URL
            requires_auth: Whether authentication is required
            
        Returns:
            (username, password) tuple or None
        """
        if not requires_auth:
            return None
        
        # Check for IFRS credentials
        if 'ifrs.org' in url:
            return self._get_ifrs_credentials()
        
        return None
    
    def _get_ifrs_credentials(self) -> Optional[Tuple[str, str]]:
        """Get IFRS credentials from environment."""
        email = os.getenv('IFRS_EMAIL')
        password = os.getenv('IFRS_PASSWORD')
        
        if email and password:
            logger.info("Using IFRS credentials from environment")
            return (email, password)
        
        logger.warning(
            "IFRS credentials not found in environment "
            "(IFRS_EMAIL, IFRS_PASSWORD)"
        )
        return None


# =============================================================================
# FILE DOWNLOADING
# =============================================================================

class FileDownloader:
    """
    Single Responsibility: Download files from URLs.
    
    Handles HTTP downloads with retry logic, authentication,
    and proper error handling.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
        chunk_size: int = 8192
    ):
        """
        Initialize file downloader.
        
        Args:
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            chunk_size: Download chunk size in bytes
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.chunk_size = chunk_size
        
        self.headers = {
            'User-Agent': 'MapPro/1.0 (Taxonomy Downloader) XBRL Library Manager'
        }
    
    async def download(
        self,
        url: str,
        destination: Path,
        auth: Optional[Tuple[str, str]] = None
    ) -> bool:
        """
        Download file with retry logic.
        
        Args:
            url: Download URL
            destination: Path to save file
            auth: Optional (username, password) tuple
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Download attempt {attempt + 1}/{self.max_retries}: {url}"
                )
                
                success = await self._attempt_download(url, destination, auth)
                if success:
                    return True
                
            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                self._cleanup_failed_download(destination)
                
                if attempt < self.max_retries - 1:
                    await self._backoff(attempt)
        
        logger.error(f"Failed to download {url} after {self.max_retries} attempts")
        return False
    
    async def _attempt_download(
        self,
        url: str,
        destination: Path,
        auth: Optional[Tuple[str, str]]
    ) -> bool:
        """Single download attempt."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        auth_obj = aiohttp.BasicAuth(auth[0], auth[1]) if auth else None
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers=self.headers,
                auth=auth_obj
            ) as response:
                response.raise_for_status()
                
                async with aiofiles.open(destination, 'wb') as f:
                    async for chunk in response.content.iter_chunked(
                        self.chunk_size
                    ):
                        await f.write(chunk)
        
        logger.info(f"Successfully downloaded: {destination}")
        return True
    
    def _cleanup_failed_download(self, file_path: Path) -> None:
        """Remove partially downloaded file."""
        if file_path.exists():
            file_path.unlink()
    
    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff between retries."""
        delay = 2 ** attempt
        await asyncio.sleep(delay)


# =============================================================================
# ARCHIVE EXTRACTION
# =============================================================================

class ArchiveExtractor:
    """
    Single Responsibility: Extract archive files.
    
    Handles extraction of ZIP, TAR, and single files
    to specified directories.
    """
    
    async def extract(
        self,
        archive_path: Path,
        extract_path: Path,
        archive_type: ArchiveType
    ) -> ExtractionResult:
        """
        Extract archive based on type.
        
        Args:
            archive_path: Path to archive file
            extract_path: Destination directory
            archive_type: Type of archive
            
        Returns:
            ExtractionResult with success status
        """
        extract_path.mkdir(parents=True, exist_ok=True)
        
        try:
            if archive_type == ArchiveType.ZIP:
                return self._extract_zip(archive_path, extract_path)
            
            elif archive_type == ArchiveType.TAR:
                return self._extract_tar(archive_path, extract_path)
            
            elif archive_type == ArchiveType.SINGLE_FILE:
                return self._copy_single_file(archive_path, extract_path)
            
            else:
                return ExtractionResult(
                    success=False,
                    error=f"Unknown archive type: {archive_type}"
                )
                
        except zipfile.BadZipFile:
            return ExtractionResult(
                success=False,
                error="Invalid ZIP file (may be HTML error page)"
            )
        
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=str(e)
            )
    
    def _extract_zip(self, archive_path: Path, extract_path: Path) -> ExtractionResult:
        """Extract ZIP archive."""
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        logger.info(f"Extracted ZIP archive to: {extract_path}")
        return ExtractionResult(success=True)
    
    def _extract_tar(self, archive_path: Path, extract_path: Path) -> ExtractionResult:
        """Extract TAR archive."""
        with tarfile.open(archive_path, 'r:*') as tar_ref:
            tar_ref.extractall(extract_path, filter='data')
        
        logger.info(f"Extracted TAR archive to: {extract_path}")
        return ExtractionResult(success=True)
    
    def _copy_single_file(
        self,
        archive_path: Path,
        extract_path: Path
    ) -> ExtractionResult:
        """Copy single file to destination."""
        final_path = extract_path / archive_path.name
        shutil.copy2(archive_path, final_path)
        
        logger.info(f"Copied single file to: {final_path}")
        return ExtractionResult(success=True)


# =============================================================================
# FILE VALIDATION
# =============================================================================

class FileValidator:
    """
    Single Responsibility: Validate downloaded files.
    
    Checks if files exist and are valid archives.
    """
    
    def is_valid_zip(self, file_path: Path) -> bool:
        """
        Check if file is a valid ZIP archive.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if valid ZIP archive
        """
        if not file_path.exists() or not file_path.is_file():
            return False
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                return True
        except zipfile.BadZipFile:
            return False
    
    def calculate_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return ""


# =============================================================================
# FILESYSTEM ANALYSIS
# =============================================================================

class FilesystemAnalyzer:
    """
    Single Responsibility: Analyze filesystem structures.
    
    Calculates directory sizes, file counts, etc.
    """
    
    def calculate_directory_size(self, directory: Path) -> int:
        """
        Calculate total size of directory in bytes.
        
        Args:
            directory: Path to directory
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating directory size: {e}")
        
        return total_size
    
    def count_files(self, directory: Path) -> int:
        """
        Count number of files in directory.
        
        Args:
            directory: Path to directory
            
        Returns:
            Number of files
        """
        return sum(1 for _ in directory.rglob('*') if _.is_file())


# =============================================================================
# URL UTILITIES
# =============================================================================

class URLUtilities:
    """
    Single Responsibility: URL manipulation utilities.
    
    Extracts filenames from URLs, builds paths, etc.
    """
    
    def get_filename_from_url(self, url: str) -> str:
        """
        Extract filename from URL.
        
        Args:
            url: URL to extract filename from
            
        Returns:
            Filename string
        """
        filename = url.split('/')[-1].split('?')[0]
        
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"taxonomy_{timestamp}.zip"
        
        return filename


__all__ = [
    'ArchiveType',
    'ExtractionResult',
    'AuthenticationProvider',
    'FileDownloader',
    'ArchiveExtractor',
    'FileValidator',
    'FilesystemAnalyzer',
    'URLUtilities'
]