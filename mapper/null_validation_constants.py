# File: map_pro/engines/mapper/null_validation_constants.py

"""
Null Validation Constants
==========================

Centralized constants for null value validation.
Eliminates magic numbers and strings throughout the validation system.
"""

from typing import Set, List

# Quality score thresholds
SCORE_EXCELLENT_THRESHOLD: int = 95
SCORE_GOOD_THRESHOLD: int = 85
SCORE_ACCEPTABLE_THRESHOLD: int = 75
SCORE_POOR_THRESHOLD: int = 60

# Quality grades
GRADE_EXCELLENT: str = 'EXCELLENT'
GRADE_GOOD: str = 'GOOD'
GRADE_ACCEPTABLE: str = 'ACCEPTABLE'
GRADE_POOR: str = 'POOR'
GRADE_CRITICAL: str = 'CRITICAL'
GRADE_UNKNOWN: str = 'UNKNOWN'

# Score penalties
PENALTY_SUSPICIOUS_NULL: int = 2
PENALTY_CRITICAL_NULL: int = 5

# Score bonuses
BONUS_HIGH_EXPLANATION_COVERAGE: int = 5
HIGH_EXPLANATION_THRESHOLD: float = 90.0

# Suspicion levels
SUSPICION_NONE: str = 'none'
SUSPICION_LOW: str = 'low'
SUSPICION_MEDIUM: str = 'medium'
SUSPICION_HIGH: str = 'high'

# Classification types
CLASSIFICATION_NIL_IN_SOURCE: str = 'nil_in_source'
CLASSIFICATION_EXPLAINED_NULL: str = 'explained_null'
CLASSIFICATION_UNEXPLAINED_NULL: str = 'unexplained_null'

# Text limits
MAX_EXPLANATION_TEXT_LENGTH: int = 200
MIN_EXPLANATORY_TEXT_LENGTH: int = 50

# Warning thresholds
HIGH_NULL_PERCENTAGE_THRESHOLD: float = 30.0
SUSPICIOUS_NULL_WARNING_THRESHOLD: int = 5
LOW_EXPLANATION_COVERAGE_THRESHOLD: float = 50.0

# Patterns that indicate null explanations in text blocks
EXPLANATION_PATTERNS: List[str] = [
    r'all\s+(?:values|amounts|figures)\s+(?:are\s+)?(?:in\s+)?(?:thousands|millions|dollars|usd)',
    r'unless\s+(?:otherwise\s+)?(?:stated|noted|indicated)',
    r'except\s+(?:as\s+)?(?:noted|indicated|stated)',
    r'values\s+in\s+\w+',
    r'amounts\s+in\s+\w+',
    r'expressed\s+in\s+\w+',
    r'not\s+applicable',
    r'n/?a',
    r'see\s+note',
    r'refer\s+to',
    r'as\s+described\s+in',
]

# Financial concepts that should RARELY be null
CRITICAL_CONCEPTS: Set[str] = {
    'revenue',
    'sales',
    'income',
    'assets',
    'liabilities',
    'equity',
    'cash',
    'netincome',
    'grossprofit',
    'operatingincome',
    'totalassets',
    'totalliabilities',
    'stockholdersequity'
}

# Keywords indicating explanatory concepts
EXPLANATORY_CONCEPT_KEYWORDS: List[str] = [
    'textblock',
    'disclosure',
    'policy'
]

# Keywords for general explanations
GENERAL_EXPLANATION_KEYWORDS: List[str] = [
    'all values',
    'unless otherwise',
    'amounts in'
]

# Message templates
MSG_SUCCESS_NO_NULLS: str = "[SUCCESS] No null values in mapped statements"
MSG_WARNING_HIGH_NULL_PCT: str = "[WARNING] {statement_type} has {null_pct:.1f}% null values - review source data quality"
MSG_ACTION_MISSING_SOURCES: str = "[ACTION] {count} null values in {statement_type} have no source facts - possible mapping failure"
MSG_CRITICAL_NULLS: str = "{count} critical financial concepts have null values without explanation"
MSG_SUSPICIOUS_NULLS: str = "{count} suspicious null values found - manual review recommended"
MSG_LOW_COVERAGE: str = "Low explanation coverage ({coverage:.1f}%) for null values"
MSG_NIL_IN_SOURCE: str = "{count} values are nil in source XBRL (legitimate)"
MSG_EXPLAINED_NULLS: str = "{count} null values have explanatory context"

# Explanation sources
EXPLANATION_TEXT_CONCEPT: str = "Concept is a text/disclosure element"
EXPLANATION_CONTEXT_RELATED: str = "Explained by: {text}"
EXPLANATION_DOCUMENT_LEVEL: str = "Document-level explanation: {text}"