# Path: verification/engine/__init__.py
"""
Verification Engine Package

Processing components for verification checks and scoring.

Subpackages:
- checks/: Horizontal, vertical, and library verification checks
- scoring/: Score calculation and quality classification
- markets/: Market-specific verification logic (SEC, ESEF)
"""

from .coordinator import VerificationCoordinator, VerificationResult
from .checks import HorizontalChecker, VerticalChecker, LibraryChecker, CheckResult
from .scoring import ScoreCalculator, VerificationScores, QualityClassifier, QualityClassification
from .taxonomy_manager import TaxonomyManager

__all__ = [
    'VerificationCoordinator',
    'VerificationResult',
    'HorizontalChecker',
    'VerticalChecker',
    'LibraryChecker',
    'CheckResult',
    'ScoreCalculator',
    'VerificationScores',
    'QualityClassifier',
    'QualityClassification',
    'TaxonomyManager',
]
