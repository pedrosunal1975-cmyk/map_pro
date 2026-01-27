# Path: verification/engine/checks/horizontal_checker.py
"""
Horizontal Checker for Verification Module

Validates within a single statement - checks calculation consistency.
Uses the C-Equal module for proper XBRL context-based fact grouping.

HORIZONTAL CHECK (Correctness):
Within one statement, verify:
1. Calculation relationships (e.g., Assets = Liabilities + Equity)
2. Sum totals match detail items
3. Duplicate fact detection

Source of truth: Company's calculation linkbase.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ...loaders.mapped_reader import Statement, StatementFact, MappedStatements
from ...loaders.xbrl_reader import CalculationNetwork, CalculationArc
from .c_equal import CEqual, FactGroups
from .constants import (
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_TOTAL_RECONCILIATION,
    CHECK_DUPLICATE_FACTS,
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
)
from ...constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO


@dataclass
class CheckResult:
    """
    Result of a single verification check.

    Attributes:
        check_name: Name of the check performed
        check_type: Type of check (horizontal, vertical, library)
        passed: Whether the check passed
        severity: Severity level if failed (critical, warning, info)
        message: Human-readable description
        expected_value: Expected value (for calculation checks)
        actual_value: Actual value found
        difference: Numeric difference
        details: Additional context
    """
    check_name: str
    check_type: str = 'horizontal'
    passed: bool = True
    severity: str = SEVERITY_INFO
    message: str = ''
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    details: dict = field(default_factory=dict)


class HorizontalChecker:
    """
    Validates within a single statement.

    Uses C-Equal module for proper XBRL context-based verification.
    """

    def __init__(
        self,
        calculation_tolerance: float = DEFAULT_CALCULATION_TOLERANCE,
        rounding_tolerance: float = DEFAULT_ROUNDING_TOLERANCE
    ):
        """
        Initialize horizontal checker.

        Args:
            calculation_tolerance: Percentage tolerance for calculations
            rounding_tolerance: Absolute tolerance for small differences
        """
        self.calculation_tolerance = calculation_tolerance
        self.rounding_tolerance = rounding_tolerance
        self.c_equal = CEqual()
        self.logger = logging.getLogger('process.horizontal_checker')

    def check_all(
        self,
        statements: MappedStatements,
        calc_networks: list[CalculationNetwork]
    ) -> list[CheckResult]:
        """
        Run all horizontal checks on statements.

        Args:
            statements: MappedStatements from mapped_reader
            calc_networks: Calculation networks from xbrl_reader

        Returns:
            List of CheckResult objects
        """
        self.logger.info("Running horizontal checks")
        results = []

        # Check calculation consistency using C-Equal
        calc_results = self.check_calculation_consistency(statements, calc_networks)
        results.extend(calc_results)

        # Check for duplicate facts
        dup_results = self.check_duplicate_facts(statements)
        results.extend(dup_results)

        # Check total reconciliation
        total_results = self.check_total_reconciliation(statements)
        results.extend(total_results)

        passed = sum(1 for r in results if r.passed)
        self.logger.info(f"Horizontal checks complete: {passed}/{len(results)} passed")

        return results

    def check_calculation_consistency(
        self,
        statements: MappedStatements,
        calc_networks: list[CalculationNetwork]
    ) -> list[CheckResult]:
        """
        Check if facts match company-declared calculation relationships.

        Uses C-Equal module to group facts by context_id and verify
        calculations within each context.

        Args:
            statements: MappedStatements object
            calc_networks: List of CalculationNetwork from company linkbase

        Returns:
            List of CheckResult for each calculation relationship
        """
        results = []

        if not calc_networks:
            self.logger.info("No calculation networks provided - skipping calculation check")
            return results

        # Group facts by context_id using C-Equal
        fact_groups = self.c_equal.group_facts(statements, main_only=True)

        if fact_groups.context_count == 0:
            self.logger.info("No facts found for calculation check")
            return results

        self.logger.debug(
            f"Grouped {fact_groups.total_facts} facts into "
            f"{fact_groups.context_count} contexts"
        )

        # Process each calculation network
        for network in calc_networks:
            parent_children = self._group_arcs_by_parent(network.arcs)

            for parent_concept, children in parent_children.items():
                result = self._verify_calculation_across_contexts(
                    parent_concept, children, fact_groups, network.role
                )
                if result:
                    results.append(result)

        return results

    def _verify_calculation_across_contexts(
        self,
        parent_concept: str,
        children: list[CalculationArc],
        fact_groups: FactGroups,
        role: str
    ) -> Optional[CheckResult]:
        """
        Verify a calculation across all contexts where parent exists.

        Args:
            parent_concept: Parent concept name
            children: List of child calculation arcs
            fact_groups: FactGroups from C-Equal module
            role: Statement role

        Returns:
            CheckResult or None if no data
        """
        # Normalize parent concept
        parent_norm = self.c_equal.normalize_concept(parent_concept)

        # Normalize children
        children_norm = [
            (self.c_equal.normalize_concept(arc.child_concept), arc.weight, arc.child_concept)
            for arc in children
        ]

        # Find all contexts where parent exists
        contexts_with_parent = fact_groups.get_contexts_with_concept(parent_norm)

        if not contexts_with_parent:
            return None

        # Verify in each context
        context_results = []
        for context_id in contexts_with_parent:
            context_group = fact_groups.get_context(context_id)
            if not context_group:
                continue

            parent_value = context_group.get(parent_norm)
            if parent_value is None:
                continue

            # Calculate sum of children
            calculated_sum = 0.0
            child_details = []

            for child_norm, weight, original_name in children_norm:
                child_value = context_group.get(child_norm)
                if child_value is not None:
                    weighted = child_value * weight
                    calculated_sum += weighted
                    child_details.append({
                        'concept': original_name,
                        'value': child_value,
                        'weight': weight,
                        'weighted': weighted,
                    })

            if not child_details:
                continue

            # Check if calculation passes
            diff = abs(parent_value - calculated_sum)
            passed = self._within_tolerance(parent_value, calculated_sum)

            context_results.append({
                'context_id': context_id,
                'passed': passed,
                'parent_value': parent_value,
                'calculated_sum': calculated_sum,
                'difference': diff,
                'child_details': child_details,
            })

        if not context_results:
            return None

        # Aggregate results
        all_passed = all(r['passed'] for r in context_results)
        contexts_passed = sum(1 for r in context_results if r['passed'])
        first_result = context_results[0]

        severity = SEVERITY_INFO if all_passed else SEVERITY_CRITICAL

        message = (
            f"Calculation {parent_concept}: "
            f"expected {first_result['calculated_sum']:.2f}, "
            f"found {first_result['parent_value']:.2f}"
        )

        if len(context_results) > 1:
            message += f" [{contexts_passed}/{len(context_results)} contexts passed]"

        return CheckResult(
            check_name=CHECK_CALCULATION_CONSISTENCY,
            check_type='horizontal',
            passed=all_passed,
            severity=severity,
            message=message,
            expected_value=first_result['calculated_sum'],
            actual_value=first_result['parent_value'],
            difference=first_result['difference'],
            details={
                'parent_concept': parent_concept,
                'role': role,
                'contexts_verified': len(context_results),
                'contexts_passed': contexts_passed,
                'children': first_result['child_details'],
            }
        )

    def check_duplicate_facts(self, statements: MappedStatements) -> list[CheckResult]:
        """
        Check for duplicate facts with smart classification.

        Uses context_id to properly identify duplicates.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for duplicates found
        """
        results = []

        # Track facts by (concept, context_id) to find duplicates
        intra_statement_issues = []
        cross_statement_facts: dict[str, list[tuple[str, float, str]]] = {}

        for statement in statements.statements:
            if not statement.is_main_statement:
                continue

            statement_name = statement.name or 'Unknown'
            fact_in_statement: dict[str, list[tuple[float, str]]] = {}

            for fact in statement.facts:
                if fact.is_abstract or fact.value is None:
                    continue

                # Parse value
                value = self.c_equal.parse_value(fact.value)
                if value is None:
                    continue

                concept_norm = self.c_equal.normalize_concept(fact.concept)
                context_id = fact.context_id or fact.period_end or 'unknown'

                key = f"{concept_norm}|{context_id}"

                # Track within statement
                if key not in fact_in_statement:
                    fact_in_statement[key] = []
                fact_in_statement[key].append((value, fact.concept))

                # Track across statements
                cross_key = f"{concept_norm}|{context_id}"
                if cross_key not in cross_statement_facts:
                    cross_statement_facts[cross_key] = []
                cross_statement_facts[cross_key].append((statement_name, value, fact.concept))

            # Check for intra-statement conflicts
            for key, values in fact_in_statement.items():
                if len(values) > 1:
                    unique_values = set(v for v, _ in values)
                    if len(unique_values) > 1:
                        intra_statement_issues.append({
                            'concept': values[0][1],
                            'statement': statement_name,
                            'values': list(unique_values),
                            'count': len(values),
                        })

        # Report intra-statement issues (CRITICAL)
        if intra_statement_issues:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=False,
                severity=SEVERITY_CRITICAL,
                message=f"{len(intra_statement_issues)} duplicate facts with conflicting values",
                details={
                    'duplicates': intra_statement_issues[:20],
                    'total_issues': len(intra_statement_issues),
                }
            ))

        # Analyze cross-statement duplicates
        cross_conflicts = []
        cross_healthy = []

        for key, occurrences in cross_statement_facts.items():
            if len(occurrences) > 1:
                statements_seen = set(s for s, v, c in occurrences)
                if len(statements_seen) > 1:
                    values = [v for s, v, c in occurrences]
                    unique_values = set(values)

                    if len(unique_values) > 1:
                        cross_conflicts.append({
                            'concept': occurrences[0][2],
                            'statements': list(statements_seen),
                            'values': list(unique_values),
                        })
                    else:
                        cross_healthy.append({
                            'concept': occurrences[0][2],
                            'statements': list(statements_seen),
                            'value': values[0],
                        })

        if cross_conflicts:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=False,
                severity=SEVERITY_WARNING,
                message=f"{len(cross_conflicts)} facts with different values across statements",
                details={'conflicts': cross_conflicts[:20]}
            ))

        if cross_healthy:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=True,
                severity=SEVERITY_INFO,
                message=f"{len(cross_healthy)} facts appear consistently across statements",
                details={'healthy': cross_healthy[:10]}
            ))

        if not results:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=True,
                severity=SEVERITY_INFO,
                message="No duplicate fact issues found"
            ))

        return results

    def check_total_reconciliation(self, statements: MappedStatements) -> list[CheckResult]:
        """
        Check that items marked as totals equal sum of components.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for total reconciliation
        """
        results = []

        for statement in statements.statements:
            if not statement.is_main_statement:
                continue

            # Filter to non-abstract facts
            valid_facts = [f for f in statement.facts if not f.is_abstract]

            # Find facts marked as totals
            total_facts = [f for f in valid_facts if f.is_total]

            for total_fact in total_facts:
                total_value = self.c_equal.parse_value(total_fact.value)
                if total_value is None:
                    continue

                # Find child facts based on hierarchy
                children = self._find_child_facts(valid_facts, total_fact)

                # Filter to same context
                total_context = total_fact.context_id or total_fact.period_end or 'unknown'
                children = [
                    c for c in children
                    if (c.context_id or c.period_end or 'unknown') == total_context
                ]

                if children:
                    child_sum = 0.0
                    for child in children:
                        child_value = self.c_equal.parse_value(child.value)
                        if child_value is not None:
                            child_sum += child_value

                    diff = abs(total_value - child_sum)
                    passed = self._within_tolerance(total_value, child_sum)

                    results.append(CheckResult(
                        check_name=CHECK_TOTAL_RECONCILIATION,
                        check_type='horizontal',
                        passed=passed,
                        severity=SEVERITY_WARNING if not passed else SEVERITY_INFO,
                        message=f"Total {total_fact.concept}: expected {child_sum:.2f}, found {total_value:.2f}",
                        expected_value=child_sum,
                        actual_value=total_value,
                        difference=diff,
                        details={
                            'concept': total_fact.concept,
                            'statement': statement.name,
                            'context': total_context,
                            'child_count': len(children),
                        }
                    ))

        if not results:
            results.append(CheckResult(
                check_name=CHECK_TOTAL_RECONCILIATION,
                check_type='horizontal',
                passed=True,
                severity=SEVERITY_INFO,
                message="No total reconciliation issues found"
            ))

        return results

    def _group_arcs_by_parent(
        self,
        arcs: list[CalculationArc]
    ) -> dict[str, list[CalculationArc]]:
        """Group calculation arcs by parent concept."""
        groups: dict[str, list[CalculationArc]] = {}
        for arc in arcs:
            if arc.parent_concept not in groups:
                groups[arc.parent_concept] = []
            groups[arc.parent_concept].append(arc)
        return groups

    def _find_child_facts(
        self,
        facts: list[StatementFact],
        total_fact: StatementFact
    ) -> list[StatementFact]:
        """Find child facts for a total based on depth/order."""
        children = []
        total_depth = total_fact.depth
        total_order = total_fact.order or 0

        for fact in facts:
            if fact == total_fact or fact.is_abstract:
                continue

            fact_order = fact.order or 0
            fact_depth = fact.depth

            if fact_depth > total_depth and fact_order < total_order:
                children.append(fact)

        return children

    def _within_tolerance(self, expected: float, actual: float) -> bool:
        """Check if values are within acceptable tolerance."""
        if expected == 0 and actual == 0:
            return True

        diff = abs(expected - actual)

        if abs(expected) < LARGE_VALUE_THRESHOLD:
            return diff <= self.rounding_tolerance

        if expected != 0:
            pct_diff = diff / abs(expected)
            return pct_diff <= self.calculation_tolerance

        return diff <= self.rounding_tolerance


__all__ = ['HorizontalChecker', 'CheckResult']
