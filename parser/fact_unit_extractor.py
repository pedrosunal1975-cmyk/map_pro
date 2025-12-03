"""
Fact Unit Extractor.

Extracts unit references from Arelle fact objects.

Location: engines/parser/fact_unit_extractor.py
"""

from typing import Optional

from core.system_logger import get_logger


logger = get_logger(__name__, 'engine')


class UnitExtractor:
    """
    Extracts unit references from facts.
    
    Responsibilities:
    - Extract unit IDs
    - Extract from unit objects
    - Extract from measures
    - Provide fallback mechanisms
    
    Market-agnostic unit extraction with proper error handling.
    
    Example:
        >>> extractor = UnitExtractor()
        >>> unit_ref = extractor.extract(arelle_fact)
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
        Extract unit reference with enhanced fallback chain.
        
        Args:
            arelle_fact: Arelle fact object
            filing_id: Filing ID for error context (optional)
            fact_index: Fact index for error context (optional)
            total_facts: Total facts for error context (optional)
            concept_name: Concept name for error context (optional)
            
        Returns:
            Unit reference string or None
        """
        # Store context for error logging
        self._context = {
            'filing_id': filing_id,
            'fact_index': fact_index,
            'total_facts': total_facts,
            'concept_name': concept_name
        }
        
        extraction_strategies = [
            self._extract_from_unit_object,
            self._extract_from_unit_id_attr
        ]
        
        for strategy in extraction_strategies:
            try:
                unit_ref = strategy(arelle_fact)
                if unit_ref:
                    return unit_ref
            except Exception as e:
                # Rich error context for unit extraction failures
                error_context = self._build_error_context(
                    strategy_name=strategy.__name__,
                    error_message=str(e)
                )
                logger.debug(f"[ERROR] Unit extraction strategy failed | {error_context}")
                continue
        
        return None
    
    def _extract_from_unit_object(self, arelle_fact) -> Optional[str]:
        """
        Extract unit from unit object with multiple sub-strategies.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Unit string or None
        """
        if not (hasattr(arelle_fact, 'unit') and arelle_fact.unit is not None):
            return None
        
        # Try unit.id
        if hasattr(arelle_fact.unit, 'id'):
            return arelle_fact.unit.id
        
        # Try extracting from measures
        unit_from_measures = self._extract_from_measures(arelle_fact.unit)
        if unit_from_measures:
            return unit_from_measures
        
        # Try converting unit object to string
        unit_str = str(arelle_fact.unit)
        if unit_str and unit_str != 'None':
            return unit_str
        
        return None
    
    def _extract_from_measures(self, unit_object) -> Optional[str]:
        """
        Extract unit from measures attribute.
        
        Args:
            unit_object: Arelle unit object
            
        Returns:
            Unit string or None
        """
        if not hasattr(unit_object, 'measures'):
            return None
        
        measures = unit_object.measures
        if not measures or len(measures) == 0:
            return None
        
        # Get first measure set
        measure_set = measures[0] if isinstance(measures, (list, tuple)) else measures
        if not measure_set or len(measure_set) == 0:
            return None
        
        # Get first measure
        measure = measure_set[0] if isinstance(measure_set, (list, tuple)) else measure_set
        
        # Extract measure string
        if hasattr(measure, 'localName'):
            return measure.localName
        
        return str(measure)
    
    def _extract_from_unit_id_attr(self, arelle_fact) -> Optional[str]:
        """
        Extract unit from unitID attribute.
        
        Args:
            arelle_fact: Arelle fact object
            
        Returns:
            Unit ID or None
        """
        if hasattr(arelle_fact, 'unitID'):
            return arelle_fact.unitID
        return None
    
    def _build_error_context(
        self,
        strategy_name: str,
        error_message: str
    ) -> str:
        """
        Build rich error context string using stored context.
        
        Args:
            strategy_name: Name of extraction strategy that failed
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
            f"Strategy: {strategy_name} | "
            f"Reason: {error_message}"
        )


__all__ = ['UnitExtractor']