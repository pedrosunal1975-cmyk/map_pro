# Path: verification/engine/checks/c_equal.py
"""
C-Equal (Context-Equal) Module for XBRL Verification

Per XBRL 2.1 specification section 5.2.5.2, calculation relationships
only apply between facts that are "c-equal" (context-equal).

C-EQUAL DEFINITION:
Two facts are c-equal when they share the same XBRL context, meaning:
- Same period (instant date or duration)
- Same dimensions (all dimensional qualifiers)
- Same entity

In practice, this is encoded in the context_id (e.g., "c-4", "c-5").
Facts with the same context_id are c-equal and CAN be compared.
Facts with different context_ids are NOT c-equal and MUST NOT be compared.

USAGE:
    from .c_equal import CEqual, FactGroup

    # Create c-equal grouper
    c_equal = CEqual()

    # Group facts by context
    groups = c_equal.group_facts(statements)

    # Get facts for a specific context
    facts = groups.get_context("c-4")

    # Verify a calculation within a context
    result = c_equal.verify_in_context("c-4", parent, children, groups)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Iterator

from ...loaders.mapped_reader import MappedStatements, StatementFact


@dataclass
class FactValue:
    """
    A normalized fact value for calculation verification.

    Attributes:
        concept: Normalized concept name (lowercase, local name only)
        value: Numeric value
        original_concept: Original concept name as reported
        context_id: XBRL context identifier
    """
    concept: str
    value: float
    original_concept: str
    context_id: str


@dataclass
class ContextGroup:
    """
    Facts grouped by context_id.

    All facts in a group are c-equal and can be compared in calculations.

    Attributes:
        context_id: XBRL context identifier (e.g., "c-4")
        facts: Dictionary mapping normalized concept -> value
        original_names: Dictionary mapping normalized concept -> original name
    """
    context_id: str
    facts: dict[str, float] = field(default_factory=dict)
    original_names: dict[str, str] = field(default_factory=dict)

    def get(self, concept: str) -> Optional[float]:
        """Get value for a normalized concept."""
        return self.facts.get(concept)

    def has(self, concept: str) -> bool:
        """Check if concept exists in this context."""
        return concept in self.facts

    def __len__(self) -> int:
        return len(self.facts)


class FactGroups:
    """
    Container for facts grouped by context_id.

    Provides access to facts organized by their XBRL context.
    """

    def __init__(self):
        self._groups: dict[str, ContextGroup] = {}
        self.logger = logging.getLogger('process.c_equal')

    def add_fact(
        self,
        context_id: str,
        concept: str,
        value: float,
        original_concept: str
    ) -> None:
        """
        Add a fact to the appropriate context group.

        Args:
            context_id: XBRL context identifier
            concept: Normalized concept name
            value: Numeric value
            original_concept: Original concept name
        """
        if context_id not in self._groups:
            self._groups[context_id] = ContextGroup(context_id=context_id)

        group = self._groups[context_id]

        # Store fact (first value wins for each concept in a context)
        if concept not in group.facts:
            group.facts[concept] = value
            group.original_names[concept] = original_concept

    def get_context(self, context_id: str) -> Optional[ContextGroup]:
        """Get the fact group for a specific context."""
        return self._groups.get(context_id)

    def get_contexts(self) -> list[str]:
        """Get all context IDs."""
        return list(self._groups.keys())

    def get_contexts_with_concept(self, concept: str) -> list[str]:
        """Get all context IDs that contain a specific concept."""
        return [
            ctx_id for ctx_id, group in self._groups.items()
            if concept in group.facts
        ]

    def iter_groups(self) -> Iterator[ContextGroup]:
        """Iterate over all context groups."""
        yield from self._groups.values()

    @property
    def total_facts(self) -> int:
        """Total number of facts across all contexts."""
        return sum(len(g) for g in self._groups.values())

    @property
    def context_count(self) -> int:
        """Number of unique contexts."""
        return len(self._groups)

    def __len__(self) -> int:
        return len(self._groups)


class CEqual:
    """
    C-Equal verification engine.

    Groups facts by context_id and provides verification within contexts.
    Ensures calculations only compare facts that are c-equal.
    """

    # Value representations that mean zero/nil
    NIL_VALUES = {'', '—', '–', '-', 'nil', 'N/A', 'n/a', 'None', 'none'}

    def __init__(self):
        self.logger = logging.getLogger('process.c_equal')

    @staticmethod
    def normalize_concept(concept: str) -> str:
        """
        Normalize a concept name to its local name (lowercase).

        Extracts the local name after any namespace separator
        (colon, underscore, or dash) and lowercases it.

        Args:
            concept: Original concept name (e.g., "us-gaap:Assets")

        Returns:
            Normalized local name (e.g., "assets")
        """
        if not concept:
            return ''

        # Find the last separator and take everything after
        separators = [':', '_', '-']
        local_name = concept

        for sep in separators:
            if sep in local_name:
                local_name = local_name.rsplit(sep, 1)[-1]

        return local_name.lower()

    def parse_value(self, raw_value) -> Optional[float]:
        """
        Parse a raw value to float.

        Handles financial statement conventions:
        - Em-dash, en-dash, hyphen mean zero
        - Removes commas and dollar signs
        - Returns None if unparseable

        Args:
            raw_value: Raw value from statement

        Returns:
            Float value or None
        """
        if raw_value is None:
            return None

        raw_str = str(raw_value).strip()

        if raw_str in self.NIL_VALUES:
            return 0.0

        try:
            cleaned = raw_str.replace(',', '').replace('$', '')
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def group_facts(
        self,
        statements: MappedStatements,
        main_only: bool = True,
        group_by: str = 'period'
    ) -> FactGroups:
        """
        Group all facts by their context or period.

        Args:
            statements: MappedStatements object
            main_only: If True, only use facts from main statements
            group_by: How to group facts:
                - 'context_id': Strict c-equal grouping by XBRL context_id
                - 'period': Group by period_end (more lenient, old behavior)

        Returns:
            FactGroups containing facts organized by group key
        """
        groups = FactGroups()
        skipped_statements = 0
        skipped_facts = 0
        added_facts = 0

        for statement in statements.statements:
            # Filter to main statements if requested
            if main_only and not statement.is_main_statement:
                skipped_statements += 1
                continue

            for fact in statement.facts:
                # Skip abstract facts
                if fact.is_abstract:
                    continue

                # Skip facts without values
                if fact.value is None:
                    continue

                # Parse value
                value = self.parse_value(fact.value)
                if value is None:
                    skipped_facts += 1
                    continue

                # Determine group key based on group_by parameter
                if group_by == 'context_id':
                    # Strict c-equal: use context_id (includes period + dimensions)
                    group_key = fact.context_id or fact.period_end or 'unknown'
                else:
                    # Period-based: use period_end (old behavior, more lenient)
                    group_key = fact.period_end or 'unknown'

                # Normalize concept name
                concept = self.normalize_concept(fact.concept)

                # Add to group
                groups.add_fact(group_key, concept, value, fact.concept)
                added_facts += 1

        self.logger.info(
            f"C-Equal grouping (by {group_by}): {added_facts} facts in {groups.context_count} groups"
        )

        if skipped_statements > 0:
            self.logger.debug(f"Skipped {skipped_statements} non-main statements")

        if skipped_facts > 0:
            self.logger.debug(f"Skipped {skipped_facts} unparseable facts")

        return groups

    def verify_calculation(
        self,
        context_group: ContextGroup,
        parent_concept: str,
        children: list[tuple[str, float]],
        tolerance: float = 0.01,
        rounding_tolerance: float = 1.0
    ) -> dict:
        """
        Verify a calculation within a single context.

        All facts used are from the same context_id, ensuring c-equal compliance.

        Args:
            context_group: ContextGroup containing facts for this context
            parent_concept: Normalized parent concept name
            children: List of (child_concept, weight) tuples
            tolerance: Percentage tolerance for large values
            rounding_tolerance: Absolute tolerance for small values

        Returns:
            Dictionary with verification result:
            {
                'passed': bool,
                'parent_value': float or None,
                'expected_value': float,
                'children_found': int,
                'children_total': int,
                'missing_children': list[str],
                'difference': float,
                'message': str
            }
        """
        result = {
            'passed': True,
            'parent_value': None,
            'expected_value': 0.0,
            'children_found': 0,
            'children_total': len(children),
            'missing_children': [],
            'difference': 0.0,
            'message': ''
        }

        # Get parent value
        parent_value = context_group.get(parent_concept)
        result['parent_value'] = parent_value

        if parent_value is None:
            result['message'] = f"Parent {parent_concept} not found in context {context_group.context_id}"
            return result

        # Calculate expected from children
        expected = 0.0
        for child_concept, weight in children:
            child_value = context_group.get(child_concept)

            if child_value is not None:
                expected += child_value * weight
                result['children_found'] += 1
            else:
                result['missing_children'].append(child_concept)

        result['expected_value'] = expected

        # Can't verify if no children found
        if result['children_found'] == 0:
            result['message'] = f"No children found for {parent_concept}"
            return result

        # Calculate difference
        difference = abs(expected - parent_value)
        result['difference'] = difference

        # Check tolerance
        if parent_value == 0 and expected == 0:
            result['passed'] = True
        elif abs(parent_value) < 1000:
            # Small values - use absolute tolerance
            result['passed'] = difference <= rounding_tolerance
        else:
            # Large values - use percentage tolerance
            pct_diff = difference / abs(parent_value) if parent_value != 0 else float('inf')
            result['passed'] = pct_diff <= tolerance

        # Build message
        if result['passed']:
            result['message'] = (
                f"{parent_concept}: expected={expected:,.0f}, "
                f"actual={parent_value:,.0f}, diff={difference:,.0f} OK"
            )
        else:
            result['message'] = (
                f"{parent_concept}: expected={expected:,.0f}, "
                f"actual={parent_value:,.0f}, diff={difference:,.0f} MISMATCH"
            )

        return result


__all__ = [
    'CEqual',
    'FactGroups',
    'ContextGroup',
    'FactValue',
]
