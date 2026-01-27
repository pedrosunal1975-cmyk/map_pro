# Path: verification/engine/checks/vertical_checker.py
"""
Vertical Checker for Verification Module

Validates consistency across statements using XBRL-sourced formulas.
NO hardcoded patterns - all calculation relationships come from:
1. Company XBRL calculation linkbase (PRIMARY)
2. Standard taxonomy calculation linkbase (SECONDARY)

VERTICAL CHECK (Consistency):
Verifies cross-statement relationships using actual XBRL definitions.
Also checks common values consistency across statements.
"""

import logging
from typing import Optional, TYPE_CHECKING

from ...loaders.mapped_reader import MappedStatements
from ..checks.constants import (
    CHECK_COMMON_VALUES_CONSISTENCY,
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
)
from ...constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from .horizontal_checker import CheckResult

if TYPE_CHECKING:
    from ..formula_registry import FormulaRegistry


# Check names for XBRL-sourced calculations
# IMPORTANT: Company and taxonomy must have DIFFERENT check names
# so they're scored separately (each can have many results)
CHECK_XBRL_CALCULATION_COMPANY = 'xbrl_calculation_company'
CHECK_XBRL_CALCULATION_TAXONOMY = 'xbrl_calculation_taxonomy'
CHECK_XBRL_CALCULATION_COMPARISON = 'xbrl_calculation_comparison'

# Legacy alias for backwards compatibility
CHECK_XBRL_CALCULATION = CHECK_XBRL_CALCULATION_COMPANY


class VerticalChecker:
    """
    Validates consistency across statements.

    Checks fundamental accounting relationships that must hold
    between different financial statements.

    Example:
        checker = VerticalChecker()
        results = checker.check_all(statements)
        for result in results:
            if not result.passed:
                print(f"{result.check_name}: {result.message}")
    """

    def __init__(
        self,
        calculation_tolerance: float = DEFAULT_CALCULATION_TOLERANCE,
        rounding_tolerance: float = DEFAULT_ROUNDING_TOLERANCE,
        formula_registry: Optional['FormulaRegistry'] = None
    ):
        """
        Initialize vertical checker.

        Args:
            calculation_tolerance: Percentage tolerance for calculations
            rounding_tolerance: Absolute tolerance for small differences
            formula_registry: Optional FormulaRegistry for XBRL-sourced verification
        """
        self.calculation_tolerance = calculation_tolerance
        self.rounding_tolerance = rounding_tolerance
        self.formula_registry = formula_registry
        self.logger = logging.getLogger('process.vertical_checker')

    def check_all(self, statements: MappedStatements) -> list[CheckResult]:
        """
        Run all vertical checks on statements.

        Uses XBRL-sourced verification from FormulaRegistry.
        NO hardcoded pattern-based checks - all formulas come from XBRL sources.

        Args:
            statements: MappedStatements from mapped_reader

        Returns:
            List of CheckResult objects
        """
        # Count main vs total statements
        main_count = sum(1 for s in statements.statements if s.is_main_statement)
        total_count = len(statements.statements)

        self.logger.info(
            f"Running vertical checks on {main_count} main statements "
            f"(out of {total_count} total)"
        )

        results = []

        # XBRL-sourced verification (company formulas)
        # Uses CHECK_XBRL_CALCULATION_COMPANY for scoring separation
        if self.formula_registry and self.formula_registry.has_company_formulas():
            self.logger.info("Running XBRL-sourced verification (company formulas)")
            xbrl_results = self.check_xbrl_calculations(
                statements, source='company',
                check_name=CHECK_XBRL_CALCULATION_COMPANY
            )
            results.extend(xbrl_results)
        else:
            self.logger.warning(
                "No company XBRL formulas available - vertical calculation checks skipped"
            )
            results.append(CheckResult(
                check_name=CHECK_XBRL_CALCULATION_COMPANY,
                check_type='vertical',
                passed=True,
                severity=SEVERITY_INFO,
                message="No company XBRL calculation formulas available for verification"
            ))

        # Taxonomy-sourced verification (secondary)
        # Uses CHECK_XBRL_CALCULATION_TAXONOMY for scoring separation
        if self.formula_registry and self.formula_registry.has_taxonomy_formulas():
            self.logger.info("Running taxonomy-sourced verification")
            taxonomy_results = self.check_xbrl_calculations(
                statements, source='taxonomy',
                check_name=CHECK_XBRL_CALCULATION_TAXONOMY
            )
            results.extend(taxonomy_results)
        else:
            self.logger.info("No taxonomy formulas available - taxonomy checks skipped")

        # Check common values consistency (main statements only)
        # This check doesn't rely on formulas - just cross-statement consistency
        common_results = self.check_common_values_consistency(statements)
        results.extend(common_results)

        passed = sum(1 for r in results if r.passed)
        self.logger.info(f"Vertical checks complete: {passed}/{len(results)} passed")

        return results

    def check_common_values_consistency(
        self,
        statements: MappedStatements
    ) -> list[CheckResult]:
        """
        Check that common values appear consistently across MAIN statements.

        RULES (consistent with calculation_verifier.py):
        - Only check MAIN statements
        - Skip dimensioned facts (different dimensions are not the same fact)

        IMPORTANT: A fact appearing in multiple statements with the SAME value
        is NOT a problem - that's expected cross-referencing.
        Only flag when the SAME concept has DIFFERENT values in the same period.

        Focuses on main statements only to avoid noise from detail/note files.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for inconsistencies found
        """
        results = []

        # Only check main statements for consistency
        main_statements = [s for s in statements.statements if s.is_main_statement]

        if not main_statements:
            # Fall back to all statements if no main statements identified
            main_statements = statements.statements

        # Build map of (concept, period_end) -> values across main statements
        # Using period_end to distinguish different reporting periods
        concept_period_values: dict[tuple[str, str], list[tuple[str, float]]] = {}

        for statement in main_statements:
            for fact in statement.facts:
                if fact.is_abstract or fact.value is None:
                    continue

                # RULE: Skip dimensioned facts - different dimensions are not duplicates
                if fact.dimensions and any(fact.dimensions.values()):
                    continue

                # Handle em-dash and empty values
                raw_val = str(fact.value).strip()
                if raw_val in ('', '—', '–', '-', 'nil', 'N/A', 'n/a'):
                    value = 0.0
                else:
                    try:
                        value = float(raw_val.replace(',', '').replace('$', ''))
                    except (ValueError, TypeError):
                        continue

                concept = fact.concept
                period = fact.period_end or 'unknown'
                key = (concept, period)

                if key not in concept_period_values:
                    concept_period_values[key] = []
                concept_period_values[key].append((statement.name, value))

        # Check for TRUE inconsistencies (same concept, same period, different values)
        inconsistency_count = 0
        for (concept, period), values in concept_period_values.items():
            if len(values) > 1:
                unique_values = set(v for _, v in values)

                # Same fact appearing in multiple statements with SAME value = OK
                if len(unique_values) == 1:
                    continue  # This is cross-referencing, not a problem

                # Different values for same concept in same period = potential issue
                min_val = min(unique_values)
                max_val = max(unique_values)

                if not self._within_tolerance(min_val, max_val):
                    inconsistency_count += 1
                    results.append(CheckResult(
                        check_name=CHECK_COMMON_VALUES_CONSISTENCY,
                        check_type='vertical',
                        passed=False,
                        severity=SEVERITY_WARNING,
                        message=f"Different values for {concept} in period {period}",
                        difference=max_val - min_val,
                        details={
                            'concept': concept,
                            'period': period,
                            'occurrences': [
                                {'statement': stmt, 'value': val}
                                for stmt, val in values
                            ],
                        }
                    ))

        # Summary result
        if inconsistency_count == 0:
            results.append(CheckResult(
                check_name=CHECK_COMMON_VALUES_CONSISTENCY,
                check_type='vertical',
                passed=True,
                severity=SEVERITY_INFO,
                message=f"Common values are consistent across {len(main_statements)} main statements"
            ))

        return results

    def check_xbrl_calculations(
        self,
        statements: MappedStatements,
        source: str = 'company',
        check_name: str = None
    ) -> list[CheckResult]:
        """
        Verify calculations using XBRL-sourced formulas.

        Uses FormulaRegistry instead of hardcoded patterns.
        This is the preferred method when registry is available.

        Args:
            statements: MappedStatements object
            source: 'company' or 'taxonomy' for which formulas to use
            check_name: Check name for results (determines scoring category)

        Returns:
            List of CheckResult for each calculation verified
        """
        if not self.formula_registry:
            self.logger.warning(
                "FormulaRegistry not available - cannot run XBRL calculations"
            )
            return []

        # Default check name based on source
        if check_name is None:
            check_name = (CHECK_XBRL_CALCULATION_COMPANY if source == 'company'
                         else CHECK_XBRL_CALCULATION_TAXONOMY)

        # Import here to avoid circular imports
        from .calculation_verifier import CalculationVerifier

        verifier = CalculationVerifier(
            self.formula_registry,
            self.calculation_tolerance,
            self.rounding_tolerance
        )

        # Run verification
        results = verifier.verify_all_calculations(statements, source)

        # Convert to CheckResult format with specific check_name
        check_results = verifier.to_check_results(results, check_name)

        # Add source info to each result
        for result in check_results:
            if result.details:
                result.details['verification_source'] = source

        self.logger.info(
            f"XBRL calculation verification ({source}): "
            f"{sum(1 for r in check_results if r.passed)}/{len(check_results)} passed"
        )

        return check_results

    def check_xbrl_calculations_dual(
        self,
        statements: MappedStatements
    ) -> list[CheckResult]:
        """
        Verify calculations against both company and taxonomy sources.

        Compares results to identify where company and taxonomy disagree.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult including comparison results
        """
        if not self.formula_registry:
            self.logger.warning(
                "FormulaRegistry not available - cannot run dual verification"
            )
            return []

        # Import here to avoid circular imports
        from .calculation_verifier import CalculationVerifier

        verifier = CalculationVerifier(
            self.formula_registry,
            self.calculation_tolerance,
            self.rounding_tolerance
        )

        # Run dual verification
        dual_results = verifier.dual_verify(statements)

        check_results = []

        for dual in dual_results:
            # Add company result if available
            if dual.company_result and dual.company_result.actual_value is not None:
                check_results.append(CheckResult(
                    check_name=CHECK_XBRL_CALCULATION,
                    check_type='vertical',
                    passed=dual.company_result.passed,
                    severity=SEVERITY_WARNING if not dual.company_result.passed else SEVERITY_INFO,
                    message=f"[Company] {dual.company_result.message}",
                    expected_value=dual.company_result.expected_value,
                    actual_value=dual.company_result.actual_value,
                    difference=dual.company_result.difference,
                    details={
                        'concept': dual.concept,
                        'source': 'company',
                        'children_count': len(dual.company_result.children),
                    }
                ))

            # Add taxonomy result if available
            if dual.taxonomy_result and dual.taxonomy_result.actual_value is not None:
                check_results.append(CheckResult(
                    check_name=CHECK_XBRL_CALCULATION,
                    check_type='vertical',
                    passed=dual.taxonomy_result.passed,
                    severity=SEVERITY_WARNING if not dual.taxonomy_result.passed else SEVERITY_INFO,
                    message=f"[Taxonomy] {dual.taxonomy_result.message}",
                    expected_value=dual.taxonomy_result.expected_value,
                    actual_value=dual.taxonomy_result.actual_value,
                    difference=dual.taxonomy_result.difference,
                    details={
                        'concept': dual.concept,
                        'source': 'taxonomy',
                        'children_count': len(dual.taxonomy_result.children),
                    }
                ))

            # Add comparison result if sources disagree
            if not dual.sources_agree:
                check_results.append(CheckResult(
                    check_name=CHECK_XBRL_CALCULATION_COMPARISON,
                    check_type='vertical',
                    passed=False,
                    severity=SEVERITY_WARNING,
                    message=f"Company vs Taxonomy disagree for {dual.concept}",
                    details={
                        'concept': dual.concept,
                        'discrepancies': dual.discrepancies,
                    }
                ))

        agreed = sum(1 for d in dual_results if d.sources_agree)
        self.logger.info(
            f"Dual verification complete: {agreed}/{len(dual_results)} concepts agree"
        )

        return check_results

    def _within_tolerance(self, expected: float, actual: float) -> bool:
        """Check if values are within acceptable tolerance."""
        if expected == 0 and actual == 0:
            return True

        diff = abs(expected - actual)

        # For small values, use absolute tolerance
        if abs(expected) < LARGE_VALUE_THRESHOLD:
            return diff <= self.rounding_tolerance

        # For large values, use percentage tolerance
        if expected != 0:
            pct_diff = diff / abs(expected)
            return pct_diff <= self.calculation_tolerance

        return diff <= self.rounding_tolerance


__all__ = [
    'VerticalChecker',
    'CHECK_XBRL_CALCULATION',
    'CHECK_XBRL_CALCULATION_COMPANY',
    'CHECK_XBRL_CALCULATION_TAXONOMY',
    'CHECK_XBRL_CALCULATION_COMPARISON',
]
