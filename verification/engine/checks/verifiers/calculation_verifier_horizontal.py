# Path: verification/engine/checks/calculation_verifier_horizontal.py
"""
Calculation Verification for Horizontal Checks

Handles verification of calculations within a single statement using
company-declared calculation relationships.

Uses C-Equal, binding rules, decimal tolerance, and sign corrections.
"""

import logging
from typing import Optional

from ..c_equal.c_equal import FactGroups, ContextGroup
from ..binding.binding_checker import BindingResult
from ..core.decimal_tolerance import DecimalTolerance
from ..handlers.sign_weight_handler import SignWeightHandler
from ..core.check_result import CheckResult
from ..core.constants import CHECK_CALCULATION_CONSISTENCY, OVERSHOOT_ROUNDING_THRESHOLD
from ....constants import SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_INFO


# Configuration constants
INITIAL_EXPECTED_SUM = 0.0  # Starting value for calculation sum
DEFAULT_OVERSHOOT_RATIO = 1.0  # Default when parent magnitude is zero
MAX_MISSING_CHILDREN_DISPLAY = 5  # Max children to show in diagnostic logs
ZERO_VALUE = 0  # For zero comparisons


class CalculationVerifierHorizontal:
    """
    Verifies calculations within a single statement.

    Handles:
    - Sum calculations with proper weights
    - Sign corrections from iXBRL
    - Decimal tolerance comparison
    - Severity determination (critical vs warning)
    """

    def __init__(self, decimal_tolerance: DecimalTolerance, sign_handler: SignWeightHandler):
        """
        Initialize calculation verifier.

        Args:
            decimal_tolerance: DecimalTolerance instance for value comparison
            sign_handler: SignWeightHandler for iXBRL sign corrections
        """
        self.decimal_tolerance = decimal_tolerance
        self.sign_handler = sign_handler
        self.logger = logging.getLogger('process.calculation_verifier_horizontal')

    def verify_bound_calculation(
        self,
        binding: BindingResult,
        context_group: ContextGroup,
        parent_original: str,
        role: str,
        context_id: str
    ) -> CheckResult:
        """
        Verify a calculation that has successfully bound.

        Uses:
        - Weights from company's calculation linkbase
        - Decimal tolerance for value comparison
        - Sign corrections from XBRL iXBRL sign attributes

        Args:
            binding: BindingResult with children found
            context_group: ContextGroup containing facts
            parent_original: Original parent concept name
            role: Extended link role
            context_id: XBRL context identifier

        Returns:
            CheckResult with verification outcome
        """
        # Calculate expected sum from children with sign corrections
        expected_sum = INITIAL_EXPECTED_SUM
        child_details = []
        min_decimals = None
        sign_corrections_applied = []

        for child_info in binding.children_found:
            child_concept = child_info['original_concept']
            child_ctx = child_info.get('context_id', context_id)
            child_value = child_info['value']
            child_weight = child_info['weight']

            # Apply sign correction from XBRL instance document
            corrected_value, was_corrected = self.sign_handler.apply_sign_correction(
                child_concept, child_ctx, child_value
            )
            if was_corrected:
                sign_corrections_applied.append({
                    'concept': child_concept,
                    'original': child_value,
                    'corrected': corrected_value,
                    'type': 'child'
                })
                child_value = corrected_value

            weighted_value = child_value * child_weight
            expected_sum += weighted_value

            child_details.append({
                'concept': child_concept,
                'value': child_info['value'],  # Original value for display
                'corrected_value': child_value,  # After sign correction
                'weight': child_weight,
                'weighted': weighted_value,
                'decimals': child_info['decimals'],
                'sign_corrected': was_corrected,
            })

            # Track minimum decimals for tolerance
            if child_info['decimals'] is not None:
                if min_decimals is None:
                    min_decimals = child_info['decimals']
                else:
                    min_decimals = min(min_decimals, child_info['decimals'])

        # Apply sign correction to parent value
        parent_value = binding.parent_value
        parent_corrected, parent_was_corrected = self.sign_handler.apply_sign_correction(
            parent_original, context_id, parent_value
        )
        if parent_was_corrected:
            sign_corrections_applied.append({
                'concept': parent_original,
                'original': parent_value,
                'corrected': parent_corrected,
                'type': 'parent'
            })
            parent_value = parent_corrected

        # Compare with parent using decimal tolerance
        tolerance_result = self.decimal_tolerance.is_within_tolerance(
            expected=expected_sum,
            actual=parent_value,
            expected_decimals=min_decimals,
            actual_decimals=binding.parent_decimals,
        )

        passed = tolerance_result.values_equal
        difference = tolerance_result.difference

        if passed:
            severity, message = self._create_success_message(
                parent_original, expected_sum, parent_value, sign_corrections_applied
            )
        else:
            severity, message = self._create_failure_message(
                parent_original, expected_sum, parent_value, difference,
                binding.children_missing
            )

            # Log diagnostic info for critical failures
            if severity == SEVERITY_CRITICAL and binding.children_missing:
                self.logger.info(
                    f"DIAGNOSTIC: {parent_original} in {context_id}: "
                    f"found {len(binding.children_found)}, missing {len(binding.children_missing)} children. "
                    f"Missing: {binding.children_missing[:MAX_MISSING_CHILDREN_DISPLAY]}"
                )

        return CheckResult(
            check_name=CHECK_CALCULATION_CONSISTENCY,
            check_type='horizontal',
            passed=passed,
            skipped=False,
            severity=severity,
            message=message,
            expected_value=expected_sum,
            actual_value=parent_value,  # Use corrected value
            difference=difference,
            details={
                'parent_concept': parent_original,
                'role': role,
                'context_id': context_id,
                'children': child_details,
                'children_found': len(binding.children_found),
                'children_missing': binding.children_missing,
                'tolerance_message': tolerance_result.message,
                'sign_corrections_applied': sign_corrections_applied,
                'parent_sign_corrected': parent_was_corrected,
            }
        )

    def _create_success_message(
        self,
        parent_original: str,
        expected_sum: float,
        parent_value: float,
        sign_corrections_applied: list
    ) -> tuple[str, str]:
        """
        Create success message for passed calculation.

        Args:
            parent_original: Original parent concept name
            expected_sum: Expected sum from children
            parent_value: Actual parent value
            sign_corrections_applied: List of sign corrections

        Returns:
            Tuple of (severity, message)
        """
        message = (
            f"Calculation {parent_original}: "
            f"expected {expected_sum:,.0f}, found {parent_value:,.0f} OK"
        )
        if sign_corrections_applied:
            message += f" ({len(sign_corrections_applied)} sign corrections)"
        
        return SEVERITY_INFO, message

    def _create_failure_message(
        self,
        parent_original: str,
        expected_sum: float,
        parent_value: float,
        difference: float,
        children_missing: list
    ) -> tuple[str, str]:
        """
        Create failure message with appropriate severity.

        Severity logic:
        - Sign mismatch: CRITICAL (fundamental error)
        - Overshooting: WARNING if small (rounding), CRITICAL if large
        - Undershooting with missing children: WARNING
        - Undershooting without missing children: CRITICAL

        Args:
            parent_original: Original parent concept name
            expected_sum: Expected sum from children
            parent_value: Actual parent value
            difference: Difference between expected and actual
            children_missing: List of missing children

        Returns:
            Tuple of (severity, message)
        """
        has_missing_children = len(children_missing) > 0
        sum_magnitude = abs(expected_sum)
        parent_magnitude = abs(parent_value)

        # Check for sign mismatch (one positive, one negative, both non-zero)
        sign_mismatch = (
            expected_sum != ZERO_VALUE and parent_value != ZERO_VALUE and
            (expected_sum > ZERO_VALUE) != (parent_value > ZERO_VALUE)
        )

        # Determine direction
        overshooting = sum_magnitude > parent_magnitude
        undershooting = sum_magnitude < parent_magnitude

        if sign_mismatch:
            return self._handle_sign_mismatch(
                parent_original, expected_sum, parent_value, difference
            )
        elif overshooting:
            return self._handle_overshooting(
                parent_original, expected_sum, parent_value, difference,
                sum_magnitude, parent_magnitude
            )
        elif undershooting:
            return self._handle_undershooting(
                parent_original, expected_sum, parent_value, difference,
                has_missing_children, children_missing
            )
        else:
            # Edge case: magnitudes equal but failed tolerance
            return SEVERITY_CRITICAL, (
                f"Calculation {parent_original}: "
                f"expected {expected_sum:,.0f}, found {parent_value:,.0f}, "
                f"diff {difference:,.0f}"
            )

    def _handle_sign_mismatch(
        self,
        parent_original: str,
        expected_sum: float,
        parent_value: float,
        difference: float
    ) -> tuple[str, str]:
        """Handle sign mismatch (fundamental error)."""
        return SEVERITY_CRITICAL, (
            f"Calculation {parent_original}: "
            f"SIGN MISMATCH - sum {expected_sum:,.0f} vs reported {parent_value:,.0f}, "
            f"diff {difference:,.0f}"
        )

    def _handle_overshooting(
        self,
        parent_original: str,
        expected_sum: float,
        parent_value: float,
        difference: float,
        sum_magnitude: float,
        parent_magnitude: float
    ) -> tuple[str, str]:
        """
        Handle overshooting (calculated more than reported).

        Small overshoot (within threshold) is likely rounding - WARNING.
        Large overshoot suggests double-counting or wrong weights - CRITICAL.
        """
        if parent_magnitude > ZERO_VALUE:
            overshoot_ratio = (sum_magnitude - parent_magnitude) / parent_magnitude
        else:
            overshoot_ratio = DEFAULT_OVERSHOOT_RATIO  # Division by zero case

        if overshoot_ratio <= OVERSHOOT_ROUNDING_THRESHOLD:
            return SEVERITY_WARNING, (
                f"Calculation {parent_original}: "
                f"sum {expected_sum:,.0f} exceeds reported {parent_value:,.0f} by {difference:,.0f} "
                f"({overshoot_ratio:.1%} - likely rounding)"
            )
        else:
            return SEVERITY_CRITICAL, (
                f"Calculation {parent_original}: "
                f"sum {expected_sum:,.0f} exceeds reported {parent_value:,.0f} by {difference:,.0f} "
                f"({overshoot_ratio:.1%} overshoot)"
            )

    def _handle_undershooting(
        self,
        parent_original: str,
        expected_sum: float,
        parent_value: float,
        difference: float,
        has_missing_children: bool,
        children_missing: list
    ) -> tuple[str, str]:
        """
        Handle undershooting (calculated less than reported).

        With missing children: WARNING (expected shortfall).
        Without missing children: CRITICAL (unexplained shortfall).
        """
        if has_missing_children:
            return SEVERITY_WARNING, (
                f"Calculation {parent_original}: "
                f"sum {expected_sum:,.0f} < reported {parent_value:,.0f}, "
                f"diff {difference:,.0f} (missing {len(children_missing)} children)"
            )
        else:
            return SEVERITY_CRITICAL, (
                f"Calculation {parent_original}: "
                f"sum {expected_sum:,.0f} < reported {parent_value:,.0f}, "
                f"diff {difference:,.0f} (all children found)"
            )


__all__ = [
    'CalculationVerifierHorizontal',
    'INITIAL_EXPECTED_SUM',
    'DEFAULT_OVERSHOOT_RATIO',
    'MAX_MISSING_CHILDREN_DISPLAY',
    'ZERO_VALUE',
]
