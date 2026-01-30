# Path: verification/engine/checks/context/context_grouping.py
"""
Context-Based Fact Grouping for XBRL Verification

Handles grouping of facts by their XBRL context_id for c-equal verification.

Per XBRL 2.1 specification, facts are c-equal when they share the same context,
meaning same period, dimensions, and entity. This is encoded in the context_id.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Iterator

from .duplicate_detection import FactEntry, DuplicateInfo, DuplicateType


# Configuration constants
SAMPLE_CONCEPTS_LIMIT = 50  # Number of sample concepts to include in diagnostics
SAMPLE_CONTEXTS_LIMIT = 10  # Number of sample contexts to include in diagnostics


@dataclass
class ContextGroup:
    """
    Facts grouped by context_id.

    All facts in a group are c-equal and can be compared in calculations.
    Tracks units and decimals for u-equal and tolerance checks.

    Attributes:
        context_id: XBRL context identifier (e.g., "c-4")
        facts: Dictionary mapping normalized concept -> DuplicateInfo
    """
    context_id: str
    facts: dict[str, DuplicateInfo] = field(default_factory=dict)

    def add_fact(self, entry: FactEntry) -> None:
        """
        Add a fact entry to this context group.

        Handles duplicates by tracking all entries per concept.
        """
        if entry.concept not in self.facts:
            self.facts[entry.concept] = DuplicateInfo(concept=entry.concept)
        self.facts[entry.concept].add_entry(entry)

    def get_value(self, concept: str) -> Optional[float]:
        """
        Get the value for a concept.

        Returns None if:
        - Concept doesn't exist
        - Concept has inconsistent duplicates

        Returns the selected value for complete/consistent duplicates.
        """
        info = self.facts.get(concept)
        if not info:
            return None
        if info.duplicate_type == DuplicateType.INCONSISTENT:
            return None  # Cannot use inconsistent duplicates
        return info.selected_value

    def get_unit(self, concept: str) -> Optional[str]:
        """Get the unit for a concept."""
        info = self.facts.get(concept)
        if not info or not info.entries:
            return None
        return info.entries[0].unit

    def get_decimals(self, concept: str) -> Optional[int]:
        """Get the decimals for a concept (most precise if duplicates)."""
        info = self.facts.get(concept)
        if not info:
            return None
        return info.selected_decimals

    def get_duplicate_info(self, concept: str) -> Optional[DuplicateInfo]:
        """Get full duplicate information for a concept."""
        return self.facts.get(concept)

    def has_inconsistent_duplicates(self, concept: str) -> bool:
        """Check if concept has inconsistent duplicates."""
        info = self.facts.get(concept)
        if not info:
            return False
        return info.duplicate_type == DuplicateType.INCONSISTENT

    def get_original_name(self, concept: str) -> Optional[str]:
        """Get the original concept name."""
        info = self.facts.get(concept)
        if not info or not info.entries:
            return None
        return info.entries[0].original_concept

    def has(self, concept: str) -> bool:
        """Check if concept exists in this context."""
        return concept in self.facts

    def __len__(self) -> int:
        return len(self.facts)


class FactGroups:
    """
    Container for facts grouped by context_id.

    Provides access to facts organized by their XBRL context.
    This is the primary data structure for c-equal verification.
    """

    def __init__(self):
        self._groups: dict[str, ContextGroup] = {}
        self._inconsistent_duplicates: list[dict] = []
        self.logger = logging.getLogger('process.context_grouping')

    def add_fact(self, entry: FactEntry) -> None:
        """
        Add a fact entry to the appropriate context group.

        Args:
            entry: FactEntry with all fact metadata
        """
        context_id = entry.context_id
        if context_id not in self._groups:
            self._groups[context_id] = ContextGroup(context_id=context_id)

        self._groups[context_id].add_fact(entry)

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

    def find_inconsistent_duplicates(self) -> list[dict]:
        """
        Find all inconsistent duplicates across all contexts.

        Returns list of dicts with:
        - context_id
        - concept
        - values (list of conflicting values)
        """
        inconsistent = []
        for ctx_id, group in self._groups.items():
            for concept, info in group.facts.items():
                if info.duplicate_type == DuplicateType.INCONSISTENT:
                    inconsistent.append({
                        'context_id': ctx_id,
                        'concept': concept,
                        'original_concept': info.entries[0].original_concept if info.entries else concept,
                        'values': [e.value for e in info.entries],
                        'decimals': [e.decimals for e in info.entries],
                        'count': len(info.entries),
                    })
        return inconsistent

    @property
    def total_facts(self) -> int:
        """Total number of unique concept entries across all contexts."""
        return sum(len(g) for g in self._groups.values())

    @property
    def context_count(self) -> int:
        """Number of unique contexts."""
        return len(self._groups)

    def get_all_facts_by_concept(self) -> dict[str, list[tuple[str, float, Optional[str], Optional[int]]]]:
        """
        Get all facts indexed by concept for dimensional fallback lookups.

        Returns a dictionary where:
        - Key: normalized concept name
        - Value: list of (context_id, value, unit, decimals) tuples

        This is used by BindingChecker for cross-context lookups when
        facts are reported with dimensional qualifiers.
        """
        result = {}
        for ctx_id, group in self._groups.items():
            for concept, dup_info in group.facts.items():
                if concept not in result:
                    result[concept] = []
                # Use selected value (handles duplicates properly)
                if dup_info.selected_value is not None:
                    result[concept].append((
                        ctx_id,
                        dup_info.selected_value,
                        dup_info.entries[0].unit if dup_info.entries else None,
                        dup_info.selected_decimals
                    ))
        return result

    def get_diagnostic_summary(self) -> dict:
        """
        Get diagnostic summary of what facts are in the groups.

        Returns dict with:
        - total_contexts: number of contexts
        - total_concepts: number of unique concepts (normalized)
        - sample_concepts: sample concept names for inspection
        - contexts_sample: sample of context_id -> concept count
        """
        all_concepts = set()
        context_concept_counts = {}

        for ctx_id, group in self._groups.items():
            context_concept_counts[ctx_id] = len(group.facts)
            all_concepts.update(group.facts.keys())

        return {
            'total_contexts': len(self._groups),
            'total_concepts': len(all_concepts),
            'sample_concepts': sorted(list(all_concepts))[:SAMPLE_CONCEPTS_LIMIT],
            'contexts_sample': dict(list(context_concept_counts.items())[:SAMPLE_CONTEXTS_LIMIT]),
        }

    def __len__(self) -> int:
        return len(self._groups)


__all__ = [
    'ContextGroup',
    'FactGroups',
    'SAMPLE_CONCEPTS_LIMIT',
    'SAMPLE_CONTEXTS_LIMIT',
]
