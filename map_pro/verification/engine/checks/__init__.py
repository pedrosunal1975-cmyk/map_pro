# Path: verification/engine/checks/__init__.py
"""
Verification Checks Package

Verification check implementations:
- horizontal_checker: Within-statement validation
- vertical_checker: Cross-statement consistency
- library_checker: Standard taxonomy conformance
"""

from .horizontal_checker import HorizontalChecker, CheckResult
from .vertical_checker import VerticalChecker
from .library_checker import LibraryChecker
from .calculation_verifier import (
    CalculationVerifier,
    CalculationVerificationResult,
    DualVerificationResult,
    ChildContribution,
)

__all__ = [
    'HorizontalChecker',
    'VerticalChecker',
    'LibraryChecker',
    'CheckResult',
    'CalculationVerifier',
    'CalculationVerificationResult',
    'DualVerificationResult',
    'ChildContribution',
]
