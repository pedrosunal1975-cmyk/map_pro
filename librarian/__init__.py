"""
Map Pro Librarian Engine
========================

Standard taxonomy library management engine for all XBRL markets.
Downloads, indexes, and validates XBRL taxonomy libraries.

Components:
- LibraryCoordinator: Main engine coordinator (inherits from BaseEngine)
- LibraryDependencyAnalyzer: Analyzes filing requirements and ensures libraries are ready
- LibraryDependencyScanner: Detailed file scanning for namespace extraction
- TaxonomyDownloader: Downloads taxonomy files with retry logic
- ConceptIndexer: Indexes taxonomy concepts into PostgreSQL
- LibraryOrganizer: Organizes taxonomy file structure
- ValidationChecker: Validates taxonomy integrity
- ManualProcessor: Handles manually downloaded taxonomies
- taxonomy_config: Taxonomy URL configurations and helpers

Architecture: Uses map_pro_library PostgreSQL database for library metadata storage.

Location: /map_pro/engines/librarian/__init__.py
"""

from .library_coordinator import LibraryCoordinator
from .library_dependency_analyzer import LibraryDependencyAnalyzer
from .library_dependency_scanner import LibraryDependencyScanner
from .taxonomy_downloader import TaxonomyDownloader
from .concept_indexer import ConceptIndexer
from .library_organizer import LibraryOrganizer
from .validation_checker import ValidationChecker
from .manual_processor import ManualProcessor
from .taxonomy_config import (
    TAXONOMY_CONFIGS,
    get_taxonomies_for_market,
    get_all_taxonomies,
    get_taxonomy_by_name,
    validate_market_coverage
)


def create_librarian_engine():
    """Factory function to create librarian engine instance."""
    return LibraryCoordinator()


def create_library_dependency_analyzer():
    """Factory function to create library dependency analyzer instance."""
    return LibraryDependencyAnalyzer()


def create_library_dependency_scanner():
    """Factory function to create library dependency scanner instance."""
    return LibraryDependencyScanner()


__all__ = [
    'LibraryCoordinator',
    'LibraryDependencyAnalyzer',
    'LibraryDependencyScanner',
    'TaxonomyDownloader',
    'ConceptIndexer',
    'LibraryOrganizer',
    'ValidationChecker',
    'ManualProcessor',
    'TAXONOMY_CONFIGS',
    'get_taxonomies_for_market',
    'get_all_taxonomies',
    'get_taxonomy_by_name',
    'validate_market_coverage',
    'create_librarian_engine',
    'create_library_dependency_analyzer',
    'create_library_dependency_scanner'
]