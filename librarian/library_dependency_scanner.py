"""
Library Dependency Scanner for MapPro System.

This module provides functionality for scanning XBRL filings to identify taxonomy
library dependencies. It analyzes both parsed facts and raw XBRL files to determine
which taxonomy libraries are required for processing.

This file serves as the main entry point and re-exports all scanner functionality
from specialized submodules for better organization and maintainability.

Architecture:
    This is a helper component for LibraryDependencyAnalyzer, focusing solely on
    scanning and detection operations. It does not handle library downloads or
    job orchestration.

Responsibilities:
    - Analyze parsed facts for namespace requirements
    - Scan extracted XBRL files for taxonomy declarations
    - Map discovered namespaces to required libraries
    - Normalize and validate namespace data for consistent matching

Does NOT Handle:
    - Job processing (LibraryDependencyAnalyzer responsibility)
    - Library downloads (LibraryCoordinator responsibility)
    - Database transactions (uses read-only access only)

Market Agnostic:
    Works with any XBRL market (SEC, FCA, ESMA, etc.) through configuration-driven
    taxonomy matching.

Location: engines/librarian/library_dependency_scanner.py

Example:
    >>> scanner = LibraryDependencyScanner()
    >>> result = await scanner.scan_filing_requirements(
    ...     filing_id='uuid-123',
    ...     market_type='SEC',
    ...     facts_json_path='/path/to/facts.json'
    ... )
    >>> print(f"Found {len(result['required_libraries'])} required libraries")

Module Organization:
    The scanner functionality is split across multiple focused modules:
    
    - scanner_models.py: Data structures, enums, and constants
    - namespace_extraction.py: Namespace extraction from facts and XML
    - namespace_matching.py: Namespace normalization, matching, and library mapping
    - file_readers.py: Facts JSON and XBRL file reading
    - scanner_core.py: Main scanner orchestration logic
    
    This file re-exports all public APIs for backward compatibility.
"""

# Import all components from submodules
from .scanner_models import (
    ScannerConstants,
    NamespaceSource,
    ScanResult
)

from .namespace_extraction import (
    NamespaceExtractor
)

from .namespace_matching import (
    NamespaceNormalizer,
    NamespaceMatcher,
    LibraryMapper
)

from .file_readers import (
    FactsJsonReader,
    XbrlFileScanner
)

from .scanner_core import (
    LibraryDependencyScanner
)


# Re-export all public APIs for backward compatibility
__all__ = [
    # Main scanner class
    'LibraryDependencyScanner',
    
    # Data models and constants
    'ScannerConstants',
    'NamespaceSource',
    'ScanResult',
    
    # Namespace operations
    'NamespaceNormalizer',
    'NamespaceExtractor',
    'NamespaceMatcher',
    'LibraryMapper',
    
    # File readers
    'FactsJsonReader',
    'XbrlFileScanner'
]