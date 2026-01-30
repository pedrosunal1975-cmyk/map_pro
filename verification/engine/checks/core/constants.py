# Path: verification/engine/checks/core/constants.py
"""
Verification Checks Constants

Check names and tolerance values for verification checks.
NO hardcoded concept patterns or formulas - all relationships
come from XBRL sources (company linkbase and standard taxonomy).

CONCEPT NORMALIZATION:
Different XBRL sources use different separators for QNames:
- Calculation linkbase: us-gaap:Assets (colon)
- Presentation/mapped: us-gaap_Assets (underscore)
- Some sources: us-gaap-Assets (dash)

The ConceptNormalizer provides TEMPORARY normalization for matching
during calculation verification ONLY. Original names are preserved
and returned in results.
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

# Calculation completeness threshold (minimum percentage of children required)
# If fewer than this percentage of children are found, calculation is SKIPPED
# (not failed) because incomplete data cannot give meaningful verification results.
# Example: 0.5 means at least 50% of children must be found to verify
CALCULATION_COMPLETENESS_THRESHOLD = 0.5  # 50% minimum

# Overshoot severity threshold (percentage of parent magnitude)
# When sum of children exceeds parent, if the excess is less than this percentage,
# it's treated as a rounding issue (WARNING) rather than a real problem (CRITICAL).
# Example: 0.05 means overshoot up to 5% of parent value is considered rounding.
OVERSHOOT_ROUNDING_THRESHOLD = 0.05  # 5%


# ==============================================================================
# CONCEPT NAME NORMALIZATION (for calculation verification only)
# ==============================================================================

from ....loaders.constants import normalize_name as loader_normalize_name

# Separators used in different XBRL sources
# These can be interchanged when matching concept names
CONCEPT_SEPARATORS = [
    ':',   # Colon - used in calculation linkbase (us-gaap:Assets)
    '_',   # Underscore - used in presentation/mapped (us-gaap_Assets)
    '-',   # Dash - sometimes used (us-gaap-Assets)
    ' ',   # Space - rare but possible
]

# The canonical separator used for normalization (internal use only)
CANONICAL_SEPARATOR = '_'


class ConceptNormalizer:
    """
    Temporary concept name normalizer for calculation verification.

    DESIGN:
    - Normalizes concept names for matching (colon/underscore/dash → canonical)
    - Maintains bidirectional mapping to preserve original names
    - Only used during calculation comparison, not for permanent changes

    USAGE:
        normalizer = ConceptNormalizer()

        # Normalize for comparison
        norm_name = normalizer.normalize("us-gaap:Assets")  # → "us-gaap_assets"

        # Register original names
        normalizer.register("us-gaap:Assets", source="xbrl")
        normalizer.register("us-gaap_Assets", source="statement")

        # Get original name back
        original = normalizer.get_original(norm_name, source="xbrl")
    """

    def __init__(self):
        """Initialize normalizer with empty mappings."""
        # Maps: normalized_name → {source: original_name}
        self._originals: dict[str, dict[str, str]] = {}

    @staticmethod
    def normalize(concept: str) -> str:
        """
        Normalize a concept name for comparison using LOCAL NAME only.

        Extracts the local name (after namespace separator), then applies
        canonical normalization (removes separators, lowercases).

        Args:
            concept: Original concept name (e.g., "us-gaap:Assets" or "Assets")

        Returns:
            Normalized LOCAL name (e.g., "assets")
        """
        if not concept:
            return ''

        # Extract local name - find the LAST separator and take everything after
        # This handles: "us-gaap:Assets" -> "Assets", "Assets" -> "Assets"
        local_name = concept
        for sep in CONCEPT_SEPARATORS:
            if sep in local_name:
                # Take the part after the LAST occurrence of this separator
                local_name = local_name.rsplit(sep, 1)[-1]

        # Use canonical normalize_name for consistent comparison
        return loader_normalize_name(local_name)

    def register(self, concept: str, source: str = 'default') -> str:
        """
        Register a concept and return its normalized form.

        Maintains mapping from normalized → original for each source.

        Args:
            concept: Original concept name
            source: Source identifier (e.g., 'xbrl', 'statement', 'taxonomy')

        Returns:
            Normalized concept name
        """
        normalized = self.normalize(concept)

        if normalized not in self._originals:
            self._originals[normalized] = {}

        self._originals[normalized][source] = concept

        return normalized

    def get_original(self, normalized: str, source: str = 'default') -> str:
        """
        Get original concept name from normalized form.

        Args:
            normalized: Normalized concept name
            source: Source to get original from

        Returns:
            Original concept name, or normalized if not found
        """
        if normalized in self._originals:
            if source in self._originals[normalized]:
                return self._originals[normalized][source]
            # Return any original if specific source not found
            if self._originals[normalized]:
                return next(iter(self._originals[normalized].values()))

        return normalized

    def get_all_originals(self, normalized: str) -> dict[str, str]:
        """
        Get all original names for a normalized concept.

        Args:
            normalized: Normalized concept name

        Returns:
            Dictionary mapping source → original_name
        """
        return self._originals.get(normalized, {})

    def build_normalized_lookup(
        self,
        concepts: dict[str, any],
        source: str = 'default'
    ) -> dict[str, any]:
        """
        Build a lookup dictionary with normalized keys.

        Useful for creating fact lookups that work with any separator format.

        Args:
            concepts: Dictionary with concept names as keys
            source: Source identifier for these concepts

        Returns:
            New dictionary with normalized keys, original values
        """
        normalized_lookup = {}

        for concept, value in concepts.items():
            norm_key = self.register(concept, source)
            normalized_lookup[norm_key] = value

        return normalized_lookup

    def clear(self):
        """Clear all registered mappings."""
        self._originals.clear()


# ==============================================================================
# DIMENSIONAL CONTEXT DETECTION
# ==============================================================================
# Patterns to identify dimensional (non-default) contexts
# Dimensional contexts contain axis and member identifiers, indicating
# the fact is for a specific dimensional slice (e.g., by equity component,
# by segment, by product line)
#
# Uses simple substring matching (case-insensitive):
# - 'axis' anywhere in context_id indicates a dimensional axis
# - 'member' anywhere in context_id indicates a dimensional member

DIMENSIONAL_CONTEXT_INDICATORS = [
    'axis',      # Matches *axis* - any axis indicator
    'member',    # Matches *member* - any member indicator
]


# ==============================================================================
# PERIOD EXTRACTION FROM CONTEXT_ID
# ==============================================================================
# Context IDs encode period information in various formats.
# These patterns allow extraction of period data for compatibility matching.
#
# IMPORTANT: These patterns are flexible to support multiple market formats.
# The order matters - more specific patterns should be tried first.

# Period type indicators found in context_id prefixes (case-insensitive)
# Format: (indicator, period_type) where period_type is 'duration' or 'instant'
PERIOD_TYPE_INDICATORS = [
    ('duration', 'duration'),    # Duration_1_1_2024_To_12_31_2024
    ('period', 'duration'),      # Period_...
    ('from', 'duration'),        # From_1_1_2024_To_12_31_2024
    ('asof', 'instant'),         # AsOf_12_31_2024
    ('instant', 'instant'),      # Instant_12_31_2024
    ('as_of', 'instant'),        # As_Of_12_31_2024
    ('at', 'instant'),           # At_12_31_2024
]

# Separator patterns used in context_id date encoding
# Different markets and tools use different separators
CONTEXT_ID_DATE_SEPARATORS = [
    '_',   # Underscore: Duration_1_1_2024
    '-',   # Dash: Duration-1-1-2024
    '.',   # Dot: Duration.1.1.2024
]

# Date component patterns
# These regex fragments match common date component formats in context_ids
# Format: month_day_year or day_month_year depending on market
#
# The patterns are building blocks combined by PeriodExtractor in fact_rules.py:
# - MONTH: 1-12 or 01-12
# - DAY: 1-31 or 01-31
# - YEAR: 4-digit year (19xx, 20xx)
#
# NOTE: Curly braces in regex quantifiers must be doubled ({{1,2}}) because
# these patterns are used with str.format() for template substitution.
DATE_COMPONENT_PATTERNS = {
    'month': r'(\d{{1,2}})',           # 1-12 or 01-12 (escaped braces for format)
    'day': r'(\d{{1,2}})',             # 1-31 or 01-31 (escaped braces for format)
    'year': r'(\d{{4}})',              # 4-digit year (escaped braces for format)
    'separator': r'[_\-\.]',           # Any date separator
    'range_indicator': r'[_\-\.]?(?:to|through|thru)[_\-\.]?',  # Duration range separator
}

# Full context_id period extraction patterns (compiled in fact_rules.py)
# These define the structure of period information in context_ids
# Format: (pattern_name, regex_template, extraction_groups)
# Note: regex_template uses {sep} placeholder for separator pattern
PERIOD_EXTRACTION_PATTERNS = [
    # Duration: Duration_M_D_YYYY_To_M_D_YYYY or Duration_MM_DD_YYYY_To_MM_DD_YYYY
    (
        'duration_mdy_mdy',
        r'^(?:duration|period|from){sep}{month}{sep}{day}{sep}{year}{range}{month}{sep}{day}{sep}{year}',
        ['start_month', 'start_day', 'start_year', 'end_month', 'end_day', 'end_year']
    ),
    # Duration: Duration_YYYY-MM-DD_To_YYYY-MM-DD (ISO format)
    (
        'duration_ymd_ymd',
        r'^(?:duration|period|from){sep}{year}{sep}{month}{sep}{day}{range}{year}{sep}{month}{sep}{day}',
        ['start_year', 'start_month', 'start_day', 'end_year', 'end_month', 'end_day']
    ),
    # Instant: AsOf_M_D_YYYY or Instant_MM_DD_YYYY
    (
        'instant_mdy',
        r'^(?:asof|instant|as_of|at){sep}{month}{sep}{day}{sep}{year}',
        ['month', 'day', 'year']
    ),
    # Instant: AsOf_YYYY-MM-DD (ISO format)
    (
        'instant_ymd',
        r'^(?:asof|instant|as_of|at){sep}{year}{sep}{month}{sep}{day}',
        ['year', 'month', 'day']
    ),
    # Fallback: Extract any 4-digit year from context_id
    # NOTE: Braces escaped for str.format() compatibility
    (
        'year_only',
        r'(\d{{4}})',
        ['year']
    ),
]


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
    'CALCULATION_COMPLETENESS_THRESHOLD',
    'OVERSHOOT_ROUNDING_THRESHOLD',

    # Concept normalization (for calculation verification)
    'CONCEPT_SEPARATORS',
    'CANONICAL_SEPARATOR',
    'ConceptNormalizer',

    # Dimensional context detection
    'DIMENSIONAL_CONTEXT_INDICATORS',

    # Period extraction patterns
    'PERIOD_TYPE_INDICATORS',
    'CONTEXT_ID_DATE_SEPARATORS',
    'DATE_COMPONENT_PATTERNS',
    'PERIOD_EXTRACTION_PATTERNS',
]
