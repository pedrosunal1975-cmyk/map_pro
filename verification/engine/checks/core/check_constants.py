# Path: verification/engine/checks/core/check_constants.py
"""
Additional Constants for Verification Checks

This file contains configuration constants extracted from the check implementations
to eliminate magic numbers and improve maintainability.

All numeric thresholds, limits, and configuration values should be defined here
with clear documentation of their purpose.
"""

# ==============================================================================
# SIGN WEIGHT HANDLER CONSTANTS
# ==============================================================================

# Tolerance for detecting sign pattern issues
# Used to check if values match in magnitude but differ in sign
SIGN_MAGNITUDE_TOLERANCE = 0.01  # 1% tolerance for magnitude comparison

# Tolerance for detecting doubling pattern (parent sign opposite of expected)
# Used when difference is approximately 2x the expected sum
SIGN_DOUBLING_TOLERANCE = 0.01  # 1% tolerance for doubling detection


# ==============================================================================
# DECIMAL TOLERANCE CONSTANTS
# ==============================================================================

# Epsilon for floating point comparison when decimals is None
# Used as a small tolerance to account for floating point arithmetic
DECIMAL_COMPARISON_EPSILON_BASE = 0.5

# Multiplier for epsilon calculation when decimals is specified
# epsilon = 10 ** (-decimals) * EPSILON_MULTIPLIER
DECIMAL_EPSILON_MULTIPLIER = 0.5


# ==============================================================================
# CALCULATION VERIFIER CONSTANTS
# ==============================================================================

# Default calculation tolerance (percentage difference allowed)
CALC_VERIFIER_DEFAULT_TOLERANCE = 0.01  # 1%

# Default rounding tolerance (absolute value for small differences)
CALC_VERIFIER_DEFAULT_ROUNDING = 1.0  # $1

# Initial expected sum value before children are added
INITIAL_EXPECTED_SUM = 0.0

# Default overshoot ratio when division by zero would occur
DEFAULT_OVERSHOOT_RATIO = 1.0


# ==============================================================================
# BINDING CHECKER CONSTANTS
# ==============================================================================

# Maximum number of missing children to display in detailed messages
MAX_MISSING_CHILDREN_DISPLAY = 5

# Index for accessing first element in arrays
FIRST_ELEMENT_INDEX = 0


# ==============================================================================
# CONTEXT GROUPING CONSTANTS
# ==============================================================================

# Number of sample concepts to include in diagnostic summaries
SAMPLE_CONCEPTS_LIMIT = 50

# Number of sample contexts to include in diagnostic summaries
SAMPLE_CONTEXTS_LIMIT = 10


# ==============================================================================
# DUPLICATE DETECTION CONSTANTS
# ==============================================================================

# Percentage tolerance for duplicate detection fallback
# When decimal tolerance doesn't work, use this percentage threshold
DUPLICATE_PERCENTAGE_TOLERANCE = 0.02  # 2%


# ==============================================================================
# CONCEPT NORMALIZATION CONSTANTS
# ==============================================================================

# Maximum length for company extension prefixes
# Extension prefixes like 'v', 'aapl', 'msft' are typically short
MAX_EXTENSION_PREFIX_LENGTH = 6


# ==============================================================================
# VALUE PARSING CONSTANTS
# ==============================================================================

# Return value for nil/zero representations
NIL_VALUE_RETURN = 0.0


# ==============================================================================
# VERTICAL CHECKER CONSTANTS
# ==============================================================================

# Default value for unparseable/nil values in vertical checks
VERTICAL_DEFAULT_VALUE = 0.0


# ==============================================================================
# HORIZONTAL CHECKER CONSTANTS
# ==============================================================================

# Minimum context count required for horizontal checks
CONTEXT_COUNT_MINIMUM = 0

# Maximum inconsistent duplicates to display in inline results
MAX_INCONSISTENT_DUPLICATES_DISPLAY = 20

# Minimum multi-role parents to trigger info log message
MAX_MULTI_ROLE_PARENTS_LOG = 1

# Maximum duplicates to display in duplicate check results
MAX_DUPLICATES_DISPLAY = 20


# ==============================================================================
# CALCULATION VERIFIER HORIZONTAL CONSTANTS
# ==============================================================================

# Initial value for expected sum before adding children
INITIAL_EXPECTED_SUM_HORIZONTAL = 0.0

# Default overshoot ratio when parent magnitude is zero (division by zero case)
DEFAULT_OVERSHOOT_RATIO_HORIZONTAL = 1.0

# Maximum missing children to show in diagnostic log messages
MAX_MISSING_CHILDREN_DISPLAY_HORIZONTAL = 5

# Zero value constant for comparisons
ZERO_VALUE_HORIZONTAL = 0


# ==============================================================================
# COMPARISON AND ITERATION CONSTANTS
# ==============================================================================

# Threshold for considering a value as zero in comparisons
ZERO_THRESHOLD = 0

# Minimum number of entries to be considered a duplicate set
MIN_DUPLICATE_ENTRIES = 1

# Starting index for iterating over entries after the first
ITERATION_START_INDEX = 1


# ==============================================================================
# PERIOD EXTRACTION CONSTANTS
# ==============================================================================

# Regex pattern for extracting 4-digit years from context IDs
REGEX_YEAR_PATTERN = r'\d{4}'

# Regex flags for case-insensitive matching
REGEX_FLAGS_VALUE = 're.IGNORECASE'  # String representation for documentation


# ==============================================================================
# PERIOD TYPE CONSTANTS
# ==============================================================================

# Period type identifiers
PERIOD_TYPE_DURATION = 'duration'
PERIOD_TYPE_INSTANT = 'instant'
PERIOD_TYPE_UNKNOWN = 'unknown'


# ==============================================================================
# FACT MATCH TYPE CONSTANTS
# ==============================================================================

# Match type identifiers for fact finding results
MATCH_TYPE_EXACT = 'exact'  # Exact context match (C-Equal)
MATCH_TYPE_FALLBACK = 'fallback'  # Compatible period fallback
MATCH_TYPE_PERIOD_MATCH = 'period_match'  # Period key match
MATCH_TYPE_NONE = 'none'  # No match found


__all__ = [
    # Sign weight handler
    'SIGN_MAGNITUDE_TOLERANCE',
    'SIGN_DOUBLING_TOLERANCE',
    
    # Decimal tolerance
    'DECIMAL_COMPARISON_EPSILON_BASE',
    'DECIMAL_EPSILON_MULTIPLIER',
    
    # Calculation verifier
    'CALC_VERIFIER_DEFAULT_TOLERANCE',
    'CALC_VERIFIER_DEFAULT_ROUNDING',
    'INITIAL_EXPECTED_SUM',
    'DEFAULT_OVERSHOOT_RATIO',
    
    # Binding checker
    'MAX_MISSING_CHILDREN_DISPLAY',
    'FIRST_ELEMENT_INDEX',
    
    # Context grouping
    'SAMPLE_CONCEPTS_LIMIT',
    'SAMPLE_CONTEXTS_LIMIT',
    
    # Duplicate detection
    'DUPLICATE_PERCENTAGE_TOLERANCE',
    
    # Concept normalization
    'MAX_EXTENSION_PREFIX_LENGTH',
    
    # Value parsing
    'NIL_VALUE_RETURN',
    
    # Vertical checker
    'VERTICAL_DEFAULT_VALUE',
    
    # Horizontal checker
    'CONTEXT_COUNT_MINIMUM',
    'MAX_INCONSISTENT_DUPLICATES_DISPLAY',
    'MAX_MULTI_ROLE_PARENTS_LOG',
    'MAX_DUPLICATES_DISPLAY',
    
    # Calculation verifier horizontal
    'INITIAL_EXPECTED_SUM_HORIZONTAL',
    'DEFAULT_OVERSHOOT_RATIO_HORIZONTAL',
    'MAX_MISSING_CHILDREN_DISPLAY_HORIZONTAL',
    'ZERO_VALUE_HORIZONTAL',
    
    # Comparison and iteration
    'ZERO_THRESHOLD',
    'MIN_DUPLICATE_ENTRIES',
    'ITERATION_START_INDEX',
    
    # Period extraction
    'REGEX_YEAR_PATTERN',
    'REGEX_FLAGS_VALUE',
    
    # Period types
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_UNKNOWN',
    
    # Fact match types
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',
]
