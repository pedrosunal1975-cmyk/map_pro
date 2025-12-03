"""
File: engines/mapper/resolvers/fact_filter.py
Path: engines/mapper/resolvers/fact_filter.py

Fact Filter
===========

Filters facts to determine which should be mapped to taxonomy concepts.

ULTRA-FLOODGATE UPDATE (2025-11-20):
- Removed ALL namespace filtering (no namespaces excluded)
- Only excludes pointer references (ExtensibleList/Enumeration)
- Everything else gets mapped with proper taxonomy labels

Excludes ONLY:
    - Extensible list/enumeration references (these are pointers/URLs, not data)
"""

from typing import Dict, Any

from engines.mapper.resolvers.constants import (
    NON_MAPPABLE_NAMESPACES,
    NON_MAPPABLE_PATTERNS
)


class FactFilter:
    """
    Determines if facts should be mapped to taxonomy concepts.
    
    ULTRA-FLOODGATE: Maps everything except pointer references.
    No namespace filtering - all namespaces are mapped.
    """
    
    def is_mappable_fact(self, fact: Dict[str, Any]) -> bool:
        """
        Determine if a fact should be mapped to taxonomy.
        
        Applies minimal filtering - only excludes pointer references.
        
        ULTRA-FLOODGATE: ALL namespaces (dei, srt, country, currency, etc.) are MAPPABLE.
        
        Args:
            fact: Fact dictionary to evaluate
            
        Returns:
            True if fact should be mapped, False only if it's a pointer reference
        """
        concept = fact.get('concept_qname') or fact.get('concept_local_name', '')
        
        # No namespace exclusions - all namespaces are mapped
        # Only check for pointer references (ExtensibleList/Enumeration)
        if self._is_pointer_reference(concept):
            return False
        
        # Everything else is mappable
        return True
    
    def _is_pointer_reference(self, concept: str) -> bool:
        """
        Check if concept is a pointer reference (ExtensibleList/Enumeration).
        
        These are URLs/references to other concepts, not actual data values.
        
        Args:
            concept: Concept name to check
            
        Returns:
            True if concept is a pointer reference
        """
        concept_lower = concept.lower()
        return any(pattern.lower() in concept_lower for pattern in NON_MAPPABLE_PATTERNS)
    
    # Legacy methods kept for backward compatibility
    
    def _is_non_mappable_namespace(self, concept: str) -> bool:
        """
        DEPRECATED: No longer filters namespaces.
        
        Kept for backward compatibility. Always returns False.
        
        Args:
            concept: Concept name to check
            
        Returns:
            False (no namespaces are filtered)
        """
        # ULTRA-FLOODGATE: No namespace filtering
        return False
    
    def _matches_non_mappable_pattern(self, concept: str) -> bool:
        """
        Check if concept matches non-mappable patterns.
        
        Only pointer references (ExtensibleList/Enumeration) are excluded.
        
        Args:
            concept: Concept name to check
            
        Returns:
            True if matches a pointer reference pattern
        """
        return self._is_pointer_reference(concept)
    
    def _is_extensible_reference(self, concept: str) -> bool:
        """
        Check if concept is an extensible list/enumeration reference.
        
        These are pointers to data, not the data itself.
        
        NOTE: This method is deprecated - use _matches_non_mappable_pattern instead.
        Kept for backward compatibility.
        
        Args:
            concept: Concept name to check
            
        Returns:
            True if concept is an extensible reference
        """
        return self._matches_non_mappable_pattern(concept)


__all__ = ['FactFilter']