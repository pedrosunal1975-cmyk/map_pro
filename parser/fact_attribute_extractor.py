"""
Fact Attribute Extractor.

Extracts various fact attributes (decimals, precision, balance, period type).

Location: engines/parser/fact_attribute_extractor.py
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger


logger = get_logger(__name__, 'engine')


class AttributeExtractor:
    """
    Extracts fact attributes.
    
    Responsibilities:
    - Extract decimals
    - Extract precision
    - Extract balance type
    - Determine period type (instant vs duration)
    - Extract nil status
    
    Example:
        >>> extractor = AttributeExtractor()
        >>> attributes = extractor.extract(arelle_fact)
    """
    
    def extract(
        self,
        arelle_fact,
        filing_id: Optional[str] = None,
        fact_index: Optional[int] = None,
        total_facts: Optional[int] = None,
        concept_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract all fact attributes.
        
        Args:
            arelle_fact: Arelle fact object
            filing_id: Filing ID for error context (optional)
            fact_index: Fact index for error context (optional)
            total_facts: Total facts for error context (optional)
            concept_name: Concept name for error context (optional)
            
        Returns:
            Dictionary with all attributes
        """
        # Store context for error logging
        self._context = {
            'filing_id': filing_id,
            'fact_index': fact_index,
            'total_facts': total_facts,
            'concept_name': concept_name
        }
        
        return {
            'decimals': self._extract_decimals(arelle_fact),
            'precision': self._extract_precision(arelle_fact),
            'is_nil': getattr(arelle_fact, 'isNil', False),
            'is_instant': self._is_instant_fact(arelle_fact),
            'is_duration': not self._is_instant_fact(arelle_fact),
            'balance': self._extract_balance(arelle_fact)
        }
    
    def _extract_decimals(self, arelle_fact) -> Optional[str]:
        """
        Extract decimals value with enhanced handling.
        
        Market-agnostic decimals extraction with proper error handling.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Decimals value as string or None
        """
        try:
            # Check if numeric first
            if not self._is_numeric_fact(arelle_fact):
                return None
            
            # Try decimals attribute
            if hasattr(arelle_fact, 'decimals') and arelle_fact.decimals is not None:
                return str(arelle_fact.decimals)
            
            # Try attributes dictionary
            if hasattr(arelle_fact, 'attributes'):
                decimals = arelle_fact.attributes.get('decimals')
                if decimals is not None:
                    return str(decimals)
        
        except Exception as e:
            # Rich error context
            error_context = self._build_error_context(
                error_type="decimals",
                error_message=str(e)
            )
            logger.debug(f"[ERROR] Failed to extract decimals | {error_context}")
        
        return None
    
    def _is_numeric_fact(self, arelle_fact) -> bool:
        """
        Check if fact is numeric.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            True if numeric fact
        """
        return hasattr(arelle_fact, 'isNumeric') and arelle_fact.isNumeric is not None
    
    def _extract_precision(self, arelle_fact) -> Optional[str]:
        """
        Extract precision value.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Precision value as string or None
        """
        try:
            if hasattr(arelle_fact, 'precision') and arelle_fact.precision is not None:
                return str(arelle_fact.precision)
        except Exception as e:
            # Rich error context
            error_context = self._build_error_context(
                error_type="precision",
                error_message=str(e)
            )
            logger.debug(f"[ERROR] Failed to extract precision | {error_context}")
        
        return None
    
    def _is_instant_fact(self, arelle_fact) -> bool:
        """
        Determine if fact is instant or duration.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            True if instant, False if duration or undetermined
        """
        try:
            if hasattr(arelle_fact, 'context') and arelle_fact.context is not None:
                if hasattr(arelle_fact.context, 'isInstantPeriod'):
                    return arelle_fact.context.isInstantPeriod
        except Exception as e:
            # Rich error context
            error_context = self._build_error_context(
                error_type="period_type",
                error_message=str(e)
            )
            logger.debug(f"[ERROR] Failed to determine period type | {error_context}")
        
        # Default to duration if can't determine
        return False
    
    def _extract_balance(self, arelle_fact) -> Optional[str]:
        """
        Extract balance type (credit/debit).
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Balance type string or None
        """
        try:
            if (hasattr(arelle_fact, 'concept') and 
                arelle_fact.concept is not None and
                hasattr(arelle_fact.concept, 'balance') and 
                arelle_fact.concept.balance is not None):
                return str(arelle_fact.concept.balance)
        except Exception as e:
            # Rich error context
            error_context = self._build_error_context(
                error_type="balance",
                error_message=str(e)
            )
            logger.debug(f"[ERROR] Failed to extract balance | {error_context}")
        
        return None
    
    def _build_error_context(
        self,
        error_type: str,
        error_message: str
    ) -> str:
        """
        Build rich error context string using stored context.
        
        Args:
            error_type: Type of attribute extraction that failed
            error_message: Error description
            
        Returns:
            Formatted error context string
        """
        ctx = self._context
        filing_id = ctx.get('filing_id')
        fact_index = ctx.get('fact_index')
        total_facts = ctx.get('total_facts')
        concept_name = ctx.get('concept_name') or "UNKNOWN"
        
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
            f"Attribute: {error_type} | "
            f"Reason: {error_message}"
        )


__all__ = ['AttributeExtractor']