# Path: verification/engine/checks/context/fact_rules.py
"""
Centralized Fact Finding Rules for XBRL Verification

This module provides shared logic for fact finding, context classification,
and period matching used by all verification checkers (horizontal, vertical,
binding, etc.).

DESIGN PRINCIPLES:
- All patterns come from constants.py (no hardcoded regex in this file)
- Market and taxonomy agnostic
- Provides consistent fact matching across all checkers
- Handles dimensional contexts, period extraction, and compatibility

COMPONENTS:
- PeriodExtractor: Extract period information from context_id
- ContextClassifier: Classify context type (dimensional, default)
- ContextMatcher: Check if two contexts are compatible for comparison
- FactFinder: Find facts across contexts with various strategies

USAGE:
    from .fact_rules import ContextClassifier, PeriodExtractor, ContextMatcher, FactFinder

    # Check if context is dimensional
    classifier = ContextClassifier()
    is_dim = classifier.is_dimensional(context_id)

    # Extract period from context
    extractor = PeriodExtractor()
    period = extractor.extract(context_id)

    # Check if contexts are compatible
    matcher = ContextMatcher()
    compatible = matcher.are_compatible(parent_ctx, child_ctx)

    # Find facts with fallback
    finder = FactFinder(all_facts)
    result = finder.find_compatible(concept, parent_context)
"""

# Re-export all components from the split modules
from .period_extraction import (
    PeriodInfo,
    PeriodExtractor,
    REGEX_YEAR_PATTERN,
    REGEX_FLAGS,
)

from .context_classification import (
    ContextClassifier,
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
    # Period extraction
    'PeriodInfo',
    'PeriodExtractor',
    'REGEX_YEAR_PATTERN',
    'REGEX_FLAGS',

    # Context classification
    'ContextClassifier',

    # Context matching
    'ContextMatcher',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_UNKNOWN',

    # Fact finding
    'FactMatch',
    'FactFinder',
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',
]
