"""
File: engines/searcher/entity_statistics_updater.py
Path: engines/searcher/entity_statistics_updater.py

Entity Statistics Updater
=========================

Updates entity statistics based on associated filings.
Extracted from FilingSaver to follow Single Responsibility Principle.
"""

from typing import Optional

from core.system_logger import get_logger
from database.models.core_models import Entity, Filing

logger = get_logger(__name__, 'engine')


class EntityStatisticsUpdater:
    """
    Updates entity filing statistics.
    
    Responsibilities:
    - Update filing counts
    - Update last filing date
    - Query filing data efficiently
    """
    
    def __init__(self) -> None:
        """Initialize entity statistics updater."""
        logger.debug("Entity statistics updater initialized")
    
    def update_entity_statistics(
        self, 
        session, 
        entity: Entity
    ) -> None:
        """
        Update entity statistics based on filings.
        
        Args:
            session: Database session
            entity: Entity to update
        """
        self._update_filing_count(session, entity)
        self._update_last_filing_date(session, entity)
    
    def _update_filing_count(
        self, 
        session, 
        entity: Entity
    ) -> None:
        """
        Update total filings count for entity.
        
        Args:
            session: Database session
            entity: Entity to update
        """
        count = session.query(Filing).filter_by(
            entity_universal_id=entity.entity_universal_id
        ).count()
        
        if entity.total_filings_count != count:
            entity.total_filings_count = count
            logger.debug(
                f"Updated filing count for entity {entity.entity_universal_id}: {count}"
            )
    
    def _update_last_filing_date(
        self, 
        session, 
        entity: Entity
    ) -> None:
        """
        Update last filing date for entity.
        
        Args:
            session: Database session
            entity: Entity to update
        """
        latest_filing = self._get_latest_filing(session, entity)
        
        if latest_filing:
            if entity.last_filing_date != latest_filing.filing_date:
                entity.last_filing_date = latest_filing.filing_date
                logger.debug(
                    f"Updated last filing date for entity "
                    f"{entity.entity_universal_id}: {latest_filing.filing_date}"
                )
    
    def _get_latest_filing(
        self, 
        session, 
        entity: Entity
    ) -> Optional[Filing]:
        """
        Get most recent filing for entity.
        
        Args:
            session: Database session
            entity: Entity to query
            
        Returns:
            Latest filing or None
        """
        return session.query(Filing).filter_by(
            entity_universal_id=entity.entity_universal_id
        ).order_by(Filing.filing_date.desc()).first()