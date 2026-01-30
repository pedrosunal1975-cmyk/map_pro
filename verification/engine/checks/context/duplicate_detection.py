# Path: verification/engine/checks/context/duplicate_detection.py
"""
Duplicate Fact Detection for XBRL Verification

Handles detection and classification of duplicate facts per XBRL Duplicates Guidance.

DUPLICATE TYPES:
- COMPLETE: Same value, same precision - ignore, use one
- CONSISTENT: Same value (within tolerance), different precision - use most precise
- INCONSISTENT: Different values - error, skip calculation

This module uses DecimalTolerance for proper XBRL-compliant value comparison.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from ..core.decimal_tolerance import DecimalTolerance


# Configuration constants
DUPLICATE_PERCENTAGE_TOLERANCE = 0.02  # 2% tolerance for duplicate detection fallback


class DuplicateType(Enum):
    """Types of duplicate facts per XBRL Duplicates Guidance."""
    COMPLETE = "complete"           # Same value - ignore, use one
    CONSISTENT = "consistent"       # Same value, different precision - use most precise
    INCONSISTENT = "inconsistent"   # Different values - error, skip calculation


@dataclass
class FactEntry:
    """
    A fact entry with full metadata for verification.

    Stores all information needed for c-equal, u-equal, and
    decimal tolerance checks.

    Attributes:
        concept: Normalized concept name (lowercase, local name only)
        original_concept: Original concept name as reported
        value: Numeric value
        unit: Unit of measurement (e.g., 'USD', 'shares')
        decimals: Decimal precision (e.g., -6 means millions)
        context_id: XBRL context identifier
        is_nil: Whether fact is nil-valued
    """
    concept: str
    original_concept: str
    value: float
    unit: Optional[str] = None
    decimals: Optional[int] = None
    context_id: str = ""
    is_nil: bool = False


@dataclass
class DuplicateInfo:
    """
    Information about duplicate facts for a concept in a context.

    Attributes:
        concept: Normalized concept name
        entries: List of all FactEntry objects for this concept
        duplicate_type: Type of duplicate (complete/consistent/inconsistent)
        selected_value: The value to use (most precise for consistent)
        selected_decimals: The decimals of selected value
    """
    concept: str
    entries: list[FactEntry] = field(default_factory=list)
    duplicate_type: Optional[DuplicateType] = None
    selected_value: Optional[float] = None
    selected_decimals: Optional[int] = None

    def __post_init__(self):
        """Initialize decimal tolerance checker."""
        self._decimal_tolerance = DecimalTolerance()
        self.logger = logging.getLogger('process.duplicate_detection')

    def add_entry(self, entry: FactEntry) -> None:
        """Add a fact entry and update duplicate classification."""
        self.entries.append(entry)
        self._classify()

    def _normalize_decimals(self, decimals: any) -> Optional[int]:
        """
        Normalize decimals value to int.
        
        Handles string decimals (common in mapped statements).
        """
        if decimals is None:
            return None
        if isinstance(decimals, str):
            if decimals.upper() == 'INF':
                return None
            try:
                return int(decimals)
            except ValueError:
                return None
        return int(decimals)

    def _classify(self) -> None:
        """
        Classify the type of duplicate using decimal tolerance.

        Properly handles:
        1. String decimals (converts to int)
        2. Decimal tolerance comparison
        3. Percentage tolerance fallback (for edge cases)
        """
        if len(self.entries) <= 1:
            self.duplicate_type = None
            if self.entries:
                self.selected_value = self.entries[0].value
                self.selected_decimals = self._normalize_decimals(self.entries[0].decimals)
            return

        # Strategy 1: Check using decimal tolerance
        all_equal_decimals = self._are_all_values_equal_with_tolerance()
        
        # Strategy 2: Check using percentage tolerance (fallback)
        all_equal_percentage = self._are_values_within_percentage_tolerance(
            tolerance=DUPLICATE_PERCENTAGE_TOLERANCE
        )

        # Values are equal if EITHER strategy succeeds
        all_equal = all_equal_decimals or all_equal_percentage

        if all_equal:
            # All values are equal when rounded to appropriate precision
            decimals_list = [self._normalize_decimals(e.decimals) 
                           for e in self.entries if e.decimals is not None]
            
            if len(set(decimals_list)) <= 1:
                # Same precision = complete duplicate
                self.duplicate_type = DuplicateType.COMPLETE
            else:
                # Different precision = consistent duplicate
                self.duplicate_type = DuplicateType.CONSISTENT

            # Select the most precise value
            self._select_most_precise_value()
        else:
            # Different values even when considering tolerance = inconsistent duplicate
            self.duplicate_type = DuplicateType.INCONSISTENT
            self.selected_value = None  # Cannot select - error condition
            self.selected_decimals = None

    def _select_most_precise_value(self) -> None:
        """Select value with highest precision (largest decimals value)."""
        if not self.entries:
            return
        
        best_idx = 0
        best_decimals = self._normalize_decimals(self.entries[0].decimals)
        if best_decimals is None:
            best_decimals = float('-inf')
        
        for i in range(1, len(self.entries)):
            entry_decimals = self._normalize_decimals(self.entries[i].decimals)
            if entry_decimals is None:
                continue
            
            # Higher decimals = more precise (e.g., -3 is more precise than -6)
            if entry_decimals > best_decimals:
                best_decimals = entry_decimals
                best_idx = i
        
        self.selected_value = self.entries[best_idx].value
        self.selected_decimals = self._normalize_decimals(self.entries[best_idx].decimals)

    def _are_all_values_equal_with_tolerance(self) -> bool:
        """
        Check if all entries have equal values when considering decimal tolerance.

        Compares each pair of values using DecimalTolerance to respect
        their decimal precision attributes.

        Returns:
            True if all values are equal within tolerance
        """
        if len(self.entries) <= 1:
            return True

        # Use first entry as reference
        reference = self.entries[0]
        ref_decimals = self._normalize_decimals(reference.decimals)

        # Compare all other entries to reference
        for entry in self.entries[1:]:
            entry_decimals = self._normalize_decimals(entry.decimals)
            
            result = self._decimal_tolerance.compare(
                reference.value,
                entry.value,
                ref_decimals,
                entry_decimals
            )
            
            if not result.values_equal:
                # Found a value that doesn't match
                return False

        return True

    def _are_values_within_percentage_tolerance(self, tolerance: float) -> bool:
        """
        Check if all values are within percentage tolerance of each other.
        
        This is a fallback for cases where decimal tolerance doesn't work
        but values are clearly meant to be equal (e.g., minor rounding differences).
        
        Args:
            tolerance: Maximum percentage difference
            
        Returns:
            True if all values within tolerance
        """
        if len(self.entries) <= 1:
            return True
        
        values = [abs(e.value) for e in self.entries]
        max_val = max(values)
        min_val = min(values)
        
        if max_val == 0:
            # All zero
            return all(v == 0 for v in values)
        
        # Check percentage difference
        pct_diff = abs(max_val - min_val) / max_val
        return pct_diff <= tolerance


__all__ = [
    'DuplicateType',
    'FactEntry',
    'DuplicateInfo',
    'DUPLICATE_PERCENTAGE_TOLERANCE',
]
