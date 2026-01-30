# Path: verification/engine/checks/handlers/sign_weight_handler.py
"""
Sign and Weight Handler for XBRL Verification.

This module handles the complexities of XBRL sign conventions and calculation weights:

1. **XBRL Sign Attributes**: In iXBRL, negative values are often displayed as positive
   text with a sign="-" attribute. This module parses these attributes.

2. **Calculation Weights**: XBRL calculation linkbase uses weights (-1.0, 1.0) to
   indicate how children contribute to parent totals.

3. **Sign Reconciliation**: Provides methods to reconcile values when source data
   (like XLSX exports) loses sign information.

Key Use Cases:
- Cash Flow Statements: Payments (outflows) have weight=-1, Proceeds (inflows) have weight=1
- Income Statements: Expenses typically subtracted, Revenues added
- Balance Sheet: Typically straightforward (no sign issues)

This module is designed to be:
- Agnostic: Works with any XBRL filing, any taxonomy
- Robust: Handles missing data gracefully
- Efficient: Parses once, provides fast lookups
- Diagnostic: Can explain sign decisions when needed
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import re
import logging

from ....loaders.constants import normalize_name

logger = logging.getLogger(__name__)


class SignSource(Enum):
    """Source of sign information."""
    XBRL_ATTRIBUTE = "xbrl_sign_attribute"  # sign="-" in iXBRL
    CALCULATION_WEIGHT = "calculation_weight"  # weight attribute in cal linkbase
    CONCEPT_SEMANTICS = "concept_semantics"  # Inferred from concept name
    VALUE_PATTERN = "value_pattern"  # Detected from value patterns
    NONE = "none"


@dataclass
class SignInfo:
    """Sign information for a specific fact."""
    concept: str
    context_id: str
    sign_multiplier: int  # 1 or -1
    source: SignSource
    original_value: Optional[float] = None
    corrected_value: Optional[float] = None
    notes: str = ""


@dataclass
class ConceptSignPattern:
    """Sign pattern for a concept based on semantic analysis."""
    concept_pattern: str  # regex pattern
    expected_sign: int  # 1 for positive, -1 for negative
    statement_type: str  # 'cash_flow', 'income', 'balance_sheet'
    description: str


# Common patterns for cash flow concepts
CASH_FLOW_SIGN_PATTERNS = [
    ConceptSignPattern(
        r"Payments?(To|For|Of|Related)",
        -1,
        "cash_flow",
        "Payments are cash outflows (negative)"
    ),
    ConceptSignPattern(
        r"Repayments?Of",
        -1,
        "cash_flow",
        "Repayments are cash outflows (negative)"
    ),
    ConceptSignPattern(
        r"Proceeds?From",
        1,
        "cash_flow",
        "Proceeds are cash inflows (positive)"
    ),
    ConceptSignPattern(
        r"NetCashProvidedByUsedIn",
        0,  # 0 means sign depends on actual cash position
        "cash_flow",
        "Net cash can be positive or negative"
    ),
]


@dataclass
class SignWeightHandler:
    """
    Handles XBRL sign attributes and calculation weights.

    This handler parses XBRL instance documents to extract sign information
    that may be lost when exporting to XLSX or other formats.

    Attributes:
        sign_corrections: Dict mapping (concept, context) to sign multiplier
        parsed_files: Set of files that have been parsed
        diagnostics: List of diagnostic messages for debugging
    """

    sign_corrections: dict = field(default_factory=dict)
    parsed_files: set = field(default_factory=set)
    diagnostics: list = field(default_factory=list)
    _concept_cache: dict = field(default_factory=dict)

    def parse_instance_document(self, instance_file: str | Path) -> int:
        """
        Parse XBRL instance document to extract sign attributes.

        Handles both inline XBRL (iXBRL) and traditional XBRL formats.

        Args:
            instance_file: Path to XBRL instance document (.htm, .xml)

        Returns:
            Number of sign corrections found
        """
        instance_path = Path(instance_file)
        if not instance_path.exists():
            logger.warning(f"Instance file not found: {instance_path}")
            return 0

        if str(instance_path) in self.parsed_files:
            return len([k for k in self.sign_corrections if k[0] == str(instance_path)])

        try:
            with open(instance_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Detect if iXBRL or traditional XBRL
            is_ixbrl = '<ix:' in content or 'xmlns:ix=' in content

            if is_ixbrl:
                count = self._parse_ixbrl(content, instance_path)
            else:
                count = self._parse_traditional_xbrl(content, instance_path)

            self.parsed_files.add(str(instance_path))
            logger.info(f"Parsed {instance_path.name}: found {count} sign corrections")

            # Log sample of corrections for debugging - show at INFO level for troubleshooting
            if count > 0:
                sample_keys = list(self.sign_corrections.keys())[:5]
                logger.info(f"Sample sign correction keys (concept, context_id): {sample_keys}")
                # Also log a few full entries to see the format
                for i, (key, info) in enumerate(list(self.sign_corrections.items())[:3]):
                    logger.info(f"  Sign correction {i+1}: concept='{key[0]}', context='{key[1]}', multiplier={info.sign_multiplier}")

            return count

        except Exception as e:
            logger.error(f"Error parsing {instance_path}: {e}")
            return 0

    def _parse_ixbrl(self, content: str, source_file: Path) -> int:
        """
        Parse inline XBRL (iXBRL) document for sign attributes.

        iXBRL uses sign="-" attribute to indicate negative values that are
        displayed as positive text in the document.

        XBRL attribute order varies, so we use a flexible approach:
        1. Find all ix:nonFraction elements (with various namespace prefixes)
        2. Extract attributes from each element regardless of order
        """
        count = 0

        # Find all nonFraction elements with sign attribute
        # Handle various namespace prefixes: ix:, ixbrl:, iXBRL:, etc.
        # Also handle both double and single quotes for attribute values
        # The (?:...) is non-capturing group, allows attributes in any order
        patterns = [
            # Standard ix: prefix
            re.compile(
                r'<ix:nonFraction\s+([^>]*sign\s*=\s*["\'][+-]["\'][^>]*)>',
                re.IGNORECASE
            ),
            # Alternative prefixes (iXBRL, ixbrl, etc.)
            re.compile(
                r'<(?:ixbrl|iXBRL):nonFraction\s+([^>]*sign\s*=\s*["\'][+-]["\'][^>]*)>',
                re.IGNORECASE
            ),
        ]

        for pattern in patterns:
            for match in pattern.finditer(content):
                attrs = match.group(1)

                # Extract individual attributes using flexible patterns
                # Handle both single and double quotes, optional whitespace around =
                sign_match = re.search(r'sign\s*=\s*["\']([+-])["\']', attrs)
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', attrs)
                context_match = re.search(r'contextRef\s*=\s*["\']([^"\']+)["\']', attrs)

                if sign_match and name_match and context_match:
                    sign_attr = sign_match.group(1)
                    concept = name_match.group(1)
                    context_id = context_match.group(1)

                    # sign="-" means the value should be negated
                    sign_multiplier = -1 if sign_attr == '-' else 1

                    key = (concept, context_id)
                    if key not in self.sign_corrections:
                        self.sign_corrections[key] = SignInfo(
                            concept=concept,
                            context_id=context_id,
                            sign_multiplier=sign_multiplier,
                            source=SignSource.XBRL_ATTRIBUTE,
                            notes=f"sign='{sign_attr}' in {source_file.name}"
                        )
                        count += 1

        return count

    def _parse_traditional_xbrl(self, content: str, source_file: Path) -> int:
        """
        Parse traditional XBRL document.

        Traditional XBRL doesn't use sign attributes - negative values are
        represented with a minus sign in the value itself.
        """
        # Traditional XBRL typically doesn't need sign correction
        # as negative values are already negative in the XML
        return 0

    def _extract_local_name(self, concept: str) -> str:
        """
        Extract local name from concept, stripping namespace prefix.

        Handles both colon (us-gaap:Assets) and underscore (us-gaap_Assets) separators.

        Args:
            concept: Full concept name with optional namespace

        Returns:
            Local name without namespace prefix
        """
        # Handle colon separator (us-gaap:Assets)
        if ':' in concept:
            return concept.split(':')[-1]
        # Handle underscore separator for namespace (us-gaap_Assets)
        # But be careful: concept names themselves can have underscores
        # Check if first part looks like a namespace prefix
        if '_' in concept:
            parts = concept.split('_', 1)
            # Common namespace prefixes
            if parts[0].lower() in ('us-gaap', 'usgaap', 'ifrs', 'dei', 'srt', 'ecd', 'country'):
                return parts[1]
        return concept

    def get_sign_correction(
        self,
        concept: str,
        context_id: str,
        do_normalize: bool = True
    ) -> int:
        """
        Get sign correction multiplier for a fact.

        Args:
            concept: XBRL concept name (e.g., "us-gaap:NetCashProvidedByUsedInFinancingActivities")
            context_id: XBRL context reference
            do_normalize: If True, normalize concept name for matching

        Returns:
            1 if no correction needed, -1 if value should be negated
        """
        # Try exact match first
        key = (concept, context_id)
        if key in self.sign_corrections:
            logger.debug(f"Sign correction FOUND (exact): {concept} in {context_id} -> -1")
            return self.sign_corrections[key].sign_multiplier

        # Try with normalized concept name
        if do_normalize:
            # Handle both us-gaap:Name and us-gaap_Name formats
            norm_concept = concept.replace('_', ':') if '_' in concept else concept
            key = (norm_concept, context_id)
            if key in self.sign_corrections:
                return self.sign_corrections[key].sign_multiplier

            # Extract local name and normalize using the standard function
            local_name = self._extract_local_name(concept)
            normalized_lookup = normalize_name(local_name)

            # Try to find a stored correction that matches by normalized local name
            for (stored_concept, ctx), info in self.sign_corrections.items():
                if ctx != context_id:
                    continue
                # Extract and normalize stored concept's local name
                stored_local = self._extract_local_name(stored_concept)
                normalized_stored = normalize_name(stored_local)

                if normalized_stored == normalized_lookup:
                    logger.debug(f"Sign correction FOUND (normalized): {concept} in {context_id} -> {info.sign_multiplier}")
                    return info.sign_multiplier

        # Check if this concept has ANY sign correction (any context)
        # This helps diagnose context ID format mismatches
        if self.sign_corrections:
            local_name = self._extract_local_name(concept)
            normalized_lookup = normalize_name(local_name)

            # Look for any matching concept regardless of context
            matching_concepts = []
            for (stored_concept, stored_ctx), info in self.sign_corrections.items():
                stored_local = self._extract_local_name(stored_concept)
                if normalize_name(stored_local) == normalized_lookup:
                    matching_concepts.append((stored_ctx, info.sign_multiplier))

            if matching_concepts:
                # Found sign corrections for this concept but in different context(s)
                logger.warning(
                    f"Sign correction EXISTS for '{concept}' but in different context(s). "
                    f"Looking for context: '{context_id}'. "
                    f"Available: {[ctx for ctx, _ in matching_concepts[:3]]}{'...' if len(matching_concepts) > 3 else ''}"
                )
            else:
                # Log when concept has no sign correction at all (common for concepts that
                # don't have sign="-" in iXBRL - they may genuinely be positive values)
                logger.debug(
                    f"No sign correction for '{concept}' (normalized: '{normalized_lookup}') - "
                    f"concept may not have sign='-' in iXBRL"
                )

        return 1  # No correction needed

    def apply_sign_correction(
        self,
        concept: str,
        context_id: str,
        value: float
    ) -> tuple[float, bool]:
        """
        Apply sign correction to a value.

        Args:
            concept: XBRL concept name
            context_id: XBRL context reference
            value: Original value (possibly unsigned)

        Returns:
            Tuple of (corrected_value, was_corrected)
        """
        multiplier = self.get_sign_correction(concept, context_id)
        if multiplier == -1:
            return -abs(value), True
        return value, False

    def get_weight_adjusted_value(
        self,
        value: float,
        weight: float,
        apply_sign_correction: bool = True,
        concept: str = None,
        context_id: str = None
    ) -> float:
        """
        Get value adjusted for calculation weight and optional sign correction.

        This is the main method for use during verification.

        Args:
            value: Original fact value
            weight: Calculation weight from linkbase (-1.0 or 1.0)
            apply_sign_correction: Whether to apply XBRL sign correction
            concept: Concept name (required if apply_sign_correction=True)
            context_id: Context ID (required if apply_sign_correction=True)

        Returns:
            Adjusted value ready for calculation
        """
        adjusted = value

        # First apply XBRL sign correction if requested
        if apply_sign_correction and concept and context_id:
            adjusted, _ = self.apply_sign_correction(concept, context_id, adjusted)

        # Then apply calculation weight
        return adjusted * weight

    def analyze_calculation_mismatch(
        self,
        parent_concept: str,
        parent_context: str,
        parent_value: float,
        children: list[dict],
        expected_sum: float
    ) -> dict:
        """
        Analyze a calculation mismatch and suggest corrections.

        This diagnostic method examines why a calculation might not match
        and suggests whether sign correction would help.

        Args:
            parent_concept: Parent concept name
            parent_context: Parent context ID
            parent_value: Actual parent value from filing
            children: List of child dicts with 'concept', 'value', 'weight', 'context'
            expected_sum: Sum of children * weights

        Returns:
            Analysis dict with diagnosis and suggestions
        """
        analysis = {
            'parent_concept': parent_concept,
            'parent_context': parent_context,
            'parent_value': parent_value,
            'expected_sum': expected_sum,
            'difference': parent_value - expected_sum,
            'diagnosis': [],
            'suggestions': [],
            'sign_corrections_applied': [],
            'corrected_sum': None,
        }

        # Check if parent has sign correction
        parent_correction = self.get_sign_correction(parent_concept, parent_context)
        if parent_correction == -1:
            analysis['suggestions'].append(
                f"Parent '{parent_concept}' has sign='-' in XBRL. "
                f"Corrected value would be {-abs(parent_value):,.0f}"
            )
            # Check if correction fixes the issue
            corrected_parent = -abs(parent_value)
            if abs(corrected_parent - expected_sum) < abs(parent_value - expected_sum):
                analysis['diagnosis'].append(
                    "Sign correction on parent would improve/fix the mismatch"
                )
                analysis['corrected_sum'] = expected_sum

        # Check for sign pattern issues
        diff = parent_value - expected_sum
        if abs(diff) > 0 and abs(abs(parent_value) - abs(expected_sum)) < 0.01 * abs(parent_value):
            analysis['diagnosis'].append(
                f"Values match in magnitude ({abs(parent_value):,.0f} vs {abs(expected_sum):,.0f}) "
                f"but signs differ - likely sign correction needed"
            )

        # Check if doubling suggests sign issue
        if abs(diff) > 0 and abs(diff - 2 * abs(expected_sum)) < 0.01 * abs(parent_value):
            analysis['diagnosis'].append(
                f"Difference is approximately 2x the expected sum - "
                f"suggests parent sign is opposite of expected"
            )

        return analysis

    def get_concepts_with_sign_corrections(self, context_filter: str = None) -> list[str]:
        """
        Get list of concepts that have sign corrections.

        Args:
            context_filter: Optional context ID to filter by

        Returns:
            List of concept names with sign corrections
        """
        if context_filter:
            return [
                info.concept for (_, ctx), info in self.sign_corrections.items()
                if ctx == context_filter and info.sign_multiplier == -1
            ]
        return [
            info.concept for info in self.sign_corrections.values()
            if info.sign_multiplier == -1
        ]

    def get_summary(self) -> dict:
        """Get summary of parsed sign information."""
        negative_corrections = sum(
            1 for info in self.sign_corrections.values()
            if info.sign_multiplier == -1
        )
        return {
            'files_parsed': len(self.parsed_files),
            'total_corrections': len(self.sign_corrections),
            'negative_corrections': negative_corrections,
            'positive_corrections': len(self.sign_corrections) - negative_corrections,
        }

    def clear(self):
        """Clear all parsed data."""
        self.sign_corrections.clear()
        self.parsed_files.clear()
        self.diagnostics.clear()
        self._concept_cache.clear()


def infer_sign_from_concept_name(concept: str) -> Optional[int]:
    """
    Infer expected sign from concept name semantics.

    This is a fallback when no explicit sign information is available.
    Uses common XBRL naming conventions to guess the sign.

    Args:
        concept: Concept name (with or without namespace)

    Returns:
        1 for expected positive, -1 for expected negative, None if unknown
    """
    # Extract local name
    local_name = concept.split(':')[-1] if ':' in concept else concept
    local_name = local_name.split('_')[-1] if '_' in local_name else local_name

    # Check patterns for negative values
    negative_patterns = [
        r'^Payments?',
        r'^Repayments?',
        r'Expense$',
        r'Cost$',
        r'Loss$',
        r'^Decrease',
        r'Outflow',
        r'^Use[ds]?',
    ]

    for pattern in negative_patterns:
        if re.search(pattern, local_name, re.IGNORECASE):
            return -1

    # Check patterns for positive values
    positive_patterns = [
        r'^Proceeds?',
        r'^Revenue',
        r'^Income',
        r'^Gain',
        r'^Increase',
        r'Inflow',
        r'^Provide[ds]?',
    ]

    for pattern in positive_patterns:
        if re.search(pattern, local_name, re.IGNORECASE):
            return 1

    return None


def create_sign_weight_handler_from_filing(
    instance_file: str | Path,
    calculation_linkbase: str | Path = None
) -> SignWeightHandler:
    """
    Factory function to create a SignWeightHandler from XBRL files.

    Args:
        instance_file: Path to XBRL instance document
        calculation_linkbase: Optional path to calculation linkbase

    Returns:
        Configured SignWeightHandler
    """
    handler = SignWeightHandler()
    handler.parse_instance_document(instance_file)
    return handler
