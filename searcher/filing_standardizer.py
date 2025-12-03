# File: /map_pro/engines/searcher/filing_standardizer.py

"""
Filing Standardizer
===================

Standardizes filing information from various market formats to common format.

Responsibilities:
- Validate required fields
- Parse and normalize dates
- Format filing information consistently
- Handle optional fields gracefully
"""

from typing import Dict, Any, Optional
from datetime import datetime, date, timezone

from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import EngineError

logger = get_logger(__name__, 'engine')

# Required fields for all filings
REQUIRED_FIELDS = ['market_filing_id', 'filing_type', 'filing_date']

# Date format patterns to try
DATE_FORMATS = ['%Y-%m-%d', '%Y%m%d', '%m/%d/%Y', '%d/%m/%Y']


class FilingStandardizer:
    """Standardizes filing information to common format."""
    
    def standardize_filing(
        self, 
        filing_info: Dict[str, Any], 
        market_type: str
    ) -> Dict[str, Any]:
        """
        Standardize filing information to common format.
        
        Args:
            filing_info: Raw filing info from market plugin
            market_type: Market type
            
        Returns:
            Standardized filing information dictionary
            
        Raises:
            EngineError: If required fields are missing
        """
        # Validate required fields
        self._validate_required_fields(filing_info)
        
        # Build standardized format
        standardized = {
            # Required fields
            'market_filing_id': str(filing_info['market_filing_id']),
            'filing_type': str(filing_info['filing_type']),
            'filing_date': self.parse_date(filing_info['filing_date']),
            'market_type': market_type,
            
            # Optional date fields
            'period_start_date': self.parse_date(filing_info.get('period_start')),
            'period_end_date': self.parse_date(filing_info.get('period_end')),
            
            # Optional metadata
            'filing_title': filing_info.get('title'),
            'download_url': filing_info.get('url'),
            'file_format': filing_info.get('format'),
            'file_size_bytes': filing_info.get('size'),
            
            # System metadata
            'discovered_at': datetime.now(timezone.utc),
            'source_url': filing_info.get('source_url'),
            'additional_info': filing_info.get('additional_info', {})
        }
        
        return standardized
    
    def _validate_required_fields(self, filing_info: Dict[str, Any]) -> None:
        """
        Validate that all required fields are present.
        
        Args:
            filing_info: Filing information to validate
            
        Raises:
            EngineError: If required fields are missing
        """
        missing_fields = [
            field for field in REQUIRED_FIELDS
            if field not in filing_info
        ]
        
        if missing_fields:
            raise EngineError(
                f"Market plugin returned incomplete filing data: "
                f"missing {', '.join(missing_fields)}"
            )
    
    def parse_date(self, date_value: Any) -> Optional[date]:
        """
        Parse date from various formats to date object.
        
        Args:
            date_value: Date in various formats (string, date, datetime, None)
            
        Returns:
            date object or None
        """
        if date_value is None:
            return None
        
        # Already a date object
        if isinstance(date_value, date):
            return date_value
        
        # datetime object
        if isinstance(date_value, datetime):
            return date_value.date()
        
        # String - try multiple formats
        if isinstance(date_value, str):
            return self._parse_date_string(date_value)
        
        return None
    
    def _parse_date_string(self, date_string: str) -> Optional[date]:
        """
        Parse date from string trying multiple formats.
        
        Args:
            date_string: Date string to parse
            
        Returns:
            date object or None if parsing fails
        """
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_string, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_string}")
        return None


__all__ = ['FilingStandardizer']