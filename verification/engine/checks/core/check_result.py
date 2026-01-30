# Path: verification/engine/checks/core/check_result.py
"""
Check Result Data Structure

Provides the CheckResult dataclass used by all verification checks
to report their findings in a standardized format.
"""

from dataclasses import dataclass, field
from typing import Optional

from ....constants import SEVERITY_INFO


@dataclass
class CheckResult:
    """
    Result of a single verification check.

    Provides a standardized format for reporting check results across
    all verification components (horizontal, vertical, library checks).

    Attributes:
        check_name: Name of the check performed (e.g., CHECK_CALCULATION_CONSISTENCY)
        check_type: Type of check (horizontal, vertical, library)
        passed: Whether the check passed (None if skipped, True/False otherwise)
        skipped: Whether the check was skipped (e.g., binding failed)
        severity: Severity level if failed (critical, warning, info)
        message: Human-readable description of the result
        expected_value: Expected value (for calculation checks)
        actual_value: Actual value found
        difference: Numeric difference between expected and actual
        details: Additional context (dict with check-specific information)
    """
    check_name: str
    check_type: str = 'horizontal'
    passed: Optional[bool] = True
    skipped: bool = False
    severity: str = SEVERITY_INFO
    message: str = ''
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    details: dict = field(default_factory=dict)

    def is_successful(self) -> bool:
        """Check if result represents a successful check (passed or skipped)."""
        return self.passed is True or self.skipped

    def is_failed(self) -> bool:
        """Check if result represents a failed check."""
        return self.passed is False and not self.skipped

    def get_severity_label(self) -> str:
        """Get human-readable severity label."""
        from ....constants import SEVERITY_CRITICAL, SEVERITY_WARNING
        
        if self.severity == SEVERITY_CRITICAL:
            return "CRITICAL"
        elif self.severity == SEVERITY_WARNING:
            return "WARNING"
        else:
            return "INFO"


__all__ = ['CheckResult']
