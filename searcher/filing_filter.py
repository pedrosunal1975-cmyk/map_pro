# File: /map_pro/engines/searcher/filing_filter.py

"""
Filing Filter
=============

Filters filings based on search criteria.
Reduces complexity by separating filtering logic into focused methods.

Responsibilities:
- Apply date range filters
- Apply filing type filters
- Determine if filing should be included
- Handle various filter types
"""

from typing import Dict, Any, Optional
from datetime import date

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class FilingFilter:
    """Filters filings based on search criteria."""
    
    def __init__(self):
        """Initialize filing filter."""
        self.standardizer = None  # Set by filing_identification if needed
    
    def should_include_filing(
        self, 
        filing: Dict[str, Any], 
        criteria: Dict[str, Any]
    ) -> bool:
        """
        Check if filing matches search criteria filters.
        
        Complexity reduced by delegating each filter type to separate method.
        
        Args:
            filing: Standardized filing information
            criteria: Search criteria with filters
            
        Returns:
            True if filing should be included, False otherwise
        """
        # Apply date range filter
        if not self._passes_date_filter(filing, criteria):
            return False
        
        # Apply filing type filter
        if not self._passes_type_filter(filing, criteria):
            return False
        
        # All filters passed
        return True
    
    def _passes_date_filter(
        self,
        filing: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> bool:
        """
        Check if filing passes date range filter.
        
        Args:
            filing: Filing information
            criteria: Search criteria
            
        Returns:
            True if filing passes date filter
        """
        filing_date = filing.get('filing_date')
        
        if not filing_date:
            return True  # No filing date to filter on
        
        # Check date_from
        if not self._passes_date_from(filing_date, criteria):
            return False
        
        # Check date_to
        if not self._passes_date_to(filing_date, criteria):
            return False
        
        return True
    
    def _passes_date_from(
        self,
        filing_date: date,
        criteria: Dict[str, Any]
    ) -> bool:
        """
        Check if filing date is after or equal to date_from.
        
        Args:
            filing_date: Filing date
            criteria: Search criteria
            
        Returns:
            True if passes date_from filter
        """
        if 'date_from' not in criteria:
            return True
        
        date_from = self._parse_date_value(criteria['date_from'])
        
        if date_from and filing_date < date_from:
            return False
        
        return True
    
    def _passes_date_to(
        self,
        filing_date: date,
        criteria: Dict[str, Any]
    ) -> bool:
        """
        Check if filing date is before or equal to date_to.
        
        Args:
            filing_date: Filing date
            criteria: Search criteria
            
        Returns:
            True if passes date_to filter
        """
        if 'date_to' not in criteria:
            return True
        
        date_to = self._parse_date_value(criteria['date_to'])
        
        if date_to and filing_date > date_to:
            return False
        
        return True
    
    def _passes_type_filter(
        self,
        filing: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> bool:
        """
        Check if filing type matches allowed types.
        
        Args:
            filing: Filing information
            criteria: Search criteria
            
        Returns:
            True if filing type is allowed
        """
        if 'filing_types' not in criteria:
            return True
        
        allowed_types = criteria['filing_types']
        
        # Empty list means no filtering
        if not allowed_types or not isinstance(allowed_types, list):
            return True
        
        filing_type = filing.get('filing_type')
        
        return filing_type in allowed_types
    
    def _parse_date_value(self, date_value: Any) -> Optional[date]:
        """
        Parse date value using standardizer if available.
        
        Args:
            date_value: Date value to parse
            
        Returns:
            date object or None
        """
        # Import here to avoid circular dependency
        from .filing_standardizer import FilingStandardizer
        
        if self.standardizer is None:
            self.standardizer = FilingStandardizer()
        
        return self.standardizer.parse_date(date_value)


__all__ = ['FilingFilter']