# Path: verification/engine/checks/horizontal_checker.py
"""
Horizontal Checker for Verification Module

Validates within a single statement - checks calculation consistency.
Uses company-declared calculation linkbase as the ONLY source of formulas.

HORIZONTAL CHECK (Correctness):
Within one statement, verify:
1. Calculation relationships (e.g., Assets = Liabilities + Equity)
2. Sum totals match detail items

IMPORTANT PRINCIPLES:
- NO hardcoded formulas - all rules come from company XBRL files
- C-Equal compliance: only compare facts with same context_id
- U-Equal compliance: only compare facts with same unit
- Proper binding: skip calculations where conditions aren't met
- Proper duplicate handling: per XBRL Duplicates Guidance
- Sign handling: applies XBRL iXBRL sign attributes when present

Source of truth: Company's calculation linkbase.
"""

import logging
from pathlib import Path
from typing import Optional

from ...loaders.mapped_reader import MappedStatements
from ...loaders.xbrl_reader import CalculationNetwork, CalculationArc
from .c_equal import CEqual, FactGroups
from .binding_checker import BindingChecker
from .decimal_tolerance import DecimalTolerance
from .sign_weight_handler import SignWeightHandler
from .check_result import CheckResult
from .instance_document_finder import InstanceDocumentFinder
from .calculation_verifier_horizontal import CalculationVerifierHorizontal
from .duplicate_fact_checker import DuplicateFactChecker
from .constants import CHECK_CALCULATION_CONSISTENCY, CHECK_DUPLICATE_FACTS
from .role_scoping import group_arcs_by_role_and_parent
from ...constants import SEVERITY_CRITICAL, SEVERITY_INFO


# Configuration constants
CONTEXT_COUNT_MINIMUM = 0  # Minimum contexts needed for checks
MAX_INCONSISTENT_DUPLICATES_DISPLAY = 20  # Max duplicates to show in inline results
MAX_MULTI_ROLE_PARENTS_LOG = 1  # Minimum multi-role parents to log info message


class HorizontalChecker:
    """
    Validates calculation consistency within statements.

    Uses:
    - CEqual for context-based fact grouping
    - BindingChecker to determine if calculations should bind
    - DecimalTolerance for XBRL-compliant value comparison
    - SignWeightHandler for iXBRL sign attribute handling

    All calculation rules come from company's calculation linkbase.
    No hardcoded formulas.
    """

    def __init__(self):
        """Initialize horizontal checker with required components."""
        self.c_equal = CEqual()
        self.binding_checker = BindingChecker()
        self.decimal_tolerance = DecimalTolerance()
        self.sign_handler = SignWeightHandler()
        self.instance_finder = InstanceDocumentFinder()
        self.calculation_verifier = CalculationVerifierHorizontal(
            self.decimal_tolerance, self.sign_handler
        )
        self.duplicate_checker = DuplicateFactChecker(self.c_equal)
        self.logger = logging.getLogger('process.horizontal_checker')

    def check_all(
        self,
        statements: MappedStatements,
        calc_networks: list[CalculationNetwork],
        filing_path: Path = None
    ) -> list[CheckResult]:
        """
        Run all horizontal checks on statements.

        Args:
            statements: MappedStatements from mapped_reader
            calc_networks: Calculation networks from company's XBRL files
            filing_path: Optional path to XBRL filing directory for sign corrections

        Returns:
            List of CheckResult objects
        """
        self.logger.info("Running horizontal checks")
        results = []

        # Load sign corrections from instance document
        sign_corrections_count = self._load_sign_corrections(filing_path)

        # Check calculation consistency using company-declared formulas
        calc_results = self.check_calculation_consistency(statements, calc_networks)
        results.extend(calc_results)

        # Check for duplicate facts
        dup_results = self.duplicate_checker.check_duplicate_facts(statements)
        results.extend(dup_results)

        # Summary
        self._log_summary(results, sign_corrections_count)

        return results

    def _load_sign_corrections(self, filing_path: Optional[Path]) -> int:
        """
        Load sign corrections from XBRL instance document.

        Args:
            filing_path: Path to filing directory

        Returns:
            Number of sign corrections loaded
        """
        self.sign_handler.clear()
        sign_corrections_count = 0

        if filing_path:
            instance_file = self.instance_finder.find_instance_document(Path(filing_path))
            if instance_file:
                sign_corrections_count = self.sign_handler.parse_instance_document(instance_file)
                self.logger.info(f"Parsed {sign_corrections_count} sign corrections from instance document")

        return sign_corrections_count

    def _log_summary(self, results: list[CheckResult], sign_corrections_count: int) -> None:
        """
        Log summary of horizontal check results.

        Args:
            results: List of check results
            sign_corrections_count: Number of sign corrections applied
        """
        passed = sum(1 for r in results if r.passed and not r.skipped)
        failed = sum(1 for r in results if not r.passed and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)

        self.logger.info(
            f"Horizontal checks complete: {passed} passed, {failed} failed, {skipped} skipped"
        )
        if sign_corrections_count > 0:
            self.logger.info(f"Sign corrections applied from XBRL instance: {sign_corrections_count}")

    def check_calculation_consistency(
        self,
        statements: MappedStatements,
        calc_networks: list[CalculationNetwork]
    ) -> list[CheckResult]:
        """
        Check if facts match company-declared calculation relationships.

        Uses company's calculation linkbase as the ONLY source of formulas.
        Weights (signs) come from the company's declarations.

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

        # Group facts by context_id (strict c-equal compliance)
        fact_groups = self.c_equal.group_facts(statements)

        if fact_groups.context_count == CONTEXT_COUNT_MINIMUM:
            self.logger.info("No facts found for calculation check")
            return results

        self.logger.info(
            f"Grouped {fact_groups.total_facts} facts into "
            f"{fact_groups.context_count} contexts"
        )

        # Check for inconsistent duplicates upfront
        inconsistent = fact_groups.find_inconsistent_duplicates()
        if inconsistent:
            results.append(CheckResult(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=False,
                severity=SEVERITY_CRITICAL,
                message=f"{len(inconsistent)} concepts have inconsistent duplicate values",
                details={'inconsistent_duplicates': inconsistent[:MAX_INCONSISTENT_DUPLICATES_DISPLAY]},
            ))

        # XBRL Calculations 1.1: Group arcs by (role, parent) to enforce role scoping
        role_parent_groups = group_arcs_by_role_and_parent(calc_networks)

        self.logger.info(
            f"Role-scoped grouping: {len(role_parent_groups)} unique (role, parent) combinations"
        )

        # Log multi-role parents for diagnostics
        self._log_multi_role_parents(role_parent_groups)

        # Process each (role, parent) combination separately
        for (role, parent_concept), arcs in role_parent_groups.items():
            calc_results = self._verify_calculation_for_role_parent(
                parent_concept, arcs, role, fact_groups
            )
            results.extend(calc_results)

        return results

    def _log_multi_role_parents(self, role_parent_groups: dict) -> None:
        """
        Log information about parents that appear in multiple roles.

        Args:
            role_parent_groups: Dictionary of (role, parent) -> arcs
        """
        parent_to_roles: dict[str, list[str]] = {}
        for (role, parent), _ in role_parent_groups.items():
            if parent not in parent_to_roles:
                parent_to_roles[parent] = []
            parent_to_roles[parent].append(role)
        
        multi_role_parents = {p: roles for p, roles in parent_to_roles.items() if len(roles) > 1}
        if len(multi_role_parents) >= MAX_MULTI_ROLE_PARENTS_LOG:
            self.logger.info(
                f"Found {len(multi_role_parents)} parents in multiple roles "
                f"(role scoping prevents mixing)"
            )

    def _verify_calculation_for_role_parent(
        self,
        parent_concept: str,
        arcs: list[CalculationArc],
        role: str,
        fact_groups: FactGroups
    ) -> list[CheckResult]:
        """
        Verify calculation for a specific (role, parent) combination.

        Args:
            parent_concept: Parent concept name
            arcs: Calculation arcs for this parent in this role
            role: Extended link role
            fact_groups: Grouped facts by context

        Returns:
            List of CheckResult, one per context
        """
        # Convert arcs to (child, weight) tuples with normalized names
        children = [
            (self.c_equal.normalize_concept(arc.child_concept), arc.weight)
            for arc in arcs
        ]

        parent_norm = self.c_equal.normalize_concept(parent_concept)

        # Verify across all contexts where parent exists
        return self._verify_calculation_in_contexts(
            parent_norm, parent_concept, children, arcs, fact_groups, role
        )

    def _verify_calculation_in_contexts(
        self,
        parent_norm: str,
        parent_original: str,
        children: list[tuple[str, float]],
        arcs: list[CalculationArc],
        fact_groups: FactGroups,
        role: str
    ) -> list[CheckResult]:
        """
        Verify a calculation across all contexts where parent exists.

        For each context:
        1. Check if calculation binds (all conditions met)
        2. If doesn't bind strictly, try dimensional fallback
        3. If binds, verify the calculation
        4. If doesn't bind after fallback, skip (not fail)

        Returns one CheckResult per context.
        """
        results = []

        # Find all contexts where parent exists
        contexts_with_parent = fact_groups.get_contexts_with_concept(parent_norm)

        if not contexts_with_parent:
            return results

        # Build all_facts lookup for dimensional fallback
        all_facts = fact_groups.get_all_facts_by_concept()

        for context_id in contexts_with_parent:
            context_group = fact_groups.get_context(context_id)
            if not context_group:
                continue

            # Check if calculation binds - try with dimensional fallback
            binding = self.binding_checker.check_binding_with_fallback(
                context_group, parent_norm, children, all_facts
            )

            if not binding.binds:
                # Calculation doesn't bind - skip (not fail)
                results.append(CheckResult(
                    check_name=CHECK_CALCULATION_CONSISTENCY,
                    check_type='horizontal',
                    passed=None,  # Neither pass nor fail
                    skipped=True,
                    severity=SEVERITY_INFO,
                    message=f"Skipped: {binding.message}",
                    details={
                        'parent_concept': parent_original,
                        'role': role,
                        'context_id': context_id,
                        'skip_reason': binding.status.value,
                        'children_missing': binding.children_missing,
                    }
                ))
                continue

            # Calculation binds - verify it
            result = self.calculation_verifier.verify_bound_calculation(
                binding, context_group, parent_original, role, context_id
            )
            results.append(result)

        return results


__all__ = ['HorizontalChecker', 'CheckResult']
