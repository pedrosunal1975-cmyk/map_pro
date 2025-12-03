# File: shared/exceptions/__init__.py
"""
Map Pro Shared Exceptions Package
=================================

Custom exception classes for the Map Pro system.
"""

from .custom_exceptions import (
    MapProError,
    EngineError,
    DatabaseError,
    CriticalEngineError,
    JobProcessingError,
    StatusReportingError,
    ValidationError,
    ConfigurationError
)

__all__ = [
    'MapProError',
    'EngineError',
    'DatabaseError',
    'CriticalEngineError',
    'JobProcessingError',
    'StatusReportingError',
    'ValidationError',
    'ConfigurationError'
]