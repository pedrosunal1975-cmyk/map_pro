# Path: verification/engine/checks/__init__.py
"""
Verification Checks Package

Reorganized into logical subpackages:

- core/: Fundamental types and utilities
  - check_result: CheckResult dataclass for standardized results
  - constants: Check type constants and thresholds
  - check_constants: Configuration constants for all checks
  - decimal_tolerance: XBRL rounding rules for value comparison
  - value_parsing: Parsing raw values from statements
  - concept_normalization: Normalizing concept names for comparison

- context/: Context-based fact grouping and matching
  - duplicate_detection: Duplicate fact detection and classification
  - context_grouping: Grouping facts by XBRL context
  - context_classification: Classifying context types (dimensional, default)
  - period_extraction: Extracting period information from context_id
  - context_matching: Checking context compatibility
  - fact_finder: Finding facts across contexts
  - fact_rules: Re-exports all context utilities

- c_equal/: C-Equal (context-equal) verification
  - c_equal: Main CEqual class for context-based verification

- binding/: Calculation binding logic
  - binding_checker: Determines if calculations should bind per XBRL spec
  - role_scoping: Role-based scoping for XBRL Calculations 1.1

- handlers/: Specialized handlers for XBRL attributes
  - sign_weight_handler: XBRL sign attributes and calculation weight handling
  - dimension_handler: XBRL dimensional structure parsing
  - instance_document_finder: Finding XBRL instance documents

- verifiers/: Calculation verification implementations
  - calculation_verifier: General calculation verification
  - calculation_verifier_horizontal: Horizontal calculation verification
  - duplicate_fact_checker: Duplicate fact checking

- checkers/: High-level verification checkers
  - horizontal_checker: Within-statement validation
  - vertical_checker: Cross-statement consistency
  - library_checker: Standard taxonomy conformance
"""

# Import from core modules
from .core.check_result import CheckResult
from .core.constants import (
    CHECK_CALCULATION_CONSISTENCY,
    CHECK_DUPLICATE_FACTS,
    CHECK_COMMON_VALUES_CONSISTENCY,
    CHECK_CONCEPT_VALIDITY,
    CHECK_PERIOD_TYPE_MATCH,
    CHECK_BALANCE_TYPE_MATCH,
    CHECK_DATA_TYPE_MATCH,
    DEFAULT_CALCULATION_TOLERANCE,
    DEFAULT_ROUNDING_TOLERANCE,
    LARGE_VALUE_THRESHOLD,
    OVERSHOOT_ROUNDING_THRESHOLD,
)
from .core.check_constants import (
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
from .core.decimal_tolerance import DecimalTolerance, ToleranceResult
from .core.value_parsing import (
    ValueParser,
    NIL_VALUES,
    EM_DASH,
    EN_DASH,
)
from .core.concept_normalization import (
    ConceptNormalizer,
    KNOWN_TAXONOMY_PREFIXES,
    MAX_EXTENSION_PREFIX_LENGTH,
)

# Import from context modules
from .context.duplicate_detection import (
    DuplicateType,
    FactEntry,
    DuplicateInfo,
    DUPLICATE_PERCENTAGE_TOLERANCE,
)
from .context.context_grouping import (
    ContextGroup,
    FactGroups,
    SAMPLE_CONCEPTS_LIMIT,
    SAMPLE_CONTEXTS_LIMIT,
)
from .context.period_extraction import (
    PeriodInfo,
    PeriodExtractor,
    REGEX_YEAR_PATTERN,
    REGEX_FLAGS,
)
from .context.context_classification import ContextClassifier
from .context.context_matching import (
    ContextMatcher,
    PERIOD_TYPE_DURATION,
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_UNKNOWN,
)
from .context.fact_finder import (
    FactMatch,
    FactFinder,
    MATCH_TYPE_EXACT,
    MATCH_TYPE_FALLBACK,
    MATCH_TYPE_PERIOD_MATCH,
    MATCH_TYPE_NONE,
)

# Import from c_equal module
from .c_equal.c_equal import CEqual

# Import from binding modules
from .binding.binding_checker import BindingChecker, BindingResult, BindingStatus
from .binding.role_scoping import group_arcs_by_role_and_parent

# Import from handlers
from .handlers.sign_weight_handler import (
    SignWeightHandler,
    SignInfo,
    SignSource,
    create_sign_weight_handler_from_filing,
    infer_sign_from_concept_name,
)
from .handlers.dimension_handler import (
    DimensionHandler,
    Dimension,
    DimensionMember,
    RoleDimensions,
    ContextDimensions,
)
from .handlers.instance_document_finder import (
    InstanceDocumentFinder,
    INSTANCE_DOCUMENT_PATTERNS,
    INSTANCE_DOCUMENT_EXCLUSIONS,
)

# Import from verifiers
from .verifiers.calculation_verifier import (
    CalculationVerifier,
    CalculationVerificationResult,
    DualVerificationResult,
    ChildContribution,
)
from .verifiers.calculation_verifier_horizontal import (
    CalculationVerifierHorizontal,
    INITIAL_EXPECTED_SUM as INITIAL_EXPECTED_SUM_HORIZONTAL,
    DEFAULT_OVERSHOOT_RATIO as DEFAULT_OVERSHOOT_RATIO_HORIZONTAL,
    MAX_MISSING_CHILDREN_DISPLAY as MAX_MISSING_CHILDREN_DISPLAY_HORIZONTAL,
    ZERO_VALUE as ZERO_VALUE_HORIZONTAL,
)
from .verifiers.duplicate_fact_checker import (
    DuplicateFactChecker,
    MAX_DUPLICATES_DISPLAY,
)

# Import from checkers
from .checkers.horizontal_checker import HorizontalChecker
from .checkers.vertical_checker import VerticalChecker
from .checkers.library_checker import LibraryChecker

__all__ = [
    # Core types
    'CheckResult',
    'DecimalTolerance',
    'ToleranceResult',
    'ValueParser',
    'ConceptNormalizer',

    # Context grouping
    'CEqual',
    'FactGroups',
    'ContextGroup',
    'FactEntry',
    'DuplicateInfo',
    'DuplicateType',

    # Period and context handling
    'PeriodInfo',
    'PeriodExtractor',
    'ContextClassifier',
    'ContextMatcher',
    'FactMatch',
    'FactFinder',

    # Binding
    'BindingChecker',
    'BindingResult',
    'BindingStatus',
    'group_arcs_by_role_and_parent',

    # Handlers
    'SignWeightHandler',
    'SignInfo',
    'SignSource',
    'create_sign_weight_handler_from_filing',
    'infer_sign_from_concept_name',
    'DimensionHandler',
    'Dimension',
    'DimensionMember',
    'RoleDimensions',
    'ContextDimensions',
    'InstanceDocumentFinder',

    # Verifiers
    'CalculationVerifier',
    'CalculationVerificationResult',
    'DualVerificationResult',
    'ChildContribution',
    'CalculationVerifierHorizontal',
    'DuplicateFactChecker',

    # Checkers
    'HorizontalChecker',
    'VerticalChecker',
    'LibraryChecker',

    # Constants - check names
    'CHECK_CALCULATION_CONSISTENCY',
    'CHECK_DUPLICATE_FACTS',
    'CHECK_COMMON_VALUES_CONSISTENCY',
    'CHECK_CONCEPT_VALIDITY',
    'CHECK_PERIOD_TYPE_MATCH',
    'CHECK_BALANCE_TYPE_MATCH',
    'CHECK_DATA_TYPE_MATCH',

    # Constants - thresholds
    'DEFAULT_CALCULATION_TOLERANCE',
    'DEFAULT_ROUNDING_TOLERANCE',
    'LARGE_VALUE_THRESHOLD',
    'OVERSHOOT_ROUNDING_THRESHOLD',
    'SIGN_MAGNITUDE_TOLERANCE',
    'SIGN_DOUBLING_TOLERANCE',
    'DECIMAL_COMPARISON_EPSILON_BASE',
    'DECIMAL_EPSILON_MULTIPLIER',

    # Constants - configuration
    'CALC_VERIFIER_DEFAULT_TOLERANCE',
    'CALC_VERIFIER_DEFAULT_ROUNDING',
    'INITIAL_EXPECTED_SUM',
    'DEFAULT_OVERSHOOT_RATIO',
    'MAX_MISSING_CHILDREN_DISPLAY',
    'FIRST_ELEMENT_INDEX',
    'VERTICAL_DEFAULT_VALUE',
    'CONTEXT_COUNT_MINIMUM',
    'MAX_INCONSISTENT_DUPLICATES_DISPLAY',
    'MAX_MULTI_ROLE_PARENTS_LOG',
    'ZERO_THRESHOLD',
    'MIN_DUPLICATE_ENTRIES',
    'ITERATION_START_INDEX',

    # Constants - duplicates
    'DUPLICATE_PERCENTAGE_TOLERANCE',
    'SAMPLE_CONCEPTS_LIMIT',
    'SAMPLE_CONTEXTS_LIMIT',

    # Constants - horizontal aliases
    'INITIAL_EXPECTED_SUM_HORIZONTAL',
    'DEFAULT_OVERSHOOT_RATIO_HORIZONTAL',
    'MAX_MISSING_CHILDREN_DISPLAY_HORIZONTAL',
    'ZERO_VALUE_HORIZONTAL',
    'MAX_DUPLICATES_DISPLAY',

    # Constants - value parsing
    'NIL_VALUES',
    'EM_DASH',
    'EN_DASH',
    'KNOWN_TAXONOMY_PREFIXES',
    'MAX_EXTENSION_PREFIX_LENGTH',

    # Constants - period/context
    'REGEX_YEAR_PATTERN',
    'REGEX_FLAGS',
    'PERIOD_TYPE_DURATION',
    'PERIOD_TYPE_INSTANT',
    'PERIOD_TYPE_UNKNOWN',
    'MATCH_TYPE_EXACT',
    'MATCH_TYPE_FALLBACK',
    'MATCH_TYPE_PERIOD_MATCH',
    'MATCH_TYPE_NONE',

    # Constants - instance document
    'INSTANCE_DOCUMENT_PATTERNS',
    'INSTANCE_DOCUMENT_EXCLUSIONS',
]
