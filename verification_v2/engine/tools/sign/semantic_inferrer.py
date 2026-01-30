# Path: verification/engine/checks_v2/tools/sign/semantic_inferrer.py
"""
Semantic Sign Inferrer for XBRL Concepts

Infers expected sign from concept name semantics as a fallback when
explicit sign information is not available.

Uses common XBRL naming conventions:
- Payments, Expenses, Costs, Losses -> typically negative (cash outflows)
- Proceeds, Revenues, Income, Gains -> typically positive (cash inflows)

This is a fallback strategy - explicit sign attributes always take precedence.
"""

import logging
import re
from typing import Optional

from ..naming import extract_local_name
from ...constants.patterns import (
    NEGATIVE_CONCEPT_PATTERNS,
    POSITIVE_CONCEPT_PATTERNS,
)


class SemanticSignInferrer:
    """
    Infer expected sign from concept name semantics.

    Uses pattern matching on concept names to guess whether a value
    should typically be positive or negative.

    Usage:
        inferrer = SemanticSignInferrer()

        # Infer sign for cash flow concept
        sign = inferrer.infer('us-gaap:PaymentsForCapitalExpenditures')
        # Returns -1 (payments are typically negative/outflows)

        sign = inferrer.infer('us-gaap:ProceedsFromSaleOfEquipment')
        # Returns 1 (proceeds are typically positive/inflows)

        sign = inferrer.infer('us-gaap:Assets')
        # Returns None (cannot determine from name)
    """

    def __init__(self):
        """Initialize the inferrer with compiled patterns."""
        self.logger = logging.getLogger('tools.sign.semantic_inferrer')
        self._negative_patterns = [
            re.compile(p, re.IGNORECASE) for p in NEGATIVE_CONCEPT_PATTERNS
        ]
        self._positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in POSITIVE_CONCEPT_PATTERNS
        ]

    def infer(self, concept: str) -> Optional[int]:
        """
        Infer expected sign from concept name semantics.

        Args:
            concept: Concept name (with or without namespace)

        Returns:
            1 for expected positive, -1 for expected negative, None if unknown
        """
        if not concept:
            return None

        # Extract local name for pattern matching
        local_name = extract_local_name(concept)

        # Check negative patterns first
        for pattern in self._negative_patterns:
            if pattern.search(local_name):
                self.logger.debug(f"Inferred negative sign for '{concept}'")
                return -1

        # Check positive patterns
        for pattern in self._positive_patterns:
            if pattern.search(local_name):
                self.logger.debug(f"Inferred positive sign for '{concept}'")
                return 1

        # Cannot determine
        return None

    def is_likely_negative(self, concept: str) -> bool:
        """
        Check if concept is likely to be negative.

        Args:
            concept: Concept name

        Returns:
            True if concept name suggests negative value
        """
        return self.infer(concept) == -1

    def is_likely_positive(self, concept: str) -> bool:
        """
        Check if concept is likely to be positive.

        Args:
            concept: Concept name

        Returns:
            True if concept name suggests positive value
        """
        return self.infer(concept) == 1

    def explain_inference(self, concept: str) -> str:
        """
        Get explanation of sign inference for a concept.

        Args:
            concept: Concept name

        Returns:
            Human-readable explanation
        """
        local_name = extract_local_name(concept)

        for pattern in self._negative_patterns:
            if pattern.search(local_name):
                return f"'{local_name}' matches negative pattern: {pattern.pattern}"

        for pattern in self._positive_patterns:
            if pattern.search(local_name):
                return f"'{local_name}' matches positive pattern: {pattern.pattern}"

        return f"No sign pattern matched for '{local_name}'"


__all__ = ['SemanticSignInferrer']
