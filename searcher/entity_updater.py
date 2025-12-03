"""
File: engines/searcher/entity_updater.py
Path: engines/searcher/entity_updater.py

Entity Record Updater
====================

Handles updating existing entity records with new information.
Extracted from EntitySaver to follow Single Responsibility Principle.
"""

from typing import Dict, Any
from datetime import datetime, timezone

from core.system_logger import get_logger
from database.models.core_models import Entity
from engines.searcher.search_constants import (
    FIELD_NAME,
    FIELD_TICKER,
    FIELD_STATUS,
    FIELD_IDENTIFIERS,
    ENTITY_STATUS_ACTIVE
)

logger = get_logger(__name__, 'engine')


class EntityUpdater:
    """
    Updates existing entity records.
    
    Responsibilities:
    - Compare entity fields with new information
    - Update changed fields
    - Track update timestamps
    """
    
    def __init__(self) -> None:
        """Initialize entity updater."""
        logger.debug("Entity updater initialized")
    
    def update_if_changed(
        self, 
        entity: Entity, 
        company_info: Dict[str, Any]
    ) -> bool:
        """
        Update entity if information has changed.
        
        Args:
            entity: Existing entity record
            company_info: New company information
            
        Returns:
            True if entity was updated, False otherwise
        """
        updated = False
        
        updated |= self._update_name(entity, company_info)
        updated |= self._update_ticker(entity, company_info)
        updated |= self._update_status(entity, company_info)
        updated |= self._update_identifiers(entity, company_info)
        
        if updated:
            self._update_timestamp(entity)
        
        return updated
    
    def _update_name(
        self, 
        entity: Entity, 
        company_info: Dict[str, Any]
    ) -> bool:
        """
        Update entity name if changed.
        
        Args:
            entity: Entity to update
            company_info: New company information
            
        Returns:
            True if updated
        """
        new_name = company_info.get(FIELD_NAME)
        
        if new_name and new_name != entity.primary_name:
            logger.debug(
                f"Updating entity name from '{entity.primary_name}' to '{new_name}'"
            )
            entity.primary_name = new_name
            return True
        
        return False
    
    def _update_ticker(
        self, 
        entity: Entity, 
        company_info: Dict[str, Any]
    ) -> bool:
        """
        Update ticker symbol if changed.
        
        Args:
            entity: Entity to update
            company_info: New company information
            
        Returns:
            True if updated
        """
        new_ticker = company_info.get(FIELD_TICKER)
        
        if new_ticker and new_ticker != entity.ticker_symbol:
            logger.debug(
                f"Updating entity ticker from '{entity.ticker_symbol}' to '{new_ticker}'"
            )
            entity.ticker_symbol = new_ticker
            return True
        
        return False
    
    def _update_status(
        self, 
        entity: Entity, 
        company_info: Dict[str, Any]
    ) -> bool:
        """
        Update entity status if changed.
        
        Args:
            entity: Entity to update
            company_info: New company information
            
        Returns:
            True if updated
        """
        new_status = company_info.get(FIELD_STATUS, ENTITY_STATUS_ACTIVE)
        
        if new_status != entity.entity_status:
            logger.debug(
                f"Updating entity status from '{entity.entity_status}' to '{new_status}'"
            )
            entity.entity_status = new_status
            return True
        
        return False
    
    def _update_identifiers(
        self, 
        entity: Entity, 
        company_info: Dict[str, Any]
    ) -> bool:
        """
        Update entity identifiers if changed.
        
        Args:
            entity: Entity to update
            company_info: New company information
            
        Returns:
            True if updated
        """
        new_identifiers = company_info.get(FIELD_IDENTIFIERS)
        
        if new_identifiers and new_identifiers != entity.identifiers:
            logger.debug("Updating entity identifiers")
            entity.identifiers = new_identifiers
            return True
        
        return False
    
    def _update_timestamp(self, entity: Entity) -> None:
        """
        Update entity's last updated timestamp.
        
        Args:
            entity: Entity to update
        """
        entity.updated_at = datetime.now(timezone.utc)