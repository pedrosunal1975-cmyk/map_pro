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
    ConceptNormalizer,
)
from ...constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from .horizontal_checker import CheckResult
from .calculation_resolver import CalculationResolver


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
    source: str  # 'company' or 'taxonomy'
    role: str
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    passed: bool = False
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
        normalizer: ConceptNormalizer = None,
        tolerance: float = None
    ) -> CalculationVerificationResult:
        """
        Verify a single calculation tree against actual facts.

        Uses NORMALIZED concept names for lookup to handle different
        separator formats (colon vs underscore vs dash).

        Args:
            tree: CalculationTree defining the calculation
            facts: Dictionary mapping NORMALIZED concept names to values
            normalizer: ConceptNormalizer for name translation (optional)
            tolerance: Optional custom tolerance

        Returns:
            CalculationVerificationResult with details (uses ORIGINAL names)
        """
        tol = tolerance if tolerance is not None else self.calculation_tolerance

        # Create normalizer if not provided
        if normalizer is None:
            normalizer = ConceptNormalizer()

        result = CalculationVerificationResult(
            parent_concept=tree.parent,  # Keep ORIGINAL name in result
            source=tree.source,
            role=tree.role,
            tolerance_used=tol
        )

        # Normalize parent concept for lookup
        parent_normalized = normalizer.normalize(tree.parent)

        # Get actual parent value using normalized name
        actual = facts.get(parent_normalized)
        result.actual_value = actual

        if actual is None:
            result.passed = True  # Can't verify without parent value
            result.message = f"Parent concept {tree.parent} not found in facts"
            return result

        # Calculate expected value from children
        expected = 0.0
        missing_count = 0

        for child_concept, weight in tree.children:
            # Normalize child concept for lookup
            child_normalized = normalizer.normalize(child_concept)
            child_value = facts.get(child_normalized)

            contribution = ChildContribution(
                concept=child_concept,  # Keep ORIGINAL name
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
                result.missing_children.append(child_concept)  # ORIGINAL name

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

        Uses NORMALIZED concept names for matching, allowing different
        separator formats (colon vs underscore) to match correctly.

        PERIOD HANDLING: Calculations are verified SEPARATELY for each period.
        A calculation passes only if it passes for ALL periods where the
        parent concept exists. Periods are never mixed.

        Args:
            statements: MappedStatements with fact values
            source: 'company' or 'taxonomy'
            role: Optional role filter

        Returns:
            List of CalculationVerificationResult objects (with ORIGINAL names)
        """
        self.logger.info(f"Verifying calculations against {source} formulas")

        # Build NORMALIZED facts dictionary from all statements, GROUPED BY PERIOD
        facts_by_period, normalizer = self._extract_facts_by_period(statements)

        if not facts_by_period:
            self.logger.warning("No facts extracted from statements")
            return []

        total_facts = sum(len(pf) for pf in facts_by_period.values())
        self.logger.info(
            f"Extracted {total_facts} facts across {len(facts_by_period)} periods"
        )

        # Get calculation trees from registry
        trees = self.registry.get_all_calculations(source, role)

        if not trees:
            self.logger.warning(f"No calculation trees found for source={source}")
            return []

        self.logger.info(f"Verifying {len(trees)} calculation trees across {len(facts_by_period)} periods")

        # Create resolver for parent vs children resolution
        resolver = CalculationResolver(self.registry)

        # Verify each tree across ALL periods
        # A tree passes if it passes for all periods where the parent exists
        results = []
        for tree in trees:
            # Track results across periods for this tree
            period_results = []
            periods_with_parent = 0

            parent_normalized = normalizer.normalize(tree.parent)

            for period, period_facts in facts_by_period.items():
                # Only verify if parent exists in this period
                if parent_normalized not in period_facts:
                    continue

                periods_with_parent += 1

                # Resolve facts for this period
                resolved_facts = resolver.get_resolved_facts(period_facts, normalizer, source)

                # Verify calculation for this period
                period_result = self.verify_calculation(tree, resolved_facts, normalizer)
                period_results.append((period, period_result))

            # Aggregate results across periods
            if not period_results:
                # Parent not found in any period - skip
                result = CalculationVerificationResult(
                    parent_concept=tree.parent,
                    source=tree.source,
                    role=tree.role,
                    passed=True,  # Can't verify without parent
                    message=f"Parent concept {tree.parent} not found in any period"
                )
            else:
                # Use result from most recent period for details,
                # but pass only if ALL periods passed
                all_passed = all(pr[1].passed for pr in period_results)
                periods_passed = sum(1 for pr in period_results if pr[1].passed)

                # Get most recent period's result for details
                most_recent = sorted(period_results, key=lambda x: x[0], reverse=True)[0]
                result = most_recent[1]

                # Override passed status based on all periods
                result.passed = all_passed

                # Update message with period info
                if len(period_results) > 1:
                    result.message = (
                        f"Verified across {len(period_results)} periods: "
                        f"{periods_passed}/{len(period_results)} passed"
                    )

            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed and r.actual_value is not None)
        skipped = len(results) - passed - failed

        self.logger.info(
            f"Calculation verification ({source}): "
            f"{passed} passed, {failed} failed, {skipped} skipped (no data)"
        )

        return results

    def dual_verify(
        self,
        statements: MappedStatements,
        role: str = None
    ) -> list[DualVerificationResult]:
        """
        Verify calculations against both company and taxonomy sources.

        Compares results to identify discrepancies.
        Uses NORMALIZED concept names for matching.

        PERIOD HANDLING: Uses per-period verification - verifies each period
        separately and aggregates results.

        Args:
            statements: MappedStatements with fact values
            role: Optional role filter

        Returns:
            List of DualVerificationResult objects
        """
        self.logger.info("Running dual verification (company + taxonomy)")

        # Extract facts by period
        facts_by_period, normalizer = self._extract_facts_by_period(statements)

        if not facts_by_period:
            self.logger.warning("No facts extracted for dual verification")
            return []

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
            f"{len(taxonomy_trees)} taxonomy, {len(all_parents)} total concepts, "
            f"{len(facts_by_period)} periods"
        )

        # Create resolver for parent vs children resolution
        resolver = CalculationResolver(self.registry)

        results = []
        for parent in sorted(all_parents):
            parent_normalized = normalizer.normalize(parent)

            # Verify across all periods where parent exists
            company_results_by_period = []
            taxonomy_results_by_period = []

            for period, period_facts in facts_by_period.items():
                if parent_normalized not in period_facts:
                    continue

                # Resolve facts for this period
                resolved_company = resolver.get_resolved_facts(period_facts, normalizer, 'company')
                resolved_taxonomy = resolver.get_resolved_facts(period_facts, normalizer, 'taxonomy')

                # Verify against company if available
                if parent in company_trees:
                    result = self.verify_calculation(
                        company_trees[parent], resolved_company, normalizer
                    )
                    company_results_by_period.append((period, result))

                # Verify against taxonomy if available
                if parent in taxonomy_trees:
                    result = self.verify_calculation(
                        taxonomy_trees[parent], resolved_taxonomy, normalizer
                    )
                    taxonomy_results_by_period.append((period, result))

            # Aggregate results across periods
            dual_result = DualVerificationResult(
                concept=parent,
                company_result=None,
                taxonomy_result=None,
                sources_agree=True
            )

            # Aggregate company results
            if company_results_by_period:
                all_passed = all(pr[1].passed for pr in company_results_by_period)
                most_recent = sorted(company_results_by_period, key=lambda x: x[0], reverse=True)[0]
                dual_result.company_result = most_recent[1]
                dual_result.company_result.passed = all_passed

            # Aggregate taxonomy results
            if taxonomy_results_by_period:
                all_passed = all(pr[1].passed for pr in taxonomy_results_by_period)
                most_recent = sorted(taxonomy_results_by_period, key=lambda x: x[0], reverse=True)[0]
                dual_result.taxonomy_result = most_recent[1]
                dual_result.taxonomy_result.passed = all_passed

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

        Uses NORMALIZED concept names for matching.

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

        facts, normalizer, period = self._get_most_recent_period_facts(statements)

        # Resolve facts (parent vs children)
        resolver = CalculationResolver(self.registry)
        resolved_facts = resolver.get_resolved_facts(facts, normalizer, source)

        return self.verify_calculation(tree, resolved_facts, normalizer)

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

    def _get_calc_tree_concepts(self) -> set[str]:
        """
        Get all concepts referenced in calculation trees.

        Collects both parent and child concepts from company AND taxonomy
        calculation trees. These are concepts the company (or taxonomy)
        has explicitly declared as part of calculations.

        Returns:
            Set of NORMALIZED concept names from calc trees
        """
        normalizer = ConceptNormalizer()
        concepts = set()

        # Get from both sources
        for source in ('company', 'taxonomy'):
            trees = self.registry.get_all_calculations(source)
            for tree in trees:
                # Add parent
                concepts.add(normalizer.normalize(tree.parent))
                # Add all children
                for child_concept, _ in tree.children:
                    concepts.add(normalizer.normalize(child_concept))

        return concepts

    def _extract_facts_by_period(
        self,
        statements: MappedStatements
    ) -> tuple[dict[str, dict[str, float]], ConceptNormalizer]:
        """
        Extract all fact values from statements, organized by period.

        Uses NORMALIZED concept names for matching across different sources.
        Returns facts grouped by period to enable per-period verification.

        NORMALIZATION:
        Different sources use different separators (: vs _ vs -).
        This method normalizes all concept names so they can be matched
        regardless of the separator used.

        PERIOD HANDLING:
        SEC filings have multiple periods (current year, prior year, quarters).
        We return facts GROUPED BY PERIOD - never mixing periods.
        Each calculation must be verified within a single period context.

        Args:
            statements: MappedStatements object

        Returns:
            Tuple of:
            - Dictionary mapping period -> {NORMALIZED concept: value}
            - ConceptNormalizer with original name mappings
        """
        # First pass: collect all facts with their periods
        facts_by_period: dict[str, dict[str, float]] = {}  # period -> {concept: value}
        normalizer = ConceptNormalizer()

        # Get concepts declared in calculation trees
        # These override our default "skip dimensioned facts" rule
        calc_tree_concepts = self._get_calc_tree_concepts()

        dimensioned_count = 0
        dimensioned_allowed = 0  # Dimensioned facts allowed because calc tree references them
        skipped_non_main = 0
        for statement in statements.statements:
            # CRITICAL: Only use facts from MAIN statements for calculation verification
            # Non-main statements (notes, schedules, details) may have different values
            # that don't represent the primary aggregates we want to verify
            if not statement.is_main_statement:
                skipped_non_main += 1
                continue

            for fact in statement.facts:
                if fact.is_abstract or fact.value is None:
                    continue

                # Normalize concept name early - needed for calc tree check
                concept_normalized = normalizer.normalize(fact.concept)

                # DIMENSIONAL HANDLING:
                # Default rule (ours): Skip dimensioned facts - they shouldn't mix with aggregates
                # Override rule (company's): If calc tree explicitly references this concept,
                # the company has declared its use - allow it through
                if fact.dimensions and any(fact.dimensions.values()):
                    if concept_normalized in calc_tree_concepts:
                        # Company declared this concept in calc tree - their rule overrides ours
                        dimensioned_allowed += 1
                    else:
                        # Not in calc tree - our default rule applies: skip it
                        dimensioned_count += 1
                        continue

                # Parse value - handle financial statement conventions
                # Em-dash (—), en-dash (–), hyphen (-), and empty string mean zero/nil
                raw_val = str(fact.value).strip() if fact.value else ''
                if raw_val in ('', '—', '–', '-', 'nil', 'N/A', 'n/a'):
                    value = 0.0
                else:
                    try:
                        value = float(raw_val.replace(',', '').replace('$', ''))
                    except (ValueError, TypeError):
                        continue

                # Register the concept (stores original->normalized mapping)
                # We already have concept_normalized from earlier
                normalizer.register(fact.concept, source='statement')

                # Use period_end as the key (or 'unknown' if not available)
                period = fact.period_end or 'unknown'

                if period not in facts_by_period:
                    facts_by_period[period] = {}

                # Within same period, prefer main statements
                if concept_normalized not in facts_by_period[period] or statement.is_main_statement:
                    facts_by_period[period][concept_normalized] = value

        # Log extraction summary
        if not facts_by_period:
            self.logger.debug("No facts found in statements")
            return {}, normalizer

        total_facts = sum(len(pf) for pf in facts_by_period.values())
        periods_found = sorted(facts_by_period.keys(), reverse=True)

        self.logger.debug(
            f"Extracted {total_facts} facts across {len(facts_by_period)} periods: "
            f"{', '.join(periods_found[:3])}{'...' if len(periods_found) > 3 else ''}"
        )

        self.logger.debug(
            f"Skipped {dimensioned_count} dimensioned facts, "
            f"allowed {dimensioned_allowed} calc-tree-declared dimensioned facts"
        )

        return facts_by_period, normalizer

    def _get_most_recent_period_facts(
        self,
        statements: MappedStatements
    ) -> tuple[dict[str, float], ConceptNormalizer, str]:
        """
        Extract facts from the most recent period only.

        Convenience method for single-calculation verification where
        per-period aggregation is not needed.

        Args:
            statements: MappedStatements object

        Returns:
            Tuple of:
            - Dictionary mapping NORMALIZED concept names to values
            - ConceptNormalizer with original name mappings
            - Period string (e.g., '2024-09-28')
        """
        facts_by_period, normalizer = self._extract_facts_by_period(statements)

        if not facts_by_period:
            return {}, normalizer, 'unknown'

        # Get most recent period (excluding 'unknown')
        valid_periods = [p for p in facts_by_period.keys() if p != 'unknown']
        if valid_periods:
            valid_periods.sort(reverse=True)
            most_recent = valid_periods[0]
        elif 'unknown' in facts_by_period:
            most_recent = 'unknown'
        else:
            most_recent = list(facts_by_period.keys())[0]

        return facts_by_period[most_recent], normalizer, most_recent

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
