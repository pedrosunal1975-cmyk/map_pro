# Path: verification/engine/checks/vertical_checker.py
"""
Vertical Checker for Verification Module

Validates consistency across statements.
Cross-statement relationships must hold.

VERTICAL CHECK (Consistency):
Across statements, verify:
1. Balance Sheet balances (Assets = Liabilities + Equity)
2. Net Income flows to Retained Earnings
3. Cash Flow ends with Cash position matching Balance Sheet
4. Common values appear consistently

These are fundamental accounting relationships.

XBRL-SOURCED VERIFICATION (preferred):
When FormulaRegistry is provided, uses XBRL calculation linkbase
instead of hardcoded patterns. This provides:
- Company-defined calculation relationships
- Standard taxonomy calculation relationships
- Comparison between both sources
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from ...loaders.mapped_reader import Statement, StatementFact, MappedStatements
from ..checks.constants import (
    CHECK_BALANCE_SHEET_EQUATION,
    CHECK_INCOME_LINKAGE,
    CHECK_CASH_FLOW_LINKAGE,
    CHECK_RETAINED_EARNINGS_ROLL,
    CHECK_COMMON_VALUES_CONSISTENCY,
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
    TOTAL_ASSETS_PATTERNS,
    TOTAL_LIABILITIES_PATTERNS,
    TOTAL_EQUITY_PATTERNS,
    LIABILITIES_AND_EQUITY_PATTERNS,
    NET_INCOME_PATTERNS,
    CASH_ENDING_PATTERNS,
)
from ...constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO
from .horizontal_checker import CheckResult

if TYPE_CHECKING:
    from ..formula_registry import FormulaRegistry


# Check name for XBRL-sourced calculations
CHECK_XBRL_CALCULATION = 'xbrl_calculation'
CHECK_XBRL_CALCULATION_COMPARISON = 'xbrl_calculation_comparison'


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

        Focuses on main statements (balance sheet, income, cash flow, equity)
        to verify fundamental accounting relationships.

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

        # Check balance sheet equation
        bs_result = self.check_balance_sheet_equation(statements)
        if bs_result:
            results.append(bs_result)

        # Check income statement linkage
        income_result = self.check_income_statement_linkage(statements)
        if income_result:
            results.append(income_result)

        # Check cash flow linkage
        cf_result = self.check_cash_flow_linkage(statements)
        if cf_result:
            results.append(cf_result)

        # Check common values consistency (main statements only)
        common_results = self.check_common_values_consistency(statements)
        results.extend(common_results)

        passed = sum(1 for r in results if r.passed)
        self.logger.info(f"Vertical checks complete: {passed}/{len(results)} passed")

        return results

    def check_balance_sheet_equation(
        self,
        statements: MappedStatements
    ) -> Optional[CheckResult]:
        """
        Verify: Total Assets = Total Liabilities + Total Equity

        This is the fundamental accounting equation that must always hold.

        Args:
            statements: MappedStatements object

        Returns:
            CheckResult or None if balance sheet not found
        """
        self.logger.debug("Checking balance sheet equation")

        # Find balance sheet
        balance_sheet = self._find_statement_by_type(statements, 'balance')
        if not balance_sheet:
            self.logger.info("No balance sheet found - skipping equation check")
            return None

        # Find key values
        total_assets = self._find_fact_value(balance_sheet, TOTAL_ASSETS_PATTERNS)
        total_liabilities = self._find_fact_value(balance_sheet, TOTAL_LIABILITIES_PATTERNS)
        total_equity = self._find_fact_value(balance_sheet, TOTAL_EQUITY_PATTERNS)
        liab_and_equity = self._find_fact_value(balance_sheet, LIABILITIES_AND_EQUITY_PATTERNS)

        # Try different equation forms
        if total_assets is not None:
            # Form 1: Assets = Liabilities + Equity
            if total_liabilities is not None and total_equity is not None:
                expected = total_liabilities + total_equity
                actual = total_assets
                passed = self._within_tolerance(expected, actual)

                return CheckResult(
                    check_name=CHECK_BALANCE_SHEET_EQUATION,
                    check_type='vertical',
                    passed=passed,
                    severity=SEVERITY_CRITICAL if not passed else SEVERITY_INFO,
                    message=f"Balance sheet equation: Assets ({actual:,.0f}) = Liabilities ({total_liabilities:,.0f}) + Equity ({total_equity:,.0f})",
                    expected_value=expected,
                    actual_value=actual,
                    difference=abs(expected - actual),
                    details={
                        'total_assets': total_assets,
                        'total_liabilities': total_liabilities,
                        'total_equity': total_equity,
                        'statement': balance_sheet.name,
                    }
                )

            # Form 2: Assets = Liabilities and Equity (single line item)
            elif liab_and_equity is not None:
                passed = self._within_tolerance(liab_and_equity, total_assets)

                return CheckResult(
                    check_name=CHECK_BALANCE_SHEET_EQUATION,
                    check_type='vertical',
                    passed=passed,
                    severity=SEVERITY_CRITICAL if not passed else SEVERITY_INFO,
                    message=f"Balance sheet equation: Assets ({total_assets:,.0f}) = Liabilities and Equity ({liab_and_equity:,.0f})",
                    expected_value=liab_and_equity,
                    actual_value=total_assets,
                    difference=abs(liab_and_equity - total_assets),
                    details={
                        'total_assets': total_assets,
                        'liabilities_and_equity': liab_and_equity,
                        'statement': balance_sheet.name,
                    }
                )

        # Could not verify equation
        return CheckResult(
            check_name=CHECK_BALANCE_SHEET_EQUATION,
            check_type='vertical',
            passed=True,  # Can't fail if we can't verify
            severity=SEVERITY_INFO,
            message="Could not locate all balance sheet equation components",
            details={
                'total_assets_found': total_assets is not None,
                'total_liabilities_found': total_liabilities is not None,
                'total_equity_found': total_equity is not None,
            }
        )

    def check_income_statement_linkage(
        self,
        statements: MappedStatements
    ) -> Optional[CheckResult]:
        """
        Verify: Net Income appears in both Income Statement and flows to Equity.

        Args:
            statements: MappedStatements object

        Returns:
            CheckResult or None
        """
        self.logger.debug("Checking income statement linkage")

        # Find income statement
        income_stmt = self._find_statement_by_type(statements, 'income')
        if not income_stmt:
            self.logger.info("No income statement found - skipping linkage check")
            return None

        # Find net income in income statement
        net_income_is = self._find_fact_value(income_stmt, NET_INCOME_PATTERNS)
        if net_income_is is None:
            return CheckResult(
                check_name=CHECK_INCOME_LINKAGE,
                check_type='vertical',
                passed=True,
                severity=SEVERITY_INFO,
                message="Net income not found in income statement"
            )

        # Find equity/comprehensive income statement
        equity_stmt = self._find_statement_by_type(statements, 'equity')
        comp_income_stmt = self._find_statement_by_type(statements, 'comprehensive')

        # Look for net income in equity changes
        net_income_eq = None
        if equity_stmt:
            net_income_eq = self._find_fact_value(equity_stmt, NET_INCOME_PATTERNS)
        if net_income_eq is None and comp_income_stmt:
            net_income_eq = self._find_fact_value(comp_income_stmt, NET_INCOME_PATTERNS)

        if net_income_eq is not None:
            passed = self._within_tolerance(net_income_is, net_income_eq)

            return CheckResult(
                check_name=CHECK_INCOME_LINKAGE,
                check_type='vertical',
                passed=passed,
                severity=SEVERITY_WARNING if not passed else SEVERITY_INFO,
                message=f"Net income linkage: IS ({net_income_is:,.0f}) vs Equity/CI ({net_income_eq:,.0f})",
                expected_value=net_income_is,
                actual_value=net_income_eq,
                difference=abs(net_income_is - net_income_eq) if net_income_eq else None,
                details={
                    'income_statement_net_income': net_income_is,
                    'equity_statement_net_income': net_income_eq,
                }
            )

        return CheckResult(
            check_name=CHECK_INCOME_LINKAGE,
            check_type='vertical',
            passed=True,
            severity=SEVERITY_INFO,
            message=f"Net income found in IS ({net_income_is:,.0f}), could not verify linkage to equity"
        )

    def check_cash_flow_linkage(
        self,
        statements: MappedStatements
    ) -> Optional[CheckResult]:
        """
        Verify: Ending Cash in Cash Flow = Cash in Balance Sheet

        Args:
            statements: MappedStatements object

        Returns:
            CheckResult or None
        """
        self.logger.debug("Checking cash flow linkage")

        # Find cash flow statement
        cash_flow = self._find_statement_by_type(statements, 'cash')
        balance_sheet = self._find_statement_by_type(statements, 'balance')

        if not cash_flow:
            self.logger.info("No cash flow statement found - skipping linkage check")
            return None

        if not balance_sheet:
            self.logger.info("No balance sheet found - skipping cash linkage check")
            return None

        # Find ending cash in cash flow
        cf_ending_cash = self._find_fact_value(cash_flow, CASH_ENDING_PATTERNS)

        # Find cash in balance sheet
        bs_cash = self._find_fact_value(balance_sheet, CASH_ENDING_PATTERNS)

        if cf_ending_cash is not None and bs_cash is not None:
            passed = self._within_tolerance(cf_ending_cash, bs_cash)

            return CheckResult(
                check_name=CHECK_CASH_FLOW_LINKAGE,
                check_type='vertical',
                passed=passed,
                severity=SEVERITY_WARNING if not passed else SEVERITY_INFO,
                message=f"Cash linkage: CF ending ({cf_ending_cash:,.0f}) vs BS cash ({bs_cash:,.0f})",
                expected_value=cf_ending_cash,
                actual_value=bs_cash,
                difference=abs(cf_ending_cash - bs_cash),
                details={
                    'cash_flow_ending': cf_ending_cash,
                    'balance_sheet_cash': bs_cash,
                }
            )

        return CheckResult(
            check_name=CHECK_CASH_FLOW_LINKAGE,
            check_type='vertical',
            passed=True,
            severity=SEVERITY_INFO,
            message="Could not locate cash values in both statements for linkage check",
            details={
                'cf_cash_found': cf_ending_cash is not None,
                'bs_cash_found': bs_cash is not None,
            }
        )

    def check_common_values_consistency(
        self,
        statements: MappedStatements
    ) -> list[CheckResult]:
        """
        Check that common values appear consistently across MAIN statements.

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

                try:
                    value = float(fact.value)
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
        source: str = 'company'
    ) -> list[CheckResult]:
        """
        Verify calculations using XBRL-sourced formulas.

        Uses FormulaRegistry instead of hardcoded patterns.
        This is the preferred method when registry is available.

        Args:
            statements: MappedStatements object
            source: 'company' or 'taxonomy' for which formulas to use

        Returns:
            List of CheckResult for each calculation verified
        """
        if not self.formula_registry:
            self.logger.warning(
                "FormulaRegistry not available - cannot run XBRL calculations"
            )
            return []

        # Import here to avoid circular imports
        from .calculation_verifier import CalculationVerifier

        verifier = CalculationVerifier(
            self.formula_registry,
            self.calculation_tolerance,
            self.rounding_tolerance
        )

        # Run verification
        results = verifier.verify_all_calculations(statements, source)

        # Convert to CheckResult format
        check_results = verifier.to_check_results(results, CHECK_XBRL_CALCULATION)

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

    def check_all_with_xbrl(
        self,
        statements: MappedStatements,
        include_legacy: bool = True
    ) -> list[CheckResult]:
        """
        Run all checks including XBRL-sourced calculations.

        When FormulaRegistry is available, runs both:
        - XBRL calculation verification (preferred)
        - Legacy pattern-based checks (optional, for comparison)

        Args:
            statements: MappedStatements object
            include_legacy: Whether to include legacy pattern-based checks

        Returns:
            List of all CheckResult objects
        """
        results = []

        # XBRL-sourced calculations (if registry available)
        if self.formula_registry:
            xbrl_results = self.check_xbrl_calculations_dual(statements)
            results.extend(xbrl_results)
            self.logger.info(f"Added {len(xbrl_results)} XBRL-sourced check results")

        # Legacy checks (optional, for comparison or fallback)
        if include_legacy or not self.formula_registry:
            legacy_results = self.check_all(statements)
            # Mark legacy results
            for result in legacy_results:
                if result.details is None:
                    result.details = {}
                result.details['verification_method'] = 'legacy_patterns'
            results.extend(legacy_results)
            self.logger.info(f"Added {len(legacy_results)} legacy check results")

        return results

    def _find_statement_by_type(
        self,
        statements: MappedStatements,
        statement_type: str
    ) -> Optional[Statement]:
        """
        Find a statement by type keyword.

        Prefers main statements (is_main_statement=True) over secondary statements.
        This ensures we're checking the primary financial statements, not
        parenthetical or detail files.

        Args:
            statements: MappedStatements object
            statement_type: Type keyword (balance, income, cash, equity, comprehensive)

        Returns:
            Statement or None if not found
        """
        type_lower = statement_type.lower()

        # First pass: look in main statements only
        for statement in statements.statements:
            if not statement.is_main_statement:
                continue

            name_lower = statement.name.lower()
            role_lower = (statement.role or '').lower()

            if type_lower in name_lower or type_lower in role_lower:
                return statement

        # Second pass: look in all statements if not found in main
        for statement in statements.statements:
            name_lower = statement.name.lower()
            role_lower = (statement.role or '').lower()

            if type_lower in name_lower or type_lower in role_lower:
                return statement

        return None

    def _find_fact_value(
        self,
        statement: Statement,
        patterns: list[str]
    ) -> Optional[float]:
        """Find a fact value matching any of the patterns."""
        for fact in statement.facts:
            if fact.is_abstract or fact.value is None:
                continue

            concept_lower = fact.concept.lower()

            for pattern in patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in concept_lower:
                    try:
                        return float(fact.value)
                    except (ValueError, TypeError):
                        continue

        return None

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


__all__ = ['VerticalChecker', 'CHECK_XBRL_CALCULATION', 'CHECK_XBRL_CALCULATION_COMPARISON']
