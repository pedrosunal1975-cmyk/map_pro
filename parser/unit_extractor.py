# File: engines/parser/unit_extractor.py

"""
Unit Extractor
==============

Extracts unit information from Arelle XBRL models.
Handles measure extraction and unit type classification.

Architecture: Single Responsibility - Focuses only on unit extraction logic.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger

try:
    from arelle.ModelXbrl import ModelXbrl
    ARELLE_AVAILABLE = True
except ImportError:
    ARELLE_AVAILABLE = False
    ModelXbrl = None

from engines.parser.context_constants import (
    SINGLE_MEASURE_COUNT,
    DIVIDE_MEASURE_COUNT,
    UNIT_TYPE_MEASURE,
    UNIT_TYPE_DIVIDE,
    UNIT_TYPE_COMPLEX
)

logger = get_logger(__name__, 'engine')


class UnitExtractionError(Exception):
    """Raised when unit extraction fails."""
    pass


class UnitExtractor:
    """
    Extracts unit information from Arelle unit objects.
    
    Responsibilities:
    - Extract single unit from Arelle unit object
    - Extract measure information
    - Classify unit types (measure, divide, complex)
    
    Does NOT handle:
    - Unit processing logic (context_processor handles this)
    - Output formatting (output_formatter handles this)
    """
    
    def __init__(self):
        """Initialize unit extractor."""
        pass
    
    def extract_single_unit(
        self, 
        arelle_unit: Any, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract single unit from Arelle unit object.
        
        Args:
            arelle_unit: Arelle unit object
            document_id: Document universal ID
            
        Returns:
            Unit dictionary or None if extraction failed
            
        Raises:
            UnitExtractionError: If unit extraction fails critically
        """
        unit_id = self._get_unit_id(arelle_unit)
        
        unit_dict = {
            'unit_id': unit_id,
            'document_universal_id': document_id,
            'unit_type': UNIT_TYPE_MEASURE,
            'measures': []
        }
        
        try:
            self._populate_unit_measures(arelle_unit, unit_dict)
        except (AttributeError, TypeError, ValueError) as error:
            logger.warning(
                "Error extracting unit measures for %s: %s",
                unit_id,
                str(error)
            )
            self._set_fallback_measures(arelle_unit, unit_dict)
        
        unit_dict['extracted_at'] = datetime.now(timezone.utc).isoformat()
        
        return unit_dict
    
    def _get_unit_id(self, arelle_unit: Any) -> str:
        """
        Extract unit ID from Arelle unit object.
        
        Args:
            arelle_unit: Arelle unit object
            
        Returns:
            Unit ID string
        """
        if hasattr(arelle_unit, 'id'):
            return arelle_unit.id
        elif hasattr(arelle_unit, 'unitId'):
            return arelle_unit.unitId
        else:
            return str(arelle_unit)
    
    def _populate_unit_measures(
        self, 
        arelle_unit: Any, 
        unit_dict: Dict[str, Any]
    ) -> None:
        """
        Populate unit dictionary with measure information.
        
        Args:
            arelle_unit: Arelle unit object
            unit_dict: Dictionary to populate with measure data
            
        Raises:
            AttributeError: If measures attribute is missing
        """
        if not hasattr(arelle_unit, 'measures') or not arelle_unit.measures:
            raise AttributeError("Unit missing 'measures' attribute")
        
        measures_list = arelle_unit.measures
        
        if not isinstance(measures_list, (list, tuple)):
            measures_list = [measures_list]
        
        measure_count = len(measures_list)
        
        if measure_count == SINGLE_MEASURE_COUNT:
            self._set_single_measure(measures_list[0], unit_dict)
        elif measure_count == DIVIDE_MEASURE_COUNT:
            self._set_divide_measures(measures_list, unit_dict)
        else:
            self._set_complex_measures(measures_list, unit_dict)
    
    def _set_single_measure(
        self, 
        measure: Any, 
        unit_dict: Dict[str, Any]
    ) -> None:
        """
        Set single measure unit type.
        
        Args:
            measure: Single measure object
            unit_dict: Dictionary to populate
        """
        unit_dict['unit_type'] = UNIT_TYPE_MEASURE
        unit_dict['measures'] = self._extract_measure_names(measure)
    
    def _set_divide_measures(
        self, 
        measures_list: List[Any], 
        unit_dict: Dict[str, Any]
    ) -> None:
        """
        Set divide unit type with numerator and denominator.
        
        Args:
            measures_list: List with exactly 2 measures
            unit_dict: Dictionary to populate
        """
        unit_dict['unit_type'] = UNIT_TYPE_DIVIDE
        unit_dict['numerator'] = self._extract_measure_names(measures_list[0])
        unit_dict['denominator'] = self._extract_measure_names(measures_list[1])
    
    def _set_complex_measures(
        self, 
        measures_list: List[Any], 
        unit_dict: Dict[str, Any]
    ) -> None:
        """
        Set complex unit type with multiple measures.
        
        Args:
            measures_list: List with 3+ measures
            unit_dict: Dictionary to populate
        """
        unit_dict['unit_type'] = UNIT_TYPE_COMPLEX
        unit_dict['measures'] = [
            self._extract_measure_names(measure) for measure in measures_list
        ]
    
    def _set_fallback_measures(
        self, 
        arelle_unit: Any, 
        unit_dict: Dict[str, Any]
    ) -> None:
        """
        Set fallback measures when normal extraction fails.
        
        Args:
            arelle_unit: Arelle unit object
            unit_dict: Dictionary to populate
        """
        try:
            if hasattr(arelle_unit, '__str__'):
                unit_str = str(arelle_unit)
                if unit_str and unit_str != 'None':
                    unit_dict['measures'] = [unit_str]
        except (AttributeError, TypeError, ValueError) as error:
            logger.warning(
                "Fallback unit extraction failed: %s",
                str(error)
            )
            unit_dict['measures'] = []
    
    def _extract_measure_names(self, measure_set: Any) -> List[str]:
        """
        Extract measure names from measure set.
        Handles various measure representations across different XBRL implementations.
        
        Args:
            measure_set: Measure set (could be list, tuple, or single measure)
            
        Returns:
            List of measure name strings
        """
        measures = []
        
        try:
            if not isinstance(measure_set, (list, tuple, set)):
                measure_set = [measure_set]
            
            for measure in measure_set:
                if measure is None:
                    continue
                
                measure_name = self._get_measure_name(measure)
                if measure_name:
                    measures.append(measure_name)
        
        except (AttributeError, TypeError, ValueError) as error:
            logger.warning(
                "Error extracting measure names from measure set: %s",
                str(error)
            )
        
        return measures
    
    def _get_measure_name(self, measure: Any) -> Optional[str]:
        """
        Get name from a single measure object.
        
        Args:
            measure: Measure object
            
        Returns:
            Measure name string or None
        """
        if hasattr(measure, 'localName'):
            return measure.localName
        
        if hasattr(measure, 'qname'):
            return str(measure.qname)
        
        measure_str = str(measure)
        if measure_str and measure_str != 'None':
            return measure_str
        
        return None


__all__ = [
    'UnitExtractor',
    'UnitExtractionError'
]