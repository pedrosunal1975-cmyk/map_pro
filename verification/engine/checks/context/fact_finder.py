# Path: verification/engine/checks/fact_finder.py
"""
Fact Finding for XBRL Verification

Finds facts across contexts with various strategies including exact matching,
period-compatible fallback, and dimensional-aware filtering.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .context_classification import ContextClassifier
from .context_matching import ContextMatcher


# Configuration constants
MATCH_TYPE_EXACT = 'exact'
MATCH_TYPE_FALLBACK = 'fallback'
MATCH_TYPE_PERIOD_MATCH = 'period_match'
MATCH_TYPE_NONE = 'none'


@dataclass
class FactMatch:
    """
    Result of finding a fact.

    Attributes:
        found: Whether fact was found
        context_id: Context where fact was found
        value: Fact value
        unit: Unit of measurement
        decimals: Decimal precision
        match_type: 'exact' (same context), 'fallback' (different context), or 'none'
    """
    found: bool = False
    context_id: str = ''
    value: Optional[float] = None
    unit: Optional[str] = None
    decimals: Optional[int] = None
    match_type: str = MATCH_TYPE_NONE


class FactFinder:
    """
    Find facts across contexts with various strategies.

    Provides:
    - Exact matching (same context_id, C-Equal)
    - Period-compatible fallback (different context, same period)
    - Dimensional-aware filtering

    Example:
        finder = FactFinder(all_facts_dict)

        # Find with fallback
        match = finder.find_compatible(
            concept='assets',
            parent_context='Duration_1_1_2024_To_12_31_2024',
            parent_unit='USD'
        )
    """

    def __init__(
        self,
        all_facts: dict[str, list[tuple[str, float, Optional[str], Optional[int]]]] = None
    ):
        """
        Initialize fact finder.

        Args:
            all_facts: Dictionary mapping concept -> list of (context_id, value, unit, decimals)
        """
        self.all_facts = all_facts or {}
        self.logger = logging.getLogger('process.fact_finder')
        self.classifier = ContextClassifier()
        self.matcher = ContextMatcher()

    def find_in_context(
        self,
        concept: str,
        context_id: str
    ) -> FactMatch:
        """
        Find a fact in a specific context (strict C-Equal).

        Args:
            concept: Normalized concept name
            context_id: Context to search in

        Returns:
            FactMatch with result
        """
        if concept not in self.all_facts:
            return FactMatch()

        for ctx, value, unit, decimals in self.all_facts[concept]:
            if ctx == context_id:
                return FactMatch(
                    found=True,
                    context_id=ctx,
                    value=value,
                    unit=unit,
                    decimals=decimals,
                    match_type=MATCH_TYPE_EXACT,
                )

        return FactMatch()

    def find_compatible(
        self,
        concept: str,
        parent_context: str,
        parent_unit: Optional[str] = None,
        allow_dimensional_child: bool = False
    ) -> FactMatch:
        """
        Find a fact compatible with parent context.

        First tries exact match (same context), then fallback (compatible period).

        Args:
            concept: Normalized concept name
            parent_context: Parent's context_id
            parent_unit: Parent's unit (for u-equal check)
            allow_dimensional_child: Whether to allow children from dimensional contexts
                                     when parent is non-dimensional

        Returns:
            FactMatch with result
        """
        if concept not in self.all_facts:
            return FactMatch()

        parent_is_dimensional = self.classifier.is_dimensional(parent_context)

        # First pass: exact context match
        for ctx, value, unit, decimals in self.all_facts[concept]:
            if ctx == parent_context:
                # Check unit compatibility
                if parent_unit and unit and parent_unit != unit:
                    continue

                return FactMatch(
                    found=True,
                    context_id=ctx,
                    value=value,
                    unit=unit,
                    decimals=decimals,
                    match_type=MATCH_TYPE_EXACT,
                )

        # Second pass: compatible context fallback
        for ctx, value, unit, decimals in self.all_facts[concept]:
            # Skip if already checked (exact match)
            if ctx == parent_context:
                continue

            # Check dimensional compatibility
            child_is_dimensional = self.classifier.is_dimensional(ctx)

            # Rule: If parent is non-dimensional, skip dimensional children
            # unless explicitly allowed
            if not parent_is_dimensional and child_is_dimensional and not allow_dimensional_child:
                self.logger.debug(
                    f"Skipping '{concept}' from dimensional context {ctx} "
                    f"(parent is non-dimensional)"
                )
                continue

            # Rule: If parent is dimensional, only accept children from same
            # dimensional context (strict C-Equal required)
            if parent_is_dimensional:
                # For dimensional parents, we don't do fallback
                # This is enforced at a higher level, but double-check here
                continue

            # Check period compatibility
            if not self.matcher.is_period_compatible(parent_context, ctx):
                self.logger.debug(
                    f"Skipping '{concept}' from {ctx} - period incompatible with {parent_context}"
                )
                continue

            # Check unit compatibility
            if parent_unit and unit and parent_unit != unit:
                continue

            # Found compatible match
            return FactMatch(
                found=True,
                context_id=ctx,
                value=value,
                unit=unit,
                decimals=decimals,
                match_type=MATCH_TYPE_FALLBACK,
            )

        return FactMatch()

    def find_all_in_period(
        self,
        concept: str,
        period_key: str
    ) -> list[FactMatch]:
        """
        Find all instances of a concept in a specific period.

        Useful for consistency checking across statements.

        Args:
            concept: Normalized concept name
            period_key: Period key to match

        Returns:
            List of FactMatch for all matching instances
        """
        matches = []

        if concept not in self.all_facts:
            return matches

        for ctx, value, unit, decimals in self.all_facts[concept]:
            ctx_period = self.matcher.period_extractor.extract(ctx)

            if ctx_period.period_key == period_key:
                matches.append(FactMatch(
                    found=True,
                    context_id=ctx,
                    value=value,
                    unit=unit,
                    decimals=decimals,
                    match_type=MATCH_TYPE_EXACT if ctx_period.period_key == period_key else MATCH_TYPE_PERIOD_MATCH,
                ))

        return matches


__all__ = [
    'FactMatch',
    'FactFinder',
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',
]
