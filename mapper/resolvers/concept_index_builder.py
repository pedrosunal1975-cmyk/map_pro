"""
File: engines/mapper/resolvers/concept_index_builder.py
Path: engines/mapper/resolvers/concept_index_builder.py

Concept Index Builder
=====================

Builds and manages lookup indexes for fast concept matching.
Provides three index types:
    1. Case-insensitive exact match (by full QName)
    2. Base name match (by local name without prefix)
    3. Namespace prefix registry
"""

from typing import Dict, Any, List, Set, Optional

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class ConceptIndexBuilder:
    """
    Builds and manages lookup indexes for taxonomy concepts.
    
    Maintains three primary indexes:
    - case_insensitive_lookup: Full QName -> concept(s)
    - base_name_lookup: Local name -> concept(s)
    - namespace_prefixes: Set of all namespace prefixes seen
    """
    
    def __init__(self):
        """Initialize empty indexes."""
        self.case_insensitive_lookup: Dict[str, List[Dict[str, Any]]] = {}
        self.base_name_lookup: Dict[str, List[Dict[str, Any]]] = {}
        self.namespace_prefixes: Set[str] = set()
    
    def build_lookups(self, concepts: List[Dict[str, Any]]) -> None:
        """
        Build all lookup indexes from taxonomy concepts.
        
        Clears existing indexes and rebuilds from scratch. This method
        should be called once before resolving a batch of facts.
        
        Args:
            concepts: List of concept dictionaries from taxonomy
        """
        self._clear_indexes()
        
        for concept in concepts:
            qname = self._get_concept_qname(concept)
            if not qname:
                continue
            
            self._index_concept(qname, concept)
        
        self._log_index_statistics()
    
    def _clear_indexes(self) -> None:
        """Clear all lookup indexes."""
        self.case_insensitive_lookup.clear()
        self.base_name_lookup.clear()
        self.namespace_prefixes.clear()
    
    def _index_concept(self, qname: str, concept: Dict[str, Any]) -> None:
        """
        Index a single concept in all lookup structures.
        
        Args:
            qname: Qualified name of concept
            concept: Concept dictionary
        """
        qname_lower = str(qname).lower().strip()
        
        # Index by full QName (case-insensitive)
        if qname_lower not in self.case_insensitive_lookup:
            self.case_insensitive_lookup[qname_lower] = []
        self.case_insensitive_lookup[qname_lower].append(concept)
        
        # Extract and index by local name
        local_name = self._extract_local_name(qname_lower)
        if local_name not in self.base_name_lookup:
            self.base_name_lookup[local_name] = []
        self.base_name_lookup[local_name].append(concept)
        
        # Register namespace prefix
        prefix = self._extract_prefix(qname_lower)
        if prefix:
            self.namespace_prefixes.add(prefix)
    
    def _extract_local_name(self, qname: str) -> str:
        """
        Extract local name from qualified name.
        
        Args:
            qname: Qualified name (possibly with prefix)
            
        Returns:
            Local name portion
        """
        if ':' in qname:
            return qname.split(':', 1)[1]
        return qname
    
    def _extract_prefix(self, qname: str) -> Optional[str]:
        """
        Extract namespace prefix from qualified name.
        
        Args:
            qname: Qualified name (possibly with prefix)
            
        Returns:
            Namespace prefix if present, None otherwise
        """
        if ':' in qname:
            return qname.split(':', 1)[0]
        return None
    
    def _get_concept_qname(self, concept: Dict[str, Any]) -> Optional[str]:
        """
        Extract qname from concept dictionary.
        
        Tries multiple common key names for flexibility.
        
        Args:
            concept: Concept dictionary
            
        Returns:
            Qualified name if found, None otherwise
        """
        return (
            concept.get('concept_qname') or
            concept.get('concept') or
            concept.get('name')
        )
    
    def _log_index_statistics(self) -> None:
        """Log statistics about built indexes."""
        logger.info(
            f"Built lookups: {len(self.case_insensitive_lookup)} exact, "
            f"{len(self.base_name_lookup)} base names"
        )


__all__ = ['ConceptIndexBuilder']