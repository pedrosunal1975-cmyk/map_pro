"""
SEC Company Search Operations.

Handles all company search functionality including ticker, CIK, and name search.

Location: markets/sec/sec_searcher/sec_company_searcher.py
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from logging import Logger

from markets.base.success_evaluator import success_evaluator
from .sec_validators import SECValidator, identify_identifier_type
from .sec_api_client import SECAPIClient


# Constants
CIK_PADDING_LENGTH = 10


class CompanySearcher:
    """
    Handles company search operations for SEC market.
    
    Responsibilities:
    - Search by ticker, CIK, or name
    - Build standardized company information
    - Validate search results
    - Handle ticker-to-CIK resolution
    
    Example:
        >>> searcher = CompanySearcher(api_client, logger)
        >>> company = await searcher.search('AAPL')
    """
    
    def __init__(self, api_client: SECAPIClient, logger: Logger):
        """
        Initialize company searcher.
        
        Args:
            api_client: SEC API client instance
            logger: Logger instance
        """
        self.api_client = api_client
        self.logger = logger
        
        # Cache for ticker-to-CIK mappings
        self._ticker_cache: Optional[Dict[str, Any]] = None
    
    async def search(self, company_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Search for company by ticker, CIK, or name.
        
        Args:
            company_identifier: Ticker, CIK, or company name
            
        Returns:
            Standardized company information or None if not found
        """
        # Identify identifier type
        identifier_type = identify_identifier_type(company_identifier)
        
        if identifier_type == 'cik':
            cik = SECValidator.normalize_cik(company_identifier)
            return await self._search_by_cik(cik)
        
        elif identifier_type == 'ticker':
            ticker = SECValidator.normalize_ticker(company_identifier)
            return await self._search_by_ticker(ticker)
        
        else:
            self.logger.info(f"Attempting name search for: {company_identifier}")
            return await self._search_by_name(company_identifier)
    
    async def _search_by_cik(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by CIK.
        
        Args:
            cik: Normalized CIK (10 digits with leading zeros)
            
        Returns:
            Company information or None if not found
        """
        try:
            # Get company submissions data
            submissions_data = await self.api_client.get_submissions(cik)
            
            # Build company info
            from .sec_data_builder import CompanyDataBuilder
            company_info = CompanyDataBuilder.build_company_info(cik, submissions_data)
            
            # Validate result
            evaluation = success_evaluator.evaluate_company_search(company_info)
            
            if not evaluation['success']:
                self.logger.warning(f"Company data quality check failed for CIK {cik}")
                return None
            
            return company_info
        
        except Exception as e:
            self.logger.error(f"Failed to get company by CIK {cik}: {e}", exc_info=True)
            return None
    
    async def _search_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by ticker symbol.
        
        Args:
            ticker: Normalized ticker symbol
            
        Returns:
            Company information or None if not found
        """
        try:
            # Load ticker cache if needed
            if self._ticker_cache is None:
                self._ticker_cache = await self.api_client.get_company_tickers()
            
            # Find CIK for ticker
            cik = self._find_cik_for_ticker(ticker)
            
            if not cik:
                self.logger.warning(f"Ticker '{ticker}' not found in SEC database")
                return None
            
            # Get full company info by CIK
            return await self._search_by_cik(cik)
        
        except Exception as e:
            self.logger.error(f"Failed to get company by ticker {ticker}: {e}", exc_info=True)
            return None
    
    def _find_cik_for_ticker(self, ticker: str) -> Optional[str]:
        """
        Find CIK for ticker in cache.
        
        Args:
            ticker: Ticker symbol (normalized)
            
        Returns:
            CIK string or None if not found
        """
        ticker_upper = ticker.upper()
        
        for key, company in self._ticker_cache.items():
            if key == 'fields':
                continue
            
            company_ticker = company.get('ticker', '')
            if company_ticker.upper() == ticker_upper:
                cik_str = str(company.get('cik_str'))
                return cik_str.zfill(CIK_PADDING_LENGTH)
        
        return None
    
    async def _search_by_name(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Get company information by name search.
        
        Args:
            company_name: Company name to search
            
        Returns:
            Company information or None if not found
        """
        try:
            # Search by name using API
            matches = await self.api_client.search_company_by_name(company_name)
            
            if not matches:
                self.logger.warning(f"No companies found matching name: {company_name}")
                return None
            
            # Log multiple matches
            if len(matches) > 1:
                self.logger.info(
                    f"Found {len(matches)} matches for '{company_name}', using first match"
                )
            
            # Get full company info for best match
            best_match = matches[0]
            cik = best_match['cik']
            
            return await self._search_by_cik(cik)
        
        except Exception as e:
            self.logger.error(
                f"Failed to search company by name '{company_name}': {e}",
                exc_info=True
            )
            return None
    
    def validate_identifier(self, company_identifier: str) -> bool:
        """
        Validate company identifier format.
        
        Args:
            company_identifier: Identifier to validate
            
        Returns:
            True if valid format
        """
        if not company_identifier:
            return False
        
        identifier_type = identify_identifier_type(company_identifier)
        return identifier_type is not None


__all__ = ['CompanySearcher']