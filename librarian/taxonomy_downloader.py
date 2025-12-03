"""
Map Pro Taxonomy Downloader
===========================

Downloads XBRL taxonomy files with proper separation of concerns.
Coordinates the download, extraction, and validation workflow.

File: /map_pro/engines/librarian/taxonomy_downloader.py

Usage:
    from engines.librarian.taxonomy_downloader import TaxonomyDownloader
    
    downloader = TaxonomyDownloader()
    result = await downloader.download_taxonomy(config)
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

from .taxonomy_download_components import (
    ArchiveType,
    ExtractionResult,
    AuthenticationProvider,
    FileDownloader,
    ArchiveExtractor,
    FileValidator,
    FilesystemAnalyzer,
    URLUtilities
)

logger = get_logger(__name__, 'engine')


# =============================================================================
# CONFIGURATION & RESULTS
# =============================================================================

@dataclass
class DownloadConfig:
    """Configuration for taxonomy download."""
    url: str
    folder_name: str
    file_type: str = "zip"
    credentials_required: bool = False
    
    @property
    def archive_type(self) -> ArchiveType:
        """Convert file_type string to ArchiveType enum."""
        try:
            return ArchiveType(self.file_type)
        except ValueError:
            return ArchiveType.ZIP


@dataclass
class DownloadResult:
    """Result of taxonomy download operation."""
    success: bool
    extract_path: Optional[Path] = None
    size_mb: float = 0.0
    file_count: int = 0
    error: Optional[str] = None
    folder_name: Optional[str] = None
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'extract_path': str(self.extract_path) if self.extract_path else None,
            'size_mb': self.size_mb,
            'file_count': self.file_count,
            'error': self.error,
            'folder_name': self.folder_name,
            'url': self.url
        }


# =============================================================================
# DOWNLOAD COORDINATION
# =============================================================================

class TaxonomyDownloadCoordinator:
    """
    Single Responsibility: Coordinate taxonomy download workflow.
    
    Orchestrates the download, extraction, and validation process
    by delegating to specialized components.
    
    Responsibilities:
    - Coordinate workflow steps
    - Manage paths and directories
    - Handle cleanup operations
    - Return structured results
    
    Does NOT:
    - Download files (FileDownloader handles this)
    - Extract archives (ArchiveExtractor handles this)
    - Validate files (FileValidator handles this)
    - Analyze directories (FilesystemAnalyzer handles this)
    """
    
    def __init__(
        self,
        downloads_dir: Optional[Path] = None,
        libraries_dir: Optional[Path] = None
    ):
        """
        Initialize download coordinator.
        
        Args:
            downloads_dir: Directory for temporary downloads
            libraries_dir: Directory for extracted libraries
        """
        self.downloads_dir = downloads_dir or (
            map_pro_paths.data_taxonomies / "downloads"
        )
        self.libraries_dir = libraries_dir or (
            map_pro_paths.data_taxonomies / "libraries"
        )
        
        # Create directories
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.libraries_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.downloader = FileDownloader()
        self.extractor = ArchiveExtractor()
        self.validator = FileValidator()
        self.analyzer = FilesystemAnalyzer()
        self.auth_provider = AuthenticationProvider()
        self.url_utils = URLUtilities()
        
        logger.info("Taxonomy download coordinator initialized")
    
    async def download_taxonomy(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Download and extract taxonomy.
        
        This is the main entry point for taxonomy downloads. It:
        1. Validates configuration
        2. Checks if download can be skipped
        3. Downloads file with authentication if needed
        4. Extracts archive
        5. Analyzes extracted files
        6. Cleans up temporary files
        
        Args:
            config: Taxonomy configuration dictionary with:
                - url: Download URL
                - folder_name: Target folder name
                - file_type: Archive type (zip, tar, single_file)
                - credentials_required: Whether auth is needed
            
        Returns:
            Dictionary with download results:
                - success: bool
                - extract_path: Path to extracted files
                - size_mb: Size in megabytes
                - file_count: Number of files
                - error: Error message if failed
        """
        download_config = DownloadConfig(**config)
        
        logger.info(
            f"Processing taxonomy: {download_config.folder_name} "
            f"from {download_config.url}"
        )
        
        # Determine paths
        filename = self.url_utils.get_filename_from_url(download_config.url)
        download_path = self.downloads_dir / filename
        extract_path = self.libraries_dir / download_config.folder_name
        
        # Check if already downloaded
        if self._should_skip_download(download_config, download_path):
            logger.info(f"Valid archive exists, skipping download: {download_path}")
        else:
            # Download file
            download_success = await self._download_file(
                download_config,
                download_path
            )
            
            if not download_success:
                return DownloadResult(
                    success=False,
                    error=f"Download failed after retries",
                    url=download_config.url
                ).to_dict()
        
        # Extract archive
        extraction_result = await self._extract_file(
            download_path,
            extract_path,
            download_config
        )
        
        if not extraction_result.success:
            self._cleanup_download(download_path)
            return DownloadResult(
                success=False,
                error=extraction_result.error,
                url=download_config.url
            ).to_dict()
        
        # Analyze extracted files
        analysis = self._analyze_extraction(extract_path)
        
        # Cleanup
        self._cleanup_download(download_path)
        
        logger.info(
            f"Successfully extracted {download_config.folder_name}: "
            f"{analysis['file_count']} files, {analysis['size_mb']:.2f} MB"
        )
        
        return DownloadResult(
            success=True,
            extract_path=extract_path,
            size_mb=analysis['size_mb'],
            file_count=analysis['file_count'],
            folder_name=download_config.folder_name
        ).to_dict()
    
    def _should_skip_download(
        self,
        config: DownloadConfig,
        download_path: Path
    ) -> bool:
        """
        Check if download can be skipped.
        
        Args:
            config: Download configuration
            download_path: Path to potential existing download
            
        Returns:
            True if valid file exists and download can be skipped
        """
        return (
            config.archive_type == ArchiveType.ZIP and
            self.validator.is_valid_zip(download_path)
        )
    
    async def _download_file(
        self,
        config: DownloadConfig,
        destination: Path
    ) -> bool:
        """
        Download file with authentication if needed.
        
        Args:
            config: Download configuration
            destination: Where to save file
            
        Returns:
            True if successful
        """
        auth = self.auth_provider.get_credentials(
            config.url,
            config.credentials_required
        )
        return await self.downloader.download(config.url, destination, auth)
    
    async def _extract_file(
        self,
        archive_path: Path,
        extract_path: Path,
        config: DownloadConfig
    ) -> ExtractionResult:
        """
        Extract downloaded file.
        
        Args:
            archive_path: Path to archive
            extract_path: Where to extract
            config: Download configuration
            
        Returns:
            ExtractionResult with success status
        """
        return await self.extractor.extract(
            archive_path,
            extract_path,
            config.archive_type
        )
    
    def _analyze_extraction(self, extract_path: Path) -> Dict[str, Any]:
        """
        Analyze extracted directory.
        
        Args:
            extract_path: Path to extracted files
            
        Returns:
            Dictionary with size_mb and file_count
        """
        total_size = self.analyzer.calculate_directory_size(extract_path)
        file_count = self.analyzer.count_files(extract_path)
        
        return {
            'size_mb': total_size / (1024 * 1024),
            'file_count': file_count
        }
    
    def _cleanup_download(self, download_path: Path) -> None:
        """
        Remove downloaded archive file.
        
        Args:
            download_path: Path to file to remove
        """
        if download_path.exists():
            download_path.unlink()
            logger.debug(f"Cleaned up download file: {download_path}")


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

class TaxonomyDownloader(TaxonomyDownloadCoordinator):
    """
    Backward compatibility wrapper for TaxonomyDownloader.
    
    Maintains the original TaxonomyDownloader interface while
    using the refactored implementation underneath.
    
    This allows existing code to continue working without changes:
        downloader = TaxonomyDownloader()
        result = await downloader.download_taxonomy(config)
    """
    
    def __init__(self):
        """Initialize with default paths."""
        super().__init__()
        
        # Expose internal component properties for backward compatibility
        self.max_retries = self.downloader.max_retries
        self.timeout = self.downloader.timeout
        self.chunk_size = self.downloader.chunk_size
        self.headers = self.downloader.headers
        
        logger.info("Taxonomy downloader initialized (legacy interface)")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Backward compatibility method that delegates to FileValidator.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash as hex string
        """
        return self.validator.calculate_hash(file_path)


__all__ = [
    'TaxonomyDownloader',
    'TaxonomyDownloadCoordinator',
    'DownloadConfig',
    'DownloadResult'
]