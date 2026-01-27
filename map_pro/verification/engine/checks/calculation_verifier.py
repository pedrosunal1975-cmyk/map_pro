# Path: verification/engine/checks/calculation_verifier.py
"""
Calculation Verifier for Verification Module

Verifies calculations using formulas from the FormulaRegistry.
Uses the C-Equal module for proper XBRL context-based verification.

RESPONSIBILITY: Verify that reported values match their calculation
relationships as defined in either company XBRL or standard taxonomy.

VERIFICATION APPROACH:
1. Group facts by context_id using C-Equal module
2. For each calculation tree:
   - Find all contexts where the parent exists
   - Verify the calculation in each context
   - Aggregate results (pass only if ALL contexts pass)
3. Report pass/fail with details
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..formula_registry import FormulaRegistry, CalculationTree
from ...loaders.mapped_reader import MappedStatements
from .c_equal import CEqual, FactGroups, ContextGroup
from ...constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from .horizontal_checker import CheckResult


@dataclass
class ChildContribution:
    """Contribution of a child concept to a calculation."""
    concept: str
    value: Optional[float]
    weight: float
    contribution: Optional[float]
    found: bool


@dataclass
class CalculationVerificationResult:
    """Result of verifying a single calculation."""
    parent_concept: str
    source: str
    role: str
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    passed: bool = False
    children: list[ChildContribution] = field(default_factory=list)
    difference: Optional[float] = None
    tolerance_used: float = 0.0
    message: str = ''
    missing_children: list[str] = field(default_factory=list)
    contexts_verified: int = 0
    contexts_passed: int = 0


@dataclass
class DualVerificationResult:
    """Result of verifying against both company and taxonomy."""
    concept: str
    company_result: Optional[CalculationVerificationResult]
    taxonomy_result: Optional[CalculationVerificationResult]
    sources_agree: bool
    discrepancies: list[str] = field(default_factory=list)


class CalculationVerifier:
    """
    Verifies calculations using FormulaRegistry and C-Equal module.

    Uses XBRL-defined calculation relationships with proper
    context-based (c-equal) verification.
    """

    DEFAULT_TOLERANCE = 0.01  # 1%
    DEFAULT_ROUNDING = 1.0    # $1

    def __init__(
        self,
        registry: FormulaRegistry,
        calculation_tolerance: float = DEFAULT_TOLERANCE,
        rounding_tolerance: float = DEFAULT_ROUNDING
    ):
        """
        Initialize calculation verifier.

        Args:
            registry: FormulaRegistry with loaded formulas
            calculation_tolerance: Percentage tolerance for calculations
            rounding_tolerance: Absolute tolerance for small differences
        """
        self.registry = registry
        self.calculation_tolerance = calculation_tolerance
        self.rounding_tolerance = rounding_tolerance
        self.c_equal = CEqual()
        self.logger = logging.getLogger('process.calculation_verifier')

    def verify_all_calculations(
        self,
        statements: MappedStatements,
        source: str = 'company',
        role: str = None
    ) -> list[CalculationVerificationResult]:
        """
        Verify all calculations for statements against a source.

        Uses C-Equal module to ensure proper context-based verification.
        A calculation passes only if it passes in ALL contexts where
        the parent concept exists.

        Args:
            statements: MappedStatements with fact values
            source: 'company' or 'taxonomy'
            role: Optional role filter

        Returns:
            List of CalculationVerificationResult objects
        """
        self.logger.info(f"Verifying calculations against {source} formulas")

        # Group facts by context_id (c-equal rule)
        fact_groups = self.c_equal.group_facts(statements, main_only=True, group_by='context_id')

        if fact_groups.context_count == 0:
            self.logger.warning("No facts extracted from statements")
            return []

        self.logger.info(
            f"Extracted {fact_groups.total_facts} facts across "
            f"{fact_groups.context_count} contexts"
        )

        # Get calculation trees from registry
        trees = self.registry.get_all_calculations(source, role)

        if not trees:
            self.logger.warning(f"No calculation trees found for source={source}")
            return []

        self.logger.info(f"Verifying {len(trees)} calculation trees")

        # Verify each tree - returns list of results per context
        results = []
        for tree in trees:
            context_results = self._verify_tree(tree, fact_groups)
            results.extend(context_results)

        # Log summary
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed and r.actual_value is not None)
        skipped = len(results) - passed - failed

        self.logger.info(
            f"Calculation verification ({source}): "
            f"{passed} passed, {failed} failed, {skipped} skipped"
        )

        return results

    def _verify_tree(
        self,
        tree: CalculationTree,
        fact_groups: FactGroups
    ) -> list[CalculationVerificationResult]:
        """
        Verify a single calculation tree across all contexts.

        Returns one result per context for granular c-equal verification.

        Args:
            tree: CalculationTree to verify
            fact_groups: FactGroups from C-Equal module

        Returns:
            List of CalculationVerificationResult (one per context)
        """
        results = []

        # Normalize parent concept
        parent_norm = self.c_equal.normalize_concept(tree.parent)

        # Normalize children concepts
        children_norm = [
            (self.c_equal.normalize_concept(child), weight)
            for child, weight in tree.children
        ]

        # Find all contexts where parent exists
        contexts_with_parent = fact_groups.get_contexts_with_concept(parent_norm)

        if not contexts_with_parent:
            # Return empty list - no contexts to verify
            return results

        # Verify in each context - return individual result per context
        for context_id in contexts_with_parent:
            context_group = fact_groups.get_context(context_id)
            if not context_group:
                continue

            result = self.c_equal.verify_calculation(
                context_group,
                parent_norm,
                children_norm,
                self.calculation_tolerance,
                self.rounding_tolerance
            )

            # Build children list for this context
            children = []
            for child_concept, weight in tree.children:
                child_norm = self.c_equal.normalize_concept(child_concept)
                child_value = context_group.get(child_norm)

                children.append(ChildContribution(
                    concept=child_concept,
                    value=child_value,
                    weight=weight,
                    contribution=child_value * weight if child_value is not None else None,
                    found=child_value is not None
                ))

            results.append(CalculationVerificationResult(
                parent_concept=tree.parent,
                source=tree.source,
                role=tree.role,
                expected_value=result.get('expected_value'),
                actual_value=result.get('parent_value'),
                passed=result.get('passed', False),
                children=children,
                difference=result.get('difference'),
                tolerance_used=self.calculation_tolerance,
                message=result.get('message', ''),
                missing_children=result.get('missing_children', []),
                contexts_verified=1,
                contexts_passed=1 if result.get('passed') else 0
            ))

        return results

    def dual_verify(
        self,
        statements: MappedStatements,
        role: str = None
    ) -> list[DualVerificationResult]:
        """
        Verify calculations against both company and taxonomy sources.

        Args:
            statements: MappedStatements with fact values
            role: Optional role filter

        Returns:
            List of DualVerificationResult objects
        """
        self.logger.info("Running dual verification (company + taxonomy)")

        # Group facts by period (lenient grouping)
        fact_groups = self.c_equal.group_facts(statements, main_only=True, group_by='period')

        if fact_groups.context_count == 0:
            self.logger.warning("No facts extracted for dual verification")
            return []

        # Get trees from both sources
        company_trees = {
            t.parent: t for t in self.registry.get_all_calculations('company', role)
        }
        taxonomy_trees = {
            t.parent: t for t in self.registry.get_all_calculations('taxonomy', role)
        }

        all_parents = set(company_trees.keys()) | set(taxonomy_trees.keys())

        self.logger.info(
            f"Dual verification: {len(company_trees)} company, "
            f"{len(taxonomy_trees)} taxonomy, {len(all_parents)} total concepts"
        )

        # Verify each parent
        results = []
        for parent in sorted(all_parents):
            dual_result = DualVerificationResult(
                concept=parent,
                company_result=None,
                taxonomy_result=None,
                sources_agree=True
            )

            # Verify company
            if parent in company_trees:
                dual_result.company_result = self._verify_tree(
                    company_trees[parent], fact_groups
                )

            # Verify taxonomy
            if parent in taxonomy_trees:
                dual_result.taxonomy_result = self._verify_tree(
                    taxonomy_trees[parent], fact_groups
                )

            # Check for discrepancies
            if dual_result.company_result and dual_result.taxonomy_result:
                if dual_result.company_result.passed != dual_result.taxonomy_result.passed:
                    dual_result.sources_agree = False
                    dual_result.discrepancies.append(
                        f"Pass/fail differs: company={dual_result.company_result.passed}, "
                        f"taxonomy={dual_result.taxonomy_result.passed}"
                    )

            results.append(dual_result)

        agreed = sum(1 for r in results if r.sources_agree)
        self.logger.info(f"Dual verification: {agreed}/{len(results)} agree")

        return results

    def to_check_results(
        self,
        results: list[CalculationVerificationResult],
        check_name: str = 'calculation_from_xbrl'
    ) -> list[CheckResult]:
        """
        Convert verification results to CheckResult format.

        Args:
            results: List of CalculationVerificationResult
            check_name: Name for the check

        Returns:
            List of CheckResult objects
        """
        check_results = []

        for result in results:
            if result.actual_value is None:
                continue

            severity = SEVERITY_INFO if result.passed else SEVERITY_WARNING

            check_results.append(CheckResult(
                check_name=check_name,
                check_type='vertical',
                passed=result.passed,
                severity=severity,
                message=result.message,
                expected_value=result.expected_value,
                actual_value=result.actual_value,
                difference=result.difference,
                details={
                    'parent_concept': result.parent_concept,
                    'source': result.source,
                    'verification_source': result.source,
                    'role': result.role,
                    'children_count': len(result.children),
                    'missing_children': result.missing_children,
                    'tolerance': result.tolerance_used,
                    'contexts_verified': result.contexts_verified,
                    'contexts_passed': result.contexts_passed,
                }
            ))

        return check_results

    def get_failed_calculations(
        self,
        results: list[CalculationVerificationResult]
    ) -> list[CalculationVerificationResult]:
        """Filter to only failed verifications."""
        return [r for r in results if not r.passed and r.actual_value is not None]


__all__ = [
    'CalculationVerifier',
    'CalculationVerificationResult',
    'DualVerificationResult',
    'ChildContribution',
]
