"""
Duplicate Detection Constants
==============================

Location: map_pro/engines/mapper/analysis/duplicate_constants.py

Constants and configuration for Map Pro duplicate detection.

Constants:
- Severity thresholds
- Display limits
- Severity level identifiers
- Source attribution identifiers
- Field name mappings
"""

# ============================================================================
# SEVERITY THRESHOLDS
# ============================================================================

# Variance thresholds (as decimal, e.g., 0.05 = 5%)
CRITICAL_VARIANCE_THRESHOLD = 0.05  # 5% or more variance
MAJOR_VARIANCE_THRESHOLD = 0.01     # 1-5% variance
MINOR_VARIANCE_THRESHOLD = 0.0001   # 0.01-1% variance

# ============================================================================
# DISPLAY LIMITS
# ============================================================================

MAX_DUPLICATES_DETAIL_LOG = 10
SEPARATOR_LENGTH = 80

# ============================================================================
# SEVERITY LEVELS
# ============================================================================

SEVERITY_CRITICAL = 'CRITICAL'
SEVERITY_MAJOR = 'MAJOR'
SEVERITY_MINOR = 'MINOR'
SEVERITY_REDUNDANT = 'REDUNDANT'

# Severity descriptions for logging
SEVERITY_DESCRIPTIONS = {
    SEVERITY_CRITICAL: 'SEVERE DATA INTEGRITY ISSUES - Material variance >5%',
    SEVERITY_MAJOR: 'SIGNIFICANT DATA QUALITY CONCERNS - Notable variance 1-5%',
    SEVERITY_MINOR: 'Minor duplicate variances - Likely formatting/rounding',
    SEVERITY_REDUNDANT: 'Harmless redundant duplicates - No integrity concerns'
}

# ============================================================================
# SOURCE ATTRIBUTION
# ============================================================================

SOURCE_DATA = 'SOURCE_DATA'  # Duplicates exist in parsed_facts.json
SOURCE_MAPPING = 'MAPPING_INTRODUCED'  # Mapper created duplicates
SOURCE_UNKNOWN = 'UNKNOWN'  # Cannot determine source

# ============================================================================
# FIELD NAME MAPPINGS (Market-Agnostic)
# ============================================================================

# Concept field names (different markets use different names)
CONCEPT_FIELD_NAMES = [
    'concept_qname',
    'concept',
    'qname',
    'concept_local_name',
    'name',
    'element_name'
]

# Context field names
CONTEXT_FIELD_NAMES = [
    'context_ref',
    'contextRef',
    'context_id',
    'context'
]

# Value field names
VALUE_FIELD_NAMES = [
    'fact_value',
    'value',
    'amount',
    'data'
]

# ============================================================================
# SIGNIFICANCE THRESHOLDS
# ============================================================================

# Financial significance thresholds (for risk assessment)
HIGH_SIGNIFICANCE_AMOUNT = 1000000  # $1M+
MEDIUM_SIGNIFICANCE_AMOUNT = 100000  # $100K+

# Core financial statement concepts (high significance)
CORE_STATEMENT_CONCEPTS = {
    # Balance Sheet
    'Assets',
    'Liabilities',
    'StockholdersEquity',
    'LiabilitiesAndStockholdersEquity',
    'CurrentAssets',
    'CurrentLiabilities',
    'Cash',
    'CashAndCashEquivalents',
    
    # Income Statement
    'Revenues',
    'Revenue',
    'NetIncomeLoss',
    'OperatingIncomeLoss',
    'GrossProfit',
    'CostOfRevenue',
    
    # Cash Flow
    'NetCashProvidedByUsedInOperatingActivities',
    'NetCashProvidedByUsedInInvestingActivities',
    'NetCashProvidedByUsedInFinancingActivities',
    'CashAndCashEquivalentsPeriodIncreaseDecrease'
}