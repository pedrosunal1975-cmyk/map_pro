# File: engines/mapper/loaders/taxonomy_database_loader.py
"""
Taxonomy Database Loader
========================

Handles loading taxonomy concepts from database.

Responsibilities:
- Query taxonomy concepts from database
- Convert database models to concept dictionaries
- Handle database errors gracefully
"""

from typing import Dict, Any, List

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.library_models import TaxonomyConcept
from .taxonomy_constants import DEFAULT_LIBRARY_STATUS

logger = get_logger(__name__, 'engine')


class TaxonomyDatabaseLoader:
    """
    Loads taxonomy concepts from database.
    
    Attributes:
        logger: System logger instance
    """
    
    def __init__(self) -> None:
        """Initialize database loader."""
        self.logger = logger
    
    def load_from_database(self) -> List[Dict[str, Any]]:
        """
        Load taxonomy concepts from database.
        
        Queries all active taxonomy concepts from the library database.
        
        Returns:
            List of concept dictionaries or empty list on failure
            
        Raises:
            No exceptions raised - errors are caught and logged
        """
        try:
            with db_coordinator.get_session('library') as session:
                taxonomy_concepts = self._query_active_concepts(session)
                concepts = [
                    self._convert_concept_to_dict(concept)
                    for concept in taxonomy_concepts
                ]
                
                if concepts:
                    self.logger.debug(
                        "Successfully loaded %d concepts from database",
                        len(concepts)
                    )
                
                return concepts
                
        except Exception as error:
            self.logger.warning(
                "Database taxonomy lookup failed: %s",
                str(error)
            )
            return []
    
    def _query_active_concepts(self, session) -> List[TaxonomyConcept]:
        """
        Query active taxonomy concepts from database session.
        
        Args:
            session: SQLAlchemy database session
            
        Returns:
            List of TaxonomyConcept database objects
        """
        return session.query(TaxonomyConcept).join(
            TaxonomyConcept.library
        ).filter(
            TaxonomyConcept.library.has(library_status=DEFAULT_LIBRARY_STATUS)
        ).all()
    
    def _convert_concept_to_dict(
        self,
        concept: TaxonomyConcept
    ) -> Dict[str, Any]:
        """
        Convert database concept to dictionary format.
        
        Args:
            concept: TaxonomyConcept database object
            
        Returns:
            Concept dictionary with standardized keys
        """
        return {
            'concept_qname': concept.concept_qname,
            'concept_local_name': concept.concept_local_name,
            'concept_namespace': concept.concept_namespace,
            'concept_type': concept.concept_type,
            'concept_label': concept.concept_label,
            'period_type': concept.period_type,
            'balance_type': concept.balance_type,
            'is_abstract': concept.abstract_concept,
            'is_extension': False
        }


__all__ = ['TaxonomyDatabaseLoader']