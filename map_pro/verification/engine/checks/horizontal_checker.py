# Path: verification/engine/checks/horizontal_checker.py
"""
Horizontal Checker for Verification Module

Validates within a single statement - checks calculation consistency.
Compares facts against company-declared calculation relationships.

HORIZONTAL CHECK (Correctness):
Within one statement, verify:
1. Calculation relationships (e.g., Assets = Liabilities + Equity)
2. Sum totals match detail items
3. Sign conventions are consistent

Source of truth: Company's calculation linkbase.
We check if company's facts match their own declared calculations.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ...loaders.mapped_reader import Statement, StatementFact, MappedStatements
from ...loaders.xbrl_reader import CalculationNetwork, CalculationArc
from ..checks.constants import (
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_TOTAL_RECONCILIATION,
    CHECK_SIGN_CONVENTION,
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

    Checks calculation consistency using company-declared
    calculation linkbase relationships.

    Example:
        checker = HorizontalChecker()
        results = checker.check_all(statements, calc_networks)
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
        Initialize horizontal checker.

        Args:
            calculation_tolerance: Percentage tolerance for calculations
            rounding_tolerance: Absolute tolerance for small differences
        """
        self.calculation_tolerance = calculation_tolerance
        self.rounding_tolerance = rounding_tolerance
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

        # Check calculation consistency
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

        For each calculation relationship company declared:
        - Find parent fact value
        - Find all child fact values
        - Apply weights (+1 or -1)
        - Check if sum matches parent

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

        # Build fact lookup by concept
        fact_lookup = self._build_fact_lookup(statements)

        for network in calc_networks:
            # Group arcs by parent
            parent_children = self._group_arcs_by_parent(network.arcs)

            for parent_concept, children in parent_children.items():
                result = self._verify_calculation(
                    parent_concept,
                    children,
                    fact_lookup,
                    network.role
                )
                if result:
                    results.append(result)

        return results

    def check_duplicate_facts(self, statements: MappedStatements) -> list[CheckResult]:
        """
        Check for duplicate facts with smart classification.

        Distinguishes between:
        1. CRITICAL: Same fact, same statement, different values (genuine issue)
        2. WARNING: Same fact, different statements, different values (possible issue)
        3. INFO: Same fact, same value across statements (healthy/expected)

        Cross-statement duplicates with identical values are expected and healthy
        (e.g., Net Income appears in both Income Statement and Cash Flow Statement).

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for duplicates found
        """
        results = []

        # Track duplicates within same statement (CRITICAL)
        intra_statement_issues = []

        # Track duplicates across statements
        cross_statement_facts: dict[str, list[tuple[str, any, StatementFact]]] = {}

        for statement in statements.statements:
            statement_name = statement.name or 'Unknown'

            # Group facts by concept and period WITHIN this statement
            fact_groups: dict[str, list[StatementFact]] = {}

            for fact in statement.facts:
                if fact.is_abstract:
                    continue

                key = f"{fact.concept}|{fact.period_end}|{fact.context_id or ''}"

                # Track for intra-statement check
                if key not in fact_groups:
                    fact_groups[key] = []
                fact_groups[key].append(fact)

                # Track for cross-statement check
                cross_key = f"{fact.concept}|{fact.period_end}"
                if cross_key not in cross_statement_facts:
                    cross_statement_facts[cross_key] = []
                cross_statement_facts[cross_key].append((statement_name, fact.value, fact))

            # Check for duplicates with different values WITHIN same statement
            for key, facts in fact_groups.items():
                if len(facts) > 1:
                    values = [f.value for f in facts if f.value is not None]
                    unique_values = set(str(v) for v in values)

                    if len(unique_values) > 1:
                        # CRITICAL: Same statement, different values
                        intra_statement_issues.append({
                            'concept': facts[0].concept,
                            'statement': statement_name,
                            'values': list(unique_values),
                            'count': len(facts),
                        })

        # Report intra-statement issues (CRITICAL)
        if intra_statement_issues:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=False,
                severity=SEVERITY_CRITICAL,
                message=f"{len(intra_statement_issues)} duplicate facts with conflicting values within same statement",
                details={
                    'duplicates': intra_statement_issues[:20],
                    'total_issues': len(intra_statement_issues),
                    'issue_type': 'intra_statement_conflict',
                }
            ))

        # Analyze cross-statement duplicates
        cross_statement_conflicts = []
        cross_statement_healthy = []

        for key, occurrences in cross_statement_facts.items():
            if len(occurrences) > 1:
                # Get unique statements where this fact appears
                statements_seen = set(s for s, v, f in occurrences)

                if len(statements_seen) > 1:
                    # Fact appears in multiple statements
                    values = [v for s, v, f in occurrences if v is not None]
                    unique_values = set(str(v) for v in values)

                    concept = occurrences[0][2].concept

                    if len(unique_values) > 1:
                        # Different values across statements - WARNING
                        cross_statement_conflicts.append({
                            'concept': concept,
                            'statements': list(statements_seen),
                            'values': list(unique_values),
                        })
                    else:
                        # Same value across statements - HEALTHY
                        cross_statement_healthy.append({
                            'concept': concept,
                            'statements': list(statements_seen),
                            'value': values[0] if values else None,
                        })

        # Report cross-statement conflicts (WARNING)
        if cross_statement_conflicts:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=False,
                severity=SEVERITY_WARNING,
                message=f"{len(cross_statement_conflicts)} facts with different values across statements",
                details={
                    'conflicts': cross_statement_conflicts[:20],
                    'total_conflicts': len(cross_statement_conflicts),
                    'issue_type': 'cross_statement_conflict',
                }
            ))

        # Report healthy cross-statement duplicates (INFO - passing)
        if cross_statement_healthy:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=True,
                severity=SEVERITY_INFO,
                message=f"{len(cross_statement_healthy)} facts appear consistently across multiple statements (expected)",
                details={
                    'healthy_duplicates': cross_statement_healthy[:10],
                    'total_healthy': len(cross_statement_healthy),
                    'issue_type': 'cross_statement_consistent',
                }
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

        Uses fact hierarchy (depth/order) to identify parent-child relationships.

        Args:
            statements: MappedStatements object

        Returns:
            List of CheckResult for total reconciliation
        """
        results = []

        for statement in statements.statements:
            # Find facts marked as totals
            total_facts = [f for f in statement.facts if f.is_total and not f.is_abstract]

            for total_fact in total_facts:
                if total_fact.value is None:
                    continue

                try:
                    total_value = float(total_fact.value)
                except (ValueError, TypeError):
                    continue

                # Find child facts (facts with depth > total's depth that come before it)
                children = self._find_child_facts(statement.facts, total_fact)

                if children:
                    child_sum = sum(
                        float(f.value) for f in children
                        if f.value is not None and not f.is_abstract
                    )

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

    def _build_fact_lookup(
        self,
        statements: MappedStatements
    ) -> dict[str, list[StatementFact]]:
        """Build lookup dictionary from concept to facts."""
        lookup: dict[str, list[StatementFact]] = {}

        for statement in statements.statements:
            for fact in statement.facts:
                if fact.is_abstract:
                    continue

                concept = fact.concept
                if concept not in lookup:
                    lookup[concept] = []
                lookup[concept].append(fact)

                # Also index without namespace prefix
                if ':' in concept:
                    local_name = concept.split(':')[-1]
                    if local_name not in lookup:
                        lookup[local_name] = []
                    lookup[local_name].append(fact)

        return lookup

    def _group_arcs_by_parent(
        self,
        arcs: list[CalculationArc]
    ) -> dict[str, list[CalculationArc]]:
        """Group calculation arcs by parent concept."""
        groups: dict[str, list[CalculationArc]] = {}

        for arc in arcs:
            parent = arc.parent_concept
            if parent not in groups:
                groups[parent] = []
            groups[parent].append(arc)

        return groups

    def _verify_calculation(
        self,
        parent_concept: str,
        children: list[CalculationArc],
        fact_lookup: dict[str, list[StatementFact]],
        role: str
    ) -> Optional[CheckResult]:
        """Verify a single calculation relationship."""
        # Find parent fact value
        parent_facts = fact_lookup.get(parent_concept, [])
        if not parent_facts:
            # Try without namespace
            if ':' in parent_concept:
                local_name = parent_concept.split(':')[-1]
                parent_facts = fact_lookup.get(local_name, [])

        if not parent_facts:
            return None  # No fact for this calculation

        # Get parent value (use first non-None value)
        parent_value = None
        for pf in parent_facts:
            if pf.value is not None:
                try:
                    parent_value = float(pf.value)
                    break
                except (ValueError, TypeError):
                    continue

        if parent_value is None:
            return None

        # Calculate sum of children with weights
        calculated_sum = 0.0
        child_details = []

        for arc in children:
            child_concept = arc.child_concept
            child_facts = fact_lookup.get(child_concept, [])

            if not child_facts and ':' in child_concept:
                local_name = child_concept.split(':')[-1]
                child_facts = fact_lookup.get(local_name, [])

            for cf in child_facts:
                if cf.value is not None:
                    try:
                        child_value = float(cf.value)
                        weighted_value = child_value * arc.weight
                        calculated_sum += weighted_value
                        child_details.append({
                            'concept': child_concept,
                            'value': child_value,
                            'weight': arc.weight,
                            'weighted': weighted_value,
                        })
                        break  # Use first value found
                    except (ValueError, TypeError):
                        continue

        if not child_details:
            return None  # No child values found

        # Check if calculation matches
        diff = abs(parent_value - calculated_sum)
        passed = self._within_tolerance(parent_value, calculated_sum)

        severity = SEVERITY_INFO if passed else SEVERITY_CRITICAL

        return CheckResult(
            check_name=CHECK_CALCULATION_CONSISTENCY,
            check_type='horizontal',
            passed=passed,
            severity=severity,
            message=f"Calculation check for {parent_concept}: expected {calculated_sum:.2f}, found {parent_value:.2f}",
            expected_value=calculated_sum,
            actual_value=parent_value,
            difference=diff,
            details={
                'parent_concept': parent_concept,
                'role': role,
                'children': child_details,
            }
        )

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

            # Child should have greater depth and come before total
            if fact_depth > total_depth and fact_order < total_order:
                children.append(fact)

        return children

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


__all__ = ['HorizontalChecker', 'CheckResult']
