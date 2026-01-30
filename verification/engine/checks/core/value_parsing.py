# Path: verification/engine/checks/core/value_parsing.py
"""
Value Parsing and Normalization for XBRL Verification

Handles parsing of raw values from financial statements, including:
- Nil/zero value representations
- Currency formatting (commas, dollar signs)
- Parenthetical negatives
- Em-dash and en-dash conventions
"""

import logging
from typing import Optional


# Configuration constants
# Unicode characters for dash representations
EM_DASH = '\u2014'  # Em-dash character
EN_DASH = '\u2013'  # En-dash character

# Value representations that mean zero/nil
NIL_VALUES = {'', '-', '--', '---', 'nil', 'N/A', 'n/a', 'None', 'none'}


class ValueParser:
    """
    Handles parsing of raw values from financial statements.

    Converts various string representations into numeric values,
    handling common financial statement conventions.
    """

    def __init__(self):
        self.logger = logging.getLogger('process.value_parsing')

    def parse_value(self, raw_value) -> Optional[float]:
        """
        Parse a raw value to float.

        Handles financial statement conventions:
        - Em-dash, en-dash, hyphen mean zero/nil
        - Removes commas and dollar signs
        - Parentheses indicate negative values
        - Returns None if unparseable

        Args:
            raw_value: Raw value from statement

        Returns:
            Float value or None
        """
        if raw_value is None:
            return None

        raw_str = str(raw_value).strip()

        # Check for nil/zero representations
        if raw_str in NIL_VALUES:
            return 0.0

        # Handle em-dash and en-dash
        if raw_str in {EM_DASH, EN_DASH}:
            return 0.0

        try:
            # Clean common financial formatting:
            # - Remove commas (thousands separators)
            # - Remove dollar signs
            # - Convert parentheses to negative sign
            cleaned = raw_str.replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def is_nil_value(self, raw_value) -> bool:
        """
        Check if a value represents nil/zero.

        Args:
            raw_value: Raw value to check

        Returns:
            True if value is nil/zero representation
        """
        if raw_value is None:
            return True
        raw_str = str(raw_value).strip()
        return raw_str in NIL_VALUES or raw_str in {EM_DASH, EN_DASH}


__all__ = [
    'ValueParser',
    'NIL_VALUES',
    'EM_DASH',
    'EN_DASH',
]
