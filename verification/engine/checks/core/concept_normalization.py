# Path: verification/engine/checks/core/concept_normalization.py
"""
Concept Name Normalization for XBRL Verification

Handles normalization of concept names for comparison across different formats.

XBRL concept names can appear with different separators:
- us-gaap:Assets (colon - in linkbase)
- us-gaap_Assets (underscore - in presentation)
- Custom concepts: v_CustomConcept (company extension)

This module extracts the local name and applies standard normalization.
"""

import logging
from typing import Set

from ....loaders.constants import normalize_name


# Configuration constants
# Maximum length for company extension prefixes
MAX_EXTENSION_PREFIX_LENGTH = 6

# Known taxonomy prefixes (standard namespaces)
KNOWN_TAXONOMY_PREFIXES: Set[str] = {
    'us-gaap', 'usgaap', 'ifrs-full', 'ifrs', 'dei', 'srt', 'country',
    'currency', 'exch', 'naics', 'sic', 'stpr', 'invest',
    'ecd', 'custom'
}


class ConceptNormalizer:
    """
    Normalizes concept names for comparison.

    Extracts local name from namespaced concepts and applies
    standard normalization (lowercase, no separators).

    Handles:
    - Colon separators: us-gaap:Assets
    - Underscore separators: us-gaap_Assets, v_CustomConcept
    - Company extension patterns
    """

    def __init__(self):
        self.logger = logging.getLogger('process.concept_normalization')

    @staticmethod
    def normalize_concept(concept: str) -> str:
        """
        Normalize a concept name to its local name for comparison.

        Extracts the local name after namespace prefix, then applies
        standard normalization (removes separators, lowercases).

        Handles:
        - Clark notation: {http://fasb.org/us-gaap/2024}Assets
        - Colon separators: us-gaap:Assets
        - Underscore separators: us-gaap_Assets or v_CustomConcept

        Args:
            concept: Original concept name (e.g., "us-gaap:Assets" or "v_CustomConcept")

        Returns:
            Normalized local name (e.g., "assets" or "customconcept")
        """
        if not concept:
            return ''

        # Handle Clark notation first: {namespace}LocalName
        # This format is used in some XBRL parsers and APIs
        if concept.startswith('{') and '}' in concept:
            local_name = concept.split('}')[-1]
            return normalize_name(local_name)

        # Handle colon separator (us-gaap:Assets)
        # But NOT if it looks like a URL (contains ://)
        if ':' in concept and '://' not in concept:
            local_name = concept.split(':')[-1]
        # Handle underscore separator (us-gaap_Assets or v_CustomConcept)
        # Check if first part looks like a namespace prefix
        elif '_' in concept:
            parts = concept.split('_', 1)
            if len(parts) == 2:
                prefix = parts[0].lower()
                
                # Company extension prefixes are typically:
                # 1. Short (1-6 characters) - like 'v', 'aapl', 'msft', 'plug'
                # 2. All alphabetic
                # 3. The rest of the name starts with an uppercase letter (CamelCase concept)
                is_company_prefix = (
                    len(prefix) <= MAX_EXTENSION_PREFIX_LENGTH and
                    prefix.isalpha() and
                    len(parts[1]) > 0 and
                    parts[1][0].isupper()
                )
                if prefix in KNOWN_TAXONOMY_PREFIXES or is_company_prefix:
                    local_name = parts[1]
                else:
                    local_name = concept
            else:
                local_name = concept
        else:
            local_name = concept

        # Use canonical normalize_name for consistent comparison
        return normalize_name(local_name)


__all__ = [
    'ConceptNormalizer',
    'KNOWN_TAXONOMY_PREFIXES',
    'MAX_EXTENSION_PREFIX_LENGTH',
]
