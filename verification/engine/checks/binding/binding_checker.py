# Path: verification/engine/checks/binding/binding_checker.py
"""
Calculation Binding Checker for XBRL Verification

Determines whether a calculation should "bind" (be verified) based on
XBRL 2.1 and Calculations 1.1 specification rules.

BINDING RULES (from XBRL spec + completeness enhancement):
A calculation binds (is checked) ONLY when:
1. The summation item (parent/total) EXISTS in the context
2. At least one contributing item (child) EXISTS in the same context
3. NO inconsistent duplicate facts exist for parent or children
4. All items are c-equal (same context_id)
5. All items are u-equal (same unit)
6. COMPLETENESS: At least CALCULATION_COMPLETENESS_THRESHOLD % of children found
   (If too many children are missing, the sum cannot meaningfully match the total)

If ANY of these conditions is not met, the calculation is SKIPPED (not failed).
Skipping is different from failing - it means the check cannot be performed.

DIMENSIONAL FALLBACK:
When facts are reported with dimensional qualifiers (e.g., ClassOfStockAxis),
they appear in different context_ids than the parent total. To handle this:
1. First try strict C-Equal (same context_id)
2. If children are missing, try dimensional fallback:
   - Search for children in ANY context
   - Use found values if they match the calculation pattern

This module is AGNOSTIC - it does NOT contain any hardcoded formulas.
All calculation rules must come from company XBRL files.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from ..c_equal.c_equal import ContextGroup, DuplicateType
from ..core.constants import CALCULATION_COMPLETENESS_THRESHOLD
from ..context.fact_rules import ContextClassifier, ContextMatcher, FactFinder, FactMatch


class BindingStatus(Enum):
    """Status of calculation binding attempt."""
    BINDS = "binds"                           # Can verify this calculation
    SKIP_NO_PARENT = "skip_no_parent"         # Parent not found in context
    SKIP_NO_CHILDREN = "skip_no_children"     # No children found in context
    SKIP_INCOMPLETE = "skip_incomplete"       # Too few children found (below threshold)
    SKIP_INCONSISTENT_PARENT = "skip_inconsistent_parent"  # Parent has inconsistent duplicates
    SKIP_INCONSISTENT_CHILD = "skip_inconsistent_child"    # A child has inconsistent duplicates
    SKIP_UNIT_MISMATCH = "skip_unit_mismatch"  # Units don't match (not u-equal)


@dataclass
class BindingResult:
    """
    Result of checking if a calculation binds.

    Attributes:
        binds: Whether the calculation binds (can be verified)
        status: Detailed status explaining why it binds or doesn't
        parent_value: Parent value if found
        parent_unit: Parent unit if found
        parent_decimals: Parent decimals if found
        children_found: List of (concept, value, weight, unit, decimals) tuples
        children_missing: List of concept names not found in context
        message: Human-readable explanation
    """
    binds: bool
    status: BindingStatus
    parent_value: Optional[float] = None
    parent_unit: Optional[str] = None
    parent_decimals: Optional[int] = None
    children_found: list = field(default_factory=list)
    children_missing: list = field(default_factory=list)
    message: str = ""


class BindingChecker:
    """
    Checks if calculations should bind per XBRL specification.

    A calculation binds only when all required conditions are met.
    If a calculation doesn't bind, it is SKIPPED (not failed).

    This is a critical distinction:
    - SKIP: Cannot verify because data is incomplete or invalid
    - PASS: Verified successfully, values match
    - FAIL: Verified and found inconsistency

    Example:
        checker = BindingChecker()

        # Check if Assets = Liabilities + Equity binds in context c-1
        result = checker.check_binding(
            context_group=context,
            parent_concept='assets',
            children=[('liabilities', 1.0), ('stockholdersequity', 1.0)]
        )

        if result.binds:
            # Proceed with verification
            pass
        else:
            # Skip this calculation
            print(f"Skipped: {result.message}")
    """

    def __init__(self):
        self.logger = logging.getLogger('process.binding_checker')
        self.classifier = ContextClassifier()
        self.matcher = ContextMatcher()

    def check_binding(
        self,
        context_group: ContextGroup,
        parent_concept: str,
        children: list[tuple[str, float]]
    ) -> BindingResult:
        """
        Check if a calculation binds in a given context.

        Args:
            context_group: ContextGroup with facts for this context
            parent_concept: Normalized parent concept name
            children: List of (child_concept, weight) tuples from calculation linkbase

        Returns:
            BindingResult indicating whether calculation binds and why
        """
        # Rule 1: Parent must exist
        parent_info = context_group.get_duplicate_info(parent_concept)
        if not parent_info or not parent_info.entries:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_NO_PARENT,
                message=f"Parent '{parent_concept}' not found in context {context_group.context_id}",
            )

        # Rule 3: Parent must not have inconsistent duplicates
        if parent_info.duplicate_type == DuplicateType.INCONSISTENT:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_INCONSISTENT_PARENT,
                parent_value=None,
                message=f"Parent '{parent_concept}' has inconsistent duplicates in context {context_group.context_id}",
            )

        parent_value = parent_info.selected_value
        parent_unit = parent_info.entries[0].unit if parent_info.entries else None
        parent_decimals = parent_info.selected_decimals

        # Find children
        children_found = []
        children_missing = []

        # DEBUG: Log available concepts in this context for troubleshooting
        if self.logger.isEnabledFor(logging.DEBUG):
            available_concepts = list(context_group.facts.keys())
            self.logger.debug(
                f"Binding check for '{parent_concept}' in context {context_group.context_id}: "
                f"{len(available_concepts)} concepts available"
            )

        for child_concept, weight in children:
            child_info = context_group.get_duplicate_info(child_concept)

            if not child_info or not child_info.entries:
                children_missing.append(child_concept)
                continue

            # Rule 3: Child must not have inconsistent duplicates
            if child_info.duplicate_type == DuplicateType.INCONSISTENT:
                return BindingResult(
                    binds=False,
                    status=BindingStatus.SKIP_INCONSISTENT_CHILD,
                    parent_value=parent_value,
                    parent_unit=parent_unit,
                    parent_decimals=parent_decimals,
                    message=f"Child '{child_concept}' has inconsistent duplicates in context {context_group.context_id}",
                )

            child_value = child_info.selected_value
            child_unit = child_info.entries[0].unit if child_info.entries else None
            child_decimals = child_info.selected_decimals

            # Rule 5: Check u-equal (same unit)
            if parent_unit and child_unit and parent_unit != child_unit:
                return BindingResult(
                    binds=False,
                    status=BindingStatus.SKIP_UNIT_MISMATCH,
                    parent_value=parent_value,
                    parent_unit=parent_unit,
                    parent_decimals=parent_decimals,
                    message=f"Unit mismatch: parent unit '{parent_unit}' != child '{child_concept}' unit '{child_unit}'",
                )

            children_found.append({
                'concept': child_concept,
                'original_concept': child_info.entries[0].original_concept if child_info.entries else child_concept,
                'value': child_value,
                'weight': weight,
                'unit': child_unit,
                'decimals': child_decimals,
            })

        # DEBUG: Log found vs missing children for troubleshooting
        if self.logger.isEnabledFor(logging.DEBUG) and children_missing:
            self.logger.debug(
                f"  Children for '{parent_concept}': found={len(children_found)}, missing={len(children_missing)}"
            )
            for missing in children_missing[:5]:  # Limit to first 5
                self.logger.debug(f"    MISSING: {missing}")

        # Rule 2: At least one child must exist
        if not children_found:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_NO_CHILDREN,
                parent_value=parent_value,
                parent_unit=parent_unit,
                parent_decimals=parent_decimals,
                children_missing=children_missing,
                message=f"No children found for '{parent_concept}' in context {context_group.context_id}",
            )

        # Rule 6: Completeness check - skip if too many children missing
        # If we have data for fewer than threshold % of children, verification
        # would be meaningless (incomplete sums cannot match expected totals)
        total_children = len(children)
        found_count = len(children_found)
        completeness = found_count / total_children if total_children > 0 else 0.0

        if completeness < CALCULATION_COMPLETENESS_THRESHOLD:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_INCOMPLETE,
                parent_value=parent_value,
                parent_unit=parent_unit,
                parent_decimals=parent_decimals,
                children_found=children_found,
                children_missing=children_missing,
                message=(
                    f"Incomplete data for '{parent_concept}': "
                    f"{found_count}/{total_children} children found ({completeness:.0%}), "
                    f"threshold is {CALCULATION_COMPLETENESS_THRESHOLD:.0%}"
                ),
            )

        # All rules passed - calculation binds
        return BindingResult(
            binds=True,
            status=BindingStatus.BINDS,
            parent_value=parent_value,
            parent_unit=parent_unit,
            parent_decimals=parent_decimals,
            children_found=children_found,
            children_missing=children_missing,
            message=f"Calculation binds: {len(children_found)} children found, {len(children_missing)} missing",
        )

    def should_verify(self, binding_result: BindingResult) -> bool:
        """
        Simple helper to check if verification should proceed.

        Args:
            binding_result: Result from check_binding

        Returns:
            True if calculation binds and should be verified
        """
        return binding_result.binds

    def check_binding_with_fallback(
        self,
        context_group: ContextGroup,
        parent_concept: str,
        children: list[tuple[str, float]],
        all_facts: dict[str, list[tuple[str, float, Optional[str], Optional[int]]]] = None
    ) -> BindingResult:
        """
        Check binding with dimensional fallback for missing children.

        When children are not found in the same context as the parent,
        this method searches for them in any available context.

        IMPORTANT: Dimensional fallback is ONLY used when the parent is in
        a non-dimensional (default) context. If the parent is in a dimensional
        context (e.g., StatementEquityComponentsAxis=CommonStockMember), then
        children MUST be in the SAME dimensional context or the calculation
        is skipped. This prevents mixing values from different dimensional slices.

        Args:
            context_group: ContextGroup with facts for the parent context
            parent_concept: Normalized parent concept name
            children: List of (child_concept, weight) tuples from calculation linkbase
            all_facts: Dict of concept -> [(context_id, value, unit, decimals)] for fallback lookups

        Returns:
            BindingResult with dimensional fallback applied (only for non-dimensional parent)
        """
        # First try strict C-Equal binding
        strict_result = self.check_binding(context_group, parent_concept, children)

        # If we don't have fallback data, return strict result as-is
        if not all_facts:
            return strict_result

        # Check if parent is in a dimensional context
        # Dimensional contexts contain axis/member identifiers
        parent_context = context_group.context_id
        is_dimensional_context = self.classifier.is_dimensional(parent_context)

        if is_dimensional_context:
            # Parent is in dimensional context - DO NOT use fallback
            # Children must be in the SAME dimensional context
            # If not found, skip the calculation (don't mix dimensional slices)
            self.logger.debug(
                f"Parent '{parent_concept}' is in dimensional context '{parent_context}' - "
                f"fallback disabled to prevent cross-dimensional mixing"
            )
            return strict_result

        # Parent is in non-dimensional context - fallback is allowed

        # If no children were found at all and fallback is available, try it
        if strict_result.status == BindingStatus.SKIP_NO_CHILDREN:
            return self._apply_dimensional_fallback(
                strict_result, parent_concept, children, all_facts, context_group.context_id
            )

        # If some children are missing (even if calculation binds), try to fill them
        # This handles dimensional contexts where some facts are in different contexts
        if strict_result.children_missing:
            return self._fill_missing_with_fallback(
                strict_result, children, all_facts, context_group.context_id
            )

        return strict_result

    def _apply_dimensional_fallback(
        self,
        base_result: BindingResult,
        parent_concept: str,
        children: list[tuple[str, float]],
        all_facts: dict,
        parent_context: str
    ) -> BindingResult:
        """
        Apply dimensional fallback when no children found in same context.

        Uses FactFinder from fact_rules.py for compatible context lookups.

        IMPORTANT: When parent is in a non-dimensional (default) context,
        children from dimensional contexts should NOT be used. This prevents
        mixing consolidated totals with dimensional breakdowns (e.g., VIE disclosures).
        """
        children_found = []
        children_missing = []

        # Create FactFinder for this lookup
        finder = FactFinder(all_facts)
        parent_is_dimensional = self.classifier.is_dimensional(parent_context)

        # Log what we're looking for vs what's available
        self.logger.debug(
            f"Fallback for '{parent_concept}' in {parent_context} "
            f"(dimensional={parent_is_dimensional}): "
            f"looking for {len(children)} children in {len(all_facts)} available concepts"
        )

        for child_concept, weight in children:
            # Use FactFinder for compatible lookup
            match = finder.find_compatible(
                concept=child_concept,
                parent_context=parent_context,
                parent_unit=base_result.parent_unit,
                allow_dimensional_child=False  # Never allow dimensional children for non-dimensional parent
            )

            if match.found:
                children_found.append({
                    'concept': child_concept,
                    'original_concept': child_concept,
                    'value': match.value,
                    'weight': weight,
                    'unit': match.unit,
                    'decimals': match.decimals,
                    'source_context': match.context_id,  # Track that this came from fallback
                })
                self.logger.debug(
                    f"  Found '{child_concept}' via {match.match_type} in {match.context_id}"
                )
            else:
                children_missing.append(child_concept)
                self.logger.debug(f"  '{child_concept}' has no compatible instances")

        if not children_found:
            return base_result  # No improvement from fallback

        # Completeness check - skip if too many children missing
        total_children = len(children)
        found_count = len(children_found)
        completeness = found_count / total_children if total_children > 0 else 0.0

        if completeness < CALCULATION_COMPLETENESS_THRESHOLD:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_INCOMPLETE,
                parent_value=base_result.parent_value,
                parent_unit=base_result.parent_unit,
                parent_decimals=base_result.parent_decimals,
                children_found=children_found,
                children_missing=children_missing,
                message=(
                    f"Incomplete data (fallback): "
                    f"{found_count}/{total_children} children found ({completeness:.0%}), "
                    f"threshold is {CALCULATION_COMPLETENESS_THRESHOLD:.0%}"
                ),
            )

        return BindingResult(
            binds=True,
            status=BindingStatus.BINDS,
            parent_value=base_result.parent_value,
            parent_unit=base_result.parent_unit,
            parent_decimals=base_result.parent_decimals,
            children_found=children_found,
            children_missing=children_missing,
            message=f"Dimensional fallback: {len(children_found)} children found via cross-context lookup",
        )

    def _fill_missing_with_fallback(
        self,
        base_result: BindingResult,
        children: list[tuple[str, float]],
        all_facts: dict,
        parent_context: str
    ) -> BindingResult:
        """
        Fill in missing children using dimensional fallback.

        Uses FactFinder from fact_rules.py for compatible context lookups.

        IMPORTANT: When parent is in a non-dimensional (default) context,
        children from dimensional contexts should NOT be used. This prevents
        mixing consolidated totals with dimensional breakdowns (e.g., VIE disclosures).
        """
        children_found = list(base_result.children_found)  # Copy existing
        children_missing = []
        fallback_count = 0

        # Create FactFinder for this lookup
        finder = FactFinder(all_facts)

        for child_concept, weight in children:
            # Check if already found
            already_found = any(c['concept'] == child_concept for c in children_found)
            if already_found:
                continue

            # Use FactFinder for compatible lookup
            match = finder.find_compatible(
                concept=child_concept,
                parent_context=parent_context,
                parent_unit=base_result.parent_unit,
                allow_dimensional_child=False
            )

            if match.found:
                children_found.append({
                    'concept': child_concept,
                    'original_concept': child_concept,
                    'value': match.value,
                    'weight': weight,
                    'unit': match.unit,
                    'decimals': match.decimals,
                    'source_context': match.context_id,
                })
                fallback_count += 1
            else:
                children_missing.append(child_concept)

        # Completeness check - skip if too many children missing
        total_children = len(children)
        found_count = len(children_found)
        completeness = found_count / total_children if total_children > 0 else 0.0

        if completeness < CALCULATION_COMPLETENESS_THRESHOLD:
            return BindingResult(
                binds=False,
                status=BindingStatus.SKIP_INCOMPLETE,
                parent_value=base_result.parent_value,
                parent_unit=base_result.parent_unit,
                parent_decimals=base_result.parent_decimals,
                children_found=children_found,
                children_missing=children_missing,
                message=(
                    f"Incomplete data (fill): "
                    f"{found_count}/{total_children} children found ({completeness:.0%}), "
                    f"threshold is {CALCULATION_COMPLETENESS_THRESHOLD:.0%}"
                ),
            )

        return BindingResult(
            binds=True,
            status=BindingStatus.BINDS,
            parent_value=base_result.parent_value,
            parent_unit=base_result.parent_unit,
            parent_decimals=base_result.parent_decimals,
            children_found=children_found,
            children_missing=children_missing,
            message=f"Calculation binds: {len(children_found)} children ({fallback_count} via fallback), {len(children_missing)} missing",
        )


__all__ = ['BindingChecker', 'BindingResult', 'BindingStatus']
