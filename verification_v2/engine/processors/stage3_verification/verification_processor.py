# Path: verification/engine/checks_v2/processors/stage3_verification/verification_processor.py
"""
Stage 3: Verification Processor

Performs verification checks on prepared data:
- Horizontal checks (calculation linkbase verification)
- Vertical checks (cross-statement consistency)
- Library checks (taxonomy conformance)

RESPONSIBILITY: Verify and report. All data is pre-validated by Stage 2.
Focus is on producing accurate verification results.

TOOLS USED:
- hierarchy/: BindingChecker for calculation binding rules
- calculation/: SumCalculator for weighted sum verification
- tolerance/: DecimalTolerance for value comparison
- sign/: SignLookup for sign corrections during verification

OUTPUT: VerificationResult with all check results and summary
"""

import logging
from datetime import datetime
from typing import Optional

from ..pipeline_data import (
    PreparationResult,
    VerificationResult,
    VerificationCheck,
    VerificationSummary,
    FactGroup,
)

# Import tools
from ...tools.hierarchy import BindingChecker
from ...tools.calculation import SumCalculator
from ...tools.tolerance import DecimalTolerance
from ...tools.sign import SignLookup
from ...tools.context import ContextGrouper, ContextGroup

# Import constants
from ...constants.tolerances import (
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    OVERSHOOT_ROUNDING_THRESHOLD,
)
from ...constants.check_names import (
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_DUPLICATE_FACTS,
    CHECK_SIGN_CONVENTION,
)


class VerificationProcessor:
    """
    Stage 3: Verifies prepared data and produces results.

    Performs verification using specialized tools:
    1. Horizontal checks - Verify calculation linkbase relationships
    2. Vertical checks - Verify cross-statement consistency
    3. Library checks - Verify taxonomy conformance

    Tools are configured based on filing characteristics.

    Usage:
        processor = VerificationProcessor()
        result = processor.verify(preparation_result)

        print(f"Score: {result.summary.score}")
        print(f"Critical issues: {result.summary.critical_issues}")
    """

    def __init__(self):
        self.logger = logging.getLogger('processors.stage3.verification')

        # Initialize tools with defaults
        self._binding_checker = BindingChecker(strategy='fallback')
        self._sum_calculator = SumCalculator()
        self._decimal_tolerance = DecimalTolerance()
        self._sign_lookup = None  # Set during verification

        # Configuration
        self._calculation_tolerance = DEFAULT_CALCULATION_TOLERANCE
        self._rounding_tolerance = DEFAULT_ROUNDING_TOLERANCE

    def set_calculation_tolerance(self, tolerance: float) -> None:
        """Set calculation tolerance (percentage)."""
        self._calculation_tolerance = tolerance

    def set_rounding_tolerance(self, tolerance: float) -> None:
        """Set rounding tolerance (absolute value)."""
        self._rounding_tolerance = tolerance

    def set_binding_strategy(self, strategy: str) -> None:
        """
        Set binding strategy.

        Options: 'strict', 'fallback'
        """
        self._binding_checker.set_strategy(strategy)

    def verify(self, preparation: PreparationResult) -> VerificationResult:
        """
        Verify prepared data.

        Args:
            preparation: PreparationResult from Stage 2

        Returns:
            VerificationResult with all checks
        """
        start_time = datetime.now()
        self.logger.info(
            f"Stage 3: Verifying {len(preparation.facts)} facts, "
            f"{len(preparation.calculations)} calculations"
        )

        result = VerificationResult(preparation=preparation)
        result.verification_timestamp = start_time.isoformat()

        # Set up sign lookup from preparation data
        self._setup_sign_lookup(preparation)

        # Step 1: Horizontal checks (calculation verification)
        self._run_horizontal_checks(preparation, result)

        # Step 2: Vertical checks (cross-statement consistency)
        self._run_vertical_checks(preparation, result)

        # Step 3: Library checks (taxonomy conformance)
        self._run_library_checks(preparation, result)

        # Build summary
        self._build_summary(result)

        # Calculate processing time
        end_time = datetime.now()
        result.processing_time_ms = (end_time - start_time).total_seconds() * 1000

        self.logger.info(
            f"Stage 3 complete: {result.summary.total_checks} checks, "
            f"score {result.summary.score:.1f}/100"
        )

        return result

    def _setup_sign_lookup(self, preparation: PreparationResult) -> None:
        """Set up sign lookup from prepared sign corrections."""
        self._sign_lookup = SignLookup()

        for (concept, context_id), correction in preparation.sign_corrections.items():
            self._sign_lookup.add_correction(concept, context_id, correction)

        self._sum_calculator.set_sign_lookup(self._sign_lookup)

    def _run_horizontal_checks(self, preparation: PreparationResult, result: VerificationResult) -> None:
        """Run horizontal (calculation) checks."""
        self.logger.info(f"Running horizontal checks on {len(preparation.calculations)} calculations")

        # Build context groups for binding checker
        context_groups = self._build_context_groups(preparation)

        for calc in preparation.calculations:
            # Find all contexts where parent exists
            parent_contexts = self._get_contexts_for_concept(
                calc.parent_concept, preparation
            )

            if not parent_contexts:
                # No facts for this calculation - skip
                continue

            # Verify in each context
            for context_id in parent_contexts:
                check = self._verify_calculation_in_context(
                    calc, context_id, context_groups, preparation
                )
                if check:
                    result.checks.append(check)
                    result.horizontal_checks.append(check)

        # Duplicate fact checks
        self._check_duplicates(preparation, result)

    def _verify_calculation_in_context(
        self,
        calc,
        context_id: str,
        context_groups: dict[str, ContextGroup],
        preparation: PreparationResult
    ) -> Optional[VerificationCheck]:
        """Verify a single calculation in a specific context."""
        ctx_group = context_groups.get(context_id)
        if not ctx_group:
            return None

        # Check binding using binding checker
        binding = self._binding_checker.check_binding_with_fallback(
            context_group=ctx_group,
            parent_concept=calc.parent_concept,
            children=calc.children,
            all_facts=preparation.all_facts_by_concept,
        )

        if not binding.binds:
            # Calculation doesn't bind - skip (not fail)
            return VerificationCheck(
                check_name=CHECK_CALCULATION_CONSISTENCY,
                check_type='horizontal',
                passed=False,
                severity='info',
                message=f"Skipped: {binding.message}",
                concept=calc.original_parent,
                context_id=context_id,
                role=calc.role,
                details={
                    'status': 'skipped',
                    'binding_status': binding.status.value,
                    'missing_children': binding.children_missing,
                },
            )

        # Calculate sum and compare
        sum_result = self._sum_calculator.calculate_and_compare(
            children=binding.children_found,
            parent_value=binding.parent_value,
            parent_decimals=binding.parent_decimals,
            parent_concept=calc.parent_concept,
            parent_context_id=context_id,
        )

        # Determine severity
        if sum_result.passed:
            severity = 'info'
        else:
            severity = self._determine_severity(
                sum_result.expected_sum,
                sum_result.actual_value,
                binding.children_missing
            )

        return VerificationCheck(
            check_name=CHECK_CALCULATION_CONSISTENCY,
            check_type='horizontal',
            passed=sum_result.passed,
            severity=severity,
            message=f"{calc.original_parent}: {sum_result.message}",
            expected_value=sum_result.expected_sum,
            actual_value=sum_result.actual_value,
            difference=sum_result.difference,
            concept=calc.original_parent,
            context_id=context_id,
            role=calc.role,
            details={
                'source': calc.source,
                'children_count': len(binding.children_found),
                'missing_children': binding.children_missing,
                'sign_corrections': sum_result.sign_corrections_applied,
            },
        )

    def _determine_severity(
        self,
        expected: float,
        actual: float,
        missing_children: list
    ) -> str:
        """Determine severity of a failed check."""
        if expected == 0 and actual == 0:
            return 'info'

        # Check for sign mismatch
        if expected != 0 and actual != 0:
            if (expected > 0) != (actual > 0):
                return 'critical'

        # Calculate magnitude difference
        exp_mag = abs(expected)
        act_mag = abs(actual)

        overshooting = exp_mag > act_mag
        undershooting = exp_mag < act_mag

        if overshooting:
            if act_mag > 0:
                overshoot_ratio = (exp_mag - act_mag) / act_mag
            else:
                overshoot_ratio = 1.0

            if overshoot_ratio <= OVERSHOOT_ROUNDING_THRESHOLD:
                return 'warning'
            else:
                return 'critical'
        elif undershooting and missing_children:
            return 'warning'
        else:
            return 'critical'

    def _check_duplicates(self, preparation: PreparationResult, result: VerificationResult) -> None:
        """Check for duplicate facts."""
        for key, dup_info in preparation.duplicates.items():
            concept, context_id = key.split(':', 1)

            severity = 'critical' if dup_info.is_inconsistent else 'warning'

            check = VerificationCheck(
                check_name=CHECK_DUPLICATE_FACTS,
                check_type='horizontal',
                passed=not dup_info.is_inconsistent,
                severity=severity,
                message=f"Duplicate facts for {concept}: {dup_info.duplicate_type.value}",
                concept=concept,
                context_id=context_id,
                details={
                    'duplicate_type': dup_info.duplicate_type.value,
                    'count': dup_info.count,
                    'values': dup_info.values,
                },
            )

            result.checks.append(check)
            result.horizontal_checks.append(check)

    def _run_vertical_checks(self, preparation: PreparationResult, result: VerificationResult) -> None:
        """Run vertical (cross-statement) checks."""
        # Placeholder for vertical checks
        # These check consistency across different statements
        self.logger.info("Running vertical checks")

    def _run_library_checks(self, preparation: PreparationResult, result: VerificationResult) -> None:
        """Run library (taxonomy) checks."""
        # Placeholder for library checks
        # These verify conformance to taxonomy definitions
        self.logger.info("Running library checks")

    def _build_context_groups(self, preparation: PreparationResult) -> dict[str, ContextGroup]:
        """Build ContextGroup objects for binding checker."""
        groups = {}

        for context_id, fact_group in preparation.fact_groups.items():
            # Create a ContextGroup using the grouper
            grouper = ContextGrouper()

            for concept, fact in fact_group.facts.items():
                grouper.add_fact(
                    concept=fact.concept,
                    value=fact.value,
                    context_id=fact.context_id,
                    unit=fact.unit,
                    decimals=fact.decimals,
                    original_name=fact.original_concept,
                )

            ctx_group = grouper.get_group(context_id)
            if ctx_group:
                groups[context_id] = ctx_group

        return groups

    def _get_contexts_for_concept(
        self,
        concept: str,
        preparation: PreparationResult
    ) -> list[str]:
        """Get all context IDs where a concept exists."""
        contexts = []
        if concept in preparation.all_facts_by_concept:
            for ctx_id, _, _, _ in preparation.all_facts_by_concept[concept]:
                if ctx_id not in contexts:
                    contexts.append(ctx_id)
        return contexts

    def _build_summary(self, result: VerificationResult) -> None:
        """Build verification summary."""
        summary = VerificationSummary()

        for check in result.checks:
            summary.total_checks += 1

            if check.passed:
                summary.passed += 1
            elif check.severity == 'info' and 'skipped' in check.message.lower():
                summary.skipped += 1
            else:
                summary.failed += 1

            if check.severity == 'critical':
                summary.critical_issues += 1
            elif check.severity == 'warning':
                summary.warning_issues += 1
                summary.warnings += 1
            elif check.severity == 'info':
                summary.info_issues += 1

        # Calculate score
        if summary.total_checks > 0:
            # Penalize critical issues heavily, warnings less so
            penalty = (summary.critical_issues * 10) + (summary.warning_issues * 2)
            raw_score = ((summary.passed + summary.skipped) / summary.total_checks) * 100
            summary.score = max(0, min(100, raw_score - penalty))
        else:
            summary.score = 100.0

        result.summary = summary


__all__ = ['VerificationProcessor']
