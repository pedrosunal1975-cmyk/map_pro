# Path: verification/engine/checks/constants.py
"""
Verification Checks Constants

Constants for horizontal, vertical, and library verification checks.
"""

# ==============================================================================
# HORIZONTAL CHECK NAMES
# ==============================================================================
# Checks within a single statement

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
# Checks across statements

CHECK_BALANCE_SHEET_EQUATION = 'balance_sheet_equation'
CHECK_INCOME_LINKAGE = 'income_statement_linkage'
CHECK_CASH_FLOW_LINKAGE = 'cash_flow_linkage'
CHECK_RETAINED_EARNINGS_ROLL = 'retained_earnings_rollforward'
CHECK_COMMON_VALUES_CONSISTENCY = 'common_values_consistency'

VERTICAL_CHECK_NAMES = [
    CHECK_BALANCE_SHEET_EQUATION,
    CHECK_INCOME_LINKAGE,
    CHECK_CASH_FLOW_LINKAGE,
    CHECK_RETAINED_EARNINGS_ROLL,
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

# ==============================================================================
# BALANCE SHEET CONCEPTS
# ==============================================================================
# Concepts that typically represent totals (market-agnostic patterns)

TOTAL_ASSETS_PATTERNS = [
    'Assets',
    'TotalAssets',
    'AssetsTotal',
]

TOTAL_LIABILITIES_PATTERNS = [
    'Liabilities',
    'TotalLiabilities',
    'LiabilitiesTotal',
]

TOTAL_EQUITY_PATTERNS = [
    'Equity',
    'StockholdersEquity',
    'ShareholdersEquity',
    'TotalEquity',
    'EquityTotal',
]

LIABILITIES_AND_EQUITY_PATTERNS = [
    'LiabilitiesAndEquity',
    'LiabilitiesAndStockholdersEquity',
    'TotalLiabilitiesAndEquity',
]

# ==============================================================================
# INCOME STATEMENT CONCEPTS
# ==============================================================================

NET_INCOME_PATTERNS = [
    'NetIncome',
    'NetIncomeLoss',
    'ProfitLoss',
    'NetProfitLoss',
    'ProfitLossAttributableToOwnersOfParent',
]

REVENUE_PATTERNS = [
    'Revenue',
    'Revenues',
    'SalesRevenueNet',
    'RevenueFromContractWithCustomerExcludingAssessedTax',
]

# ==============================================================================
# CASH FLOW CONCEPTS
# ==============================================================================

CASH_BEGINNING_PATTERNS = [
    'CashAndCashEquivalentsAtCarryingValue',
    'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
    'CashAndCashEquivalentsPeriodBeginning',
]

CASH_ENDING_PATTERNS = [
    'CashAndCashEquivalentsAtCarryingValue',
    'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
    'CashAndCashEquivalentsPeriodEnd',
]

CASH_CHANGE_PATTERNS = [
    'CashAndCashEquivalentsPeriodIncreaseDecrease',
    'NetCashProvidedByUsedInFinancingActivities',
]

# ==============================================================================
# RETAINED EARNINGS CONCEPTS
# ==============================================================================

RETAINED_EARNINGS_PATTERNS = [
    'RetainedEarnings',
    'RetainedEarningsAccumulatedDeficit',
    'AccumulatedOtherComprehensiveIncomeLossNetOfTax',
]


__all__ = [
    # Horizontal checks
    'CHECK_CALCULATION_CONSISTENCY',
    'CHECK_TOTAL_RECONCILIATION',
    'CHECK_SIGN_CONVENTION',
    'CHECK_DUPLICATE_FACTS',
    'HORIZONTAL_CHECK_NAMES',

    # Vertical checks
    'CHECK_BALANCE_SHEET_EQUATION',
    'CHECK_INCOME_LINKAGE',
    'CHECK_CASH_FLOW_LINKAGE',
    'CHECK_RETAINED_EARNINGS_ROLL',
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

    # Concept patterns
    'TOTAL_ASSETS_PATTERNS',
    'TOTAL_LIABILITIES_PATTERNS',
    'TOTAL_EQUITY_PATTERNS',
    'LIABILITIES_AND_EQUITY_PATTERNS',
    'NET_INCOME_PATTERNS',
    'REVENUE_PATTERNS',
    'CASH_BEGINNING_PATTERNS',
    'CASH_ENDING_PATTERNS',
    'CASH_CHANGE_PATTERNS',
    'RETAINED_EARNINGS_PATTERNS',
]
