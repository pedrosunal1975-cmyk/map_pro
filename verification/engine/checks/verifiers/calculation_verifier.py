# Path: verification/engine/checks/verifiers/calculation_verifier.py
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
   - Check if calculation binds (all conditions met)
   - Apply sign corrections from iXBRL instance document
   - Verify using decimal tolerance
3. Report pass/fail with details

Uses:
- CEqual for context-based fact grouping
- BindingChecker for XBRL binding rules
- DecimalTolerance for XBRL-compliant value comparison
- SignWeightHandler for iXBRL sign attribute handling
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ...formula_registry import FormulaRegistry, CalculationTree
from ....loaders.mapped_reader import MappedStatements
from ..c_equal.c_equal import CEqual, FactGroups, ContextGroup
from ..binding.binding_checker import BindingChecker, BindingResult, BindingStatus
from ..core.decimal_tolerance import DecimalTolerance
from ..handlers.sign_weight_handler import SignWeightHandler
from ..core.constants import OVERSHOOT_ROUNDING_THRESHOLD
from ....constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from ..core.check_result import CheckResult


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
    context-based (c-equal) verification and iXBRL sign corrections.
    """

    DEFAULT_TOLERANCE = 0.01  # 1%
    DEFAULT_ROUNDING = 1.0    # $1

    def __init__(
        self,
        registry: FormulaRegistry,
        calculation_tolerance: float = DEFAULT_TOLERANCE,
        rounding_tolerance: float = DEFAULT_ROUNDING,
        sign_handler: SignWeightHandler = None
    ):
        """
        Initialize calculation verifier.

        Args:
            registry: FormulaRegistry with loaded formulas
            calculation_tolerance: Percentage tolerance for calculations
            rounding_tolerance: Absolute tolerance for small differences
            sign_handler: Optional SignWeightHandler with parsed sign corrections
        """
        self.registry = registry
        self.calculation_tolerance = calculation_tolerance
        self.rounding_tolerance = rounding_tolerance
        self.c_equal = CEqual()
        self.binding_checker = BindingChecker()
        self.decimal_tolerance = DecimalTolerance()
        self.sign_handler = sign_handler if sign_handler else SignWeightHandler()
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
        # All statements included - calculation children may be in detail statements
        fact_groups = self.c_equal.group_facts(statements)

        if fact_groups.context_count == 0:
            self.logger.warning("No facts extracted from statements")
            return []

        self.logger.info(
            f"Extracted {fact_groups.total_facts} facts across "
            f"{fact_groups.context_count} contexts"
        )

        # Build all_facts lookup for dimensional fallback
        # This allows finding children that are in different contexts
        all_facts = fact_groups.get_all_facts_by_concept()
        self.logger.info(f"Built cross-context lookup with {len(all_facts)} concepts")

        # Log diagnostic summary for debugging
        diag = fact_groups.get_diagnostic_summary()
        self.logger.info(
            f"Fact groups diagnostic: {diag['total_contexts']} contexts, "
            f"{diag['total_concepts']} unique concepts"
        )
        if diag['sample_concepts']:
            self.logger.debug(f"Sample concepts (first 50): {diag['sample_concepts']}")

        # Get calculation trees from registry
        trees = self.registry.get_all_calculations(source, role)

        if not trees:
            self.logger.warning(f"No calculation trees found for source={source}")
            return []

        self.logger.info(f"Verifying {len(trees)} calculation trees")

        # Verify each tree - returns list of results per context
        results = []
        for tree in trees:
            context_results = self._verify_tree(tree, fact_groups, all_facts)
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
        fact_groups: FactGroups,
        all_facts: dict = None
    ) -> list[CalculationVerificationResult]:
        """
        Verify a single calculation tree across all contexts.

        Uses BindingChecker to determine if calculation binds,
        then DecimalTolerance for value comparison.

        Returns one result per context for granular c-equal verification.

        Args:
            tree: CalculationTree to verify
            fact_groups: FactGroups from C-Equal module
            all_facts: Cross-context fact lookup for dimensional fallback

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

            # Check if calculation binds using BindingChecker with fallback
            # The fallback enables finding children in different contexts
            # (handles dimensional qualifiers like ClassOfStockAxis)
            binding = self.binding_checker.check_binding_with_fallback(
                context_group, parent_norm, children_norm, all_facts
            )

            if not binding.binds:
                # Calculation doesn't bind - skip (not fail)
                results.append(CalculationVerificationResult(
                    parent_concept=tree.parent,
                    source=tree.source,
                    role=tree.role,
                    expected_value=None,
                    actual_value=binding.parent_value,
                    passed=False,
                    children=[],
                    difference=None,
                    tolerance_used=self.calculation_tolerance,
                    message=f"Skipped: {binding.message}",
                    missing_children=binding.children_missing,
                    contexts_verified=0,
                    contexts_passed=0
                ))
                continue

            # Calculate expected sum from children with sign corrections
            expected_sum = 0.0
            min_decimals = None
            children_list = []
            sign_corrections_applied = []

            for child_info in binding.children_found:
                # Find original concept name
                original_concept = child_info.get('original_concept', child_info['concept'])
                child_ctx = child_info.get('context_id', context_id)
                child_value = child_info['value']
                child_weight = child_info['weight']

                # Apply sign correction from XBRL instance document
                corrected_value, was_corrected = self.sign_handler.apply_sign_correction(
                    original_concept, child_ctx, child_value
                )
                if was_corrected:
                    sign_corrections_applied.append({
                        'concept': original_concept,
                        'original': child_value,
                        'corrected': corrected_value,
                        'type': 'child'
                    })
                    child_value = corrected_value

                weighted_value = child_value * child_weight
                expected_sum += weighted_value

                children_list.append(ChildContribution(
                    concept=original_concept,
                    value=child_info['value'],  # Original for display
                    weight=child_weight,
                    contribution=weighted_value,
                    found=True
                ))

                # Track minimum decimals for tolerance
                if child_info['decimals'] is not None:
                    if min_decimals is None:
                        min_decimals = child_info['decimals']
                    else:
                        min_decimals = min(min_decimals, child_info['decimals'])

            # Add missing children to list
            for child_concept, weight in tree.children:
                child_norm = self.c_equal.normalize_concept(child_concept)
                if child_norm in binding.children_missing:
                    children_list.append(ChildContribution(
                        concept=child_concept,
                        value=None,
                        weight=weight,
                        contribution=None,
                        found=False
                    ))

            # Apply sign correction to parent value
            parent_value = binding.parent_value
            parent_corrected, parent_was_corrected = self.sign_handler.apply_sign_correction(
                tree.parent, context_id, parent_value
            )
            if parent_was_corrected:
                sign_corrections_applied.append({
                    'concept': tree.parent,
                    'original': parent_value,
                    'corrected': parent_corrected,
                    'type': 'parent'
                })
                parent_value = parent_corrected

            # Compare using decimal tolerance
            tolerance_result = self.decimal_tolerance.is_within_tolerance(
                expected=expected_sum,
                actual=parent_value,
                expected_decimals=min_decimals,
                actual_decimals=binding.parent_decimals,
            )

            passed = tolerance_result.values_equal
            difference = tolerance_result.difference

            if passed:
                message = (
                    f"Calculation {tree.parent}: "
                    f"expected {expected_sum:,.0f}, found {parent_value:,.0f} OK"
                )
                if sign_corrections_applied:
                    message += f" ({len(sign_corrections_applied)} sign corrections)"
            else:
                message = (
                    f"Calculation {tree.parent}: "
                    f"expected {expected_sum:,.0f}, found {parent_value:,.0f}, "
                    f"diff {difference:,.0f}"
                )

            results.append(CalculationVerificationResult(
                parent_concept=tree.parent,
                source=tree.source,
                role=tree.role,
                expected_value=expected_sum,
                actual_value=parent_value,  # Use corrected value
                passed=passed,
                children=children_list,
                difference=difference,
                tolerance_used=self.calculation_tolerance,
                message=message,
                missing_children=binding.children_missing,
                contexts_verified=1,
                contexts_passed=1 if passed else 0
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

        # Group facts by context_id (c-equal rule)
        # All statements included - calculation children may be in detail statements
        fact_groups = self.c_equal.group_facts(statements)

        if fact_groups.context_count == 0:
            self.logger.warning("No facts extracted for dual verification")
            return []

        # Build all_facts lookup for dimensional fallback
        all_facts = fact_groups.get_all_facts_by_concept()

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

            # Verify company - _verify_tree returns list, aggregate to single result
            if parent in company_trees:
                tree_results = self._verify_tree(company_trees[parent], fact_groups, all_facts)
                dual_result.company_result = self._aggregate_results(
                    tree_results, company_trees[parent]
                )

            # Verify taxonomy - _verify_tree returns list, aggregate to single result
            if parent in taxonomy_trees:
                tree_results = self._verify_tree(taxonomy_trees[parent], fact_groups, all_facts)
                dual_result.taxonomy_result = self._aggregate_results(
                    tree_results, taxonomy_trees[parent]
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

    def _aggregate_results(
        self,
        results: list[CalculationVerificationResult],
        tree: CalculationTree
    ) -> Optional[CalculationVerificationResult]:
        """
        Aggregate multiple context results into a single result.

        A calculation passes only if ALL contexts pass.
        """
        if not results:
            return None

        # Count verified contexts (exclude skipped)
        verified = [r for r in results if r.contexts_verified > 0]
        if not verified:
            # All were skipped - return first result
            return results[0] if results else None

        # Calculate aggregates
        total_verified = len(verified)
        total_passed = sum(1 for r in verified if r.passed)
        all_passed = total_passed == total_verified

        # Use first verified result as base
        base = verified[0]

        return CalculationVerificationResult(
            parent_concept=tree.parent,
            source=tree.source,
            role=tree.role,
            expected_value=base.expected_value,
            actual_value=base.actual_value,
            passed=all_passed,
            children=base.children,
            difference=base.difference,
            tolerance_used=base.tolerance_used,
            message=f"{total_passed}/{total_verified} contexts passed",
            missing_children=base.missing_children,
            contexts_verified=total_verified,
            contexts_passed=total_passed
        )

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

            if result.passed:
                severity = SEVERITY_INFO
            else:
                # Severity logic based on overshooting vs undershooting:
                # Use MAGNITUDES (absolute values) to determine direction.
                has_missing = len(result.missing_children) > 0
                expected_sum = result.expected_value if result.expected_value is not None else 0
                parent_value = result.actual_value if result.actual_value is not None else 0
                sum_magnitude = abs(expected_sum)
                parent_magnitude = abs(parent_value)

                # Check for sign mismatch
                sign_mismatch = (
                    expected_sum != 0 and parent_value != 0 and
                    (expected_sum > 0) != (parent_value > 0)
                )

                overshooting = sum_magnitude > parent_magnitude
                undershooting = sum_magnitude < parent_magnitude

                if sign_mismatch:
                    severity = SEVERITY_CRITICAL
                elif overshooting:
                    # Check if small overshoot (rounding) or large (real issue)
                    if parent_magnitude > 0:
                        overshoot_ratio = (sum_magnitude - parent_magnitude) / parent_magnitude
                    else:
                        overshoot_ratio = 1.0
                    if overshoot_ratio <= OVERSHOOT_ROUNDING_THRESHOLD:
                        severity = SEVERITY_WARNING
                    else:
                        severity = SEVERITY_CRITICAL
                elif undershooting and has_missing:
                    severity = SEVERITY_WARNING
                else:
                    severity = SEVERITY_CRITICAL

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
