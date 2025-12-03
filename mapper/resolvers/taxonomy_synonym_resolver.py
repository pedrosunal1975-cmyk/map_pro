"""
File: engines/mapper/resolvers/taxonomy_synonym_resolver.py
Path: engines/mapper/resolvers/taxonomy_synonym_resolver.py

Taxonomy Synonym Resolver
==========================

Resolves concept synonyms and variations using taxonomy relationships.
Maps specific concept variations to their canonical forms using:
    1. Calculation linkbase relationships (parent-child)
    2. Presentation linkbase relationships (display hierarchies)
    3. Pattern-based matching for common variations
    4. Substring matching for compound concepts

Examples:
    StockIssuedDuringPeriodValueShareBasedCompensation -> ShareBasedCompensation
    RestrictedCashAndCashEquivalents -> RestrictedCash
    AccountsReceivableNetCurrent -> AccountsReceivableNet

This resolver is integrated into the ConceptMatcher as Strategy #3.
"""

from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import re

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class TaxonomySynonymResolver:
    """
    Resolves concept names to canonical forms using taxonomy relationships.
    
    This resolver builds synonym mappings from taxonomy concepts and provides
    fast lookup for concept variations. It handles:
    - Exact synonym mappings
    - Parent-child relationships
    - Pattern-based matching
    - Substring matching for compound concepts
    """
    
    def __init__(self):
        """Initialize taxonomy synonym resolver."""
        self.logger = logger
        
        # Core mapping structures
        self.synonym_map: Dict[str, str] = {}           # variation -> canonical
        self.parent_map: Dict[str, str] = {}            # child -> parent
        self.concept_registry: Set[str] = set()         # all known concepts
        self.canonical_concepts: Set[str] = set()       # canonical forms
        
        # Pattern-based mappings (built from taxonomy)
        self.keyword_map: Dict[str, List[str]] = {}     # keyword -> concepts
        self.prefix_map: Dict[str, List[str]] = {}      # prefix -> concepts
        self.suffix_map: Dict[str, List[str]] = {}      # suffix -> concepts
        
        # Statistics
        self.stats = {
            'synonyms_built': 0,
            'parent_relationships': 0,
            'pattern_mappings': 0,
            'concepts_indexed': 0
        }
        
        self.logger.info("Taxonomy synonym resolver initialized")
    
    def build_synonym_map(self, taxonomy_concepts: List[Dict]) -> None:
        """
        Build synonym mapping from taxonomy concepts.
        
        This method analyzes all taxonomy concepts to build synonym mappings,
        parent-child relationships, and pattern-based indexes.
        
        Args:
            taxonomy_concepts: List of concept dictionaries from taxonomy
        """
        self._reset_mappings()
        
        # Phase 1: Register all canonical concepts
        self._register_canonical_concepts(taxonomy_concepts)
        
        # Phase 2: Build pattern-based indexes
        self._build_pattern_indexes(taxonomy_concepts)
        
        # Phase 3: Build direct synonym mappings
        self._build_direct_synonyms(taxonomy_concepts)
        
        # Phase 4: Build parent-child relationships
        self._build_parent_relationships(taxonomy_concepts)
        
        # Log statistics
        self._log_build_statistics()
    
    def resolve_to_canonical(self, concept_name: str) -> Optional[str]:
        """
        Resolve concept name to its canonical form.
        
        Tries multiple resolution strategies in order:
        1. Direct synonym lookup
        2. Parent concept lookup
        3. Pattern-based matching
        4. Substring matching
        
        Args:
            concept_name: Original concept name to resolve
            
        Returns:
            Canonical concept name if found, None otherwise
        """
        if not concept_name:
            return None
        
        # Normalize for lookup
        concept_lower = concept_name.lower().strip()
        
        # Extract local name (remove namespace prefix if present)
        local_name = self._extract_local_name(concept_lower)
        
        # Strategy 1: Direct synonym lookup
        if local_name in self.synonym_map:
            return self.synonym_map[local_name]
        
        # Strategy 2: Check if already canonical
        if local_name in self.canonical_concepts:
            return local_name
        
        # Strategy 3: Parent concept lookup
        if local_name in self.parent_map:
            return self.parent_map[local_name]
        
        # Strategy 4: Pattern-based matching
        canonical = self._pattern_based_resolution(local_name)
        if canonical:
            return canonical
        
        # Strategy 5: Substring matching
        canonical = self._substring_matching(local_name)
        if canonical:
            return canonical
        
        return None
    
    def _reset_mappings(self) -> None:
        """Clear all mapping structures for rebuild."""
        self.synonym_map.clear()
        self.parent_map.clear()
        self.concept_registry.clear()
        self.canonical_concepts.clear()
        self.keyword_map.clear()
        self.prefix_map.clear()
        self.suffix_map.clear()
        
        for key in self.stats:
            self.stats[key] = 0
    
    def _register_canonical_concepts(self, concepts: List[Dict]) -> None:
        """
        Register all canonical concepts from taxonomy.
        
        Args:
            concepts: Taxonomy concepts
        """
        for concept in concepts:
            concept_name = self._get_concept_name(concept)
            if not concept_name:
                continue
            
            local_name = self._extract_local_name(concept_name.lower())
            self.canonical_concepts.add(local_name)
            self.concept_registry.add(local_name)
            self.stats['concepts_indexed'] += 1
    
    def _build_pattern_indexes(self, concepts: List[Dict]) -> None:
        """
        Build pattern-based indexes for fuzzy matching.
        
        Indexes concepts by:
        - Keywords (extracted words)
        - Prefixes (first N characters)
        - Suffixes (last N characters)
        
        Args:
            concepts: Taxonomy concepts
        """
        for concept in concepts:
            concept_name = self._get_concept_name(concept)
            if not concept_name:
                continue
            
            local_name = self._extract_local_name(concept_name.lower())
            
            # Index by keywords
            keywords = self._extract_keywords(local_name)
            for keyword in keywords:
                if keyword not in self.keyword_map:
                    self.keyword_map[keyword] = []
                self.keyword_map[keyword].append(local_name)
            
            # Index by prefix (first 10 chars)
            if len(local_name) >= 10:
                prefix = local_name[:10]
                if prefix not in self.prefix_map:
                    self.prefix_map[prefix] = []
                self.prefix_map[prefix].append(local_name)
            
            # Index by suffix (last 10 chars)
            if len(local_name) >= 10:
                suffix = local_name[-10:]
                if suffix not in self.suffix_map:
                    self.suffix_map[suffix] = []
                self.suffix_map[suffix].append(local_name)
            
            self.stats['pattern_mappings'] += 1
    
    def _build_direct_synonyms(self, concepts: List[Dict]) -> None:
        """
        Build direct synonym mappings based on concept analysis.
        
        This creates mappings for known patterns like:
        - Compound concepts (e.g., XxxYyyZzz -> Yyy if Yyy exists)
        - Temporal variations (e.g., XxxCurrent -> Xxx)
        - Scope variations (e.g., XxxNet -> Xxx)
        
        Args:
            concepts: Taxonomy concepts
        """
        # Build base concept set for reference
        base_concepts = {self._extract_local_name(self._get_concept_name(c).lower()) 
                        for c in concepts if self._get_concept_name(c)}
        
        for concept in concepts:
            concept_name = self._get_concept_name(concept)
            if not concept_name:
                continue
            
            local_name = self._extract_local_name(concept_name.lower())
            
            # Try to find canonical form by removing common suffixes/prefixes
            canonical = self._find_canonical_form(local_name, base_concepts)
            if canonical and canonical != local_name:
                self.synonym_map[local_name] = canonical
                self.stats['synonyms_built'] += 1
    
    def _build_parent_relationships(self, concepts: List[Dict]) -> None:
        """
        Build parent-child concept relationships.
        
        This would ideally parse calculation/presentation linkbases,
        but for now uses heuristic matching based on concept names.
        
        Args:
            concepts: Taxonomy concepts
        """
        # Build concept list for parent detection
        concept_names = [
            self._extract_local_name(self._get_concept_name(c).lower())
            for c in concepts if self._get_concept_name(c)
        ]
        
        for concept_name in concept_names:
            # Find potential parent by removing compound parts
            parent = self._detect_parent_concept(concept_name, concept_names)
            if parent and parent != concept_name:
                self.parent_map[concept_name] = parent
                self.stats['parent_relationships'] += 1
    
    def _pattern_based_resolution(self, concept_name: str) -> Optional[str]:
        """
        Resolve using pattern-based matching.
        
        Handles common concept variations:
        - ShareBased/StockBased -> ShareBasedCompensation
        - Restricted*Cash -> RestrictedCash
        - Accounts*Receivable -> AccountsReceivable
        
        Args:
            concept_name: Concept to resolve
            
        Returns:
            Canonical concept if pattern matches
        """
        # Common financial concept patterns
        patterns = [
            # Share-based compensation variations
            (r'(stock|share).*compensation', 'sharebasedcompensation'),
            (r'stock.*issued.*compensation', 'sharebasedcompensation'),
            
            # Cash variations
            (r'restricted.*cash', 'restrictedcash'),
            (r'cash.*restricted', 'restrictedcash'),
            (r'cash.*equivalent', 'cashandcashequivalents'),
            
            # Receivables variations
            (r'accounts.*receivable', 'accountsreceivable'),
            (r'receivable.*trade', 'accountsreceivable'),
            (r'trade.*receivable', 'accountsreceivable'),
            
            # Payables variations
            (r'accounts.*payable', 'accountspayable'),
            (r'payable.*trade', 'accountspayable'),
            (r'trade.*payable', 'accountspayable'),
            
            # Revenue variations
            (r'revenue.*operations', 'revenue'),
            (r'sales.*revenue', 'revenue'),
            (r'revenue.*sales', 'revenue'),
            
            # Asset variations
            (r'total.*assets', 'assets'),
            (r'asset.*total', 'assets'),
            
            # Liability variations
            (r'total.*liabilities', 'liabilities'),
            (r'liability.*total', 'liabilities'),
            
            # Equity variations
            (r'stockholder.*equity', 'stockholdersequity'),
            (r'shareholder.*equity', 'stockholdersequity'),
            (r'equity.*stockholder', 'stockholdersequity'),
            
            # Inventory variations
            (r'inventory.*net', 'inventory'),
            (r'inventory.*gross', 'inventory'),
            
            # Property/Equipment variations
            (r'property.*plant.*equipment', 'propertyplantandequipment'),
            (r'ppe', 'propertyplantandequipment'),
            
            # Goodwill variations
            (r'goodwill.*net', 'goodwill'),
            (r'goodwill.*intangible', 'goodwill'),
            
            # Debt variations
            (r'debt.*long.*term', 'longtermdebt'),
            (r'long.*term.*debt', 'longtermdebt'),
            (r'debt.*short.*term', 'shorttermdebt'),
            (r'short.*term.*debt', 'shorttermdebt'),
        ]
        
        concept_clean = re.sub(r'[^a-z]', '', concept_name)
        
        for pattern, canonical in patterns:
            if re.search(pattern, concept_clean):
                # Verify canonical exists in our registry
                if canonical in self.canonical_concepts:
                    return canonical
        
        return None
    
    def _substring_matching(self, concept_name: str) -> Optional[str]:
        """
        Match by finding canonical concepts that are substrings.
        
        This handles cases like:
        - StockIssuedDuringPeriodValueShareBasedCompensation contains "sharebasedcompensation"
        - AccountsReceivableNetCurrent contains "accountsreceivable"
        
        Args:
            concept_name: Concept to resolve
            
        Returns:
            Canonical concept if found as substring
        """
        # Remove common affixes for cleaner matching
        cleaned = self._remove_common_affixes(concept_name)
        
        # Find the longest canonical concept that's a substring
        best_match = None
        best_length = 0
        
        for canonical in self.canonical_concepts:
            # Skip very short concepts (too many false positives)
            if len(canonical) < 8:
                continue
            
            # Check if canonical is substring of the concept
            if canonical in cleaned and len(canonical) > best_length:
                best_match = canonical
                best_length = len(canonical)
        
        return best_match
    
    def _find_canonical_form(
        self, 
        concept_name: str, 
        base_concepts: Set[str]
    ) -> Optional[str]:
        """
        Find canonical form by removing common suffixes/prefixes.
        
        Args:
            concept_name: Concept to analyze
            base_concepts: Set of known base concepts
            
        Returns:
            Canonical form if found
        """
        # Common temporal suffixes
        temporal_suffixes = [
            'current', 'noncurrent', 'longterm', 'shortterm',
            'period', 'annual', 'quarterly', 'monthly'
        ]
        
        # Common scope suffixes
        scope_suffixes = [
            'net', 'gross', 'total', 'subtotal', 'consolidated',
            'individual', 'aggregate', 'combined'
        ]
        
        # Common descriptive suffixes
        descriptive_suffixes = [
            'amount', 'value', 'balance', 'outstanding', 'remaining',
            'issued', 'authorized', 'available', 'reserved'
        ]
        
        all_suffixes = temporal_suffixes + scope_suffixes + descriptive_suffixes
        
        # Try removing each suffix
        for suffix in all_suffixes:
            if concept_name.endswith(suffix):
                base = concept_name[:-len(suffix)]
                if base in base_concepts:
                    return base
        
        # Try removing common prefixes
        prefixes = ['total', 'gross', 'net', 'other', 'prepaid', 'accrued']
        for prefix in prefixes:
            if concept_name.startswith(prefix):
                base = concept_name[len(prefix):]
                if base in base_concepts:
                    return base
        
        return None
    
    def _detect_parent_concept(
        self, 
        concept_name: str, 
        all_concepts: List[str]
    ) -> Optional[str]:
        """
        Detect parent concept using heuristic matching.
        
        Args:
            concept_name: Child concept
            all_concepts: All available concepts
            
        Returns:
            Parent concept if detected
        """
        # Extract keywords from concept
        keywords = self._extract_keywords(concept_name)
        
        if len(keywords) < 2:
            return None
        
        # Try to find parent by matching fewer keywords
        # Example: "AccountsReceivableNetCurrent" -> "AccountsReceivable"
        for i in range(len(keywords) - 1, 0, -1):
            potential_parent = ''.join(keywords[:i])
            if potential_parent in all_concepts and potential_parent != concept_name:
                return potential_parent
        
        return None
    
    def _remove_common_affixes(self, concept_name: str) -> str:
        """
        Remove common prefixes and suffixes for cleaner matching.
        
        Args:
            concept_name: Concept to clean
            
        Returns:
            Cleaned concept name
        """
        # Remove "during", "period", "value", "amount", etc.
        words_to_remove = [
            'during', 'period', 'value', 'amount', 'total', 
            'gross', 'net', 'issued', 'outstanding'
        ]
        
        cleaned = concept_name
        for word in words_to_remove:
            cleaned = cleaned.replace(word, '')
        
        return cleaned
    
    def _extract_keywords(self, concept_name: str) -> List[str]:
        """
        Extract keywords from concept name.
        
        Handles CamelCase and compound words.
        
        Args:
            concept_name: Concept to analyze
            
        Returns:
            List of keywords
        """
        # Insert spaces before capitals
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', concept_name)
        
        # Split and filter
        words = [w.lower() for w in spaced.split() if len(w) > 2]
        
        return words
    
    def _extract_local_name(self, concept: str) -> str:
        """
        Extract local name from qualified name.
        
        Args:
            concept: Concept name (may be QName)
            
        Returns:
            Local name portion
        """
        if ':' in concept:
            return concept.split(':', 1)[1]
        return concept
    
    def _get_concept_name(self, concept: Dict) -> Optional[str]:
        """
        Extract concept name from concept dictionary.
        
        Args:
            concept: Concept dictionary
            
        Returns:
            Concept name if found
        """
        return (
            concept.get('concept_qname') or
            concept.get('concept') or
            concept.get('name')
        )
    
    def _log_build_statistics(self) -> None:
        """Log statistics about built synonym mappings."""
        self.logger.info(
            f"Synonym map built: {self.stats['concepts_indexed']} concepts indexed, "
            f"{self.stats['synonyms_built']} synonyms, "
            f"{self.stats['parent_relationships']} parent relationships, "
            f"{self.stats['pattern_mappings']} pattern mappings"
        )
    
    def get_statistics(self) -> Dict:
        """Get resolver statistics."""
        return self.stats.copy()


__all__ = ['TaxonomySynonymResolver']