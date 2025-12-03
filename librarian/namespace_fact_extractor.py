"""
Fact-level Namespace Extraction.

Handles extraction from individual XBRL facts using multiple strategies.

Location: engines/librarian/namespace_fact_extractor.py
"""

from typing import Dict, Any, Set, Optional, List

from .namespace_matching import NamespaceNormalizer


class FactNamespaceExtractor:
    """
    Extracts namespaces from individual XBRL facts.
    
    Handles multiple fact formats and extraction strategies.
    """
    
    def __init__(self, logger):
        """
        Initialize fact namespace extractor.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        
        # Common namespace patterns for quick lookup
        # NOTE: This is reference data for namespace identification across ALL markets.
        # Contains patterns for SEC (US), FCA (UK), IFRS (international), and other markets.
        # This is NOT market-specific code - it's a comprehensive lookup table.
        self.common_namespace_patterns = {
            # US market namespaces (SEC)
            'us-gaap': 'http://fasb.org/us-gaap/',
            'dei': 'http://xbrl.sec.gov/dei/',
            'invest': 'http://xbrl.sec.gov/invest/',
            'country': 'http://xbrl.sec.gov/country/',
            'currency': 'http://xbrl.sec.gov/currency/',
            'exch': 'http://xbrl.sec.gov/exch/',
            'naics': 'http://xbrl.sec.gov/naics/',
            'sic': 'http://xbrl.sec.gov/sic/',
            'stpr': 'http://xbrl.sec.gov/stpr/',
            # International/IFRS namespaces
            'ifrs': 'http://xbrl.ifrs.org/taxonomy/',
            'esef': 'http://xbrl.ifrs.org/taxonomy/',
            # UK market namespaces (FCA)
            'uk-gaap': 'http://xbrl.frc.org.uk/cd/',
            'frs': 'http://xbrl.frc.org.uk/frs/',
            'dpl': 'http://xbrl.frc.org.uk/dpl/',
            'core': 'http://xbrl.frc.org.uk/cd/'
        }
    
    def extract_from_concept_name(self, concept_name: str) -> Optional[str]:
        """
        Extract namespace prefix from concept qualified name.
        
        Args:
            concept_name: Qualified concept name (e.g., 'us-gaap:Assets')
            
        Returns:
            Normalized namespace prefix or None
        """
        if not concept_name or ':' not in concept_name:
            return None
        
        namespace_prefix = concept_name.split(':')[0]
        if namespace_prefix:
            return NamespaceNormalizer.normalize(namespace_prefix)
        
        return None
    
    def extract_from_fact(self, fact: Dict[str, Any]) -> Set[str]:
        """
        Extract all namespaces from a single fact dictionary.
        
        Uses multiple strategies in order of reliability.
        
        Args:
            fact: Fact dictionary from parsed data
            
        Returns:
            Set of normalized namespaces found in fact
        """
        # Try strategies in order of reliability
        strategies = [
            self._extract_from_concept_namespace,
            self._extract_from_concept_qname,
            self._extract_from_local_name,
            self._extract_from_legacy_format,
            self._extract_from_explicit_namespace,
            self._extract_from_dimensions
        ]
        
        for strategy in strategies:
            namespaces = strategy(fact)
            if namespaces:
                return namespaces
        
        return set()
    
    def _extract_from_concept_namespace(self, fact: Dict[str, Any]) -> Set[str]:
        """Strategy 1: Extract from concept_namespace field (full URL)."""
        concept_namespace = fact.get('concept_namespace')
        if not concept_namespace:
            return set()
        
        namespace = NamespaceNormalizer.normalize(concept_namespace)
        if namespace:
            return {namespace}
        
        return set()
    
    def _extract_from_concept_qname(self, fact: Dict[str, Any]) -> Set[str]:
        """Strategy 2: Extract from concept_qname field (prefix:name)."""
        concept_qname = fact.get('concept_qname')
        if not concept_qname or ':' not in concept_qname:
            return set()
        
        prefix = concept_qname.split(':')[0]
        
        # Try common patterns first
        if prefix in self.common_namespace_patterns:
            namespace = NamespaceNormalizer.normalize(
                self.common_namespace_patterns[prefix]
            )
            if namespace:
                return {namespace}
        
        # Use prefix as-is
        namespace = self.extract_from_concept_name(concept_qname)
        if namespace:
            return {namespace}
        
        return set()
    
    def _extract_from_local_name(self, fact: Dict[str, Any]) -> Set[str]:
        """Strategy 3: Extract from concept_local_name + explicit namespace."""
        concept_local_name = fact.get('concept_local_name')
        if not concept_local_name:
            return set()
        
        # Check for explicit namespace field
        explicit_namespace = (fact.get('namespace') or 
                             fact.get('concept_namespace_uri'))
        if explicit_namespace:
            namespace = NamespaceNormalizer.normalize(explicit_namespace)
            if namespace:
                return {namespace}
        
        # Try to infer from local name prefix pattern
        if '_' in concept_local_name:
            prefix_candidate = concept_local_name.split('_')[0]
            if prefix_candidate in self.common_namespace_patterns:
                namespace = NamespaceNormalizer.normalize(
                    self.common_namespace_patterns[prefix_candidate]
                )
                if namespace:
                    return {namespace}
        
        return set()
    
    def _extract_from_legacy_format(self, fact: Dict[str, Any]) -> Set[str]:
        """Strategy 4: Extract from legacy concept.name format."""
        concept = fact.get('concept', {})
        concept_name = concept.get('name', '') or fact.get('concept_name', '')
        
        if not concept_name:
            return set()
        
        namespace = self.extract_from_concept_name(concept_name)
        if namespace:
            return {namespace}
        
        return set()
    
    def _extract_from_explicit_namespace(self, fact: Dict[str, Any]) -> Set[str]:
        """Strategy 5: Extract from explicit namespace fields."""
        concept = fact.get('concept', {})
        namespace_field = fact.get('namespace') or concept.get('namespace')
        
        if not namespace_field:
            return set()
        
        namespace = NamespaceNormalizer.normalize(namespace_field)
        if namespace:
            return {namespace}
        
        return set()
    
    def _extract_from_dimensions(self, fact: Dict[str, Any]) -> Set[str]:
        """Strategy 6: Extract from dimension information."""
        namespaces = set()
        dimensions = fact.get('dimensions', [])
        
        for dim in dimensions:
            if not isinstance(dim, dict):
                continue
            
            dim_namespace = dim.get('namespace') or dim.get('dimension_namespace')
            if dim_namespace:
                namespace = NamespaceNormalizer.normalize(dim_namespace)
                if namespace:
                    namespaces.add(namespace)
        
        return namespaces
    
    def extract_namespace_prefixes_from_facts(
        self, 
        facts: List[Dict[str, Any]]
    ) -> Set[str]:
        """
        Extract unique namespace prefixes from a list of facts.
        
        Args:
            facts: List of fact dictionaries
            
        Returns:
            Set of unique namespace prefixes
        """
        prefixes = set()
        
        for fact in facts:
            prefixes.update(self._extract_prefixes_from_qname(fact))
            prefixes.update(self._extract_prefixes_from_legacy(fact))
        
        return prefixes
    
    def _extract_prefixes_from_qname(self, fact: Dict[str, Any]) -> Set[str]:
        """Extract prefixes from concept_qname."""
        qname = fact.get('concept_qname', '')
        if ':' in qname:
            prefix = qname.split(':')[0]
            return {prefix}
        return set()
    
    def _extract_prefixes_from_legacy(self, fact: Dict[str, Any]) -> Set[str]:
        """Extract prefixes from legacy concept name."""
        concept = fact.get('concept', {})
        concept_name = concept.get('name', '') or fact.get('concept_name', '')
        if ':' in concept_name:
            prefix = concept_name.split(':')[0]
            return {prefix}
        return set()
    
    def map_prefixes_to_namespaces(
        self, 
        prefixes: Set[str]
    ) -> Dict[str, str]:
        """
        Map namespace prefixes to full namespace URLs.
        
        Args:
            prefixes: Set of namespace prefixes
            
        Returns:
            Dictionary mapping prefix to full namespace URL
        """
        mappings = {}
        
        for prefix in prefixes:
            if prefix in self.common_namespace_patterns:
                mappings[prefix] = self.common_namespace_patterns[prefix]
            else:
                self.logger.debug(
                    f"Unknown namespace prefix: {prefix} "
                    f"(may need to add to common patterns)"
                )
        
        return mappings


__all__ = ['FactNamespaceExtractor']