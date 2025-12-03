# File: engines/parser/context_processor.py

"""
Map Pro Context Processor
=========================

Coordinates XBRL context and unit processing from Arelle models.
Orchestrates extraction and statistics collection.

Architecture: Facade pattern - Coordinates specialized extractors.
Refactored from monolithic design to modular architecture.
"""

from typing import Dict, List, Any

from core.system_logger import get_logger

try:
    from arelle.ModelXbrl import ModelXbrl
    ARELLE_AVAILABLE = True
except ImportError:
    ARELLE_AVAILABLE = False
    ModelXbrl = None

from engines.parser.context_extractor import (
    ContextExtractor,
    ContextExtractionError
)
from engines.parser.unit_extractor import (
    UnitExtractor,
    UnitExtractionError
)
from engines.parser.context_statistics import ContextStatistics

logger = get_logger(__name__, 'engine')


class ContextProcessor:
    """
    Coordinates XBRL context and unit processing.
    
    Responsibilities:
    - Orchestrate context extraction from ModelXbrl
    - Orchestrate unit extraction from ModelXbrl
    - Coordinate statistics collection
    - Handle batch processing of contexts and units
    
    Does NOT handle:
    - Individual context extraction (context_extractor handles this)
    - Individual unit extraction (unit_extractor handles this)
    - Statistics calculation (context_statistics handles this)
    - Fact extraction (fact_extractor handles this)
    - Output formatting (output_formatter handles this)
    """
    
    def __init__(self):
        """
        Initialize context processor with extractors and statistics.
        """
        self.context_extractor = ContextExtractor()
        self.unit_extractor = UnitExtractor()
        self.statistics = ContextStatistics()
    
    def extract_contexts(
        self, 
        model_xbrl: ModelXbrl, 
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all contexts from XBRL model.
        
        Args:
            model_xbrl: Arelle ModelXbrl instance
            document_id: Document universal ID
            
        Returns:
            List of context dictionaries
        """
        if not self._validate_model_for_contexts(model_xbrl):
            return []
        
        contexts_list = []
        total_contexts = len(model_xbrl.contexts)
        
        logger.info(
            "Starting context extraction from %d contexts",
            total_contexts
        )
        
        for context_id, arelle_context in model_xbrl.contexts.items():
            context_dict = self._process_single_context(
                arelle_context,
                document_id,
                context_id
            )
            
            if context_dict:
                contexts_list.append(context_dict)
                self.statistics.update_context_statistics(context_dict)
        
        logger.info(
            "Context extraction completed: %d contexts",
            self.statistics.get_context_count()
        )
        
        return contexts_list
    
    def _validate_model_for_contexts(self, model_xbrl: ModelXbrl) -> bool:
        """
        Validate that model is suitable for context extraction.
        
        Args:
            model_xbrl: Arelle ModelXbrl instance
            
        Returns:
            True if model is valid, False otherwise
        """
        if not model_xbrl:
            logger.error("Cannot extract contexts: model_xbrl is None")
            return False
        
        if not hasattr(model_xbrl, 'contexts'):
            logger.error("model_xbrl does not have contexts attribute")
            return False
        
        return True
    
    def _process_single_context(
        self,
        arelle_context: Any,
        document_id: str,
        context_id: str
    ) -> Dict[str, Any]:
        """
        Process a single context with error handling.
        
        Args:
            arelle_context: Arelle context object
            document_id: Document universal ID
            context_id: Context identifier for logging
            
        Returns:
            Context dictionary or None if extraction failed
        """
        try:
            return self.context_extractor.extract_single_context(
                arelle_context,
                document_id
            )
        except ContextExtractionError as error:
            logger.error(
                "Failed to extract context %s: %s",
                context_id,
                str(error)
            )
            return None
        except (AttributeError, ValueError, TypeError) as error:
            logger.error(
                "Invalid context data for %s: %s",
                context_id,
                str(error),
                exc_info=True
            )
            return None
    
    def extract_units(
        self, 
        model_xbrl: ModelXbrl, 
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all units from XBRL model.
        
        Args:
            model_xbrl: Arelle ModelXbrl instance
            document_id: Document universal ID
            
        Returns:
            List of unit dictionaries
        """
        if not self._validate_model_for_units(model_xbrl):
            return []
        
        units_list = []
        total_units = len(model_xbrl.units)
        
        logger.info(
            "Starting unit extraction from %d units",
            total_units
        )
        
        for unit_id, arelle_unit in model_xbrl.units.items():
            unit_dict = self._process_single_unit(
                arelle_unit,
                document_id,
                unit_id
            )
            
            if unit_dict:
                units_list.append(unit_dict)
                self.statistics.increment_units_extracted()
        
        logger.info(
            "Unit extraction completed: %d units",
            self.statistics.get_unit_count()
        )
        
        return units_list
    
    def _validate_model_for_units(self, model_xbrl: ModelXbrl) -> bool:
        """
        Validate that model is suitable for unit extraction.
        
        Args:
            model_xbrl: Arelle ModelXbrl instance
            
        Returns:
            True if model is valid, False otherwise
        """
        if not model_xbrl:
            logger.error("Cannot extract units: model_xbrl is None")
            return False
        
        if not hasattr(model_xbrl, 'units'):
            logger.error("model_xbrl does not have units attribute")
            return False
        
        return True
    
    def _process_single_unit(
        self,
        arelle_unit: Any,
        document_id: str,
        unit_id: str
    ) -> Dict[str, Any]:
        """
        Process a single unit with error handling.
        
        Args:
            arelle_unit: Arelle unit object
            document_id: Document universal ID
            unit_id: Unit identifier for logging
            
        Returns:
            Unit dictionary or None if extraction failed
        """
        try:
            return self.unit_extractor.extract_single_unit(
                arelle_unit,
                document_id
            )
        except UnitExtractionError as error:
            logger.error(
                "Failed to extract unit %s: %s",
                unit_id,
                str(error)
            )
            return None
        except (AttributeError, ValueError, TypeError) as error:
            logger.error(
                "Invalid unit data for %s: %s",
                unit_id,
                str(error),
                exc_info=True
            )
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get context and unit processing statistics.
        
        Returns:
            Dictionary containing all statistics
        """
        return self.statistics.get_statistics()
    
    def reset_statistics(self) -> None:
        """Reset all processing statistics."""
        self.statistics.reset_statistics()


__all__ = [
    'ContextProcessor'
]