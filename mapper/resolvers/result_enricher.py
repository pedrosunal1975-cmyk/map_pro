"""
File: engines/mapper/resolvers/result_enricher.py
Path: engines/mapper/resolvers/result_enricher.py

Result Enricher
===============

Enriches resolved facts with taxonomy information or marks them as unmapped.
Adds metadata fields needed for downstream processing and reporting.
"""

from typing import Dict, Any, Optional

from engines.mapper.resolvers.resolution_statistics import ResolutionStatistics


class ResultEnricher:
    """
    Enriches fact dictionaries with taxonomy information.
    
    Adds fields such as:
    - taxonomy_concept: Matched concept QName
    - taxonomy_label: Human-readable label
    - taxonomy_type: Data type
    - mapping_confidence: Confidence score (0.0-1.0)
    - mapping_method: Strategy that produced the match
    - is_unmapped: Whether fact was successfully mapped
    """
    
    def enrich_fact(
        self,
        fact: Dict[str, Any],
        concept: Dict[str, Any],
        confidence: float,
        method: str
    ) -> Dict[str, Any]:
        """
        Add taxonomy information to a successfully matched fact.
        
        Args:
            fact: Original fact dictionary
            concept: Matched taxonomy concept dictionary
            confidence: Confidence score (0.0-1.0)
            method: Resolution strategy name
            
        Returns:
            Enriched fact dictionary
        """
        enriched = fact.copy()
        
        enriched.update({
            'taxonomy_concept': self._get_concept_qname(concept),
            'taxonomy_label': concept.get('concept_label'),
            'taxonomy_type': concept.get('concept_type'),
            'taxonomy_namespace': concept.get('concept_namespace'),
            'period_type': concept.get('period_type'),
            'balance_type': concept.get('balance_type'),
            'is_abstract': concept.get('is_abstract', False),
            'is_extension': concept.get('is_extension', False),
            'mapping_confidence': confidence,
            'mapping_method': method,
            'is_unmapped': False
        })
        
        return enriched
    
    def mark_unmapped(
        self,
        fact: Dict[str, Any],
        reason: str,
        statistics: ResolutionStatistics
    ) -> Dict[str, Any]:
        """
        Mark a fact as unmapped with diagnostic information.
        
        Args:
            fact: Original fact dictionary
            reason: Human-readable reason for failure
            statistics: Statistics tracker to update
            
        Returns:
            Fact dictionary marked as unmapped
        """
        statistics.increment_unmapped()
        
        unmapped = fact.copy()
        unmapped.update({
            'taxonomy_concept': None,
            'taxonomy_label': f"Unmapped: {self._get_concept_qname(fact) or 'Unknown'}",
            'taxonomy_type': None,
            'taxonomy_namespace': None,
            'period_type': None,
            'balance_type': None,
            'is_abstract': False,
            'is_extension': False,
            'mapping_confidence': 0.0,
            'mapping_method': 'unmapped',
            'mapping_reason': reason,
            'is_unmapped': True
        })
        
        return unmapped
    
    def _get_concept_qname(self, concept: Dict[str, Any]) -> Optional[str]:
        """
        Extract qualified name from concept dictionary.
        
        Args:
            concept: Concept or fact dictionary
            
        Returns:
            Qualified name if found, None otherwise
        """
        return (
            concept.get('concept_qname') or
            concept.get('concept') or
            concept.get('name')
        )


__all__ = ['ResultEnricher']