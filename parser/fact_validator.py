"""
Fact Validator.

Validates extracted facts for completeness and correctness.

Location: engines/parser/fact_validator.py
"""

from typing import Dict, Any

from core.system_logger import get_logger


logger = get_logger(__name__, 'engine')


class FactValidator:
    """
    Validates extracted facts.
    
    Responsibilities:
    - Validate required fields
    - Validate field lengths
    - Validate data types
    - Log validation errors
    
    Example:
        >>> validator = FactValidator()
        >>> is_valid = validator.validate(fact_dict, index=0)
    """
    
    # Constants
    MAX_CONCEPT_NAME_LENGTH = 500
    
    def validate(self, fact_dict: Dict[str, Any], index: int) -> bool:
        """
        Validate extracted fact.
        
        Args:
            fact_dict: Fact dictionary to validate
            index: Fact index for logging
            
        Returns:
            True if valid, False otherwise
        """
        # Must have concept name
        if not self._has_concept_name(fact_dict, index):
            return False
        
        # Concept name should be reasonable length
        if not self._validate_concept_name_length(fact_dict, index):
            return False
        
        return True
    
    def _has_concept_name(self, fact_dict: Dict[str, Any], index: int) -> bool:
        """
        Check if fact has concept local name.
        
        Args:
            fact_dict: Fact dictionary
            index: Fact index
            
        Returns:
            True if has concept name
        """
        if not fact_dict.get('concept_local_name'):
            logger.warning(f"Fact {index}: Missing concept_local_name")
            return False
        return True
    
    def _validate_concept_name_length(self, fact_dict: Dict[str, Any], index: int) -> bool:
        """
        Validate concept name length.
        
        Args:
            fact_dict: Fact dictionary
            index: Fact index
            
        Returns:
            True if length is valid
        """
        concept_name = fact_dict['concept_local_name']
        if len(concept_name) > self.MAX_CONCEPT_NAME_LENGTH:
            logger.warning(
                f"Fact {index}: Concept name too long ({len(concept_name)} chars)"
            )
            return False
        return True


__all__ = ['FactValidator']