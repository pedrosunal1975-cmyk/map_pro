"""
SEC Filing Processor.

Processes individual filings to find and validate ZIP URLs.

Location: markets/sec/sec_searcher/sec_filing_processor.py
"""

from typing import Dict, Any, Optional
from datetime import date
from logging import Logger

from .sec_api_client import SECAPIClient
from .sec_zip_finder import SECZipFinder
from .sec_data_builder import FilingDataBuilder
from .sec_constants import SEC_ARCHIVES_BASE_URL


class FilingProcessor:
    """
    Processes individual SEC filings.
    
    Responsibilities:
    - Find ZIP URLs for filings
    - Try multiple detection strategies
    - Build filing information structures
    - Handle URL pattern matching
    
    Example:
        >>> processor = FilingProcessor(api_client, zip_finder, logger)
        >>> filing_info = await processor.process_filing(cik, accession, type, date)
    """
    
    def __init__(
        self,
        api_client: SECAPIClient,
        zip_finder: SECZipFinder,
        logger: Logger
    ):
        """
        Initialize filing processor.
        
        Args:
            api_client: SEC API client instance
            zip_finder: ZIP finder utility
            logger: Logger instance
        """
        self.api_client = api_client
        self.zip_finder = zip_finder
        self.logger = logger
    
    async def process_filing(
        self,
        cik: str,
        accession_number: str,
        filing_type: str,
        filing_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Process single filing to find ZIP URL.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            filing_type: Filing type code
            filing_date: Filing date
            
        Returns:
            Filing information or None if no ZIP found
        """
        # Try to get ZIP URL
        zip_url = await self._find_zip_url(cik, accession_number)
        
        if not zip_url:
            self.logger.info(f"No XBRL ZIP found for {accession_number}, skipping")
            return None
        
        # Build filing info
        return FilingDataBuilder.build_filing_info(
            cik,
            accession_number,
            filing_type,
            filing_date,
            zip_url
        )
    
    async def _find_zip_url(
        self,
        cik: str,
        accession_number: str
    ) -> Optional[str]:
        """
        Find ZIP URL for filing using index.json or pattern matching.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            
        Returns:
            ZIP URL or None if not found
        """
        # Try index.json first
        self.logger.debug(f"Fetching index.json for {accession_number}")
        filing_index = await self.api_client.get_filing_index(cik, accession_number)
        
        if filing_index:
            # Use index.json to find ZIP
            zip_url = self.zip_finder.find_xbrl_zip(
                filing_index,
                cik,
                accession_number,
                SEC_ARCHIVES_BASE_URL
            )
            
            if zip_url:
                return zip_url
        
        # Fallback: Try pattern matching
        self.logger.debug(f"No index.json for {accession_number}, trying patterns")
        return await self._find_zip_by_patterns(cik, accession_number)
    
    async def _find_zip_by_patterns(
        self,
        cik: str,
        accession_number: str
    ) -> Optional[str]:
        """
        Find ZIP URL using multiple URL patterns.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            
        Returns:
            ZIP URL or None if not found
        """
        # Prepare URL components
        accession_no_dashes = accession_number.replace('-', '')
        accession_underscore = accession_number.replace('-', '_')
        cik_no_zeros = str(int(cik))
        
        # Generate potential ZIP URLs (priority order)
        potential_urls = [
            f"{SEC_ARCHIVES_BASE_URL}{cik_no_zeros}/{accession_no_dashes}/{accession_number}-xbrl.zip",
            f"{SEC_ARCHIVES_BASE_URL}{cik_no_zeros}/{accession_no_dashes}/{accession_underscore}_htm.zip",
            f"{SEC_ARCHIVES_BASE_URL}{cik_no_zeros}/{accession_no_dashes}/{accession_no_dashes}-xbrl.zip",
            f"{SEC_ARCHIVES_BASE_URL}{cik_no_zeros}/{accession_no_dashes}/{accession_underscore}_xbrl.zip",
        ]
        
        # Validate each URL until we find one that exists
        for url in potential_urls:
            if await self.api_client.check_url_exists(url):
                zip_filename = url.split('/')[-1]
                self.logger.info(f"Found ZIP via URL validation: {zip_filename}")
                return url
        
        self.logger.info(
            f"No XBRL ZIP found for {accession_number} after checking all patterns"
        )
        return None


__all__ = ['FilingProcessor']