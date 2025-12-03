"""
Fact Context Extractor.

Extracts context references from Arelle fact objects.

Location: engines/parser/fact_context_extractor.py
"""

from typing import Optional

from core.system_logger import get_logger


logger = get_logger(__name__, 'engine')


class ContextExtractor:
    """
    Extracts context references from facts.
    
    Responsibilities:
    - Extract context IDs
    - Try multiple extraction strategies
    - Provide fallback mechanisms
    
    Market-agnostic context extraction with proper error handling.
    
    Example:
        >>> extractor = ContextExtractor()
        >>> context_ref = extractor.extract(arelle_fact)
    """
    
    def extract(
        self,
        arelle_fact,
        filing_id: Optional[str] = None,
        fact_index: Optional[int] = None,
        total_facts: Optional[int] = None,
        concept_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract context reference with enhanced fallback chain.
        
        Args:
            arelle_fact: Arelle fact object
            filing_id: Filing ID for error context (optional)
            fact_index: Fact index for error context (optional)
            total_facts: Total facts for error context (optional)
            concept_name: Concept name for error context (optional)
            
        Returns:
            Context reference string or None
        """
        extraction_strategies = [
            self._extract_from_context_object,
            self._extract_from_context_id_attr,
            self._extract_from_get_method,
            self._extract_from_attributes
        ]
        
        for strategy in extraction_strategies:
            try:
                context_ref = strategy(arelle_fact)
                if context_ref:
                    return context_ref
            except Exception as e:
                # Only log debug for strategy failures (not errors)
                logger.debug(f"Context extraction strategy {strategy.__name__} failed: {e}")
                continue
        
        # If all strategies failed and we have context, log rich error
        if filing_id or fact_index is not None:
            error_context = self._build_error_context(
                filing_id=filing_id,
                fact_index=fact_index,
                total_facts=total_facts,
                concept_name=concept_name or "UNKNOWN",
                error_message="All extraction strategies failed"
            )
            logger.debug(f"[ERROR] Failed to extract context | {error_context}")
        
        return None
    
    def _extract_from_context_object(self, arelle_fact) -> Optional[str]:
        """
        Extract context from context object.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Context ID or None
        """
        if hasattr(arelle_fact, 'context') and arelle_fact.context is not None:
            if hasattr(arelle_fact.context, 'id'):
                return arelle_fact.context.id
        return None
    
    def _extract_from_context_id_attr(self, arelle_fact) -> Optional[str]:
        """
        Extract context from contextID attribute.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Context ID or None
        """
        if hasattr(arelle_fact, 'contextID'):
            return arelle_fact.contextID
        return None
    
    def _extract_from_get_method(self, arelle_fact) -> Optional[str]:
        """
        Extract context using get method.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Context reference or None
        """
        if hasattr(arelle_fact, 'get'):
            return arelle_fact.get('contextRef')
        return None
    
    def _extract_from_attributes(self, arelle_fact) -> Optional[str]:
        """
        Extract context from attributes dictionary.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Context reference or None
        """
        if hasattr(arelle_fact, 'attributes'):
            return arelle_fact.attributes.get('contextRef')
        return None
    
    def _build_error_context(
        self,
        filing_id: Optional[str],
        fact_index: Optional[int],
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
            concept_name: Concept name
            error_message: Error description
            
        Returns:
            Formatted error context string
        """
        filing_str = f"Filing: {filing_id[:8]}..." if filing_id else "Filing: UNKNOWN"
        
        if fact_index is not None:
            if total_facts:
                fact_str = f"Fact: {fact_index + 1}/{total_facts}"
            else:
                fact_str = f"Fact: {fact_index + 1}"
        else:
            fact_str = "Fact: UNKNOWN"
        
        return (
            f"{filing_str} | "
            f"{fact_str} | "
            f"Concept: {concept_name} | "
            f"Reason: {error_message}"
        )


__all__ = ['ContextExtractor']