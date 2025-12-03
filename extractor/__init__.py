"""
Map Pro Extraction Engine
=========================

Universal extraction engine for archive files.

Components:
- ExtractionCoordinator: Main engine inheriting from BaseEngine
- ArchiveHandlerFactory: Creates format-specific handlers
- FormatDetector: Detects archive format
- ExtractionValidator: Validates extraction operations

Architecture: Market-agnostic extraction - handles all archive formats universally.
"""

from .extraction_coordinator import ExtractionCoordinator, create_extractor_engine
from .archive_handlers import (
    ArchiveHandler,
    ZipHandler,
    TarHandler,
    GzipHandler,
    ArchiveHandlerFactory
)
from .format_detectors import FormatDetector
from .extraction_validators import ExtractionValidator, ValidationResult

__all__ = [
    'ExtractionCoordinator',
    'create_extractor_engine',
    'ArchiveHandler',
    'ZipHandler',
    'TarHandler',
    'GzipHandler',
    'ArchiveHandlerFactory',
    'FormatDetector',
    'ExtractionValidator',
    'ValidationResult'
]