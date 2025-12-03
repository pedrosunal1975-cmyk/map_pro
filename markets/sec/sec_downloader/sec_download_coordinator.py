# File: /map_pro/markets/sec/sec_downloader/sec_download_coordinator.py

"""
SEC Download Coordinator
========================

SEC-specific download coordinator that wraps the generic downloader.
Handles SEC EDGAR requirements: rate limiting, user-agent, ZIP identification.

CRITICAL FIX: Only re-identify ZIP if filing.original_url is missing!
If searcher already found the URL, use it AS IS.

This module has been refactored into:
- sec_download_coordinator.py (this file) - Main orchestration
- sec_metadata_extractor.py - Filing metadata extraction
- sec_url_resolver.py - ZIP URL resolution
- sec_validation_handler.py - SEC-specific validation
- sec_download_delegator.py - Generic downloader delegation
- sec_metrics_recorder.py - Metrics and monitoring
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

from core.system_logger import get_logger
from database.models.core_models import Filing
from engines.downloader import DownloadResult, DownloadCoordinator

from .sec_rate_limiter import SECRateLimiter, get_shared_sec_rate_limiter
from .sec_download_validator import SECDownloadValidator
from .sec_index_parser import SECIndexParser
from .sec_file_identifier import SECFileIdentifier
from .sec_download_monitor import SECDownloadMonitor, get_sec_download_monitor
from .sec_download_strategies import create_default_strategy_chain
from .sec_metadata_extractor import SECMetadataExtractor
from .sec_url_resolver import SECURLResolver
from .sec_validation_handler import SECValidationHandler
from .sec_download_delegator import SECDownloadDelegator
from .sec_metrics_recorder import SECMetricsRecorder

logger = get_logger(__name__, 'market')

# Configuration constants
SEC_USER_AGENT_ENV = 'MAP_PRO_SEC_USER_AGENT'
STRATEGY_SEARCHER_PROVIDED = 'searcher_provided'


class SECDownloadCoordinator:
    """
    SEC-specific download coordinator.
    
    Responsibilities:
    - Orchestrate SEC filing downloads
    - Coordinate between specialized handlers
    - Manage component lifecycle
    
    The actual work is delegated to specialized components:
    - SECMetadataExtractor: Extract filing metadata
    - SECURLResolver: Resolve ZIP file URLs
    - SECValidationHandler: Validate SEC requirements
    - SECDownloadDelegator: Delegate to generic downloader
    - SECMetricsRecorder: Record metrics and outcomes
    """
    
    def __init__(
        self,
        user_agent: Optional[str] = None,
        rate_limiter: Optional[SECRateLimiter] = None,
        generic_downloader: Optional[DownloadCoordinator] = None,
        monitor: Optional[SECDownloadMonitor] = None
    ):
        """
        Initialize SEC download coordinator.
        
        Args:
            user_agent: SEC user-agent (from env if None)
            rate_limiter: Rate limiter (shared if None)
            generic_downloader: Generic downloader (created if None)
            monitor: Download monitor (global if None)
            
        Raises:
            ValueError: If user_agent is not provided and not in environment
        """
        self.user_agent = user_agent or os.getenv(SEC_USER_AGENT_ENV)
        
        if not self.user_agent:
            raise ValueError(
                f"SEC user-agent required. Set {SEC_USER_AGENT_ENV} or pass user_agent parameter"
            )
        
        self.rate_limiter = rate_limiter or get_shared_sec_rate_limiter()
        self.generic_downloader = generic_downloader or DownloadCoordinator()
        self.monitor = monitor or get_sec_download_monitor()
        
        # Initialize specialized components
        self.metadata_extractor = SECMetadataExtractor()
        self.url_resolver = SECURLResolver(
            user_agent=self.user_agent,
            rate_limiter=self.rate_limiter,
            monitor=self.monitor
        )
        self.validation_handler = SECValidationHandler(user_agent=self.user_agent)
        self.download_delegator = SECDownloadDelegator(
            user_agent=self.user_agent,
            generic_downloader=self.generic_downloader
        )
        self.metrics_recorder = SECMetricsRecorder(monitor=self.monitor)
        
        self.logger = logger
        self.logger.info("SEC download coordinator initialized")
    
    async def download_filing(
        self,
        filing: Filing,
        session
    ) -> DownloadResult:
        """
        Download SEC filing.
        
        CRITICAL WORKFLOW:
        1. Extract filing metadata (CIK, accession number)
        2. Resolve ZIP URL (use searcher URL if available, otherwise identify)
        3. Validate SEC requirements
        4. Apply rate limiting
        5. Delegate to generic downloader
        6. Record metrics
        
        Args:
            filing: Filing database object
            session: Database session
            
        Returns:
            DownloadResult with success status and details
        """
        filing_id = filing.filing_universal_id
        
        try:
            self.logger.info(f"Starting SEC download for filing: {filing.market_filing_id}")
            self.metrics_recorder.record_download_start(filing_id, filing.original_url or '')
            
            # Step 1: Extract metadata
            cik, accession_number = self.metadata_extractor.extract_metadata(filing)
            if not cik or not accession_number:
                return self.metrics_recorder.handle_error(
                    filing_id,
                    "Missing CIK or accession number",
                    'metadata_error'
                )
            
            # Step 2: Resolve ZIP URL
            zip_url, strategy_used = await self.url_resolver.resolve_zip_url(
                filing,
                cik,
                accession_number
            )
            if not zip_url:
                return self.metrics_recorder.handle_error(
                    filing_id,
                    "Failed to identify ZIP URL",
                    'zip_identification'
                )
            
            # Step 3: Generate save path
            save_path = self._generate_download_path(filing, zip_url)
            
            # Step 4: Validate SEC requirements
            validation_result = self.validation_handler.validate_pre_download(
                zip_url,
                save_path,
                cik,
                accession_number
            )
            if not validation_result.is_valid:
                return self.metrics_recorder.handle_error(
                    filing_id,
                    validation_result.error_message,
                    'validation'
                )
            
            # Step 5: Apply rate limiting if needed
            await self.url_resolver.apply_rate_limiting(
                strategy_used != STRATEGY_SEARCHER_PROVIDED
            )
            
            # Step 6: Delegate download
            download_result = await self.download_delegator.delegate_download(
                filing,
                session,
                zip_url
            )
            
            # Step 7: Record outcome
            self.metrics_recorder.record_outcome(
                filing_id,
                download_result,
                strategy_used
            )
            
            return download_result
            
        except Exception as exception:
            self.download_delegator.cleanup_headers(filing)
            return self.metrics_recorder.handle_error(
                filing_id,
                f"SEC download error: {str(exception)}",
                'exception'
            )
    
    def _generate_download_path(self, filing: Filing, url: str) -> Path:
        """
        Generate download path for filing.
        
        Uses centralized path management to ensure consistency.
        
        Args:
            filing: Filing object
            url: Download URL
            
        Returns:
            Path for saving file
            
        Raises:
            ValueError: If URL is empty, entity missing, or path components invalid
        """
        from core.data_paths import map_pro_paths
        
        if not url or not url.strip():
            raise ValueError(
                f"Cannot generate download path: URL is empty for filing {filing.market_filing_id}"
            )
        
        if not filing.entity:
            raise ValueError(f"Filing {filing.market_filing_id} has no entity")
        
        if not filing.entity.data_directory_path:
            raise ValueError(
                f"Entity {filing.entity.primary_name} has no data_directory_path"
            )
        
        entity_dir = map_pro_paths.data_root / filing.entity.data_directory_path
        filing_dir = entity_dir / 'filings' / filing.filing_type / filing.market_filing_id
        
        filename = Path(url).name
        
        if not filename:
            raise ValueError(f"Cannot extract filename from URL: {url}")
        
        return filing_dir / filename
    
    async def initialize(self) -> bool:
        """
        Initialize SEC downloader and all components.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Initializing SEC downloader")
            
            # Initialize generic downloader if it has an initialize method
            if hasattr(self.generic_downloader, 'initialize'):
                success = self.generic_downloader.initialize()
                if not success:
                    self.logger.error("Generic downloader initialization failed")
                    return False
            
            # Initialize URL resolver
            await self.url_resolver.initialize()
            
            self.logger.info("SEC downloader initialized successfully")
            return True
            
        except Exception as exception:
            self.logger.error(f"SEC downloader initialization failed: {exception}")
            return False
    
    async def close(self):
        """Close and cleanup all resources."""
        try:
            await self.url_resolver.close()
            
            if hasattr(self.generic_downloader, 'cleanup'):
                await self.generic_downloader.cleanup()
            
            self.logger.info("SEC downloader closed")
            
        except Exception as exception:
            self.logger.error(f"Error closing SEC downloader: {exception}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get SEC download metrics.
        
        Returns:
            Dictionary with current metrics
        """
        return self.monitor.get_metrics()


def create_sec_downloader(
    user_agent: Optional[str] = None,
    rate_limiter: Optional[SECRateLimiter] = None,
    generic_downloader: Optional[DownloadCoordinator] = None,
    monitor: Optional[SECDownloadMonitor] = None
) -> SECDownloadCoordinator:
    """
    Factory function to create SEC downloader.
    
    Args:
        user_agent: SEC user-agent (from env if None)
        rate_limiter: Rate limiter (shared if None)
        generic_downloader: Generic downloader (created if None)
        monitor: Download monitor (global if None)
        
    Returns:
        Configured SECDownloadCoordinator instance
    """
    return SECDownloadCoordinator(
        user_agent=user_agent,
        rate_limiter=rate_limiter,
        generic_downloader=generic_downloader,
        monitor=monitor
    )