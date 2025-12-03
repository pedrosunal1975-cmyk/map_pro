"""
SEC Filing Search Operations.

Handles filing discovery and search operations.

Location: markets/sec/sec_searcher/sec_filing_searcher.py
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from logging import Logger

from .sec_validators import SECValidator
from .sec_api_client import SECAPIClient
from .sec_zip_finder import SECZipFinder
from .sec_search_criteria import SearchCriteriaParser
from .sec_filing_processor import FilingProcessor


class FilingSearcher:
    """
    Handles filing search operations for SEC market.
    
    Responsibilities:
    - Search filings for a company
    - Apply search criteria filters
    - Process filings to find ZIP URLs
    - Return standardized filing information
    
    Example:
        >>> searcher = FilingSearcher(api_client, zip_finder, logger)
        >>> filings = await searcher.search('0000320193', {'filing_types': ['10-K']})
    """
    
    def __init__(
        self,
        api_client: SECAPIClient,
        zip_finder: SECZipFinder,
        logger: Logger
    ):
        """
        Initialize filing searcher.
        
        Args:
            api_client: SEC API client instance
            zip_finder: ZIP finder utility
            logger: Logger instance
        """
        self.api_client = api_client
        self.zip_finder = zip_finder
        self.logger = logger
        
        # Initialize components
        self.criteria_parser = SearchCriteriaParser(logger)
        self.processor = FilingProcessor(api_client, zip_finder, logger)
    
    async def search(
        self,
        market_entity_id: str,
        search_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find filings for a company.
        
        Args:
            market_entity_id: CIK number
            search_criteria: Optional search filters
            
        Returns:
            List of standardized filing information
            
        Raises:
            ValueError: If CIK is invalid
        """
        # Validate CIK
        if not SECValidator.validate_cik(market_entity_id):
            raise ValueError(f"Invalid CIK: {market_entity_id}")
        
        cik = SECValidator.normalize_cik(market_entity_id)
        
        # Get company submissions
        submissions_data = await self.api_client.get_submissions(cik)
        
        # Extract recent filings
        recent_filings = submissions_data.get('filings', {}).get('recent', {})
        
        if not recent_filings:
            self.logger.warning(f"No filings found for CIK {cik}")
            return []
        
        # Parse search criteria
        criteria = self.criteria_parser.parse(search_criteria)
        
        # Process filings with filtering
        filings = await self._process_filings(cik, recent_filings, criteria)
        
        return filings
    
    async def _process_filings(
        self,
        cik: str,
        recent_filings: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process filings with filtering and ZIP validation.
        
        Args:
            cik: Company CIK
            recent_filings: Recent filings data from SEC
            criteria: Normalized search criteria
            
        Returns:
            List of processed filing information
        """
        filings = []
        checked_count = 0
        skipped_count = 0
        
        # Extract filing arrays
        accession_numbers = recent_filings.get('accessionNumber', [])
        filing_dates = recent_filings.get('filingDate', [])
        forms = recent_filings.get('form', [])
        
        # Process each filing
        for i in range(len(accession_numbers)):
            # Check limit
            if len(filings) >= criteria['limit']:
                self.logger.info(
                    f"Reached limit of {criteria['limit']} filings, stopping search"
                )
                break
            
            try:
                # Extract filing data
                filing_type = forms[i]
                filing_date_str = filing_dates[i]
                accession_number = accession_numbers[i]
                
                # Parse filing date
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                
                # Apply filters
                if self._should_skip_filing(filing_type, filing_date, criteria):
                    skipped_count += 1
                    continue
                
                # Process filing (expensive operation)
                checked_count += 1
                self.logger.info(
                    f"Checking {filing_type} filing from {filing_date} "
                    f"({checked_count}/{criteria['limit']})"
                )
                
                filing_info = await self.processor.process_filing(
                    cik,
                    accession_number,
                    filing_type,
                    filing_date
                )
                
                if filing_info:
                    filings.append(filing_info)
                    self.logger.info(f"Found {filing_type} filing: {accession_number}")
            
            except Exception as e:
                self.logger.warning(f"Failed to process filing at index {i}: {e}")
                continue
        
        self.logger.info(
            f"Search complete: Found {len(filings)} matching filings "
            f"(checked {checked_count}, skipped {skipped_count})"
        )
        
        return filings
    
    def _should_skip_filing(
        self,
        filing_type: str,
        filing_date,
        criteria: Dict[str, Any]
    ) -> bool:
        """
        Check if filing should be skipped based on criteria.
        
        Args:
            filing_type: Filing type code
            filing_date: Filing date
            criteria: Search criteria
            
        Returns:
            True if filing should be skipped
        """
        # Check date range
        if criteria['date_from'] and filing_date < criteria['date_from']:
            return True
        
        if criteria['date_to'] and filing_date > criteria['date_to']:
            return True
        
        # Check filing type filter
        if criteria['filing_types']:
            if filing_type.upper() not in criteria['filing_types']:
                return True
        
        return False


__all__ = ['FilingSearcher']