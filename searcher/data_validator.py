"""
File: engines/searcher/data_validator.py
Path: engines/searcher/data_validator.py

Search Data Validator
====================

Validates company and filing information before database operations.
Extracted from SearchResultsProcessor to follow Single Responsibility Principle.
"""

from typing import Dict, Any

from core.system_logger import get_logger
from engines.searcher.search_constants import (
    REQUIRED_ENTITY_FIELDS,
    REQUIRED_FILING_FIELDS,
    MAX_COMPANY_NAME_LENGTH,
    FIELD_NAME
)

logger = get_logger(__name__, 'engine')


class SearchDataValidator:
    """
    Validates search result data.
    
    Responsibilities:
    - Validate company information
    - Validate filing information
    - Check required fields
    - Validate field lengths
    """
    
    def __init__(self) -> None:
        """Initialize search data validator."""
        logger.debug("Search data validator initialized")
    
    def validate_company_info(self, company_info: Dict[str, Any]) -> bool:
        """
        Validate company information before saving.
        
        Args:
            company_info: Company information to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self._validate_required_fields(company_info, REQUIRED_ENTITY_FIELDS):
            return False
        
        if not self._validate_company_name_length(company_info):
            return False
        
        return True
    
    def validate_filing_info(self, filing_info: Dict[str, Any]) -> bool:
        """
        Validate filing information before saving.
        
        Args:
            filing_info: Filing information to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self._validate_required_fields(filing_info, REQUIRED_FILING_FIELDS)
    
    def _validate_required_fields(
        self, 
        data: Dict[str, Any], 
        required_fields: list
    ) -> bool:
        """
        Validate that all required fields are present and non-empty.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            
        Returns:
            True if all required fields present and valid
        """
        for field in required_fields:
            if not self._is_field_present_and_valid(data, field):
                logger.error(f"Missing or invalid required field: {field}")
                return False
        
        return True
    
    def _is_field_present_and_valid(
        self, 
        data: Dict[str, Any], 
        field: str
    ) -> bool:
        """
        Check if field is present and has valid value.
        
        Args:
            data: Data dictionary
            field: Field name to check
            
        Returns:
            True if field present and valid
        """
        if field not in data:
            return False
        
        value = data[field]
        
        # Check for None or empty string
        if value is None:
            return False
        
        if isinstance(value, str) and not value.strip():
            return False
        
        return True
    
    def _validate_company_name_length(
        self, 
        company_info: Dict[str, Any]
    ) -> bool:
        """
        Validate company name does not exceed maximum length.
        
        Args:
            company_info: Company information
            
        Returns:
            True if name length is valid
        """
        name = company_info.get(FIELD_NAME, '')
        
        if len(name) > MAX_COMPANY_NAME_LENGTH:
            logger.error(
                f"Company name exceeds maximum length of {MAX_COMPANY_NAME_LENGTH} "
                f"characters: {len(name)}"
            )
            return False
        
        return True