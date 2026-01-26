# Path: verification/engine/formula_registry.py
"""
Formula Registry for Verification Module

Central registry for calculation formulas from all sources.
Provides unified access to both company-defined and taxonomy-defined
calculation relationships.

RESPONSIBILITY: Aggregate and provide lookup for calculation relationships
from multiple sources, enabling dual verification against company XBRL
and standard taxonomy definitions.

SOURCES:
1. Company XBRL calculation linkbase - How the company declares calculations
2. Standard taxonomy calculation linkbase - How the standard defines calculations

Both should match for compliant filings, but discrepancies reveal
either company extensions or potential issues.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..loaders.xbrl_reader import XBRLReader, CalculationArc
from ..loaders.taxonomy_calc_reader import TaxonomyCalcReader, CalculationRelationship


@dataclass
class CalculationTree:
    """
    Tree structure representing a calculation.

    Shows how a parent concept is calculated from its children,
    with weights indicating addition (+1) or subtraction (-1).

    Attributes:
        parent: Parent concept name
        children: List of (child_concept, weight) tuples
        source: Source of this calculation ('company' or 'taxonomy')
        role: Statement role URI
    """
    parent: str
    children: list[tuple[str, float]] = field(default_factory=list)
    source: str = ''
    role: str = ''

    def get_child_concepts(self) -> list[str]:
        """Get list of child concept names."""
        return [child for child, _ in self.children]

    def get_weight(self, child_concept: str) -> Optional[float]:
        """Get weight for a specific child concept."""
        for child, weight in self.children:
            if child == child_concept:
                return weight
        return None


@dataclass
class FormulaComparison:
    """
    Comparison of a formula between company and taxonomy sources.

    Attributes:
        concept: The parent concept being compared
        company_tree: CalculationTree from company XBRL (or None)
        taxonomy_tree: CalculationTree from taxonomy (or None)
        matches: Whether the formulas match
        differences: List of differences found
    """
    concept: str
    company_tree: Optional[CalculationTree] = None
    taxonomy_tree: Optional[CalculationTree] = None
    matches: bool = True
    differences: list[str] = field(default_factory=list)


class FormulaRegistry:
    """
    Central registry for calculation formulas from all sources.

    Loads and aggregates calculation relationships from:
    - Company XBRL calculation linkbase
    - Standard taxonomy calculation linkbase

    Provides unified lookup and comparison capabilities.

    Example:
        registry = FormulaRegistry()

        # Load company formulas from filing
        registry.load_company_formulas(filing_path)

        # Load taxonomy formulas
        registry.load_taxonomy_formulas('us-gaap-2024')

        # Get calculation tree for a concept
        tree = registry.get_calculation('us-gaap:Assets', source='company')

        # Compare company vs taxonomy
        comparison = registry.compare_sources('us-gaap:Assets')
        if not comparison.matches:
            print(f"Differences: {comparison.differences}")
    """

    def __init__(self, config=None):
        """
        Initialize formula registry.

        Args:
            config: Optional ConfigLoader for path resolution
        """
        self.logger = logging.getLogger('process.formula_registry')
        self._config = config

        # Readers
        self._xbrl_reader = XBRLReader(config)
        self._taxonomy_reader = TaxonomyCalcReader(config)

        # Storage for calculation trees
        # Key: (concept, role), Value: CalculationTree
        self._company_trees: dict[tuple[str, str], CalculationTree] = {}
        self._taxonomy_trees: dict[tuple[str, str], CalculationTree] = {}

        # All parent concepts with calculations
        self._company_parents: set[str] = set()
        self._taxonomy_parents: set[str] = set()

        # Loaded sources tracking
        self._company_filing_path: Optional[Path] = None
        self._taxonomy_id: Optional[str] = None

    def load_company_formulas(self, filing_path: Path) -> int:
        """
        Load calculation relationships from company's XBRL filing.

        Args:
            filing_path: Path to filing directory containing calculation linkbase

        Returns:
            Number of calculation trees loaded
        """
        self.logger.info(f"Loading company formulas from {filing_path}")

        # Clear previous company data
        self._company_trees.clear()
        self._company_parents.clear()
        self._company_filing_path = filing_path

        # Read calculation linkbase
        networks = self._xbrl_reader.read_calculation_linkbase(filing_path)

        if not networks:
            self.logger.warning(f"No calculation networks found in {filing_path}")
            return 0

        # Build calculation trees from arcs
        tree_count = 0
        for network in networks:
            trees = self._build_trees_from_arcs(network.arcs, network.role, 'company')
            for tree in trees:
                key = (tree.parent, tree.role)
                self._company_trees[key] = tree
                self._company_parents.add(tree.parent)
                tree_count += 1

        self.logger.info(
            f"Loaded {tree_count} company calculation trees "
            f"({len(self._company_parents)} parent concepts)"
        )

        return tree_count

    def load_taxonomy_formulas(self, taxonomy_id: str) -> int:
        """
        Load calculation relationships from standard taxonomy.

        Args:
            taxonomy_id: Taxonomy identifier (e.g., 'us-gaap-2024')

        Returns:
            Number of calculation trees loaded
        """
        self.logger.info(f"Loading taxonomy formulas from {taxonomy_id}")

        # Clear previous taxonomy data
        self._taxonomy_trees.clear()
        self._taxonomy_parents.clear()
        self._taxonomy_id = taxonomy_id

        # Read taxonomy calculations
        calculations = self._taxonomy_reader.read_taxonomy_calculations(taxonomy_id)

        if not calculations:
            self.logger.warning(f"No calculations found in taxonomy {taxonomy_id}")
            return 0

        # Build calculation trees
        tree_count = 0
        for parent_concept, relationships in calculations.by_parent.items():
            # Group by role
            by_role: dict[str, list[CalculationRelationship]] = {}
            for rel in relationships:
                if rel.role not in by_role:
                    by_role[rel.role] = []
                by_role[rel.role].append(rel)

            # Create tree for each role
            for role, rels in by_role.items():
                children = [
                    (rel.child_concept, rel.weight)
                    for rel in sorted(rels, key=lambda x: x.order)
                ]

                tree = CalculationTree(
                    parent=parent_concept,
                    children=children,
                    source='taxonomy',
                    role=role
                )

                key = (parent_concept, role)
                self._taxonomy_trees[key] = tree
                self._taxonomy_parents.add(parent_concept)
                tree_count += 1

        self.logger.info(
            f"Loaded {tree_count} taxonomy calculation trees "
            f"({len(self._taxonomy_parents)} parent concepts)"
        )

        return tree_count

    def _build_trees_from_arcs(
        self,
        arcs: list[CalculationArc],
        role: str,
        source: str
    ) -> list[CalculationTree]:
        """
        Build calculation trees from a list of arcs.

        Groups arcs by parent concept and creates a tree for each.

        Args:
            arcs: List of CalculationArc objects
            role: Statement role
            source: Source identifier ('company' or 'taxonomy')

        Returns:
            List of CalculationTree objects
        """
        # Group arcs by parent
        by_parent: dict[str, list[CalculationArc]] = {}
        for arc in arcs:
            if arc.parent_concept not in by_parent:
                by_parent[arc.parent_concept] = []
            by_parent[arc.parent_concept].append(arc)

        # Create trees
        trees = []
        for parent, parent_arcs in by_parent.items():
            children = [
                (arc.child_concept, arc.weight)
                for arc in sorted(parent_arcs, key=lambda x: x.order)
            ]

            tree = CalculationTree(
                parent=parent,
                children=children,
                source=source,
                role=role
            )
            trees.append(tree)

        return trees

    def get_calculation(
        self,
        parent_concept: str,
        source: str = 'company',
        role: str = None
    ) -> Optional[CalculationTree]:
        """
        Get calculation tree for a concept from specified source.

        Args:
            parent_concept: Parent concept name
            source: 'company' or 'taxonomy'
            role: Optional specific role (returns first match if None)

        Returns:
            CalculationTree or None
        """
        trees = self._company_trees if source == 'company' else self._taxonomy_trees

        if role:
            return trees.get((parent_concept, role))

        # Return first matching tree if role not specified
        for (concept, tree_role), tree in trees.items():
            if concept == parent_concept:
                return tree

        return None

    def get_all_calculations(
        self,
        source: str = 'company',
        role: str = None
    ) -> list[CalculationTree]:
        """
        Get all calculation trees from a source.

        Args:
            source: 'company' or 'taxonomy'
            role: Optional role filter

        Returns:
            List of CalculationTree objects
        """
        trees = self._company_trees if source == 'company' else self._taxonomy_trees

        if role:
            return [tree for tree in trees.values() if tree.role == role]

        return list(trees.values())

    def get_children(
        self,
        parent_concept: str,
        source: str = 'company',
        role: str = None
    ) -> list[tuple[str, float]]:
        """
        Get child concepts and weights for a parent.

        Args:
            parent_concept: Parent concept name
            source: 'company' or 'taxonomy'
            role: Optional role filter

        Returns:
            List of (child_concept, weight) tuples
        """
        tree = self.get_calculation(parent_concept, source, role)
        if tree:
            return tree.children
        return []

    def compare_sources(self, concept: str, role: str = None) -> FormulaComparison:
        """
        Compare calculation definition between company and taxonomy.

        Args:
            concept: Concept to compare
            role: Optional role filter

        Returns:
            FormulaComparison showing differences
        """
        company_tree = self.get_calculation(concept, 'company', role)
        taxonomy_tree = self.get_calculation(concept, 'taxonomy', role)

        comparison = FormulaComparison(
            concept=concept,
            company_tree=company_tree,
            taxonomy_tree=taxonomy_tree
        )

        # Determine if they match and what differences exist
        if company_tree is None and taxonomy_tree is None:
            comparison.matches = True  # Neither has it
            return comparison

        if company_tree is None:
            comparison.matches = False
            comparison.differences.append(
                f"Concept {concept} has taxonomy calculation but no company calculation"
            )
            return comparison

        if taxonomy_tree is None:
            comparison.matches = False
            comparison.differences.append(
                f"Concept {concept} has company calculation but no taxonomy calculation"
            )
            return comparison

        # Both exist - compare children
        company_children = set(company_tree.get_child_concepts())
        taxonomy_children = set(taxonomy_tree.get_child_concepts())

        only_company = company_children - taxonomy_children
        only_taxonomy = taxonomy_children - company_children

        if only_company:
            comparison.matches = False
            comparison.differences.append(
                f"Children only in company: {', '.join(only_company)}"
            )

        if only_taxonomy:
            comparison.matches = False
            comparison.differences.append(
                f"Children only in taxonomy: {', '.join(only_taxonomy)}"
            )

        # Check weights for common children
        common_children = company_children & taxonomy_children
        for child in common_children:
            company_weight = company_tree.get_weight(child)
            taxonomy_weight = taxonomy_tree.get_weight(child)
            if company_weight != taxonomy_weight:
                comparison.matches = False
                comparison.differences.append(
                    f"Weight mismatch for {child}: "
                    f"company={company_weight}, taxonomy={taxonomy_weight}"
                )

        return comparison

    def compare_all(self) -> list[FormulaComparison]:
        """
        Compare all concepts that exist in either source.

        Returns:
            List of FormulaComparison for all concepts
        """
        all_concepts = self._company_parents | self._taxonomy_parents
        comparisons = []

        for concept in sorted(all_concepts):
            comparison = self.compare_sources(concept)
            comparisons.append(comparison)

        return comparisons

    def get_mismatches(self) -> list[FormulaComparison]:
        """
        Get only the comparisons where company and taxonomy differ.

        Returns:
            List of FormulaComparison with matches=False
        """
        return [c for c in self.compare_all() if not c.matches]

    def has_company_formulas(self) -> bool:
        """Check if company formulas are loaded."""
        return len(self._company_trees) > 0

    def has_taxonomy_formulas(self) -> bool:
        """Check if taxonomy formulas are loaded."""
        return len(self._taxonomy_trees) > 0

    def get_summary(self) -> dict:
        """
        Get summary of loaded formulas.

        Returns:
            Dictionary with summary statistics
        """
        comparisons = self.compare_all() if self._company_trees or self._taxonomy_trees else []
        matches = sum(1 for c in comparisons if c.matches)
        mismatches = len(comparisons) - matches

        return {
            'company_filing': str(self._company_filing_path) if self._company_filing_path else None,
            'taxonomy_id': self._taxonomy_id,
            'company_trees': len(self._company_trees),
            'company_concepts': len(self._company_parents),
            'taxonomy_trees': len(self._taxonomy_trees),
            'taxonomy_concepts': len(self._taxonomy_parents),
            'total_unique_concepts': len(self._company_parents | self._taxonomy_parents),
            'matches': matches,
            'mismatches': mismatches,
        }

    def clear(self) -> None:
        """Clear all loaded formulas."""
        self._company_trees.clear()
        self._taxonomy_trees.clear()
        self._company_parents.clear()
        self._taxonomy_parents.clear()
        self._company_filing_path = None
        self._taxonomy_id = None
        self.logger.info("Formula registry cleared")


__all__ = [
    'FormulaRegistry',
    'CalculationTree',
    'FormulaComparison',
]
