"""
Map Pro Market Interface Base Class
===================================

Abstract base class defining the contract that all market-specific plugins must implement.
Ensures consistent interface across SEC, FCA, ESMA, and future markets.

Architecture: Abstract interface defining required methods without implementation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timezone

from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


class MarketInterface(ABC):
    """
    Abstract base class for market-specific searcher plugins.
    
    All market implementations (SEC, FCA, ESMA, etc.) must inherit from this class
    and implement all abstract methods.
    
    Responsibilities:
    - Define required interface for market plugins
    - Provide common utility methods
    - Ensure consistent behavior across markets
    
    Does NOT handle:
    - Actual API calls (subclasses implement these)
    - Database operations (engines handle this)
    - Job queue management (core handles this)
    """
    
    def __init__(self, market_name: str):
        """
        Initialize market interface.
        
        Args:
            market_name: Market identifier (e.g., 'sec', 'fca', 'esma')
        """
        self.market_name = market_name
        self.logger = get_logger(f"markets.{market_name}", 'market')
        
        self.logger.info(f"Market interface initialized: {market_name}")
    
    @abstractmethod
    async def search_company(self, company_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Search for company in this market.
        
        Args:
            company_identifier: Company identifier (ticker, CIK, company number, etc.)
            
        Returns:
            Dictionary with standardized company information:
            {
                'market_entity_id': str,      # Required: Market-specific ID
                'name': str,                   # Required: Company name
                'ticker': str,                 # Optional: Trading symbol
                'identifiers': dict,           # Optional: Additional IDs
                'jurisdiction': str,           # Optional: Registration jurisdiction
                'entity_type': str,            # Optional: Company type
                'status': str,                 # Optional: Active/inactive
                'discovered_at': datetime,     # Optional: Discovery timestamp
                'source_url': str,             # Optional: Source URL
                'additional_info': dict        # Optional: Market-specific data
            }
            Or None if company not found
            
        Raises:
            Exception: If search fails due to API error or network issue
        """
        pass
    
    @abstractmethod
    async def find_filings(
        self, 
        market_entity_id: str, 
        search_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find filings for a company in this market.
        
        Args:
            market_entity_id: Market-specific entity identifier
            search_criteria: Optional filters:
                - date_from: date - Start date for filing search
                - date_to: date - End date for filing search
                - filing_types: List[str] - Specific filing types to retrieve
                - limit: int - Maximum number of filings to return
                
        Returns:
            List of dictionaries with standardized filing information:
            [{
                'market_filing_id': str,       # Required: Market-specific filing ID
                'filing_type': str,             # Required: Filing type/form
                'filing_date': date,            # Required: Filing date
                'period_start': date,           # Optional: Reporting period start
                'period_end': date,             # Optional: Reporting period end
                'title': str,                   # Optional: Filing title
                'url': str,                     # Optional: Download URL
                'format': str,                  # Optional: File format (.zip, .xml, etc.)
                'size': int,                    # Optional: File size in bytes
                'source_url': str,              # Optional: Source URL
                'additional_info': dict         # Optional: Market-specific data
            }]
            
        Raises:
            Exception: If search fails due to API error or network issue
        """
        pass
    
    @abstractmethod
    def validate_identifier(self, company_identifier: str) -> bool:
        """
        Validate company identifier format for this market.
        
        Args:
            company_identifier: Company identifier to validate
            
        Returns:
            True if identifier format is valid for this market, False otherwise
            
        Example:
            SEC: Validate CIK format (10 digits) or ticker symbol
            FCA: Validate FCA registration number
            ESMA: Validate LEI code format
        """
        pass
    
    @abstractmethod
    def get_supported_filing_types(self) -> List[str]:
        """
        Get list of filing types supported by this market.
        
        Returns:
            List of filing type identifiers
            
        Example:
            SEC: ['10-K', '10-Q', '8-K', '20-F', 'DEF 14A']
            FCA: ['Annual Report', 'Half-Yearly Report']
            ESMA: ['Annual Financial Report', 'Half-Yearly Financial Report']
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get capabilities and configuration for this market.
        
        Returns:
            Dictionary describing market capabilities:
            {
                'market_name': str,
                'supported_identifiers': List[str],  # e.g., ['ticker', 'cik']
                'requires_authentication': bool,
                'rate_limit_per_minute': int,
                'supports_date_range_search': bool,
                'supports_filing_type_filter': bool,
                'default_filing_types': List[str],
                'api_base_url': str,
                'documentation_url': str
            }
        """
        pass
    
    def get_market_name(self) -> str:
        """
        Get market identifier.
        
        Returns:
            Market name (e.g., 'sec', 'fca', 'esma')
        """
        return self.market_name
    
    def validate_search_criteria(self, criteria: Dict[str, Any]) -> bool:
        """
        Validate search criteria format (optional override).
        
        Default implementation performs basic validation.
        Markets can override for specific validation rules.
        
        Args:
            criteria: Search criteria dictionary
            
        Returns:
            True if criteria valid, False otherwise
        """
        if not isinstance(criteria, dict):
            return False
        
        # Validate date ranges if present
        if 'date_from' in criteria and 'date_to' in criteria:
            date_from = criteria['date_from']
            date_to = criteria['date_to']
            
            if isinstance(date_from, date) and isinstance(date_to, date):
                if date_from > date_to:
                    self.logger.warning("date_from cannot be after date_to")
                    return False
        
        return True
    
    def format_date_for_api(self, date_obj: date) -> str:
        """
        Format date for API calls (optional override).
        
        Default implementation returns ISO format (YYYY-MM-DD).
        Markets can override for specific date formats.
        
        Args:
            date_obj: Date to format
            
        Returns:
            Formatted date string
        """
        return date_obj.isoformat()
    
    def __repr__(self) -> str:
        """String representation of market interface."""
        return f"<{self.__class__.__name__}(market='{self.market_name}')>"