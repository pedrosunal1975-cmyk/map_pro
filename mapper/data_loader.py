# File: /map_pro/engines/mapper/data_loader.py

"""
Map Pro Data Loader
===================

Main coordinator for all data loading and saving operations.

This module has been refactored to maintain <400 line file limit and reduce complexity.
The actual loading logic is delegated to specialized loaders in the loaders/ submodule.

Responsibilities:
- Provide unified API for data loading/saving
- Coordinate between specialized loaders
- Maintain backward compatibility

Architecture:
- FactsLoader: Load parsed facts from JSON/database
- TaxonomyLoader: Load taxonomy concepts
- ExtensionsLoader: Load company extensions
- ResultsSaver: Save mapped results
"""

from typing import Dict, Any, List, Tuple

from core.system_logger import get_logger

# Import specialized loaders
from .loaders import (
    FactsLoader,
    TaxonomyLoader,
    ExtensionsLoader,
    ResultsSaver
)

logger = get_logger(__name__, 'engine')


class DataLoader:
    """
    Main data loader coordinator for mapper engine.
    
    This class provides a unified API for all data loading and saving operations,
    delegating to specialized loaders for actual implementation.
    
    Benefits of this architecture:
    - Each loader has single responsibility
    - Files stay under 500 lines
    - Methods have low complexity
    - Easy to test each component
    - Easy to add new loading strategies
    """
    
    def __init__(self):
        """Initialize data loader with specialized loaders."""
        self.logger = logger
        
        # Initialize specialized loaders
        self.facts_loader = FactsLoader()
        self.taxonomy_loader = TaxonomyLoader()
        self.extensions_loader = ExtensionsLoader()
        self.results_saver = ResultsSaver()
        
        self.logger.debug("Data loader initialized with specialized loaders")
    
    def load_parsed_facts(
        self,
        filing_id: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Load parsed facts for a filing.
        
        Uses hybrid database + filesystem approach with diagnostics on failure.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Tuple of (facts_list, metadata_dict)
        """
        return self.facts_loader.load_parsed_facts(filing_id)
    
    def load_taxonomy_concepts(
        self,
        filing_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Load taxonomy concepts.
        
        Uses hybrid database + filesystem approach with intelligent library discovery
        and fallback concepts.
        
        Args:
            filing_id: Optional filing UUID for intelligent library discovery
            
        Returns:
            List of concept dictionaries
        """
        return self.taxonomy_loader.load_taxonomy_concepts(filing_id)
    
    def load_company_extensions(
        self,
        filing_id: str
    ) -> List[Dict[str, Any]]:
        """
        Load company extension concepts.
        
        Finds extraction directory and parses company XSD files.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            List of company concept dictionaries
        """
        return self.extensions_loader.load_company_extensions(filing_id)
    
    def save_mapped_results(
        self,
        filing_id: str,
        statements: List[Dict[str, Any]],
        quality_report: Dict[str, Any],
        success_metrics: Dict[str, Any],
        parsed_metadata: Dict[str, Any],
        null_quality_report: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Save mapped results to JSON files and database.
        
        Args:
            filing_id: Filing UUID
            statements: List of statement dictionaries
            quality_report: Quality assessment results
            success_metrics: Success calculation results
            parsed_metadata: Original parsed metadata
            null_quality_report: Optional null quality report
            
        Returns:
            Dictionary with save results
        """
        return self.results_saver.save_mapped_results(
            filing_id,
            statements,
            quality_report,
            success_metrics,
            parsed_metadata,
            null_quality_report
        )


# Backward compatibility: Export constants that were in original file
# These can be accessed by importing from data_loader

# File reading constants
METADATA_READ_SIZE = 3000
CONTENT_READ_SIZE = 2000
SMALL_CONTENT_READ = 2000

# Database constants
DEFAULT_LIBRARY_STATUS = 'active'
DEFAULT_MAPPING_THRESHOLD = 0.0
DEFAULT_CURRENCY = 'USD'
DEFAULT_MAPPER_VERSION = 'map_pro_mapper_v1'

# Namespace constants
# NOTE: SEC_DEI_NAMESPACE is a fallback default for US markets only.
# Market-specific namespaces should be configured in market plugins or taxonomy config.
# This constant is kept for backward compatibility with existing code.
FASB_NAMESPACE_TEMPLATE = "http://fasb.org/{}/2023"
SEC_DEI_NAMESPACE = "http://xbrl.sec.gov/dei/2023"  # US market default fallback

# XSD constants
XSD_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'
XSD_NS_MAP = {'xs': XSD_NAMESPACE}

# Taxonomy constants
STANDARD_TAXONOMIES = ['us-gaap', 'dei', 'srt', 'ifrs']
DEFAULT_LIBRARIES = ['us-gaap-2024', 'dei-2024', 'srt-2024']

# Type constants
MONETARY_TYPES = ['monetary', 'decimal', 'integer', 'float']
DATE_TYPES = ['date', 'time']
PERCENT_TYPES = ['percent', 'ratio']


__all__ = [
    'DataLoader',
    # Export constants for backward compatibility
    'METADATA_READ_SIZE',
    'CONTENT_READ_SIZE',
    'SMALL_CONTENT_READ',
    'DEFAULT_LIBRARY_STATUS',
    'DEFAULT_MAPPING_THRESHOLD',
    'DEFAULT_CURRENCY',
    'DEFAULT_MAPPER_VERSION',
    'FASB_NAMESPACE_TEMPLATE',
    'SEC_DEI_NAMESPACE',
    'XSD_NAMESPACE',
    'XSD_NS_MAP',
    'STANDARD_TAXONOMIES',
    'DEFAULT_LIBRARIES',
    'MONETARY_TYPES',
    'DATE_TYPES',
    'PERCENT_TYPES'
]