# File: engines/mapper/loaders/taxonomy_loader.py
"""
Map Pro Taxonomy Loader
======================

Main coordinator for loading taxonomy concepts with hybrid database + filesystem approach.

Responsibilities:
- Coordinate taxonomy loading from multiple sources
- Provide fallback mechanisms
- Manage loading strategy
"""

from typing import Dict, Any, List, Optional

from core.system_logger import get_logger
from .taxonomy_database_loader import TaxonomyDatabaseLoader
from .taxonomy_filesystem_loader import TaxonomyFilesystemLoader
from .taxonomy_fallback_provider import TaxonomyFallbackProvider

logger = get_logger(__name__, 'engine')


class TaxonomyLoader:
    """
    Coordinates taxonomy concept loading using hybrid database + filesystem approach.
    
    Strategy:
    1. Try database first (fast)
    2. Fall back to XSD parsing (reliable)
    3. Use fallback concepts if all else fails
    
    Attributes:
        logger: System logger instance
        database_loader: Loader for database operations
        filesystem_loader: Loader for filesystem operations
        fallback_provider: Provider for fallback concepts
    """
    
    def __init__(
        self,
        database_loader: Optional[TaxonomyDatabaseLoader] = None,
        filesystem_loader: Optional[TaxonomyFilesystemLoader] = None,
        fallback_provider: Optional[TaxonomyFallbackProvider] = None
    ) -> None:
        """
        Initialize taxonomy loader with optional dependency injection.
        
        Args:
            database_loader: Optional database loader instance
            filesystem_loader: Optional filesystem loader instance
            fallback_provider: Optional fallback provider instance
        """
        self.logger = logger
        self.database_loader = database_loader or TaxonomyDatabaseLoader()
        self.filesystem_loader = filesystem_loader or TaxonomyFilesystemLoader()
        self.fallback_provider = fallback_provider or TaxonomyFallbackProvider()
    
    def load_taxonomy_concepts(
        self,
        filing_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load taxonomy concepts using multi-source strategy.
        
        Attempts to load from database first, then filesystem, finally fallback.
        
        Args:
            filing_id: Optional filing UUID for intelligent library discovery
            
        Returns:
            List of concept dictionaries with keys:
                - concept_qname: Qualified name (prefix:localname)
                - concept_local_name: Local name only
                - concept_namespace: Full namespace URI
                - concept_type: Type (monetary, string, etc.)
                - concept_label: Human-readable label
                - period_type: Period type (instant/duration)
                - balance_type: Balance type (debit/credit) or None
                - is_abstract: Whether concept is abstract
                - is_extension: Whether concept is an extension
        """
        concepts = self._try_database_lookup()
        if concepts:
            self.logger.info(
                "Loaded %d taxonomy concepts from database",
                len(concepts)
            )
            return concepts
        
        self.logger.warning("Database has no taxonomy concepts, scanning filesystem")
        concepts = self._try_filesystem_scan(filing_id)
        if concepts:
            self.logger.info(
                "Loaded %d taxonomy concepts from filesystem",
                len(concepts)
            )
            return concepts
        
        self.logger.warning("No taxonomy concepts found, using fallback")
        return self._use_fallback_concepts()
    
    def _try_database_lookup(self) -> List[Dict[str, Any]]:
        """
        Attempt to load taxonomy concepts from database.
        
        Returns:
            List of concept dictionaries or empty list on failure
        """
        return self.database_loader.load_from_database()
    
    def _try_filesystem_scan(self, filing_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Attempt to scan filesystem for taxonomy XSD files.
        
        Args:
            filing_id: Optional filing UUID for library discovery
            
        Returns:
            List of concept dictionaries or empty list on failure
        """
        return self.filesystem_loader.load_from_filesystem(filing_id)
    
    def _use_fallback_concepts(self) -> List[Dict[str, Any]]:
        """
        Retrieve fallback taxonomy concepts.
        
        Returns:
            List of essential concept dictionaries
        """
        return self.fallback_provider.get_fallback_concepts()


__all__ = ['TaxonomyLoader']