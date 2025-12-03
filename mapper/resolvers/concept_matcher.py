"""
File: engines/mapper/resolvers/concept_matcher.py
Path: engines/mapper/resolvers/concept_matcher.py

Concept Matcher - 8-Strategy Resolution Chain
==============================================

Implements the 8-strategy concept matching algorithm that progressively
attempts to match fact concepts to taxonomy concepts with decreasing
confidence levels.

Strategy Chain:
    1. Exact Match (1.0 confidence)
    2. Prefix Detection (0.9 confidence)
    3. Technology Transformation (0.95 confidence)
    4. Financial Concept Mapping (0.8 confidence)
    5. Company Extension Match (0.85 confidence)
    6. Base Name Match (0.75 confidence)
    7. Word Decomposition (0.7 confidence)
    8. Semantic Similarity (0.65-0.7 confidence)
"""
from typing import Dict, Any, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from engines.mapper.resolvers.taxonomy_synonym_resolver import TaxonomySynonymResolver

from engines.mapper.resolvers.concept_index_builder import ConceptIndexBuilder
from engines.mapper.resolvers.resolution_statistics import ResolutionStatistics

from engines.mapper.resolvers.text_utils import extract_words
from engines.mapper.resolvers.constants import (
    COMMON_PREFIXES,
    FINANCIAL_MAPPINGS,
    SEMANTIC_SIMILARITY_THRESHOLD,
    SEMANTIC_SIMILARITY_BONUS
)


class ConceptMatcher:
    """
    Implements the 8-strategy concept resolution chain.
    
    Each strategy is attempted in sequence until a match is found.
    Strategies are ordered from highest to lowest confidence.
    """
    
    # ============================================================================
    # MODIFIED __init__ METHOD
    # ============================================================================

    def __init__(
        self, 
        index_builder: ConceptIndexBuilder,
        synonym_resolver: Optional['TaxonomySynonymResolver'] = None
    ):
        """
        Initialize concept matcher.
        
        Args:
            index_builder: Concept index builder for lookup operations
            synonym_resolver: Optional taxonomy synonym resolver for Strategy 3
        """
        self.index_builder = index_builder
        self.synonym_resolver = synonym_resolver


    # ============================================================================
    # MODIFIED resolve_fact METHOD
    # ============================================================================

    def resolve_fact(
        self,
        fact: Dict[str, Any],
        statistics: ResolutionStatistics
    ) -> Optional[Tuple[Dict[str, Any], float, str]]:
        """
        Resolve a single fact using the 8-strategy chain (now 9 strategies).
        
        Args:
            fact: Fact dictionary to resolve
            statistics: Statistics tracker for recording resolution method
            
        Returns:
            Tuple of (concept_dict, confidence, method_name) if matched, None otherwise
        """
        # Extract concept identifier from fact
        fact_concept = fact.get('concept_qname') or fact.get('concept_local_name')
        
        if not fact_concept:
            return None
        
        # Extract local name for strategies 6-8
        fact_local_name = self._extract_local_name(fact_concept)
        
        # Define strategy chain with parameters
        # Format: (strategy_function, primary_input, optional_extra_param)
        strategies = [
            (self._exact_match, fact_concept, None),
            (self._prefix_detection, fact_concept, None),
            (self._taxonomy_synonym_resolution, fact_concept, None),
            (self._technology_transformation, fact_concept, None),
            (self._financial_concept_mapping, fact_concept, None),
            (self._company_extension_match, fact_concept, None),
            (self._base_name_match_strict, fact_local_name, fact_concept),  # Pass original concept!
            (self._word_decomposition, fact_local_name, None),
            (self._semantic_similarity_match, fact_local_name, None)
        ]
        
        # Try each strategy in sequence
        for strategy_func, input_data, extra_param in strategies:
            # Skip prefix detection if prefix already exists
            if strategy_func == self._prefix_detection and ':' in fact_concept:
                continue
            
            # Skip taxonomy synonym if resolver not available
            if strategy_func == self._taxonomy_synonym_resolution and not self.synonym_resolver:
                continue
            
            # Call strategy with or without extra parameter
            if extra_param is not None:
                result = strategy_func(input_data, extra_param)
            else:
                result = strategy_func(input_data)
            
            if result:
                concept, confidence, method_name = result
                # Update statistics for successful match
                statistics.increment_strategy(method_name)
                return (concept, confidence, method_name)
        
        return None
    
    def _extract_local_name(self, concept: str) -> str:
        """
        Extract local name from qualified name.
        
        Args:
            concept: Concept name (may be QName or local name)
            
        Returns:
            Local name portion (after ':' if present)
        """
        if ':' in concept:
            return concept.split(':', 1)[1]
        return concept
    
    def _exact_match(self, fact_concept: str) -> Optional[Tuple]:
        """
        Strategy 1: Exact QName match (case-insensitive).
        
        Args:
            fact_concept: Concept to match
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        key_lower = fact_concept.lower().strip()
        matches = self.index_builder.case_insensitive_lookup.get(key_lower)
        
        if matches:
            return (matches[0], 1.0, 'exact_match_case_insensitive')
        
        return None
    
    def _prefix_detection(self, fact_concept: str) -> Optional[Tuple]:
        """
        Strategy 2: Add missing common prefix.
        
        Attempts to prepend common prefixes (us-gaap, dei, srt) to
        unprefixed concepts.
        
        Args:
            fact_concept: Concept to match
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        if ':' in fact_concept:
            return None
        
        concept_lower = fact_concept.lower()
        
        # Try common prefixes in order of likelihood
        prefixes_to_try = [
            ('us-gaap', 0.9),
            ('dei', 0.85),
            ('srt', 0.85)
        ]
        
        for prefix, confidence in prefixes_to_try:
            prefixed = f"{prefix}:{concept_lower}"
            matches = self.index_builder.case_insensitive_lookup.get(prefixed)
            if matches:
                return (matches[0], confidence, 'prefix_detected')
        
        return None

    # ============================================================================
    # NEW METHOD: _taxonomy_synonym_resolution
    # Place this method after _prefix_detection and before _technology_transformation
    # ============================================================================

    def _taxonomy_synonym_resolution(self, fact_concept: str) -> Optional[Tuple]:
        """
        Strategy 3: Taxonomy-based synonym resolution.
        
        Uses taxonomy relationships to find canonical concept forms.
        Handles variations like:
        - StockIssuedDuringPeriodValueShareBasedCompensation -> ShareBasedCompensation
        - RestrictedCashAndCashEquivalents -> RestrictedCash
        
        This is the highest-priority fuzzy matching strategy, positioned after
        exact match and prefix detection but before other heuristics.
        
        Args:
            fact_concept: Concept to match
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        if not self.synonym_resolver:
            return None
        
        # Resolve to canonical form using taxonomy relationships
        canonical = self.synonym_resolver.resolve_to_canonical(fact_concept)
        
        if not canonical:
            return None
        
        # Look up canonical form in index
        canonical_lower = canonical.lower()
        
        # Try exact match on canonical form
        matches = self.index_builder.case_insensitive_lookup.get(canonical_lower)
        if matches:
            return (matches[0], 0.88, 'taxonomy_synonym')
        
        # Try with common prefixes if not found
        for prefix in ['us-gaap', 'ifrs-full', 'dei', 'srt']:
            prefixed = f"{prefix}:{canonical_lower}"
            matches = self.index_builder.case_insensitive_lookup.get(prefixed)
            if matches:
                return (matches[0], 0.86, 'taxonomy_synonym_prefixed')
        
        return None

    def _technology_transformation(self, fact_concept: str) -> Optional[Tuple]:
        """
        Strategy 3: Handle technology:prefix_ patterns.
        
        Some systems use technology:dei_, technology:us-gaap_, etc.
        
        Args:
            fact_concept: Concept to match
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        if ':' in fact_concept:
            return None
        
        concept_lower = fact_concept.lower()
        tech_patterns = [
            f"technology:dei_{concept_lower}",
            f"technology:us-gaap_{concept_lower}",
            f"technology:srt_{concept_lower}"
        ]
        
        for pattern in tech_patterns:
            matches = self.index_builder.case_insensitive_lookup.get(pattern)
            if matches:
                return (matches[0], 0.95, 'technology_transformed')
        
        return None
    
    def _financial_concept_mapping(self, fact_concept: str) -> Optional[Tuple]:
        """
        Strategy 4: Map business terms to financial concepts.
        
        Uses predefined mappings of business keywords to standard
        accounting concepts.
        
        Args:
            fact_concept: Concept to match
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        concept_lower = fact_concept.lower()
        
        for keyword, base_concepts in FINANCIAL_MAPPINGS.items():
            if keyword in concept_lower:
                for base_concept in base_concepts:
                    full_concept = f"us-gaap:{base_concept.lower()}"
                    matches = self.index_builder.case_insensitive_lookup.get(full_concept)
                    if matches:
                        return (matches[0], 0.8, 'financial_mapped')
        
        return None
    
    def _company_extension_match(self, fact_concept: str) -> Optional[Tuple]:
        """
        Strategy 5: Match company extension concepts.
        
        Attempts to match using company-specific namespace prefixes.
        
        Args:
            fact_concept: Concept to match
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        # Get company-specific prefixes (non-standard)
        # NEW: Normalize prefixes by removing year suffixes before comparison
        company_prefixes = [
            p for p in self.index_builder.namespace_prefixes
            if self._normalize_prefix(p) not in COMMON_PREFIXES and p != 'technology'
        ]
        
        # Extract local name
        fact_local_name = self._extract_local_name(fact_concept).lower()
        
        for prefix in company_prefixes:
            prefixed = f"{prefix}:{fact_local_name}"
            matches = self.index_builder.case_insensitive_lookup.get(prefixed)
            if matches:
                return (matches[0], 0.85, 'company_extension')
        
        return None

    def _normalize_prefix(self, prefix: str) -> str:
        """Normalize only KNOWN standard prefixes, not all prefixes."""
        # Only normalize if prefix base is in COMMON_PREFIXES
        import re
        base = re.sub(r'-\d{4}$', '', prefix)
        if base in COMMON_PREFIXES:
            return base
        return prefix  # Keep company extensions as-is
    
    def _base_name_match_strict(self, fact_local_name: str, fact_concept: str = None) -> Optional[Tuple]:
        """
        Strategy 6: Match on base name only (fuzzy match).
        
        Args:
            fact_local_name: Local name (without prefix) to match
            fact_concept: Original fact concept (with prefix) for validation
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        concept_lower = fact_local_name.lower()
        matches = self.index_builder.base_name_lookup.get(concept_lower)
        
        if not matches:
            return None
        
        # Extract fact's original namespace if provided
        fact_namespace = None
        if fact_concept and ':' in fact_concept:
            fact_prefix = fact_concept.split(':', 1)[0]
            fact_namespace = self._normalize_prefix(fact_prefix)
        
        # Try to find a match with same namespace first
        if fact_namespace:
            for match in matches:
                matched_qname = self._get_matched_concept_qname(match)
                if matched_qname and ':' in matched_qname:
                    matched_prefix = matched_qname.split(':', 1)[0]
                    matched_namespace = self._normalize_prefix(matched_prefix)
                    
                    # Same namespace - perfect match!
                    if fact_namespace == matched_namespace:
                        return (match, 0.75, 'base_name_match')
        
        # No same-namespace match found
        # Only fall back to different namespace if it's company extension
        for match in matches:
            matched_qname = self._get_matched_concept_qname(match)
            if matched_qname and ':' in matched_qname:
                matched_prefix = matched_qname.split(':', 1)[0]
                matched_namespace = self._normalize_prefix(matched_prefix)
                
                # Allow company extensions (non-standard namespaces)
                if matched_namespace not in COMMON_PREFIXES:
                    return (match, 0.75, 'base_name_match')
        
        # No acceptable match found
        return None

    def _get_matched_concept_qname(self, concept: Dict[str, Any]) -> Optional[str]:
        """
        Extract qname from matched concept dictionary.
        
        Args:
            concept: Concept dictionary
            
        Returns:
            Qualified name if found
        """
        return (
            concept.get('concept_qname') or
            concept.get('concept') or
            concept.get('name')
        )
    
    def _word_decomposition(self, fact_local_name: str) -> Optional[Tuple]:
        """
        Strategy 7: Break CamelCase/snake_case and match parts.
        
        Decomposes the concept name into words and attempts to match
        combinations of consecutive words.
        
        Args:
            fact_local_name: Local name to decompose
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        words = extract_words(fact_local_name)
        
        if len(words) < 2:
            return None
        
        # Try finding concepts composed of consecutive word pairs
        for i in range(len(words) - 1):
            word_combo = ''.join(words[i:i+2]).lower()
            matches = self.index_builder.base_name_lookup.get(word_combo)
            if matches:
                return (matches[0], 0.7, 'word_decomposition')
        
        return None
    
    def _semantic_similarity_match(self, fact_local_name: str) -> Optional[Tuple]:
        """
        Strategy 8: Semantic similarity based on word overlap.
        
        Final fallback strategy that computes word overlap between
        the fact concept and taxonomy concepts.
        
        Args:
            fact_local_name: Local name to match
            
        Returns:
            Tuple of (concept, confidence, method) if matched, None otherwise
        """
        fact_words = set(extract_words(fact_local_name))
        
        if not fact_words:
            return None
        
        best_match = None
        best_score = 0.0
        
        # Limit search for performance (top 500 base names)
        search_limit = 500
        for key in list(self.index_builder.base_name_lookup.keys())[:search_limit]:
            key_words = set(extract_words(key))
            
            # Calculate word overlap score
            common_words = fact_words.intersection(key_words)
            if not common_words:
                continue
            
            score = len(common_words) / max(len(fact_words), len(key_words), 1)
            
            if score > best_score and score >= SEMANTIC_SIMILARITY_THRESHOLD:
                best_score = score
                matches = self.index_builder.base_name_lookup[key]
                if matches:
                    best_match = matches[0]
        
        if best_match:
            confidence = 0.65 + (best_score * SEMANTIC_SIMILARITY_BONUS)
            return (best_match, confidence, 'semantic_similarity')
        
        return None


__all__ = ['ConceptMatcher']