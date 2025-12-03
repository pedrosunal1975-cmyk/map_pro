# File: /map_pro/markets/sec/sec_downloader/sec_download_delegator.py

"""
SEC Download Delegator
======================

Delegates actual download work to the generic downloader.
Manages SEC-specific headers and URL handling.
"""

from typing import Optional

from core.system_logger import get_logger
from database.models.core_models import Filing
from engines.downloader import DownloadResult, DownloadCoordinator

logger = get_logger(__name__, 'market')


class SECDownloadDelegator:
    """
    Delegates download to generic downloader.
    
    Responsibilities:
    - Set SEC-specific custom headers
    - Manage URL overrides for ZIP files
    - Delegate to generic downloader
    - Clean up custom headers after download
    """
    
    def __init__(
        self,
        user_agent: str,
        generic_downloader: Optional[DownloadCoordinator] = None
    ):
        """
        Initialize download delegator.
        
        Args:
            user_agent: SEC user-agent string
            generic_downloader: Generic downloader instance (created if None)
        """
        self.user_agent = user_agent
        self.generic_downloader = generic_downloader or DownloadCoordinator()
        self.logger = logger
    
    async def delegate_download(
        self,
        filing: Filing,
        session,
        zip_url: str
    ) -> DownloadResult:
        """
        Delegate download to generic downloader with SEC headers.
        
        Args:
            filing: Filing object
            session: Database session
            zip_url: Resolved ZIP file URL
            
        Returns:
            DownloadResult from generic downloader
        """
        self.logger.debug(f"Delegating to generic downloader: {zip_url}")
        
        # Backup original URL and set custom headers
        original_url_backup = filing.original_url
        self._set_custom_headers(filing)
        
        # Update filing URL if different
        if filing.original_url != zip_url:
            filing.original_url = zip_url
        
        # Execute download
        download_result = await self.generic_downloader.download_filing(
            filing,
            session,
            custom_headers={'User-Agent': self.user_agent},
            override_url=zip_url,
            _from_market_coordinator=True
        )
        
        # Restore original URL on failure
        if not download_result.success:
            filing.original_url = original_url_backup
        
        # Always clean up headers
        self.cleanup_headers(filing)
        
        return download_result
    
    def _set_custom_headers(self, filing: Filing):
        """
        Set SEC-specific custom headers on filing object.
        
        Args:
            filing: Filing object to modify
        """
        filing._custom_headers = {
            'User-Agent': self.user_agent
        }
        self.logger.debug(f"Set SEC User-Agent header: {self.user_agent[:50]}...")
    
    def cleanup_headers(self, filing: Filing):
        """
        Remove custom headers from filing object.
        
        Args:
            filing: Filing object to clean
        """
        if hasattr(filing, '_custom_headers'):
            delattr(filing, '_custom_headers')