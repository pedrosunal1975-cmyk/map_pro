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
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

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
        rounding_tolerance: float = DEFAULT_ROUNDING_TOLERANCE
    ):
        """
        Initialize vertical checker.

        Args:
            calculation_tolerance: Percentage tolerance for calculations
            rounding_tolerance: Absolute tolerance for small differences
        """
        self.calculation_tolerance = calculation_tolerance
        self.rounding_tolerance = rounding_tolerance
        self.logger = logging.getLogger('process.vertical_checker')

    def check_all(self, statements: MappedStatements) -> list[CheckResult]:
        """
        Run all vertical checks on statements.

        Args:
            statements: MappedStatements from mapped_reader

        Returns:
            List of CheckResult objects
        """
        self.logger.info("Running vertical checks")
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

        # Check common values consistency
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
        Check that common values appear consistently across statements.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for inconsistencies found
        """
        results = []

        # Build map of concept -> values across all statements
        concept_values: dict[str, list[tuple[str, float]]] = {}

        for statement in statements.statements:
            for fact in statement.facts:
                if fact.is_abstract or fact.value is None:
                    continue

                try:
                    value = float(fact.value)
                except (ValueError, TypeError):
                    continue

                concept = fact.concept
                if concept not in concept_values:
                    concept_values[concept] = []
                concept_values[concept].append((statement.name, value))

        # Check for inconsistencies
        for concept, values in concept_values.items():
            if len(values) > 1:
                unique_values = set(v for _, v in values)
                if len(unique_values) > 1:
                    # Check if differences are within tolerance
                    min_val = min(unique_values)
                    max_val = max(unique_values)

                    if not self._within_tolerance(min_val, max_val):
                        results.append(CheckResult(
                            check_name=CHECK_COMMON_VALUES_CONSISTENCY,
                            check_type='vertical',
                            passed=False,
                            severity=SEVERITY_WARNING,
                            message=f"Inconsistent values for {concept} across statements",
                            difference=max_val - min_val,
                            details={
                                'concept': concept,
                                'occurrences': [
                                    {'statement': stmt, 'value': val}
                                    for stmt, val in values
                                ],
                            }
                        ))

        if not results:
            results.append(CheckResult(
                check_name=CHECK_COMMON_VALUES_CONSISTENCY,
                check_type='vertical',
                passed=True,
                severity=SEVERITY_INFO,
                message="Common values are consistent across statements"
            ))

        return results

    def _find_statement_by_type(
        self,
        statements: MappedStatements,
        statement_type: str
    ) -> Optional[Statement]:
        """Find a statement by type keyword."""
        type_lower = statement_type.lower()

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


__all__ = ['VerticalChecker']
