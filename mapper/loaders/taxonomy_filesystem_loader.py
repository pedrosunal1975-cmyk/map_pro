# File: engines/mapper/loaders/taxonomy_filesystem_loader.py
"""
Taxonomy Filesystem Loader
===========================

Handles loading taxonomy concepts from filesystem XSD files.

Responsibilities:
- Scan filesystem for taxonomy XSD files
- Discover required libraries from filing facts
- Parse XSD files for concept definitions
- Coordinate filesystem-based loading
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from .taxonomy_constants import DEFAULT_LIBRARIES
from .taxonomy_library_discoverer import TaxonomyLibraryDiscoverer
from .taxonomy_xsd_parser import TaxonomyXSDParser

logger = get_logger(__name__, 'engine')


class TaxonomyFilesystemLoader:
    """
    Loads taxonomy concepts from filesystem XSD files.
    
    Attributes:
        logger: System logger instance
        library_discoverer: Discovers required libraries
        xsd_parser: Parses XSD files
    """
    
    def __init__(
        self,
        library_discoverer: Optional[TaxonomyLibraryDiscoverer] = None,
        xsd_parser: Optional[TaxonomyXSDParser] = None
    ) -> None:
        """
        Initialize filesystem loader with optional dependency injection.
        
        Args:
            library_discoverer: Optional library discoverer instance
            xsd_parser: Optional XSD parser instance
        """
        self.logger = logger
        self.library_discoverer = library_discoverer or TaxonomyLibraryDiscoverer()
        self.xsd_parser = xsd_parser or TaxonomyXSDParser()
    
    def load_from_filesystem(
        self,
        filing_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scan filesystem for taxonomy XSD files and load concepts.
        
        Args:
            filing_id: Optional filing UUID for intelligent library discovery
            
        Returns:
            List of concept dictionaries or empty list on failure
        """
        try:
            taxonomy_root = map_pro_paths.data_taxonomies
            
            if not self._validate_taxonomy_root(taxonomy_root):
                return []
            
            required_libraries = self._get_required_libraries(filing_id)
            concepts = self._parse_library_xsd_files(
                taxonomy_root,
                required_libraries
            )
            
            return concepts
            
        except Exception as error:
            self.logger.error(
                "Filesystem taxonomy scan failed: %s",
                str(error)
            )
            return []
    
    def _validate_taxonomy_root(self, taxonomy_root: Path) -> bool:
        """
        Validate that taxonomy root directory exists.
        
        Args:
            taxonomy_root: Path to taxonomy root directory
            
        Returns:
            True if directory exists, False otherwise
        """
        if not taxonomy_root.exists():
            self.logger.warning(
                "Taxonomy directory missing: %s",
                str(taxonomy_root)
            )
            return False
        return True
    
    def _get_required_libraries(
        self,
        filing_id: Optional[str] = None
    ) -> List[str]:
        """
        Get required library names for loading.
        
        Uses intelligent discovery if filing_id provided, else defaults.
        
        Args:
            filing_id: Optional filing UUID
            
        Returns:
            List of library names (e.g., ['us-gaap-2024', 'dei-2024'])
        """
        if filing_id:
            return self.library_discoverer.discover_libraries(filing_id)
        return DEFAULT_LIBRARIES
    
    def _parse_library_xsd_files(
        self,
        taxonomy_root: Path,
        library_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Parse XSD files from specified libraries.
        
        Args:
            taxonomy_root: Root taxonomy directory
            library_names: List of library names to parse
            
        Returns:
            List of concept dictionaries
        """
        concepts = []
        
        for library_name in library_names:
            library_concepts = self._parse_single_library(
                taxonomy_root,
                library_name
            )
            concepts.extend(library_concepts)
        
        return concepts
    
    def _parse_single_library(
        self,
        taxonomy_root: Path,
        library_name: str
    ) -> List[Dict[str, Any]]:
        """
        Parse all XSD files from a single library.
        
        Args:
            taxonomy_root: Root taxonomy directory
            library_name: Library name to parse
            
        Returns:
            List of concept dictionaries from this library
        """
        library_dir = taxonomy_root / 'libraries' / library_name
        
        if not library_dir.exists():
            self.logger.debug(
                "Library directory not found: %s",
                str(library_dir)
            )
            return []
        
        xsd_files = list(library_dir.rglob('*.xsd'))
        concepts = []
        
        for xsd_file in xsd_files:
            file_concepts = self.xsd_parser.parse_xsd_file(
                xsd_file,
                library_name
            )
            concepts.extend(file_concepts)
        
        return concepts


__all__ = ['TaxonomyFilesystemLoader']