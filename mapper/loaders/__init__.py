# File: /map_pro/engines/mapper/loaders/__init__.py

"""
Map Pro Data Loaders
===================

Submodule for handling all data loading and saving operations.

Main Loaders:
- FactsLoader: Load parsed facts from JSON/database
- TaxonomyLoader: Main coordinator for loading taxonomy concepts
- ExtensionsLoader: Load company extension concepts
- ResultsSaver: Save mapped results

Taxonomy Sub-modules:
- taxonomy_database_loader: Handles database operations for taxonomy
- taxonomy_filesystem_loader: Handles filesystem operations for taxonomy
- taxonomy_library_discoverer: Logic for discovering taxonomy libraries
- taxonomy_xsd_parser: Logic for parsing XSD files
- taxonomy_concept_builder: Logic for building taxonomy concepts
- taxonomy_fallback_provider: Provides essential fallback concepts

Extensions Sub-modules:
- extraction_directory_finder: Finds extraction directories for filings
- company_xsd_filter: Filters company XSD files from standard taxonomies
- company_xsd_parser: Parses company XSD files with proper error handling

Constants:
- taxonomy_constants: Standard taxonomies, data types, default libraries

Usage:
    from engines.mapper.loaders import TaxonomyLoader, ExtensionsLoader
    
    taxonomy_loader = TaxonomyLoader()
    extensions_loader = ExtensionsLoader()
    # concepts = taxonomy_loader.load_taxonomy_concepts(filing_id='abc-123')
    # extensions = extensions_loader.load_company_extensions('abc-123')
"""

# Original Core Loaders
from .facts_loader import FactsLoader
from .extensions_loader import ExtensionsLoader
from .results_saver import ResultsSaver

# Taxonomy-related Exports (including the main coordinator)
from .taxonomy_loader import TaxonomyLoader
from .taxonomy_database_loader import TaxonomyDatabaseLoader
from .taxonomy_filesystem_loader import TaxonomyFilesystemLoader
from .taxonomy_library_discoverer import TaxonomyLibraryDiscoverer
from .taxonomy_xsd_parser import TaxonomyXSDParser
from .taxonomy_concept_builder import TaxonomyConceptBuilder
from .taxonomy_fallback_provider import TaxonomyFallbackProvider

# Taxonomy Constants
from .taxonomy_constants import (
    DEFAULT_LIBRARIES,
    STANDARD_TAXONOMIES,
    MONETARY_TYPES,
    DATE_TYPES,
    PERCENT_TYPES
)

# Extensions Sub-components (NEW from refactoring)
from .extraction_directory_finder import ExtractionDirectoryFinder
from .company_xsd_filter import CompanyXSDFilter, STANDARD_TAXONOMIES as XSD_STANDARD_TAXONOMIES
from .company_xsd_parser import CompanyXSDParser

__all__ = [
    # Original Core Loaders
    'FactsLoader',
    'ExtensionsLoader',
    'ResultsSaver',

    # Taxonomy Loaders and Components
    'TaxonomyLoader',
    'TaxonomyDatabaseLoader',
    'TaxonomyFilesystemLoader',
    'TaxonomyLibraryDiscoverer',
    'TaxonomyXSDParser',
    'TaxonomyConceptBuilder',
    'TaxonomyFallbackProvider',
    
    # Taxonomy Constants
    'DEFAULT_LIBRARIES',
    'STANDARD_TAXONOMIES',
    'MONETARY_TYPES',
    'DATE_TYPES',
    'PERCENT_TYPES',
    
    # Extensions Sub-components (NEW)
    'ExtractionDirectoryFinder',
    'CompanyXSDFilter',
    'CompanyXSDParser',
    'XSD_STANDARD_TAXONOMIES',
]