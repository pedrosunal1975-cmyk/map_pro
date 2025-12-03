# File: /map_pro/markets/sec/sec_downloader/sec_url_resolver.py

"""
SEC URL Resolver
================

Resolves ZIP file URLs for SEC filings.
Uses searcher-provided URLs when available, otherwise identifies via strategies.
"""

from typing import Optional, Tuple

from core.system_logger import get_logger
from database.models.core_models import Filing
from markets.sec.sec_searcher import SECAPIClient

from .sec_rate_limiter import SECRateLimiter, get_shared_sec_rate_limiter
from .sec_index_parser import SECIndexParser
from .sec_file_identifier import SECFileIdentifier
from .sec_download_monitor import SECDownloadMonitor, get_sec_download_monitor
from .sec_download_strategies import create_default_strategy_chain

logger = get_logger(__name__, 'market')

# Strategy identifiers
STRATEGY_SEARCHER_PROVIDED = 'searcher_provided'


class SECURLResolver:
    """
    Resolves ZIP file URLs for SEC filings.
    
    Responsibilities:
    - Check if searcher already provided URL
    - Identify ZIP URL using fallback strategies
    - Apply rate limiting during identification
    - Record identification metrics
    """
    
    def __init__(
        self,
        user_agent: str,
        rate_limiter: Optional[SECRateLimiter] = None,
        monitor: Optional[SECDownloadMonitor] = None
    ):
        """
        Initialize URL resolver.
        
        Args:
            user_agent: SEC user-agent string
            rate_limiter: Rate limiter instance (shared if None)
            monitor: Download monitor instance (global if None)
        """
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter or get_shared_sec_rate_limiter()
        self.monitor = monitor or get_sec_download_monitor()
        
        # Initialize components for ZIP identification
        self.api_client = SECAPIClient(user_agent=self.user_agent)
        self.index_parser = SECIndexParser()
        self.file_identifier = SECFileIdentifier()
        
        self.strategy_chain = create_default_strategy_chain(
            self.api_client,
            self.index_parser,
            self.file_identifier
        )
        
        self.logger = logger
    
    async def resolve_zip_url(
        self,
        filing: Filing,
        cik: str,
        accession_number: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve ZIP URL either from searcher or by identification.
        
        CRITICAL: Prefer searcher-provided URL if available.
        Only identify if URL is missing or empty.
        
        Args:
            filing: Filing object that may contain original_url
            cik: Normalized CIK
            accession_number: Filing accession number
            
        Returns:
            Tuple of (zip_url, strategy_used)
            Returns (None, None) if resolution fails
        """
        # Check if searcher already provided URL
        if self._has_searcher_url(filing):
            return self._use_searcher_url(filing)
        
        # No URL from searcher - identify ZIP file
        return await self._identify_zip_url(cik, accession_number, filing.filing_universal_id)
    
    def _has_searcher_url(self, filing: Filing) -> bool:
        """
        Check if filing has a valid searcher-provided URL.
        
        Args:
            filing: Filing object
            
        Returns:
            True if original_url exists and is not empty
        """
        return bool(filing.original_url and filing.original_url.strip())
    
    def _use_searcher_url(self, filing: Filing) -> Tuple[str, str]:
        """
        Use the URL provided by searcher.
        
        Args:
            filing: Filing object with original_url
            
        Returns:
            Tuple of (url, strategy_name)
        """
        url = filing.original_url
        filename = url.split('/')[-1] if '/' in url else url
        
        self.logger.info(f"Using URL from searcher: {filename}")
        return url, STRATEGY_SEARCHER_PROVIDED
    
    async def _identify_zip_url(
        self,
        cik: str,
        accession_number: str,
        filing_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Identify ZIP URL using strategy chain.
        
        Args:
            cik: Normalized CIK
            accession_number: Filing accession number
            filing_id: Filing universal ID for logging
            
        Returns:
            Tuple of (zip_url, strategy_used)
            Returns (None, None) if identification fails
        """
        self.logger.info("No URL from searcher - identifying ZIP file")
        
        # Apply rate limiting before API calls
        wait_time = await self.rate_limiter.acquire()
        if wait_time > 0:
            self.monitor.record_rate_limit_wait(wait_time)
        
        # Execute strategy chain
        zip_result = await self.strategy_chain.execute(cik, accession_number)
        
        if not zip_result.success:
            error_msg = f"Failed to identify ZIP: {zip_result.error_message}"
            self.logger.error(error_msg)
            self.monitor.record_zip_identification_failure(filing_id, zip_result.error_message)
            return None, None
        
        filename = zip_result.zip_url.split('/')[-1] if '/' in zip_result.zip_url else zip_result.zip_url
        self.logger.info(f"ZIP identified via {zip_result.strategy_used}: {filename}")
        
        return zip_result.zip_url, zip_result.strategy_used
    
    async def apply_rate_limiting(self, should_apply: bool):
        """
        Apply rate limiting if needed.
        
        Args:
            should_apply: Whether to apply rate limiting
                         (False if searcher URL was used, as no API call needed)
        """
        if should_apply:
            wait_time = await self.rate_limiter.acquire()
            if wait_time > 0:
                self.monitor.record_rate_limit_wait(wait_time)
    
    async def initialize(self):
        """Initialize URL resolver components."""
        # API client initialization if needed
        pass
    
    async def close(self):
        """Close and cleanup resources."""
        try:
            await self.api_client.close()
            self.logger.info("URL resolver closed")
        except Exception as exception:
            self.logger.error(f"Error closing URL resolver: {exception}")