"""
Fact Concept Extractor.

Extracts concept information from Arelle fact objects.

Location: engines/parser/fact_concept_extractor.py
"""

from typing import Optional, Dict, Any

from core.system_logger import get_logger


logger = get_logger(__name__, 'engine')


class ConceptExtractor:
    """
    Extracts concept information from facts.
    
    Responsibilities:
    - Extract concept QName
    - Extract local name and namespace
    - Extract concept label
    - Provide fallback strategies
    
    Example:
        >>> extractor = ConceptExtractor()
        >>> concept_info = extractor.extract(arelle_fact, index=0)
    """
    
    def extract(
        self,
        arelle_fact,
        index: int,
        filing_id: Optional[str] = None,
        total_facts: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract concept information from fact.
        
        This is critical information - if not available, fact is invalid.
        
        Args:
            arelle_fact: Arelle fact object
            index: Fact index for logging
            filing_id: Filing ID for error context (optional)
            total_facts: Total number of facts for context (optional)
            
        Returns:
            Dictionary with concept info or None if extraction failed
        """
        try:
            # Try standard concept attribute first
            if hasattr(arelle_fact, 'concept') and arelle_fact.concept is not None:
                return self._extract_from_concept_object(arelle_fact)
            
            # Fallback to qname attribute
            return self._extract_from_qname(arelle_fact, index, filing_id, total_facts)
        
        except Exception as e:
            # Rich error context
            error_context = self._build_error_context(
                filing_id=filing_id,
                fact_index=index,
                total_facts=total_facts,
                concept_name="UNKNOWN",
                error_message=str(e)
            )
            logger.warning(f"[ERROR] Failed to extract concept | {error_context}")
            return None
    
    def _extract_from_concept_object(self, arelle_fact) -> Dict[str, Any]:
        """
        Extract concept info from concept object.
        
        Args:
            arelle_fact: Arelle fact object with concept attribute
            
        Returns:
            Dictionary with concept information
        """
        concept_info = {
            'concept_qname': str(arelle_fact.concept.qname),
            'concept_local_name': arelle_fact.concept.qname.localName,
            'concept_namespace': arelle_fact.concept.qname.namespaceURI
        }
        
        # Try to get concept label
        concept_info['concept_label'] = self._extract_label(arelle_fact)
        
        return concept_info
    
    def _extract_label(self, arelle_fact) -> Optional[str]:
        """
        Extract concept label with error handling.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Concept label or None
        """
        try:
            if hasattr(arelle_fact.concept, 'label'):
                return arelle_fact.concept.label()
        except Exception as e:
            logger.debug(f"Could not extract concept label: {e}")
        
        return None
    
    def _extract_from_qname(
        self,
        arelle_fact,
        index: int,
        filing_id: Optional[str] = None,
        total_facts: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract concept info from qname attribute (fallback).
        
        Args:
            arelle_fact: Arelle fact object
            index: Fact index for logging
            filing_id: Filing ID for error context (optional)
            total_facts: Total number of facts for context (optional)
            
        Returns:
            Dictionary with concept info or None if failed
        """
        qname = getattr(arelle_fact, 'qname', None)
        
        if not qname or not hasattr(qname, 'localName'):
            # Rich error context
            error_context = self._build_error_context(
                filing_id=filing_id,
                fact_index=index,
                total_facts=total_facts,
                concept_name="UNAVAILABLE",
                error_message="No concept information available (neither concept nor qname)"
            )
            logger.warning(f"[ERROR] No concept information | {error_context}")
            return None
        
        return {
            'concept_qname': str(qname),
            'concept_local_name': qname.localName,
            'concept_namespace': qname.namespaceURI,
            'concept_label': None
        }
    
    def _build_error_context(
        self,
        filing_id: Optional[str],
        fact_index: int,
        total_facts: Optional[int],
        concept_name: str,
        error_message: str
    ) -> str:
        """
        Build rich error context string.
        
        Args:
            filing_id: Filing ID
            fact_index: Current fact index
            total_facts: Total facts count
            concept_name: Concept name or placeholder
            error_message: Error description
            
        Returns:
            Formatted error context string
        """
        filing_str = f"Filing: {filing_id[:8]}..." if filing_id else "Filing: UNKNOWN"
        
        if total_facts:
            fact_str = f"Fact: {fact_index + 1}/{total_facts}"
        else:
            fact_str = f"Fact: {fact_index + 1}"
        
        return (
            f"{filing_str} | "
            f"{fact_str} | "
            f"Concept: {concept_name} | "
            f"Reason: {error_message}"
        )


__all__ = ['ConceptExtractor']