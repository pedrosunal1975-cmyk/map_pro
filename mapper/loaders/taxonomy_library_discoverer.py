# File: engines/mapper/loaders/taxonomy_library_discoverer.py
"""
Taxonomy Library Discoverer
============================

Discovers required taxonomy libraries from filing facts.

Responsibilities:
- Extract namespaces from parsed facts
- Map namespaces to library names
- Find existing library directories
- Provide intelligent library discovery
"""

from typing import Dict, Any, List, Set
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from .taxonomy_constants import (
    DEFAULT_LIBRARIES,
    NAMESPACE_TO_LIBRARY_MAP,
    LIBRARIES_DIR_NAME,
    CONCEPT_QNAME_SEPARATOR
)

logger = get_logger(__name__, 'engine')


class TaxonomyLibraryDiscoverer:
    """
    Discovers required taxonomy libraries from filing data.
    
    Attributes:
        logger: System logger instance
    """
    
    def __init__(self) -> None:
        """Initialize library discoverer."""
        self.logger = logger
    
    def discover_libraries(self, filing_id: str) -> List[str]:
        """
        Discover required libraries from filing's parsed facts.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            List of library names or defaults on failure
        """
        try:
            parsed_facts = self._load_parsed_facts(filing_id)
            namespaces = self._extract_namespaces(parsed_facts)
            library_names = self._map_namespaces_to_libraries(namespaces)
            existing_libs = self._find_existing_libraries(library_names)
            
            if existing_libs:
                self.logger.info(
                    "Discovered required libraries: %s",
                    existing_libs
                )
                return existing_libs
            
            return DEFAULT_LIBRARIES
            
        except Exception as error:
            self.logger.warning(
                "Library discovery failed: %s",
                str(error)
            )
            return DEFAULT_LIBRARIES
    
    def _load_parsed_facts(self, filing_id: str) -> List[Dict[str, Any]]:
        """
        Load parsed facts for a filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            List of fact dictionaries
            
        Raises:
            ImportError: If FactsLoader cannot be imported
            Exception: If facts cannot be loaded
        """
        # Import here to avoid circular dependency
        from .facts_loader import FactsLoader
        
        facts_loader = FactsLoader()
        parsed_facts, _ = facts_loader.load_parsed_facts(filing_id)
        return parsed_facts
    
    def _extract_namespaces(
        self,
        parsed_facts: List[Dict[str, Any]]
    ) -> Set[str]:
        """
        Extract namespace prefixes from parsed facts.
        
        Args:
            parsed_facts: List of fact dictionaries
            
        Returns:
            Set of namespace prefixes (e.g., {'us-gaap', 'dei'})
        """
        namespaces = set()
        
        for fact in parsed_facts:
            concept = fact.get('concept', '')
            if CONCEPT_QNAME_SEPARATOR in concept:
                prefix = concept.split(CONCEPT_QNAME_SEPARATOR, 1)[0].lower()
                namespaces.add(prefix)
        
        return namespaces
    
    def _map_namespaces_to_libraries(
        self,
        namespaces: Set[str]
    ) -> Set[str]:
        """
        Map namespace prefixes to library names.
        
        Args:
            namespaces: Set of namespace prefixes
            
        Returns:
            Set of library names (e.g., {'us-gaap', 'dei'})
        """
        library_names = set()
        
        for namespace in namespaces:
            for key, lib in NAMESPACE_TO_LIBRARY_MAP.items():
                if key in namespace:
                    library_names.add(lib)
                    break
        
        return library_names
    
    def _find_existing_libraries(
        self,
        library_names: Set[str]
    ) -> List[str]:
        """
        Find existing library directories on filesystem.
        
        Args:
            library_names: Set of library names
            
        Returns:
            List of existing library directory names
        """
        taxonomy_root = map_pro_paths.data_taxonomies / LIBRARIES_DIR_NAME
        
        if not taxonomy_root.exists():
            self.logger.debug(
                "Libraries directory not found: %s",
                str(taxonomy_root)
            )
            return []
        
        existing_libs = []
        
        for lib_name in library_names:
            matching_dirs = list(taxonomy_root.glob(f"{lib_name}-*"))
            if matching_dirs:
                existing_libs.extend([d.name for d in matching_dirs])
        
        return existing_libs


__all__ = ['TaxonomyLibraryDiscoverer']