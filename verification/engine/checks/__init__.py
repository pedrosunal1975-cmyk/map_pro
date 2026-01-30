# Path: verification/engine/checks/__init__.py
"""
Verification Checks Package

Verification check implementations:
- c_equal: C-Equal (context-equal) module for XBRL verification (refactored)
  - duplicate_detection: Duplicate fact detection and classification
  - context_grouping: Grouping facts by XBRL context
  - value_parsing: Parsing raw values from statements
  - concept_normalization: Normalizing concept names for comparison
- horizontal_checker: Within-statement validation (refactored)
  - check_result: CheckResult dataclass for standardized results
  - instance_document_finder: Finding XBRL instance documents
  - calculation_verifier_horizontal: Calculation verification logic
  - duplicate_fact_checker: Duplicate fact checking
- binding_checker: Determines if calculations should bind per XBRL spec
- decimal_tolerance: XBRL rounding rules for value comparison
- dimension_handler: XBRL dimensional structure parsing and classification
- sign_weight_handler: XBRL sign attributes and calculation weight handling
- fact_rules: Centralized fact finding and context matching rules
- vertical_checker: Cross-statement consistency
- library_checker: Standard taxonomy conformance
- check_constants: Configuration constants for all checks
"""

# Import from refactored c_equal modules
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
from .value_parsing import (
    ValueParser,
    NIL_VALUES,
    EM_DASH,
    EN_DASH,
)
from .concept_normalization import (
    ConceptNormalizer,
    KNOWN_TAXONOMY_PREFIXES,
    MAX_EXTENSION_PREFIX_LENGTH,
)
from .c_equal import CEqual

# Import from refactored horizontal_checker modules
from .check_result import CheckResult
from .instance_document_finder import (
    InstanceDocumentFinder,
    INSTANCE_DOCUMENT_PATTERNS,
    INSTANCE_DOCUMENT_EXCLUSIONS,
)
# Change this block in __init__.py
from .calculation_verifier_horizontal import (
    CalculationVerifierHorizontal,
    INITIAL_EXPECTED_SUM as INITIAL_EXPECTED_SUM_HORIZONTAL,
    DEFAULT_OVERSHOOT_RATIO as DEFAULT_OVERSHOOT_RATIO_HORIZONTAL,
    MAX_MISSING_CHILDREN_DISPLAY as MAX_MISSING_CHILDREN_DISPLAY_HORIZONTAL,
    ZERO_VALUE as ZERO_VALUE_HORIZONTAL,
)
from .duplicate_fact_checker import (
    DuplicateFactChecker,
    MAX_DUPLICATES_DISPLAY,
)
from .horizontal_checker import HorizontalChecker

# Import from other modules
from .binding_checker import BindingChecker, BindingResult, BindingStatus
from .decimal_tolerance import DecimalTolerance, ToleranceResult
from .dimension_handler import (
    DimensionHandler,
    Dimension,
    DimensionMember,
    RoleDimensions,
    ContextDimensions,
)
from .sign_weight_handler import (
    SignWeightHandler,
    SignInfo,
    SignSource,
    create_sign_weight_handler_from_filing,
    infer_sign_from_concept_name,
)
# Import from fact_rules and its sub-modules
from .fact_rules import (
    PeriodInfo,
    PeriodExtractor,
    ContextClassifier,
    ContextMatcher,
    FactMatch,
    FactFinder,
    REGEX_YEAR_PATTERN,
    REGEX_FLAGS,
    PERIOD_TYPE_DURATION,
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_UNKNOWN,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FALLBACK,
    MATCH_TYPE_PERIOD_MATCH,
    MATCH_TYPE_NONE,
)
from .period_extraction import PeriodInfo as PeriodInfoDirect, PeriodExtractor as PeriodExtractorDirect
from .context_classification import ContextClassifier as ContextClassifierDirect
from .context_matching import ContextMatcher as ContextMatcherDirect
from .fact_finder import FactMatch as FactMatchDirect, FactFinder as FactFinderDirect
from .vertical_checker import VerticalChecker
from .library_checker import LibraryChecker
from .calculation_verifier import (
    CalculationVerifier,
    CalculationVerificationResult,
    DualVerificationResult,
    ChildContribution,
)
from .check_constants import (
    # Sign weight handler constants
    SIGN_MAGNITUDE_TOLERANCE,
    SIGN_DOUBLING_TOLERANCE,
    # Decimal tolerance constants
    DECIMAL_COMPARISON_EPSILON_BASE,
    DECIMAL_EPSILON_MULTIPLIER,
    # Calculation verifier constants
    CALC_VERIFIER_DEFAULT_TOLERANCE,
    CALC_VERIFIER_DEFAULT_ROUNDING,
    INITIAL_EXPECTED_SUM,
    DEFAULT_OVERSHOOT_RATIO,
    # Binding checker constants
    MAX_MISSING_CHILDREN_DISPLAY,
    FIRST_ELEMENT_INDEX,
    # Vertical checker constants
    VERTICAL_DEFAULT_VALUE,
    # Horizontal checker constants
    CONTEXT_COUNT_MINIMUM,
    MAX_INCONSISTENT_DUPLICATES_DISPLAY,
    MAX_MULTI_ROLE_PARENTS_LOG,
    # Comparison constants
    ZERO_THRESHOLD,
    MIN_DUPLICATE_ENTRIES,
    ITERATION_START_INDEX,
)

__all__ = [
    # C-Equal module (refactored)
    'CEqual',
    'FactGroups',
    'ContextGroup',
    'FactEntry',
    'DuplicateInfo',
    'DuplicateType',
    # Value parsing
    'ValueParser',
    'NIL_VALUES',
    'EM_DASH',
    'EN_DASH',
    # Concept normalization
    'ConceptNormalizer',
    'KNOWN_TAXONOMY_PREFIXES',
    'MAX_EXTENSION_PREFIX_LENGTH',
    # Horizontal checker (refactored)
    'HorizontalChecker',
    'CheckResult',
    'InstanceDocumentFinder',
    'INSTANCE_DOCUMENT_PATTERNS',
    'INSTANCE_DOCUMENT_EXCLUSIONS',
    'CalculationVerifierHorizontal',
    'DuplicateFactChecker',
    # Binding checker
    'BindingChecker',
    'BindingResult',
    'BindingStatus',
    # Decimal tolerance
    'DecimalTolerance',
    'ToleranceResult',
    # Dimension handler
    'DimensionHandler',
    'Dimension',
    'DimensionMember',
    'RoleDimensions',
    'ContextDimensions',
    # Sign/Weight handler
    'SignWeightHandler',
    'SignInfo',
    'SignSource',
    'create_sign_weight_handler_from_filing',
    'infer_sign_from_concept_name',
    # Fact rules (centralized fact finding)
    'PeriodInfo',
    'PeriodExtractor',
    'ContextClassifier',
    'ContextMatcher',
    'FactMatch',
    'FactFinder',
    'REGEX_YEAR_PATTERN',
    'REGEX_FLAGS',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_UNKNOWN',
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',
    # Fact rules sub-modules (for direct import if needed)
    'PeriodInfoDirect',
    'PeriodExtractorDirect',
    'ContextClassifierDirect',
    'ContextMatcherDirect',
    'FactMatchDirect',
    'FactFinderDirect',
    # Checkers
    'VerticalChecker',
    'LibraryChecker',
    # Calculation verification
    'CalculationVerifier',
    'CalculationVerificationResult',
    'DualVerificationResult',
    'ChildContribution',
    # Configuration constants (c_equal)
    'DUPLICATE_PERCENTAGE_TOLERANCE',
    'SAMPLE_CONCEPTS_LIMIT',
    'SAMPLE_CONTEXTS_LIMIT',
    # Configuration constants (horizontal checker)
    'INITIAL_EXPECTED_SUM_HORIZONTAL',
    'DEFAULT_OVERSHOOT_RATIO_HORIZONTAL',
    'MAX_MISSING_CHILDREN_DISPLAY_HORIZONTAL',
    'ZERO_VALUE_HORIZONTAL',
    'MAX_DUPLICATES_DISPLAY',
    'CONTEXT_COUNT_MINIMUM',
    'MAX_INCONSISTENT_DUPLICATES_DISPLAY',
    'MAX_MULTI_ROLE_PARENTS_LOG',
    # Configuration constants (other)
    'SIGN_MAGNITUDE_TOLERANCE',
    'SIGN_DOUBLING_TOLERANCE',
    'DECIMAL_COMPARISON_EPSILON_BASE',
    'DECIMAL_EPSILON_MULTIPLIER',
    'CALC_VERIFIER_DEFAULT_TOLERANCE',
    'CALC_VERIFIER_DEFAULT_ROUNDING',
    'INITIAL_EXPECTED_SUM',
    'DEFAULT_OVERSHOOT_RATIO',
    'MAX_MISSING_CHILDREN_DISPLAY',
    'FIRST_ELEMENT_INDEX',
    'VERTICAL_DEFAULT_VALUE',
    'ZERO_THRESHOLD',
    'MIN_DUPLICATE_ENTRIES',
    'ITERATION_START_INDEX',
]
