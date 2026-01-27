# Path: verification/engine/checks/calculation_resolver.py
"""
Calculation Resolver for Verification Module

Resolves calculation values by comparing parent vs children values.
Handles common SEC XBRL patterns where either parent or children
values may be incomplete or missing.

APPROACH:
For each calculation tree:
1. Get parent value from statements
2. Get all children values from statements
3. Calculate sum of children
4. Compare and resolve:
   - If parent > children sum: Use parent (children incomplete)
   - If children sum > parent: Use children sum (parent may be empty/wrong)
   - If equal: Both are valid

This handles cases like StockholdersEquity being reported as empty
while its children (RetainedEarnings, AdditionalPaidInCapital, etc.)
have values.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..formula_registry import FormulaRegistry, CalculationTree
from .constants import ConceptNormalizer


@dataclass
class ResolvedCalculation:
    """
    Result of resolving a calculation's parent vs children.

    Attributes:
        concept: The parent concept name
        parent_value: Value reported for parent (may be 0/None)
        children_sum: Calculated sum of children
        resolved_value: The chosen value (larger of parent or children)
        source: 'parent' or 'children' - which was used
        children_found: Number of children with values
        children_total: Total number of children in tree
        children_missing: List of missing child concepts
    """
    concept: str
    parent_value: Optional[float]
    children_sum: float
    resolved_value: float
    source: str  # 'parent' or 'children'
    children_found: int
    children_total: int
    children_missing: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if all children were found."""
        return self.children_found == self.children_total

    @property
    def coverage_pct(self) -> float:
        """Percentage of children found."""
        if self.children_total == 0:
            return 100.0
        return (self.children_found / self.children_total) * 100.0


class CalculationResolver:
    """
    Resolves calculation values by comparing parent vs children.

    For each calculation in the registry, determines the best value
    to use based on what the company actually reported.

    Example:
        resolver = CalculationResolver(registry)
        resolved = resolver.resolve_all(facts, normalizer)

        for r in resolved:
            print(f"{r.concept}: {r.resolved_value} (from {r.source})")
    """

    def __init__(self, registry: FormulaRegistry):
        """
        Initialize resolver.

        Args:
            registry: FormulaRegistry with loaded calculation trees
        """
        self.registry = registry
        self.logger = logging.getLogger('process.calculation_resolver')

    def resolve_calculation(
        self,
        tree: CalculationTree,
        facts: dict[str, float],
        normalizer: ConceptNormalizer
    ) -> ResolvedCalculation:
        """
        Resolve a single calculation tree.

        Steps:
        1. Get parent value from facts
        2. Sum all children values (with weights)
        3. Choose larger value as resolved

        Args:
            tree: CalculationTree to resolve
            facts: Normalized facts dictionary
            normalizer: ConceptNormalizer for name translation

        Returns:
            ResolvedCalculation with resolution details
        """
        # Get parent value
        parent_norm = normalizer.normalize(tree.parent)
        parent_value = facts.get(parent_norm)

        # Calculate sum of children
        children_sum = 0.0
        children_found = 0
        children_missing = []

        for child_concept, weight in tree.children:
            child_norm = normalizer.normalize(child_concept)
            child_value = facts.get(child_norm)

            if child_value is not None:
                children_sum += child_value * weight
                children_found += 1
            else:
                children_missing.append(child_concept)

        # Resolve: use the larger value
        # This handles:
        # - Parent = 0, children have values -> use children
        # - Children incomplete, parent has value -> use parent
        parent_val = parent_value if parent_value is not None else 0.0

        if abs(children_sum) > abs(parent_val):
            resolved_value = children_sum
            source = 'children'
        else:
            resolved_value = parent_val
            source = 'parent'

        return ResolvedCalculation(
            concept=tree.parent,
            parent_value=parent_value,
            children_sum=children_sum,
            resolved_value=resolved_value,
            source=source,
            children_found=children_found,
            children_total=len(tree.children),
            children_missing=children_missing
        )

    def resolve_all(
        self,
        facts: dict[str, float],
        normalizer: ConceptNormalizer,
        source: str = 'company'
    ) -> list[ResolvedCalculation]:
        """
        Resolve all calculations from registry.

        Args:
            facts: Normalized facts dictionary
            normalizer: ConceptNormalizer for name translation
            source: 'company' or 'taxonomy'

        Returns:
            List of ResolvedCalculation objects
        """
        trees = self.registry.get_all_calculations(source)

        if not trees:
            self.logger.warning(f"No calculation trees for source={source}")
            return []

        resolved = []
        for tree in trees:
            result = self.resolve_calculation(tree, facts, normalizer)
            resolved.append(result)

            # Log when we choose children over parent
            if result.source == 'children' and result.parent_value == 0:
                self.logger.info(
                    f"Resolved {tree.parent}: using children sum {result.children_sum:,.0f} "
                    f"(parent was 0/empty)"
                )

        return resolved

    def get_resolved_facts(
        self,
        facts: dict[str, float],
        normalizer: ConceptNormalizer,
        source: str = 'company'
    ) -> dict[str, float]:
        """
        Get facts dictionary with resolved values.

        Updates the facts dictionary with resolved values where
        children sum is greater than parent value.

        Args:
            facts: Original normalized facts
            normalizer: ConceptNormalizer
            source: 'company' or 'taxonomy'

        Returns:
            New facts dictionary with resolved values
        """
        resolved_facts = dict(facts)  # Copy

        resolutions = self.resolve_all(facts, normalizer, source)

        updated_count = 0
        for r in resolutions:
            if r.source == 'children':
                # Update the parent concept with resolved value
                parent_norm = normalizer.normalize(r.concept)
                old_val = resolved_facts.get(parent_norm, 0)
                resolved_facts[parent_norm] = r.resolved_value

                if r.resolved_value != old_val:
                    updated_count += 1
                    self.logger.debug(
                        f"Updated {r.concept}: {old_val} -> {r.resolved_value}"
                    )

        if updated_count > 0:
            self.logger.info(f"Resolved {updated_count} calculation values from children")

        return resolved_facts


__all__ = [
    'CalculationResolver',
    'ResolvedCalculation',
]
