"""
FCA Downloader Integration
==========================

Integration layer between FCA constants and the generic downloader engine.
Shows how to use engines/downloader/ for FCA-specific downloads.

This file demonstrates the pattern but doesn't need testing yet.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import asyncio

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from engines.downloader import (
    DownloadCoordinator,
    DownloadResult,
    DownloadValidator,
    ProtocolHandlerFactory
)
from .fca_constants import (
    FCA_DOWNLOAD_TIMEOUT,
    FCA_MAX_RETRIES,
    FCA_RETRY_DELAY,
    FCA_BACKOFF_FACTOR,
    FCA_CHUNK_SIZE
)
from .fca_download_helper import FCADownloadHelper

logger = get_logger(__name__, 'market')


class FCADownloaderIntegration:
    """
    Integration class for FCA downloads using generic downloader engine.
    
    This shows the pattern for market-specific usage without
    contaminating the generic engine with FCA code.
    """
    
    def __init__(self):
        """Initialize FCA downloader integration."""
        self.helper = FCADownloadHelper()
        self.validator = DownloadValidator()
        self.protocol_factory = ProtocolHandlerFactory()
        
        # FCA-specific configuration
        self.timeout = FCA_DOWNLOAD_TIMEOUT
        self.max_retries = FCA_MAX_RETRIES
        self.retry_delay = FCA_RETRY_DELAY
        self.backoff_factor = FCA_BACKOFF_FACTOR
        self.chunk_size = FCA_CHUNK_SIZE
        
        logger.info("FCA downloader integration initialized")
    
    async def download_filing(self, company_number: str, filing_type: str,
                             filing_date: str, **kwargs) -> DownloadResult:
        """
        Download FCA filing using generic engine.
        
        Args:
            company_number: UK company number
            filing_type: Filing type (e.g., 'ANNUAL')
            filing_date: Filing date
            **kwargs: Additional parameters
            
        Returns:
            DownloadResult from generic engine
        """
        try:
            # Use FCA helper to build URL
            url = self.helper.build_download_url(
                company_number,
                filing_type,
                filing_date,
                **kwargs
            )
            
            # Generate filename using FCA conventions
            filename = self.helper.generate_file_name(
                company_number,
                filing_type,
                filing_date
            )
            
            # Generate download path
            base_path = map_pro_paths.data_root / 'parsed'
            save_path = self.helper.generate_download_path(
                company_number,
                filing_type,
                filename,
                base_path
            )
            
            # Use generic downloader coordinator
            coordinator = DownloadCoordinator(
                protocol_factory=self.protocol_factory,
                validator=self.validator,
                timeout=self.timeout,
                max_retries=self.max_retries,
                chunk_size=self.chunk_size
            )
            
            logger.info(f"Downloading FCA filing: {company_number} - {filing_type}")
            
            # Execute download using generic engine
            result = await coordinator.download(url, save_path)
            
            if result.success:
                logger.info(f"FCA download successful: {result.file_path}")
                
                # Add FCA-specific metadata
                metadata = self.helper.get_file_metadata(result.file_path)
                result.metadata.update(metadata)
            else:
                logger.error(f"FCA download failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"FCA download error: {e}")
            return DownloadResult(
                success=False,
                error_message=str(e)
            )
    
    async def batch_download(self, filings: list) -> list:
        """
        Download multiple FCA filings.
        
        Args:
            filings: List of filing dictionaries with:
                - company_number
                - filing_type
                - filing_date
                
        Returns:
            List of DownloadResult objects
        """
        tasks = []
        
        for filing in filings:
            task = self.download_filing(
                filing['company_number'],
                filing['filing_type'],
                filing['filing_date']
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, DownloadResult) and r.success)
        logger.info(f"FCA batch download complete: {successful}/{len(filings)} successful")
        
        return results


# Example usage (not executed, just shows the pattern)
async def example_fca_download():
    """
    Example showing how to use FCA downloader integration.
    
    This demonstrates the pattern without executing real downloads.
    """
    integration = FCADownloaderIntegration()
    
    # Example: Download single filing
    result = await integration.download_filing(
        company_number='00000001',
        filing_type='ANNUAL',
        filing_date='2024-12-31'
    )
    
    if result.success:
        print(f"Downloaded: {result.file_path}")
        print(f"Size: {result.file_size_mb:.2f} MB")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Requires extraction: {result.metadata.get('requires_extraction', False)}")
    
    # Example: Batch download
    filings = [
        {'company_number': '00000001', 'filing_type': 'ANNUAL', 'filing_date': '2024-12-31'},
        {'company_number': '00000002', 'filing_type': 'ANNUAL', 'filing_date': '2024-12-31'},
    ]
    
    results = await integration.batch_download(filings)
    print(f"Batch complete: {len(results)} downloads")


if __name__ == '__main__':
    # This example doesn't run - it just shows the pattern
    print("FCA Downloader Integration - Example Pattern")
    print("=" * 50)
    print("\nThis file demonstrates how to use the generic")
    print("downloader engine with FCA-specific constants.")
    print("\nKey points:")
    print("- Uses FCADownloadHelper for URL building")
    print("- Uses generic DownloadCoordinator for actual downloads")
    print("- No SEC-specific code contamination")
    print("- Direct file downloads (no extraction needed)")
    print("\nNo testing needed at this stage.")