"""
Map Pro Mapper Analysis Subsystem
==================================

Location: map_pro/engines/mapper/analysis/__init__.py

Comprehensive analysis capabilities for Map Pro's pattern-based mapper.

Main Components:
- DuplicateDetector: Main orchestrator for duplicate detection
- DuplicateSourceTracer: Traces duplicates to source (XBRL vs mapping)
- DuplicateAnalyzer: Comprehensive duplicate characterization
- DuplicatePatternDetector: Detects systematic duplicate patterns
- DuplicateRiskAssessor: Assesses financial risk of duplicates
- DuplicateSignificanceAssessor: Assesses financial significance

Supporting Components:
- duplicate_constants: Constants and thresholds
- fact_extractor: Market-agnostic field extraction
- fact_grouper: Groups facts by concept+context
- variance_calculator: Calculates variance and severity
- duplicate_analyzer_helper: Analyzes individual duplicates
- duplicate_report_builder: Builds comprehensive reports
- duplicate_logger_util: Logging utilities

Architecture: Market-agnostic analysis for all XBRL sources.
"""

from .duplicate_detector import DuplicateDetector
from .duplicate_constants import (
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    SEVERITY_REDUNDANT,
    SOURCE_DATA,
    SOURCE_MAPPING,
    SOURCE_UNKNOWN
)

__all__ = [
    'DuplicateDetector',
    'SEVERITY_CRITICAL',
    'SEVERITY_MAJOR',
    'SEVERITY_MINOR',
    'SEVERITY_REDUNDANT',
    'SOURCE_DATA',
    'SOURCE_MAPPING',
    'SOURCE_UNKNOWN'
]

__version__ = '1.0.0'