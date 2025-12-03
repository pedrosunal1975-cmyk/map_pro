"""
Map Pro Validation Engine
=========================

Validates XBRL models and extracted data.
Pre-parsing and post-parsing validation.

Architecture: Universal validation - works for all markets.
"""

from typing import Dict, Any, List
from pathlib import Path

from core.system_logger import get_logger

try:
    from arelle.ModelXbrl import ModelXbrl
    ARELLE_AVAILABLE = True
except ImportError:
    ARELLE_AVAILABLE = False
    ModelXbrl = None  # Dummy for type hints

logger = get_logger(__name__, 'engine')


class ValidationEngine:
    """
    Validates XBRL parsing operations.
    
    Responsibilities:
    - Validate XBRL models before parsing
    - Distinguish instance documents from taxonomy/linkbase files
    - Validate extracted data quality
    - Check for common issues
    """
    
    def __init__(self):
        """Initialize validation engine."""
        pass
    
    def validate_xbrl_model(self, model_xbrl: ModelXbrl) -> Dict[str, Any]:
        """
        Validate XBRL model and determine if it's an instance document.
        
        CRITICAL: Distinguishes between:
        - Instance documents (have facts) -> valid for parsing
        - Taxonomy/linkbase files (no facts, but valid files) -> not instances
        - Corrupted/invalid files -> errors
        
        Args:
            model_xbrl: Arelle ModelXbrl instance
            
        Returns:
            Validation result dictionary with:
            - is_instance: True if this is an XBRL instance document
            - valid: True if file is valid (regardless of type)
            - facts_count, contexts_count, units_count
            - errors, warnings
        """
        validation = {
            'is_instance': False,  # NEW: Is this an instance document?
            'valid': False,
            'facts_count': 0,
            'contexts_count': 0,
            'units_count': 0,
            'errors': [],
            'warnings': []
        }
        
        if not model_xbrl:
            validation['errors'].append("Model is None")
            return validation
        
        # Check facts
        if hasattr(model_xbrl, 'facts'):
            validation['facts_count'] = len(model_xbrl.facts)
        
        # Check contexts
        if hasattr(model_xbrl, 'contexts'):
            validation['contexts_count'] = len(model_xbrl.contexts)
        
        # Check units
        if hasattr(model_xbrl, 'units'):
            validation['units_count'] = len(model_xbrl.units)
        
        # Check Arelle errors
        if hasattr(model_xbrl, 'errors') and model_xbrl.errors:
            validation['errors'].extend([str(err) for err in model_xbrl.errors])
        
        # CRITICAL LOGIC: Determine if this is an instance document
        if validation['facts_count'] > 0:
            # Has facts -> This is an instance document
            validation['is_instance'] = True
            validation['valid'] = True
        else:
            # No facts -> Could be taxonomy/linkbase file
            # Check if it loaded without errors
            if len(validation['errors']) == 0:
                # File loaded successfully but has no facts
                # This is a valid taxonomy/linkbase file, NOT an instance
                validation['is_instance'] = False
                validation['valid'] = True  # File itself is valid
                validation['warnings'].append(
                    "File is not an XBRL instance document (taxonomy/linkbase file)"
                )
            else:
                # File has errors -> Invalid/corrupted
                validation['is_instance'] = False
                validation['valid'] = False
                validation['errors'].append("File failed to load or is corrupted")
        
        return validation


__all__ = ['ValidationEngine']