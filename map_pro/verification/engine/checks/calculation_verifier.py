# Path: verification/engine/checks/calculation_verifier.py
"""
Calculation Verifier for Verification Module

Verifies calculations using formulas from the FormulaRegistry.
Replaces hardcoded formula verification with XBRL-sourced relationships.

RESPONSIBILITY: Verify that reported values match their calculation
relationships as defined in either company XBRL or standard taxonomy.

VERIFICATION APPROACH:
1. Get calculation tree (parent -> children with weights)
2. For each parent concept in the data:
   - Sum: expected = sum(child_value * weight)
   - Compare: expected vs actual parent value
3. Report pass/fail with details

DUAL VERIFICATION:
- Can verify against company-defined relationships
- Can verify against taxonomy-defined relationships
- Can compare results between both sources
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..formula_registry import FormulaRegistry, CalculationTree
from ...loaders.mapped_reader import MappedStatements, Statement
from .constants import (
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
)
from ...constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from .horizontal_checker import CheckResult


@dataclass
class ChildContribution:
    """Contribution of a child concept to a calculation."""
    concept: str
    value: Optional[float]
    weight: float
    contribution: Optional[float]  # value * weight
    found: bool


@dataclass
class CalculationVerificationResult:
    """
    Result of verifying a single calculation.

    Detailed breakdown of how a calculated total was verified.
    """
    parent_concept: str
    expected_value: Optional[float]
    actual_value: Optional[float]
    passed: bool
    source: str  # 'company' or 'taxonomy'
    role: str
    children: list[ChildContribution] = field(default_factory=list)
    difference: Optional[float] = None
    tolerance_used: float = 0.0
    message: str = ''
    missing_children: list[str] = field(default_factory=list)


@dataclass
class DualVerificationResult:
    """
    Result of verifying against both company and taxonomy.
    """
    concept: str
    company_result: Optional[CalculationVerificationResult]
    taxonomy_result: Optional[CalculationVerificationResult]
    sources_agree: bool
    discrepancies: list[str] = field(default_factory=list)


class CalculationVerifier:
    """
    Verifies calculations using FormulaRegistry.

    Uses XBRL-defined calculation relationships instead of
    hardcoded patterns.

    Example:
        registry = FormulaRegistry()
        registry.load_company_formulas(filing_path)
        registry.load_taxonomy_formulas('us-gaap-2024')

        verifier = CalculationVerifier(registry)
        results = verifier.verify_all_calculations(statements)

        for result in results:
            if not result.passed:
                print(f"Failed: {result.parent_concept}")
                print(f"  Expected: {result.expected_value}")
                print(f"  Actual: {result.actual_value}")
    """

    def __init__(
        self,
        registry: FormulaRegistry,
        calculation_tolerance: float = DEFAULT_CALCULATION_TOLERANCE,
        rounding_tolerance: float = DEFAULT_ROUNDING_TOLERANCE
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
        self.logger = logging.getLogger('process.calculation_verifier')

    def verify_calculation(
        self,
        tree: CalculationTree,
        facts: dict[str, float],
        tolerance: float = None
    ) -> CalculationVerificationResult:
        """
        Verify a single calculation tree against actual facts.

        Args:
            tree: CalculationTree defining the calculation
            facts: Dictionary mapping concept names to values
            tolerance: Optional custom tolerance

        Returns:
            CalculationVerificationResult with details
        """
        tol = tolerance if tolerance is not None else self.calculation_tolerance

        result = CalculationVerificationResult(
            parent_concept=tree.parent,
            source=tree.source,
            role=tree.role,
            tolerance_used=tol
        )

        # Get actual parent value
        actual = facts.get(tree.parent)
        result.actual_value = actual

        if actual is None:
            result.passed = True  # Can't verify without parent value
            result.message = f"Parent concept {tree.parent} not found in facts"
            return result

        # Calculate expected value from children
        expected = 0.0
        missing_count = 0

        for child_concept, weight in tree.children:
            child_value = facts.get(child_concept)

            contribution = ChildContribution(
                concept=child_concept,
                value=child_value,
                weight=weight,
                contribution=None,
                found=child_value is not None
            )

            if child_value is not None:
                contrib = child_value * weight
                contribution.contribution = contrib
                expected += contrib
            else:
                missing_count += 1
                result.missing_children.append(child_concept)

            result.children.append(contribution)

        result.expected_value = expected

        # Check if verification is meaningful
        if missing_count == len(tree.children):
            result.passed = True  # Can't verify without any children
            result.message = f"No child values found for {tree.parent}"
            return result

        # Calculate difference and check tolerance
        result.difference = abs(expected - actual)
        result.passed = self._within_tolerance(expected, actual, tol)

        if result.passed:
            result.message = (
                f"{tree.parent}: calculated={expected:,.0f} matches "
                f"actual={actual:,.0f} (diff={result.difference:,.0f})"
            )
        else:
            result.message = (
                f"{tree.parent}: calculated={expected:,.0f} != "
                f"actual={actual:,.0f} (diff={result.difference:,.0f})"
            )

        return result

    def verify_all_calculations(
        self,
        statements: MappedStatements,
        source: str = 'company',
        role: str = None
    ) -> list[CalculationVerificationResult]:
        """
        Verify all calculations for statements against a source.

        Args:
            statements: MappedStatements with fact values
            source: 'company' or 'taxonomy'
            role: Optional role filter

        Returns:
            List of CalculationVerificationResult objects
        """
        self.logger.info(f"Verifying calculations against {source} formulas")

        # Build facts dictionary from all statements
        facts = self._extract_facts(statements)

        self.logger.debug(f"Extracted {len(facts)} fact values")

        # Get calculation trees from registry
        trees = self.registry.get_all_calculations(source, role)

        if not trees:
            self.logger.warning(f"No calculation trees found for source={source}")
            return []

        self.logger.info(f"Verifying {len(trees)} calculation trees")

        # Verify each tree
        results = []
        for tree in trees:
            result = self.verify_calculation(tree, facts)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        self.logger.info(f"Calculation verification: {passed}/{len(results)} passed")

        return results

    def dual_verify(
        self,
        statements: MappedStatements,
        role: str = None
    ) -> list[DualVerificationResult]:
        """
        Verify calculations against both company and taxonomy sources.

        Compares results to identify discrepancies.

        Args:
            statements: MappedStatements with fact values
            role: Optional role filter

        Returns:
            List of DualVerificationResult objects
        """
        self.logger.info("Running dual verification (company + taxonomy)")

        # Extract facts once
        facts = self._extract_facts(statements)

        # Get all parent concepts from both sources
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

        results = []
        for parent in sorted(all_parents):
            dual_result = DualVerificationResult(
                concept=parent,
                company_result=None,
                taxonomy_result=None,
                sources_agree=True
            )

            # Verify against company if available
            if parent in company_trees:
                dual_result.company_result = self.verify_calculation(
                    company_trees[parent], facts
                )

            # Verify against taxonomy if available
            if parent in taxonomy_trees:
                dual_result.taxonomy_result = self.verify_calculation(
                    taxonomy_trees[parent], facts
                )

            # Check for discrepancies
            if dual_result.company_result and dual_result.taxonomy_result:
                if dual_result.company_result.passed != dual_result.taxonomy_result.passed:
                    dual_result.sources_agree = False
                    dual_result.discrepancies.append(
                        f"Pass/fail differs: company={dual_result.company_result.passed}, "
                        f"taxonomy={dual_result.taxonomy_result.passed}"
                    )

                # Compare expected values
                if (dual_result.company_result.expected_value is not None and
                    dual_result.taxonomy_result.expected_value is not None):
                    comp_exp = dual_result.company_result.expected_value
                    tax_exp = dual_result.taxonomy_result.expected_value
                    if not self._within_tolerance(comp_exp, tax_exp):
                        dual_result.sources_agree = False
                        dual_result.discrepancies.append(
                            f"Expected values differ: company={comp_exp:,.0f}, "
                            f"taxonomy={tax_exp:,.0f}"
                        )

            elif dual_result.company_result is None and dual_result.taxonomy_result is not None:
                dual_result.discrepancies.append(
                    f"Only taxonomy has calculation for {parent}"
                )

            elif dual_result.company_result is not None and dual_result.taxonomy_result is None:
                dual_result.discrepancies.append(
                    f"Only company has calculation for {parent}"
                )

            results.append(dual_result)

        agreed = sum(1 for r in results if r.sources_agree)
        self.logger.info(f"Dual verification: {agreed}/{len(results)} agree")

        return results

    def verify_specific_calculation(
        self,
        parent_concept: str,
        statements: MappedStatements,
        source: str = 'company'
    ) -> Optional[CalculationVerificationResult]:
        """
        Verify a specific calculation.

        Args:
            parent_concept: Concept to verify
            statements: MappedStatements with fact values
            source: 'company' or 'taxonomy'

        Returns:
            CalculationVerificationResult or None if no calculation found
        """
        tree = self.registry.get_calculation(parent_concept, source)
        if not tree:
            return None

        facts = self._extract_facts(statements)
        return self.verify_calculation(tree, facts)

    def get_failed_calculations(
        self,
        results: list[CalculationVerificationResult]
    ) -> list[CalculationVerificationResult]:
        """
        Filter to only failed verifications.

        Args:
            results: List of verification results

        Returns:
            List of failed results only
        """
        return [r for r in results if not r.passed and r.actual_value is not None]

    def to_check_results(
        self,
        results: list[CalculationVerificationResult],
        check_name: str = 'calculation_from_xbrl'
    ) -> list[CheckResult]:
        """
        Convert verification results to CheckResult format.

        Enables integration with existing verification scoring system.

        Args:
            results: List of CalculationVerificationResult
            check_name: Name for the check

        Returns:
            List of CheckResult objects
        """
        check_results = []

        for result in results:
            if result.actual_value is None:
                continue  # Skip if parent not found

            severity = SEVERITY_INFO
            if not result.passed:
                severity = SEVERITY_WARNING

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
                    'verification_source': result.source,  # Add for filtering
                    'role': result.role,
                    'children_count': len(result.children),
                    'missing_children': result.missing_children,
                    'tolerance': result.tolerance_used,
                }
            ))

        return check_results

    def _extract_facts(self, statements: MappedStatements) -> dict[str, float]:
        """
        Extract all fact values from statements into a flat dictionary.

        Uses the most recent period's value for each concept.

        Args:
            statements: MappedStatements object

        Returns:
            Dictionary mapping concept names to values
        """
        facts: dict[str, float] = {}

        for statement in statements.statements:
            for fact in statement.facts:
                if fact.is_abstract or fact.value is None:
                    continue

                try:
                    value = float(fact.value)
                except (ValueError, TypeError):
                    continue

                # Use concept name as key
                # If same concept exists, prefer main statements
                if fact.concept not in facts or statement.is_main_statement:
                    facts[fact.concept] = value

        return facts

    def _within_tolerance(
        self,
        expected: float,
        actual: float,
        tolerance: float = None
    ) -> bool:
        """
        Check if values are within acceptable tolerance.

        Args:
            expected: Expected value
            actual: Actual value
            tolerance: Optional custom tolerance

        Returns:
            True if within tolerance
        """
        tol = tolerance if tolerance is not None else self.calculation_tolerance

        if expected == 0 and actual == 0:
            return True

        diff = abs(expected - actual)

        # For small values, use absolute tolerance
        if abs(expected) < LARGE_VALUE_THRESHOLD:
            return diff <= self.rounding_tolerance

        # For large values, use percentage tolerance
        if expected != 0:
            pct_diff = diff / abs(expected)
            return pct_diff <= tol

        return diff <= self.rounding_tolerance


__all__ = [
    'CalculationVerifier',
    'CalculationVerificationResult',
    'DualVerificationResult',
    'ChildContribution',
]
