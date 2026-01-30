# Path: verification/engine/checks/context/context_matching.py
"""
Context Matching for XBRL Verification

Determines if two contexts are compatible for fact comparison.
"""

import logging

from .period_extraction import PeriodInfo, PeriodExtractor
from .context_classification import ContextClassifier


# Configuration constants
PERIOD_TYPE_DURATION = 'duration'
PERIOD_TYPE_INSTANT = 'instant'
PERIOD_TYPE_UNKNOWN = 'unknown'


class ContextMatcher:
    """
    Match and compare XBRL contexts for compatibility.

    Determines if contexts from different facts are compatible enough
    to allow comparison (e.g., for dimensional fallback).

    Example:
        matcher = ContextMatcher()

        # Check period compatibility
        compatible = matcher.is_period_compatible(
            'Duration_1_1_2024_To_12_31_2024',
            'Duration_1_1_2024_To_12_31_2024_extra'
        )
        # -> True (same period)
    """

    def __init__(self):
        self.logger = logging.getLogger('process.context_matcher')
        self.period_extractor = PeriodExtractor()
        self.classifier = ContextClassifier()

    def are_compatible(
        self,
        parent_context: str,
        child_context: str,
        strict: bool = False
    ) -> bool:
        """
        Check if two contexts are compatible for comparison.

        Args:
            parent_context: Parent's context_id
            child_context: Child's context_id
            strict: If True, require exact match

        Returns:
            True if contexts are compatible
        """
        if not parent_context or not child_context:
            return False

        # Exact match always compatible
        if parent_context == child_context:
            return True

        # Strict mode requires exact match
        if strict:
            return False

        # Check period compatibility
        return self.is_period_compatible(parent_context, child_context)

    def periods_match(
        self,
        period1: PeriodInfo,
        period2: PeriodInfo
    ) -> bool:
        """
        Check if two periods match for comparison purposes.

        Matching rules:
        1. Same period_key: always match
        2. Same period_type + same year: match
        3. Otherwise: no match

        Args:
            period1: First period info
            period2: Second period info

        Returns:
            True if periods match
        """
        # Exact period key match
        if period1.period_key and period2.period_key:
            if period1.period_key == period2.period_key:
                return True

        # Same period type and year
        if period1.period_type != PERIOD_TYPE_UNKNOWN and period2.period_type != PERIOD_TYPE_UNKNOWN:
            if period1.period_type == period2.period_type and period1.year == period2.year:
                return True

        # Fallback: just same year (loose match)
        if period1.year and period2.year and period1.year == period2.year:
            return True

        return False

    def is_period_compatible(
        self,
        parent_context: str,
        child_context: str
    ) -> bool:
        """
        Check if two contexts have compatible periods.

        Args:
            parent_context: Parent's context_id
            child_context: Child's context_id

        Returns:
            True if periods are compatible
        """
        parent_period = self.period_extractor.extract(parent_context)
        child_period = self.period_extractor.extract(child_context)

        return self.periods_match(parent_period, child_period)


__all__ = [
    'ContextMatcher',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_UNKNOWN',
]
