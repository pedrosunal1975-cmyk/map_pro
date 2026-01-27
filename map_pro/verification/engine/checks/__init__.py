# Path: verification/engine/checks/__init__.py
"""
Verification Checks Package

Verification check implementations:
- c_equal: C-Equal (context-equal) module for XBRL verification
- horizontal_checker: Within-statement validation
- vertical_checker: Cross-statement consistency
- library_checker: Standard taxonomy conformance
"""

from .c_equal import CEqual, FactGroups, ContextGroup
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
    # C-Equal module
    'CEqual',
    'FactGroups',
    'ContextGroup',
    # Checkers
    'HorizontalChecker',
    'VerticalChecker',
    'LibraryChecker',
    'CheckResult',
    # Calculation verification
    'CalculationVerifier',
    'CalculationVerificationResult',
    'DualVerificationResult',
    'ChildContribution',
]
