"""
SEC Searcher Implementation.

Main entry point for SEC EDGAR company and filing search operations.
Market-specific implementation that maintains map_pro's market-agnostic architecture.

Architecture:
    Delegates to specialized components:
    - sec_company_searcher.py - Company search operations
    - sec_filing_searcher.py - Filing search operations
    - sec_filing_processor.py - Filing processing and ZIP URL detection
    - sec_data_builder.py - Data structure builders
    - sec_search_criteria.py - Search criteria parsing

Location: /map_pro/markets/sec/sec_searcher/sec_searcher.py

Example:
    >>> from markets.sec.sec_searcher import SECSearcher
    >>> searcher = SECSearcher()
    >>> company = await searcher.search_company('AAPL')
    >>> filings = await searcher.find_filings(company['market_entity_id'])
"""

import os
from typing import Dict, Any, List, Optional

from markets.base.market_interface import MarketInterface
from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import EngineError

from .sec_api_client import SECAPIClient
from .sec_zip_finder import SECZipFinder
from .sec_company_searcher import CompanySearcher
from .sec_filing_searcher import FilingSearcher
from .sec_constants import MAJOR_FILING_TYPES, ANNUAL_FILINGS, QUARTERLY_FILINGS, CURRENT_FILINGS


logger = get_logger(__name__, 'market')


# Default configuration
DEFAULT_USER_AGENT = 'MapPro/1.0 (system@mappro.com)'


class SECSearcher(MarketInterface):
    """
    SEC EDGAR market implementation.
    
    Main coordinator for SEC market operations. Delegates to specialized
    components for company search, filing search, and data processing.
    
    Handles:
    - Company search by ticker, CIK, or name
    - Filing discovery for companies
    - XBRL ZIP file identification (SEC-specific)
    - CIK resolution and validation
    - SEC-specific data formatting
    
    Power Features:
    - Fetches index.json for each filing
    - Identifies XBRL ZIP files using pattern matching
    - Returns ONLY ZIP URLs (filters out all other files)
    - Maintains market-agnostic interface
    
    Example:
        >>> searcher = SECSearcher()
        >>> company = await searcher.search_company('AAPL')
        >>> filings = await searcher.find_filings(
        ...     company['market_entity_id'],
        ...     {'filing_types': ['10-K'], 'limit': 5}
        ... )
    """
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize SEC searcher with all components.
        
        Args:
            user_agent: Optional user-agent override
            
        Raises:
            Exception: If initialization fails
        """
        super().__init__('sec')
        
        try:
            # Get user agent
            user_agent = self._get_user_agent(user_agent)
            
            # Initialize API client and utilities
            self.api_client = SECAPIClient(user_agent)
            self.zip_finder = SECZipFinder()
            
            # Initialize specialized searchers
            self.company_searcher = CompanySearcher(
                self.api_client,
                self.logger
            )
            self.filing_searcher = FilingSearcher(
                self.api_client,
                self.zip_finder,
                self.logger
            )
            
            self.logger.info("SEC searcher initialized successfully")
        
        except Exception as e:
            self.logger.error(f"SEC searcher initialization failed: {e}", exc_info=True)
            # Set components to None for graceful degradation
            self.api_client = None
            self.zip_finder = None
            self.company_searcher = None
            self.filing_searcher = None
            raise
    
    def _get_user_agent(self, user_agent: Optional[str]) -> str:
        """
        Get user agent from parameter or environment.
        
        Args:
            user_agent: Optional user agent override
            
        Returns:
            User agent string
        """
        if user_agent is not None:
            return user_agent
        
        return os.environ.get(
            'MAP_PRO_SEC_USER_AGENT',
            DEFAULT_USER_AGENT
        )
    
    async def search_company(
        self,
        company_identifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Search for company in SEC EDGAR database.
        
        Supports search by:
        - Ticker symbol (e.g., 'AAPL')
        - CIK number (e.g., '0000320193')
        - Company name (e.g., 'Apple Inc')
        
        Args:
            company_identifier: Ticker, CIK, or company name
            
        Returns:
            Standardized company information or None if not found
            
        Raises:
            EngineError: If search operation fails
            
        Example:
            >>> company = await searcher.search_company('AAPL')
            >>> print(company['name'])  # 'Apple Inc.'
        """
        try:
            return await self.company_searcher.search(company_identifier)
        
        except Exception as e:
            self.logger.error(
                f"Company search failed for '{company_identifier}': {e}",
                exc_info=True
            )
            raise EngineError(f"SEC company search failed: {str(e)}")
    
    async def find_filings(
        self,
        market_entity_id: str,
        search_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find filings for a company in SEC EDGAR.
        
        CRITICAL: Returns ONLY XBRL ZIP file URLs, nothing else.
        Applies search criteria BEFORE expensive ZIP validation.
        
        Args:
            market_entity_id: CIK number
            search_criteria: Optional filters:
                - date_from: Start date
                - date_to: End date
                - filing_types: List of filing types
                - limit: Maximum number of results
                
        Returns:
            List of standardized filing information with ZIP URLs only
            
        Raises:
            EngineError: If search operation fails
            
        Example:
            >>> filings = await searcher.find_filings(
            ...     '0000320193',
            ...     {'filing_types': ['10-K'], 'limit': 5}
            ... )
            >>> print(len(filings))  # Up to 5 filings
        """
        try:
            return await self.filing_searcher.search(
                market_entity_id,
                search_criteria
            )
        
        except Exception as e:
            self.logger.error(
                f"Filing search failed for CIK {market_entity_id}: {e}",
                exc_info=True
            )
            raise EngineError(f"SEC filing search failed: {str(e)}")
    
    def validate_identifier(self, company_identifier: str) -> bool:
        """
        Validate company identifier for SEC.
        
        Accepts CIK or ticker format.
        
        Args:
            company_identifier: Identifier to validate
            
        Returns:
            True if valid format
            
        Example:
            >>> searcher.validate_identifier('AAPL')  # True
            >>> searcher.validate_identifier('0000320193')  # True
            >>> searcher.validate_identifier('')  # False
        """
        return self.company_searcher.validate_identifier(company_identifier)
    
    def get_supported_filing_types(self) -> List[str]:
        """
        Get list of supported SEC filing types.
        
        Returns:
            List of filing type codes
            
        Example:
            >>> types = searcher.get_supported_filing_types()
            >>> print(types)  # ['10-K', '10-Q', '8-K', ...]
        """
        return MAJOR_FILING_TYPES
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get SEC market capabilities.
        
        Returns:
            Capabilities dictionary with market information
            
        Example:
            >>> caps = searcher.get_capabilities()
            >>> print(caps['market_name'])  # 'sec'
        """
        return {
            'market_name': 'sec',
            'market_description': 'U.S. Securities and Exchange Commission',
            'supported_identifiers': ['ticker', 'cik', 'name'],
            'requires_authentication': False,
            'rate_limit_per_minute': 600,
            'supports_date_range_search': True,
            'supports_filing_type_filter': True,
            'default_filing_types': MAJOR_FILING_TYPES,
            'api_base_url': 'https://data.sec.gov',
            'documentation_url': (
                'https://www.sec.gov/edgar/searchedgar/'
                'accessing-edgar-data.htm'
            ),
            'filing_categories': {
                'annual': ANNUAL_FILINGS,
                'quarterly': QUARTERLY_FILINGS,
                'current': CURRENT_FILINGS
            },
            'special_features': {
                'xbrl_zip_detection': True,
                'filters_non_zip_files': True,
                'index_json_parsing': True
            }
        }
    
    async def close(self) -> None:
        """
        Close API client and cleanup resources.
        
        Should be called when searcher is no longer needed.
        """
        if self.api_client:
            await self.api_client.close()
        self.logger.info("SEC searcher closed")


def create_sec_searcher(user_agent: Optional[str] = None) -> SECSearcher:
    """
    Create SEC searcher instance.
    
    Factory function for creating SECSearcher instances.
    
    Args:
        user_agent: Optional user agent override
        
    Returns:
        Configured SECSearcher instance
        
    Example:
        >>> searcher = create_sec_searcher()
        >>> # or with custom user agent
        >>> searcher = create_sec_searcher('MyApp/1.0 (contact@example.com)')
    """
    return SECSearcher(user_agent)


__all__ = ['SECSearcher', 'create_sec_searcher']