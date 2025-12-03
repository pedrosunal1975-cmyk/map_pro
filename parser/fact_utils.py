"""
Fact Extraction Utilities.

Utility functions for fact extraction and processing.

Location: engines/parser/fact_utils.py
"""

import re
from typing import Optional
from decimal import Decimal, InvalidOperation

from core.system_logger import get_logger


logger = get_logger(__name__, 'engine')


def extract_numeric_value(fact_value: str) -> Optional[Decimal]:
    """
    Extract numeric value from fact value string.
    
    Handles common formatting like:
    - Commas in numbers: "1,234.56"
    - Currency symbols: "$1234.56"
    - Parentheses for negatives: "(1234.56)"
    
    Args:
        fact_value: Fact value string
        
    Returns:
        Decimal value or None if not numeric
        
    Example:
        >>> value = extract_numeric_value("$1,234.56")
        >>> print(value)  # Decimal('1234.56')
    """
    if not fact_value:
        return None
    
    try:
        cleaned = clean_numeric_string(fact_value)
        return Decimal(cleaned)
    except (InvalidOperation, ValueError) as e:
        logger.debug(f"Could not convert to numeric: {e}")
        return None


def clean_numeric_string(value: str) -> str:
    """
    Clean string for numeric conversion.
    
    Args:
        value: Value string to clean
        
    Returns:
        Cleaned string suitable for Decimal conversion
        
    Example:
        >>> cleaned = clean_numeric_string("$1,234.56")
        >>> print(cleaned)  # '1234.56'
    """
    # Remove common formatting
    cleaned = re.sub(r'[,$\s]', '', str(value))
    
    # Handle parentheses as negative
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    
    return cleaned


__all__ = [
    'extract_numeric_value',
    'clean_numeric_string'
]