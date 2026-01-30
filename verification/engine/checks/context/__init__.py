# Path: verification/engine/checks/context/__init__.py
"""
Context and fact handling for XBRL verification.

Contains:
- duplicate_detection: Duplicate fact detection and classification
- context_grouping: Context-based fact grouping
- context_classification: Context type classification
- period_extraction: Period extraction from context_id
- context_matching: Context compatibility checking
- fact_finder: Fact finding strategies
- fact_rules: Facade module re-exporting all components
"""

from .duplicate_detection import (
    DuplicateType,
    FactEntry,
    DuplicateInfo,
    DUPLICATE_PERCENTAGE_TOLERANCE,
)
from .context_grouping import (
    ContextGroup,
    FactGroups,
    SAMPLE_CONCEPTS_LIMIT,
    SAMPLE_CONTEXTS_LIMIT,
)
from .context_classification import ContextClassifier
from .period_extraction import (
    PeriodInfo,
    PeriodExtractor,
    REGEX_YEAR_PATTERN,
    REGEX_FLAGS,
)
from .context_matching import (
    ContextMatcher,
    PERIOD_TYPE_DURATION,
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_UNKNOWN,
)
from .fact_finder import (
    FactMatch,
    FactFinder,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FALLBACK,
    MATCH_TYPE_PERIOD_MATCH,
    MATCH_TYPE_NONE,
)

__all__ = [
    # Duplicate detection
    'DuplicateType',
    'FactEntry',
    'DuplicateInfo',
    'DUPLICATE_PERCENTAGE_TOLERANCE',
    # Context grouping
    'ContextGroup',
    'FactGroups',
    'SAMPLE_CONCEPTS_LIMIT',
    'SAMPLE_CONTEXTS_LIMIT',
    # Context classification
    'ContextClassifier',
    # Period extraction
    'PeriodInfo',
    'PeriodExtractor',
    'REGEX_YEAR_PATTERN',
    'REGEX_FLAGS',
    # Context matching
    'ContextMatcher',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_UNKNOWN',
    # Fact finder
    'FactMatch',
    'FactFinder',
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',
]
