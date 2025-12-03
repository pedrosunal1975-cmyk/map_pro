"""
FCA Validators
=============

Validation functions for FCA-specific data formats.
Validates UK company numbers and filing types.
"""

import re
from typing import Optional
from datetime import date, timezone

from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


class FCAValidator:
    """Validator for FCA-specific formats and identifiers."""
    
    @staticmethod
    def validate_company_number(company_number: str) -> bool:
        """
        Validate UK company number format.
        
        UK company numbers are typically 8 digits, sometimes with prefix letters.
        Examples: 00000001, SC123456, NI123456
        
        Args:
            company_number: Company number to validate
            
        Returns:
            True if valid format
        """
        if not company_number or not isinstance(company_number, str):
            return False
        
        company_number = company_number.strip().upper()
        
        # Pattern: Optional 2-letter prefix + 6-8 digits
        pattern = r'^([A-Z]{2})?\d{6,8}$'
        
        return bool(re.match(pattern, company_number))
    
    @staticmethod
    def normalize_company_number(company_number: str) -> str:
        """
        Normalize company number to standard format.
        
        Args:
            company_number: Company number
            
        Returns:
            Normalized company number (uppercase)
            
        Raises:
            ValueError: If invalid format
        """
        if not FCAValidator.validate_company_number(company_number):
            raise ValueError(f"Invalid UK company number format: {company_number}")
        
        return company_number.strip().upper()
    
    @staticmethod
    def validate_filing_type(filing_type: str) -> bool:
        """
        Validate FCA filing type.
        
        Args:
            filing_type: Filing type to validate
            
        Returns:
            True if recognized filing type
        """
        if not filing_type or not isinstance(filing_type, str):
            return False
        
        from .fca_constants import FCA_FILING_TYPES, MAJOR_FILING_TYPES
        
        filing_type = filing_type.strip().upper()
        return filing_type in FCA_FILING_TYPES or filing_type in MAJOR_FILING_TYPES
    
    @staticmethod
    def validate_date(date_value: date) -> bool:
        """
        Validate filing date.
        
        Args:
            date_value: Date to validate
            
        Returns:
            True if valid date
        """
        if not isinstance(date_value, date):
            return False
        
        # FCA established in 2013
        if date_value.year < 2013:
            return False
        
        # Date cannot be in the future
        if date_value > date.today():
            return False
        
        return True
    
    @staticmethod
    def identify_identifier_type(identifier: str) -> Optional[str]:
        """
        Identify what type of identifier this is.
        
        Args:
            identifier: Company identifier
            
        Returns:
            'company_number' or None
        """
        if not identifier:
            return None
        
        identifier = identifier.strip()
        
        # Check if it's a company number
        if FCAValidator.validate_company_number(identifier):
            return 'company_number'
        
        return None


# Convenience functions
def validate_company_number(company_number: str) -> bool:
    """Validate UK company number format."""
    return FCAValidator.validate_company_number(company_number)


def normalize_company_number(company_number: str) -> str:
    """Normalize company number."""
    return FCAValidator.normalize_company_number(company_number)


def identify_identifier_type(identifier: str) -> Optional[str]:
    """Identify identifier type."""
    return FCAValidator.identify_identifier_type(identifier)