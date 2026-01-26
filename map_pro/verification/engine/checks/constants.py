# Path: verification/engine/checks/constants.py
"""
Verification Checks Constants

Check names and tolerance values for verification checks.
NO hardcoded concept patterns or formulas - all relationships
come from XBRL sources (company linkbase and standard taxonomy).
"""

# ==============================================================================
# HORIZONTAL CHECK NAMES
# ==============================================================================
# Checks within a single statement (using XBRL calculation linkbase)

CHECK_CALCULATION_CONSISTENCY = 'calculation_consistency'
CHECK_TOTAL_RECONCILIATION = 'total_reconciliation'
CHECK_SIGN_CONVENTION = 'sign_convention'
CHECK_DUPLICATE_FACTS = 'duplicate_facts'

HORIZONTAL_CHECK_NAMES = [
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_TOTAL_RECONCILIATION,
    CHECK_SIGN_CONVENTION,
    CHECK_DUPLICATE_FACTS,
]

# ==============================================================================
# VERTICAL CHECK NAMES
# ==============================================================================
# Checks across statements (using XBRL calculation linkbase)

CHECK_COMMON_VALUES_CONSISTENCY = 'common_values_consistency'

VERTICAL_CHECK_NAMES = [
    CHECK_COMMON_VALUES_CONSISTENCY,
]

# ==============================================================================
# LIBRARY CHECK NAMES
# ==============================================================================
# Checks against standard taxonomy

CHECK_CONCEPT_VALIDITY = 'concept_validity'
CHECK_PERIOD_TYPE_MATCH = 'period_type_match'
CHECK_BALANCE_TYPE_MATCH = 'balance_type_match'
CHECK_DATA_TYPE_MATCH = 'data_type_match'

LIBRARY_CHECK_NAMES = [
    CHECK_CONCEPT_VALIDITY,
    CHECK_PERIOD_TYPE_MATCH,
    CHECK_BALANCE_TYPE_MATCH,
    CHECK_DATA_TYPE_MATCH,
]

# ==============================================================================
# DEFAULT TOLERANCES
# ==============================================================================

# Calculation tolerance (percentage difference allowed)
DEFAULT_CALCULATION_TOLERANCE = 0.01  # 1%

# Rounding tolerance (absolute value for small differences)
DEFAULT_ROUNDING_TOLERANCE = 1.0  # $1 or equivalent

# Large value threshold (values above this use percentage tolerance)
LARGE_VALUE_THRESHOLD = 1000.0


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

    # Tolerances
    'DEFAULT_CALCULATION_TOLERANCE',
    'DEFAULT_ROUNDING_TOLERANCE',
    'LARGE_VALUE_THRESHOLD',
]
