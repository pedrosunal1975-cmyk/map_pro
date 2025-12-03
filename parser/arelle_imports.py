# engines/parser/arelle_imports.py
"""
Arelle Library Import Handler
==============================

Handles Arelle library imports with proper error handling.
Provides availability checking and version detection.

Design Pattern: Import Guard
Benefits: Safe imports, clear error messages, version tracking
"""

import logging
from typing import Optional, Any

from .arelle_config import UNKNOWN_VERSION


# Arelle availability and version tracking
ARELLE_AVAILABLE = False
ARELLE_VERSION: Optional[str] = None
ModelXbrl: Optional[Any] = None


def _import_arelle() -> tuple[bool, Optional[str], Optional[Any]]:
    """
    Attempt to import Arelle library.
    
    Returns:
        Tuple of (available, version, ModelXbrl_class)
    """
    try:
        from arelle import Cntlr, ModelManager
        from arelle.ModelXbrl import ModelXbrl as ModelXbrlClass
        
        # Get Arelle version
        version = _get_arelle_version()
        
        return True, version, ModelXbrlClass
        
    except ImportError as e:
        logging.warning(
            f"Arelle library not available: {e}. "
            "Install with: pip install arelle"
        )
        return False, None, None


def _get_arelle_version() -> str:
    """
    Get Arelle version string.
    
    Returns:
        Version string or 'unknown'
    """
    try:
        import arelle
        return getattr(arelle, '__version__', UNKNOWN_VERSION)
    except (ImportError, AttributeError) as e:
        logging.warning(f"Could not determine Arelle version: {e}")
        return UNKNOWN_VERSION


# Perform import at module level
ARELLE_AVAILABLE, ARELLE_VERSION, ModelXbrl = _import_arelle()


def get_arelle_info() -> dict[str, Any]:
    """
    Get information about Arelle availability and version.
    
    Returns:
        Dictionary with Arelle information containing:
        - available: whether Arelle is installed
        - version: Arelle version string or None
        - installation_command: pip command if not available
    """
    return {
        'available': ARELLE_AVAILABLE,
        'version': ARELLE_VERSION,
        'installation_command': 'pip install arelle' if not ARELLE_AVAILABLE else None
    }


def check_arelle_available() -> bool:
    """
    Check if Arelle is available.
    
    Returns:
        True if Arelle is installed and importable
    """
    return ARELLE_AVAILABLE


__all__ = [
    'ARELLE_AVAILABLE',
    'ARELLE_VERSION',
    'ModelXbrl',
    'get_arelle_info',
    'check_arelle_available'
]