# engines/parser/arelle_exceptions.py
"""
Arelle Controller Exception Classes
====================================

Custom exception types for Arelle operations.
Provides clear error types for different failure scenarios.

Design Pattern: Custom Exception Hierarchy
Benefits: Type-safe error handling, clear error semantics
"""


class ArelleError(Exception):
    """Base exception for all Arelle-related errors."""
    pass


class ArelleInitializationError(ArelleError):
    """
    Raised when Arelle controller fails to initialize.
    
    Common causes:
    - Arelle library not installed
    - Failed to create temporary directory
    - ModelManager initialization failed
    """
    pass


class ArelleModelLoadError(ArelleError):
    """
    Raised when XBRL model fails to load.
    
    Common causes:
    - File not found
    - Invalid XBRL format
    - Permission denied
    - Corrupted file
    """
    pass


class ArelleValidationError(ArelleError):
    """
    Raised when XBRL model validation fails.
    
    Common causes:
    - Missing required elements
    - Invalid structure
    - Schema violations
    """
    pass


__all__ = [
    'ArelleError',
    'ArelleInitializationError',
    'ArelleModelLoadError',
    'ArelleValidationError'
]