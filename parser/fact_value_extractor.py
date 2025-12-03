"""
Fact Value Extractor.

Extracts and cleans fact values from Arelle fact objects.

Location: engines/parser/fact_value_extractor.py
"""

import re
from typing import Optional

from core.system_logger import get_logger


logger = get_logger(__name__, 'engine')


class ValueExtractor:
    """
    Extracts and cleans fact values.
    
    Responsibilities:
    - Extract raw values from fact objects
    - Remove HTML tags
    - Normalize whitespace
    - Clean special characters
    
    Example:
        >>> extractor = ValueExtractor()
        >>> value = extractor.extract(arelle_fact)
    """
    
    def __init__(self):
        """Initialize value extractor."""
        # HTML tag removal pattern
        self.html_pattern = re.compile(r'<[^>]+>')
        
        # Special character replacements
        self.replacements = {
            '\u00a0': ' ',   # Non-breaking space
            '\u2019': "'",   # Right single quotation
            '\u201c': '"',   # Left double quotation
            '\u201d': '"'    # Right double quotation
        }
    
    def extract(self, arelle_fact) -> Optional[str]:
        """
        Extract and clean fact value.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Cleaned fact value string or None
        """
        raw_value = self._get_raw_value(arelle_fact)
        
        if not raw_value:
            return None
        
        return self._clean_value_string(raw_value)
    
    def _get_raw_value(self, arelle_fact) -> Optional[str]:
        """
        Get raw value from fact object with transform error handling.
        
        Multi-layer fallback approach:
        1. Try fact.value (with transforms)
        2. If transform error, try fact.text (raw content)
        3. If that fails, try fact.stringValue
        4. Return None if all fail
        
        This prevents transform errors from being stored as values.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Raw value string or None
        """
        # Layer 1: Try 'value' attribute (with transforms)
        try:
            if hasattr(arelle_fact, 'value'):
                value = arelle_fact.value
                
                # Check if value is an error object or error string
                if value is not None:
                    value_str = str(value)
                    
                    # Detect transform errors
                    if 'ixTransformValueError' in value_str or 'TransformError' in value_str:
                        logger.debug(f"Transform error detected for fact, falling back to text extraction")
                        # Don't return - fall through to Layer 2
                    else:
                        return value_str
        except Exception as e:
            # Transform exception caught - fall through to Layer 2
            logger.debug(f"Exception during value extraction: {e}, trying fallback")
        
        # Layer 2: Try 'text' attribute (raw content without transforms)
        try:
            if hasattr(arelle_fact, 'text') and arelle_fact.text is not None:
                return str(arelle_fact.text)
        except Exception as e:
            logger.debug(f"Exception during text extraction: {e}, trying stringValue")
        
        # Layer 3: Try 'stringValue' attribute
        try:
            if hasattr(arelle_fact, 'stringValue') and arelle_fact.stringValue is not None:
                return str(arelle_fact.stringValue)
        except Exception as e:
            logger.debug(f"Exception during stringValue extraction: {e}")
        
        # Layer 4: All extraction failed
        return None
    
    def _clean_value_string(self, raw_value: str) -> Optional[str]:
        """
        Clean and normalize value string.
        
        Steps:
        1. Remove HTML tags
        2. Normalize whitespace
        3. Remove special characters
        4. Trim result
        
        Args:
            raw_value: Raw value string
            
        Returns:
            Cleaned value string or None if empty
        """
        # Remove HTML tags
        cleaned = self.html_pattern.sub('', raw_value)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove special characters
        cleaned = self._remove_special_characters(cleaned)
        
        return cleaned if cleaned else None
    
    def _remove_special_characters(self, text: str) -> str:
        """
        Remove special formatting characters.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        for old, new in self.replacements.items():
            text = text.replace(old, new)
        
        return text


__all__ = ['ValueExtractor']