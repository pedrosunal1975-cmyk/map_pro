# File: /map_pro/engines/searcher/filing_criteria_validator.py

"""
Filing Criteria Validator
==========================

Validates and normalizes search criteria.
Reduces complexity by separating validation logic into focused methods.

Responsibilities:
- Validate date ranges
- Validate filing types
- Validate limit values
- Normalize criteria format
"""

from typing import Dict, Any
from datetime import date

from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import EngineError

logger = get_logger(__name__, 'engine')

# Validation constants
MAX_LIMIT = 1000
MIN_LIMIT = 1


class FilingCriteriaValidator:
    """Validates and normalizes search criteria."""
    
    def __init__(self):
        """Initialize criteria validator."""
        self.standardizer = None  # Set lazily when needed
    
    def validate_criteria(
        self, 
        criteria: Dict[str, Any], 
        market_type: str
    ) -> Dict[str, Any]:
        """
        Validate and normalize search criteria.
        
        Complexity reduced by delegating each validation to separate method.
        
        Args:
            criteria: Raw search criteria
            market_type: Market type (for future market-specific validation)
            
        Returns:
            Validated and normalized criteria
            
        Raises:
            EngineError: If validation fails
        """
        validated = {}
        
        # Validate date criteria
        date_criteria = self._validate_date_criteria(criteria)
        validated.update(date_criteria)
        
        # Validate filing types
        type_criteria = self._validate_filing_types(criteria)
        validated.update(type_criteria)
        
        # Validate limit
        limit_criteria = self._validate_limit(criteria)
        validated.update(limit_criteria)
        
        return validated
    
    def _validate_date_criteria(
        self,
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate date range criteria.
        
        Args:
            criteria: Raw criteria
            
        Returns:
            Validated date criteria
            
        Raises:
            EngineError: If date range is invalid
        """
        validated = {}
        
        # Parse date_from
        if 'date_from' in criteria:
            date_from = self._parse_and_validate_date(
                criteria['date_from'], 'date_from'
            )
            if date_from:
                validated['date_from'] = date_from
        
        # Parse date_to
        if 'date_to' in criteria:
            date_to = self._parse_and_validate_date(
                criteria['date_to'], 'date_to'
            )
            if date_to:
                validated['date_to'] = date_to
        
        # Validate date range logic
        self._validate_date_range(validated)
        
        return validated
    
    def _parse_and_validate_date(
        self,
        date_value: Any,
        field_name: str
    ) -> date:
        """
        Parse and validate a date value.
        
        Args:
            date_value: Date value to parse
            field_name: Name of the field (for error messages)
            
        Returns:
            Parsed date object or None
        """
        parsed_date = self._parse_date(date_value)
        
        if parsed_date is None and date_value is not None:
            logger.warning(
                f"Could not parse {field_name}: {date_value}, ignoring filter"
            )
        
        return parsed_date
    
    def _validate_date_range(self, validated: Dict[str, Any]) -> None:
        """
        Validate that date range is logically correct.
        
        Args:
            validated: Dictionary with validated dates
            
        Raises:
            EngineError: If date_from is after date_to
        """
        if 'date_from' in validated and 'date_to' in validated:
            if validated['date_from'] > validated['date_to']:
                raise EngineError("date_from cannot be after date_to")
    
    def _validate_filing_types(
        self,
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate filing types criteria.
        
        Args:
            criteria: Raw criteria
            
        Returns:
            Validated filing types criteria
        """
        if 'filing_types' not in criteria:
            return {}
        
        filing_types = criteria['filing_types']
        
        # Normalize to list
        if isinstance(filing_types, str):
            return {'filing_types': [filing_types]}
        
        if isinstance(filing_types, list):
            return {'filing_types': filing_types}
        
        logger.warning(f"Invalid filing_types format: {type(filing_types)}")
        return {}
    
    def _validate_limit(
        self,
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate limit criteria.
        
        Args:
            criteria: Raw criteria
            
        Returns:
            Validated limit criteria
        """
        if 'limit' not in criteria:
            return {}
        
        try:
            limit = int(criteria['limit'])
            
            if limit < MIN_LIMIT:
                logger.warning(f"Limit {limit} below minimum, ignoring")
                return {}
            
            # Cap at maximum
            validated_limit = min(limit, MAX_LIMIT)
            
            if validated_limit != limit:
                logger.info(f"Limit capped at maximum: {MAX_LIMIT}")
            
            return {'limit': validated_limit}
            
        except (ValueError, TypeError):
            logger.warning(f"Invalid limit value: {criteria['limit']}")
            return {}
    
    def _parse_date(self, date_value: Any) -> date:
        """
        Parse date value.
        
        Args:
            date_value: Date value to parse
            
        Returns:
            Parsed date or None
        """
        # Import here to avoid circular dependency
        from .filing_standardizer import FilingStandardizer
        
        if self.standardizer is None:
            self.standardizer = FilingStandardizer()
        
        return self.standardizer.parse_date(date_value)


__all__ = ['FilingCriteriaValidator']