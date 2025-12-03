# File: engines/parser/context_extractor.py

"""
Context Extractor
=================

Extracts context information from Arelle XBRL models.
Handles the extraction of entity, period, and dimensional data.

Architecture: Single Responsibility - Focuses only on extraction logic.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger

try:
    from arelle.ModelXbrl import ModelXbrl
    from arelle.ModelInstanceObject import ModelContext
    ARELLE_AVAILABLE = True
except ImportError:
    ARELLE_AVAILABLE = False
    ModelXbrl = None
    ModelContext = None

from engines.parser.context_constants import (
    PERIOD_TYPE_INSTANT,
    PERIOD_TYPE_DURATION,
    PERIOD_TYPE_FOREVER
)

logger = get_logger(__name__, 'engine')


class ContextExtractionError(Exception):
    """Raised when context extraction fails."""
    pass


class ContextExtractor:
    """
    Extracts context information from Arelle context objects.
    
    Responsibilities:
    - Extract single context from Arelle context object
    - Coordinate entity, period, and dimension extraction
    - Validate context structure
    
    Does NOT handle:
    - Context processing logic (context_processor handles this)
    - Context statistics (context_statistics handles this)
    - Output formatting (output_formatter handles this)
    """
    
    def __init__(self):
        """Initialize context extractor."""
        pass
    
    def extract_single_context(
        self, 
        arelle_context: Any, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract single context from Arelle context object.
        
        Args:
            arelle_context: Arelle ModelContext instance
            document_id: Document universal ID
            
        Returns:
            Context dictionary or None if extraction failed
            
        Raises:
            ContextExtractionError: If required context attributes are missing
        """
        if not self._validate_context_structure(arelle_context):
            raise ContextExtractionError("Context missing 'id' attribute")
        
        context_dict = {
            'context_id': arelle_context.id,
            'document_universal_id': document_id
        }
        
        entity_info = self._extract_entity_info(arelle_context)
        context_dict.update(entity_info)
        
        period_info = self._extract_period_info(arelle_context)
        context_dict.update(period_info)
        
        dimensions = self._extract_dimensions(arelle_context)
        context_dict['dimensions'] = dimensions
        
        context_dict['extracted_at'] = datetime.now(timezone.utc).isoformat()
        
        return context_dict
    
    def _validate_context_structure(self, arelle_context: Any) -> bool:
        """
        Validate that context has required structure.
        
        Args:
            arelle_context: Arelle context object
            
        Returns:
            True if context is valid, False otherwise
        """
        return hasattr(arelle_context, 'id')
    
    def _extract_entity_info(self, arelle_context: Any) -> Dict[str, Optional[str]]:
        """
        Extract entity information from context.
        
        Args:
            arelle_context: Arelle context object
            
        Returns:
            Dictionary with entity_scheme and entity_identifier
        """
        entity_info = {
            'entity_scheme': None,
            'entity_identifier': None
        }
        
        try:
            if hasattr(arelle_context, 'entityIdentifier') and arelle_context.entityIdentifier:
                entity_scheme, entity_id = arelle_context.entityIdentifier
                entity_info['entity_scheme'] = entity_scheme
                entity_info['entity_identifier'] = entity_id
        except (ValueError, TypeError) as error:
            logger.warning(
                "Invalid entity identifier format in context: %s",
                str(error)
            )
        except AttributeError as error:
            logger.warning(
                "Entity identifier attribute missing in context: %s",
                str(error)
            )
        
        return entity_info
    
    def _extract_period_info(self, arelle_context: Any) -> Dict[str, Any]:
        """
        Extract period information from context.
        
        Args:
            arelle_context: Arelle context object
            
        Returns:
            Dictionary with period_type and date fields
        """
        period_info = {
            'period_type': None,
            'instant_date': None,
            'period_start_date': None,
            'period_end_date': None
        }
        
        try:
            if self._is_instant_period(arelle_context):
                self._extract_instant_period(arelle_context, period_info)
            elif self._is_duration_period(arelle_context):
                self._extract_duration_period(arelle_context, period_info)
            elif self._is_forever_period(arelle_context):
                period_info['period_type'] = PERIOD_TYPE_FOREVER
        
        except (AttributeError, ValueError, TypeError) as error:
            logger.warning(
                "Error extracting period info from context: %s",
                str(error)
            )
        
        return period_info
    
    def _is_instant_period(self, arelle_context: Any) -> bool:
        """
        Check if context represents an instant period.
        
        Args:
            arelle_context: Arelle context object
            
        Returns:
            True if instant period, False otherwise
        """
        return (
            hasattr(arelle_context, 'isInstantPeriod') and 
            arelle_context.isInstantPeriod
        )
    
    def _is_duration_period(self, arelle_context: Any) -> bool:
        """
        Check if context represents a duration period.
        
        Args:
            arelle_context: Arelle context object
            
        Returns:
            True if duration period, False otherwise
        """
        return (
            hasattr(arelle_context, 'isStartEndPeriod') and 
            arelle_context.isStartEndPeriod
        )
    
    def _is_forever_period(self, arelle_context: Any) -> bool:
        """
        Check if context represents a forever period.
        
        Args:
            arelle_context: Arelle context object
            
        Returns:
            True if forever period, False otherwise
        """
        return (
            hasattr(arelle_context, 'isForeverPeriod') and 
            arelle_context.isForeverPeriod
        )
    
    def _extract_instant_period(
        self, 
        arelle_context: Any, 
        period_info: Dict[str, Any]
    ) -> None:
        """
        Extract instant period date.
        
        Args:
            arelle_context: Arelle context object
            period_info: Dictionary to populate with period information
        """
        period_info['period_type'] = PERIOD_TYPE_INSTANT
        
        if hasattr(arelle_context, 'instantDatetime') and arelle_context.instantDatetime:
            period_info['instant_date'] = arelle_context.instantDatetime.date().isoformat()
    
    def _extract_duration_period(
        self, 
        arelle_context: Any, 
        period_info: Dict[str, Any]
    ) -> None:
        """
        Extract duration period dates.
        
        Args:
            arelle_context: Arelle context object
            period_info: Dictionary to populate with period information
        """
        period_info['period_type'] = PERIOD_TYPE_DURATION
        
        if hasattr(arelle_context, 'startDatetime') and arelle_context.startDatetime:
            period_info['period_start_date'] = arelle_context.startDatetime.date().isoformat()
        
        if hasattr(arelle_context, 'endDatetime') and arelle_context.endDatetime:
            period_info['period_end_date'] = arelle_context.endDatetime.date().isoformat()
    
    def _extract_dimensions(self, arelle_context: Any) -> Dict[str, str]:
        """
        Extract dimensional information from context.
        
        Args:
            arelle_context: Arelle context object
            
        Returns:
            Dictionary mapping dimension qualified name to member qualified name
        """
        dimensions = {}
        
        try:
            if hasattr(arelle_context, 'qnameDims') and arelle_context.qnameDims:
                for dim_qname, dim_value in arelle_context.qnameDims.items():
                    dim_key = str(dim_qname)
                    
                    if hasattr(dim_value, 'memberQname'):
                        dimensions[dim_key] = str(dim_value.memberQname)
                    else:
                        dimensions[dim_key] = str(dim_value)
        except (AttributeError, TypeError, ValueError) as error:
            logger.warning(
                "Error extracting dimensions from context: %s",
                str(error)
            )
        
        return dimensions


__all__ = [
    'ContextExtractor',
    'ContextExtractionError'
]