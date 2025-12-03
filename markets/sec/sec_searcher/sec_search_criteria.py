"""
SEC Search Criteria Parser.

Parses and normalizes search criteria for filing searches.

Location: markets/sec/sec_searcher/sec_search_criteria.py
"""

from typing import Dict, Any, Optional
from logging import Logger


# Default configuration
DEFAULT_FILING_LIMIT = 100


class SearchCriteriaParser:
    """
    Parses and normalizes search criteria.
    
    Responsibilities:
    - Extract search parameters
    - Apply defaults
    - Normalize values
    - Validate criteria
    
    Example:
        >>> parser = SearchCriteriaParser(logger)
        >>> criteria = parser.parse({'filing_types': ['10-K'], 'limit': 5})
    """
    
    def __init__(self, logger: Logger):
        """
        Initialize search criteria parser.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def parse(self, search_criteria: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse and normalize search criteria.
        
        Args:
            search_criteria: Raw search criteria or None
            
        Returns:
            Normalized search criteria with defaults
        """
        criteria = search_criteria or {}
        
        # Extract values
        date_from = criteria.get('date_from')
        date_to = criteria.get('date_to')
        filing_types = criteria.get('filing_types', [])
        limit = criteria.get('limit', DEFAULT_FILING_LIMIT)
        
        # Normalize filing types
        if filing_types:
            filing_types = [ft.upper() for ft in filing_types]
            self.logger.info(
                f"Filtering for filing types: {filing_types}, limit: {limit}"
            )
        
        return {
            'date_from': date_from,
            'date_to': date_to,
            'filing_types': filing_types,
            'limit': limit
        }


__all__ = ['SearchCriteriaParser']