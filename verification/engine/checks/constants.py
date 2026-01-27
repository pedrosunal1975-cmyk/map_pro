# Path: verification/engine/checks/constants.py
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


# ==============================================================================
# CONCEPT NAME NORMALIZATION (for calculation verification only)
# ==============================================================================

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

        Extracts the local name (after namespace separator) and lowercases.
        This matches how the mapper matches concepts - by local name only.

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

        # Lowercase for case-insensitive matching
        return local_name.lower()

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

    # Concept normalization (for calculation verification)
    'CONCEPT_SEPARATORS',
    'CANONICAL_SEPARATOR',
    'ConceptNormalizer',
]
