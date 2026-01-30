# Path: verification/engine/checks_v2/constants/check_names.py
"""
Check Name Constants for XBRL Verification

Standard identifiers for verification checks.
Used for result reporting, logging, and check selection.

Categories:
1. Horizontal Checks - Within a single statement (calculation linkbase)
2. Vertical Checks - Across statements (cross-statement consistency)
3. Library Checks - Against standard taxonomy
"""

# ==============================================================================
# HORIZONTAL CHECK NAMES
# ==============================================================================
# Checks within a single statement using XBRL calculation linkbase.
# These verify that calculations defined by the company are internally consistent.

# Calculation consistency - parent = sum(children * weights)
CHECK_CALCULATION_CONSISTENCY = 'calculation_consistency'

# Total reconciliation - totals match expected sums
CHECK_TOTAL_RECONCILIATION = 'total_reconciliation'

# Sign convention - values have correct signs per XBRL convention
CHECK_SIGN_CONVENTION = 'sign_convention'

# Duplicate facts - detecting and handling duplicate fact entries
CHECK_DUPLICATE_FACTS = 'duplicate_facts'

# All horizontal check names
HORIZONTAL_CHECK_NAMES = [
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_TOTAL_RECONCILIATION,
    CHECK_SIGN_CONVENTION,
    CHECK_DUPLICATE_FACTS,
]


# ==============================================================================
# VERTICAL CHECK NAMES
# ==============================================================================
# Checks across statements using XBRL relationships.
# These verify consistency between different financial statements.

# Common values consistency - same concept has same value across statements
CHECK_COMMON_VALUES_CONSISTENCY = 'common_values_consistency'

# All vertical check names
VERTICAL_CHECK_NAMES = [
    CHECK_COMMON_VALUES_CONSISTENCY,
]


# ==============================================================================
# LIBRARY CHECK NAMES
# ==============================================================================
# Checks against standard taxonomy.
# These verify that company filings conform to taxonomy definitions.

# Concept validity - concept exists in taxonomy
CHECK_CONCEPT_VALIDITY = 'concept_validity'

# Period type match - instant vs duration matches taxonomy definition
CHECK_PERIOD_TYPE_MATCH = 'period_type_match'

# Balance type match - debit vs credit matches taxonomy definition
CHECK_BALANCE_TYPE_MATCH = 'balance_type_match'

# Data type match - value type matches taxonomy definition
CHECK_DATA_TYPE_MATCH = 'data_type_match'

# All library check names
LIBRARY_CHECK_NAMES = [
    CHECK_CONCEPT_VALIDITY,
    CHECK_PERIOD_TYPE_MATCH,
    CHECK_BALANCE_TYPE_MATCH,
    CHECK_DATA_TYPE_MATCH,
]


# ==============================================================================
# ALL CHECK NAMES
# ==============================================================================
# Complete list of all check names for iteration

ALL_CHECK_NAMES = HORIZONTAL_CHECK_NAMES + VERTICAL_CHECK_NAMES + LIBRARY_CHECK_NAMES


__all__ = [
    # Horizontal checks
    'CHECK_CALCULATION_CONSISTENCY',
    'CHECK_TOTAL_RECONCILIATION',
    'CHECK_SIGN_CONVENTION',
    'CHECK_DUPLICATE_FACTS',
    'HORIZONTAL_CHECK_NAMES',
    # Vertical checks
    'CHECK_COMMON_VALUES_CONSISTENCY',
    'VERTICAL_CHECK_NAMES',
    # Library checks
    'CHECK_CONCEPT_VALIDITY',
    'CHECK_PERIOD_TYPE_MATCH',
    'CHECK_BALANCE_TYPE_MATCH',
    'CHECK_DATA_TYPE_MATCH',
    'LIBRARY_CHECK_NAMES',
    # All checks
    'ALL_CHECK_NAMES',
]
