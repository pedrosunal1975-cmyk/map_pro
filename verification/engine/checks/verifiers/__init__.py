# Path: verification/engine/checks/verifiers/__init__.py
"""
Calculation verification modules for XBRL verification.

Contains:
- calculation_verifier: General calculation verification
- calculation_verifier_horizontal: Horizontal calculation verification
- duplicate_fact_checker: Duplicate fact checking
"""

from .calculation_verifier import (
    CalculationVerifier,
    CalculationVerificationResult,
    DualVerificationResult,
    ChildContribution,
)
from .calculation_verifier_horizontal import (
    CalculationVerifierHorizontal,
    INITIAL_EXPECTED_SUM,
    DEFAULT_OVERSHOOT_RATIO,
    MAX_MISSING_CHILDREN_DISPLAY,
    ZERO_VALUE,
)
from .duplicate_fact_checker import (
    DuplicateFactChecker,
    MAX_DUPLICATES_DISPLAY,
)

__all__ = [
    # Calculation verifier
    'CalculationVerifier',
    'CalculationVerificationResult',
    'DualVerificationResult',
    'ChildContribution',
    # Calculation verifier horizontal
    'CalculationVerifierHorizontal',
    'INITIAL_EXPECTED_SUM',
    'DEFAULT_OVERSHOOT_RATIO',
    'MAX_MISSING_CHILDREN_DISPLAY',
    'ZERO_VALUE',
    # Duplicate fact checker
    'DuplicateFactChecker',
    'MAX_DUPLICATES_DISPLAY',
]
