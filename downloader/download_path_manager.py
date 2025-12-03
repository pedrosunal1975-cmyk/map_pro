"""
Download Path Manager
====================

Handles generation of download paths for filings.
Responsible for directory structure and filename extraction.
"""

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from database.models.core_models import Filing


class DownloadPathManager:
    """
    Manages download path generation for filings.
    
    Generates market-agnostic paths using entity data directory structure:
    data_root/entities/{market}/{entity}/filings/{filing_type}/{filing_id}/filename
    """
    
    def __init__(self, paths_config):
        """
        Initialize path manager.
        
        Args:
            paths_config: Configuration object with data_root path
        """
        self.data_root = paths_config.data_root
    
    def generate_download_path(self, filing: Filing, url: str) -> Path:
        """
        Generate download path for filing.
        
        Args:
            filing: Filing database object
            url: Download URL (used to extract filename)
            
        Returns:
            Path for saving downloaded file
            
        Raises:
            ValueError: If path cannot be generated
        """
        try:
            filing_dir = self._build_filing_directory(filing)
            filename = self._extract_filename(url, filing)
            return filing_dir / filename
            
        except Exception as e:
            raise ValueError(f"Failed to generate download path: {e}") from e
    
    def _build_filing_directory(self, filing: Filing) -> Path:
        """
        Build directory structure for filing.
        
        Args:
            filing: Filing database object
            
        Returns:
            Path to filing directory
        """
        entity_dir = self.data_root / filing.entity.data_directory_path
        filing_dir = (
            entity_dir / 'filings' / filing.filing_type / filing.market_filing_id
        )
        
        # Ensure directory exists
        filing_dir.mkdir(parents=True, exist_ok=True)
        
        return filing_dir
    
    def _extract_filename(self, url: str, filing: Filing) -> str:
        """
        Extract filename from URL with fallback.
        
        Args:
            url: Download URL
            filing: Filing object (for fallback filename)
            
        Returns:
            Filename for download
        """
        filename = self._parse_filename_from_url(url)
        if filename:
            return filename
        
        # Fallback: use filing ID with .zip extension (most common)
        return f"{filing.market_filing_id}.zip"
    
    def _parse_filename_from_url(self, url: str) -> Optional[str]:
        """
        Parse filename from URL.
        
        Args:
            url: URL to parse
            
        Returns:
            Filename if found, None otherwise
        """
        try:
            parsed_url = urlparse(url)
            
            if parsed_url.path:
                filename = Path(parsed_url.path).name
                if filename and filename != '/':
                    return filename
            
            return None
            
        except Exception:
            return None