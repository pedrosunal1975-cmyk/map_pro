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
Uses SignWeightHandler for iXBRL sign attribute handling.
"""

import logging
from typing import Optional, TYPE_CHECKING

from ....loaders.mapped_reader import MappedStatements
from ..core.constants import (
    CHECK_COMMON_VALUES_CONSISTENCY,
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
)
from ....constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from ..core.check_result import CheckResult
from ..handlers.sign_weight_handler import SignWeightHandler
from ..context.fact_rules import PeriodExtractor, ContextClassifier

if TYPE_CHECKING:
    from ...formula_registry import FormulaRegistry


# Check names for XBRL-sourced calculations (company XBRL only)
# Taxonomy checking has been removed - standard taxonomy libraries don't contain
# company-specific extensions, so taxonomy verification always fails on those concepts
CHECK_XBRL_CALCULATION_COMPANY = 'xbrl_calculation_company'
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
        formula_registry: Optional['FormulaRegistry'] = None,
        sign_handler: SignWeightHandler = None
    ):
        """
        Initialize vertical checker.

        Args:
            calculation_tolerance: Percentage tolerance for calculations
            rounding_tolerance: Absolute tolerance for small differences
            formula_registry: Optional FormulaRegistry for XBRL-sourced verification
            sign_handler: Optional SignWeightHandler for iXBRL sign corrections
        """
        self.calculation_tolerance = calculation_tolerance
        self.rounding_tolerance = rounding_tolerance
        self.formula_registry = formula_registry
        self.sign_handler = sign_handler if sign_handler else SignWeightHandler()
        self.period_extractor = PeriodExtractor()
        self.context_classifier = ContextClassifier()
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

        # NOTE: Taxonomy-sourced verification has been removed
        # Standard taxonomy libraries don't contain company-specific extensions,
        # which causes hundreds of false "not found" errors. Company XBRL
        # calculation linkbase is the authoritative source for verification.

        # Check common values consistency (all statements)
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
        Check that common values appear consistently across ALL statements.

        RULES:
        - Check ALL statements (main, detail, other) for comprehensive verification
        - Skip dimensioned facts (different dimensions are not the same fact)

        IMPORTANT: A fact appearing in multiple statements with the SAME value
        is NOT a problem - that's expected cross-referencing.
        Only flag when the SAME concept has DIFFERENT values in the same period.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for inconsistencies found
        """
        results = []

        # Check ALL statements for comprehensive consistency verification
        all_statements = statements.statements

        # Build map of (concept, period) -> list of (statement, value, context_id)
        # We need context_id to differentiate legitimately different facts
        # Hierarchy:
        #   1. Same concept + same period + same context_id + different values = TRUE ERROR
        #   2. Same concept + same period + different context_id = NOT an error (different facts)
        #   3. No period available -> use context_id as the grouping key (fallback)
        concept_period_facts: dict[tuple[str, str], list[tuple[str, float, str]]] = {}

        for statement in all_statements:
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
                context_id = fact.context_id or ''

                # Determine period key using PeriodExtractor
                # Priority: explicit period_end > extracted from context_id > context_id as fallback
                if fact.period_end:
                    period_key = fact.period_end
                elif context_id:
                    # Use PeriodExtractor to get period from context_id
                    period_info = self.period_extractor.extract(context_id)
                    if period_info.period_key:
                        period_key = period_info.period_key
                    else:
                        # Fallback to using context_id as grouping key
                        period_key = f"ctx:{context_id}"
                else:
                    continue  # Skip facts with neither period nor context

                key = (concept, period_key)

                if key not in concept_period_facts:
                    concept_period_facts[key] = []
                concept_period_facts[key].append((statement.name, value, context_id))

        # Check for TRUE inconsistencies
        inconsistency_count = 0
        for (concept, period_key), fact_entries in concept_period_facts.items():
            if len(fact_entries) <= 1:
                continue

            # Group by context_id within this concept+period group
            # Facts with same context_id should have same value
            # Facts with different context_ids are legitimately different
            by_context: dict[str, list[tuple[str, float]]] = {}
            for stmt, val, ctx_id in fact_entries:
                if ctx_id not in by_context:
                    by_context[ctx_id] = []
                by_context[ctx_id].append((stmt, val))

            # Check each context_id group for inconsistencies
            for ctx_id, ctx_facts in by_context.items():
                if len(ctx_facts) <= 1:
                    continue

                unique_values = set(v for _, v in ctx_facts)

                # Same fact appearing with SAME value = OK (cross-referencing)
                if len(unique_values) == 1:
                    continue

                # Different values for same concept + same period + same context = TRUE ERROR
                min_val = min(unique_values)
                max_val = max(unique_values)

                if not self._within_tolerance(min_val, max_val):
                    inconsistency_count += 1
                    # Format display
                    display_period = period_key[4:] if period_key.startswith('ctx:') else period_key
                    results.append(CheckResult(
                        check_name=CHECK_COMMON_VALUES_CONSISTENCY,
                        check_type='vertical',
                        passed=False,
                        severity=SEVERITY_WARNING,
                        message=f"Different values for {concept} in period {display_period} (context {ctx_id})",
                        difference=max_val - min_val,
                        details={
                            'concept': concept,
                            'period': display_period,
                            'context_id': ctx_id,
                            'occurrences': [
                                {'statement': stmt, 'value': val}
                                for stmt, val in ctx_facts
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
                message=f"Common values are consistent across {len(all_statements)} statements"
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

        # Default check name for company XBRL verification
        if check_name is None:
            check_name = CHECK_XBRL_CALCULATION_COMPANY

        # Import here to avoid circular imports
        from ..verifiers.calculation_verifier import CalculationVerifier

        verifier = CalculationVerifier(
            self.formula_registry,
            self.calculation_tolerance,
            self.rounding_tolerance,
            self.sign_handler  # Pass sign handler for iXBRL sign corrections
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
        from ..verifiers.calculation_verifier import CalculationVerifier

        verifier = CalculationVerifier(
            self.formula_registry,
            self.calculation_tolerance,
            self.rounding_tolerance,
            self.sign_handler  # Pass sign handler for iXBRL sign corrections
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
    'CHECK_XBRL_CALCULATION_COMPARISON',
]
