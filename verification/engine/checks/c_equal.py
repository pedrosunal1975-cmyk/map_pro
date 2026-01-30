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

This module is AGNOSTIC and can be used by any verification component.
It does NOT contain any hardcoded formulas or market-specific logic.

USAGE:
    from .c_equal import CEqual, FactGroups

    # Create c-equal grouper
    c_equal = CEqual()

    # Group facts by context (strict c-equal)
    groups = c_equal.group_facts(statements)

    # Get facts for a specific context
    context = groups.get_context("c-4")

    # Check if facts are c-equal
    if c_equal.are_c_equal(fact1, fact2):
        # Can compare these facts
        pass
"""

import logging

from ...loaders.mapped_reader import MappedStatements, StatementFact
from .duplicate_detection import FactEntry, DuplicateInfo, DuplicateType
from .context_grouping import ContextGroup, FactGroups
from .value_parsing import ValueParser
from .concept_normalization import ConceptNormalizer


class CEqual:
    """
    C-Equal verification engine.

    Groups facts by context_id and provides verification within contexts.
    Ensures calculations only compare facts that are c-equal.

    This class is AGNOSTIC - it contains no hardcoded formulas or
    market-specific logic. All calculation rules must come from
    company XBRL files.
    """

    def __init__(self):
        self.logger = logging.getLogger('process.c_equal')
        self._value_parser = ValueParser()
        self._concept_normalizer = ConceptNormalizer()

    def normalize_concept(self, concept: str) -> str:
        """
        Normalize a concept name for comparison.

        Delegates to ConceptNormalizer for consistent normalization.

        Args:
            concept: Original concept name

        Returns:
            Normalized concept name
        """
        return self._concept_normalizer.normalize_concept(concept)

    def parse_value(self, raw_value) -> float:
        """
        Parse a raw value to float.

        Delegates to ValueParser for consistent parsing.

        Args:
            raw_value: Raw value from statement

        Returns:
            Float value or None
        """
        return self._value_parser.parse_value(raw_value)

    def is_nil_value(self, raw_value) -> bool:
        """
        Check if a value represents nil/zero.

        Delegates to ValueParser for consistent nil detection.

        Args:
            raw_value: Raw value to check

        Returns:
            True if value is nil/zero representation
        """
        return self._value_parser.is_nil_value(raw_value)

    def group_facts(
        self,
        statements: MappedStatements,
        include_nil: bool = False
    ) -> FactGroups:
        """
        Group all facts by their context_id (strict c-equal).

        C-Equal Principle: Facts are grouped by context_id to ensure only
        c-equal facts (same entity, period, dimensions) are compared.

        Args:
            statements: MappedStatements object
            include_nil: Whether to include nil-valued facts (default False)

        Returns:
            FactGroups containing facts organized by context_id
        """
        groups = FactGroups()
        skipped_abstract = 0
        skipped_nil = 0
        skipped_no_context = 0
        added_facts = 0

        for statement in statements.statements:
            for fact in statement.facts:
                # Skip abstract facts (they have no value)
                if fact.is_abstract:
                    skipped_abstract += 1
                    continue

                # Skip facts without context_id (cannot determine c-equal)
                if not fact.context_id:
                    skipped_no_context += 1
                    continue

                # Check for nil
                is_nil = self.is_nil_value(fact.value)
                if is_nil and not include_nil:
                    skipped_nil += 1
                    continue

                # Parse value
                value = self.parse_value(fact.value)
                if value is None:
                    skipped_nil += 1
                    continue

                # Create fact entry with full metadata
                entry = FactEntry(
                    concept=self.normalize_concept(fact.concept),
                    original_concept=fact.concept,
                    value=value,
                    unit=fact.unit,
                    decimals=fact.decimals,
                    context_id=fact.context_id,
                    is_nil=is_nil,
                )

                groups.add_fact(entry)
                added_facts += 1

        self.logger.info(
            f"C-Equal grouping: {added_facts} facts in {groups.context_count} contexts"
        )

        # Log filter statistics at INFO level for visibility
        self.logger.info(
            f"C-Equal filtering: {skipped_abstract} abstract, {skipped_nil} nil, "
            f"{skipped_no_context} no context_id"
        )

        if skipped_abstract > 0:
            self.logger.debug(f"Skipped {skipped_abstract} abstract facts")
        if skipped_nil > 0:
            self.logger.debug(f"Skipped {skipped_nil} nil/unparseable facts")
        if skipped_no_context > 0:
            self.logger.debug(f"Skipped {skipped_no_context} facts without context_id")

        # Report inconsistent duplicates
        inconsistent = groups.find_inconsistent_duplicates()
        if inconsistent:
            self.logger.warning(
                f"Found {len(inconsistent)} concepts with inconsistent duplicates"
            )

        return groups

    def are_c_equal(self, fact1: StatementFact, fact2: StatementFact) -> bool:
        """
        Check if two facts are c-equal (same context).

        Args:
            fact1: First fact
            fact2: Second fact

        Returns:
            True if facts share the same context_id
        """
        if not fact1.context_id or not fact2.context_id:
            return False
        return fact1.context_id == fact2.context_id

    def are_u_equal(self, fact1: StatementFact, fact2: StatementFact) -> bool:
        """
        Check if two facts are u-equal (same unit).

        Args:
            fact1: First fact
            fact2: Second fact

        Returns:
            True if facts share the same unit
        """
        # If either has no unit, consider them u-equal (non-monetary)
        if not fact1.unit or not fact2.unit:
            return True
        return fact1.unit == fact2.unit


__all__ = [
    'CEqual',
    'FactGroups',
    'ContextGroup',
    'FactEntry',
    'DuplicateInfo',
    'DuplicateType',
]
