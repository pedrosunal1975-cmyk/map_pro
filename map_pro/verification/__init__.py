# Path: verification/__init__.py
"""
Verification Module

Validates mapped financial statements for quality assessment.
Determines whether company-provided XBRL filings are consistent,
accurate, and suitable for financial analysis.

Key Principle: We do NOT correct company data. We detect and
report inconsistencies in what companies have declared.

Architecture (IPO):
- INPUT: loaders/ - Data access from mapper, parser, XBRL files
- PROCESS: engine/ - Verification checks, scoring, classification
- OUTPUT: output/ - Reports, summaries, simplified statements

Usage:
    python verify.py

    # Or programmatically:
    from verification.engine.coordinator import VerificationCoordinator

    coordinator = VerificationCoordinator()
    results = coordinator.verify_all_filings()
"""

__version__ = '0.1.0'
__author__ = 'MAP PRO'

# Core exports for convenient access
from .engine.coordinator import VerificationCoordinator, VerificationResult
from .engine.scoring import VerificationScores, QualityClassification

__all__ = [
    '__version__',
    '__author__',
    'VerificationCoordinator',
    'VerificationResult',
    'VerificationScores',
    'QualityClassification',
]
