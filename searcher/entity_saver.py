"""
File: engines/searcher/entity_saver.py
Path: engines/searcher/entity_saver.py

Entity Database Saver
====================

Handles saving and updating entity records in the database.
Extracted from SearchResultsProcessor to follow Single Responsibility Principle.
"""

import uuid as uuid_module
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from core.system_logger import get_logger
from database.models.core_models import Entity
from shared.exceptions.custom_exceptions import DatabaseError
from engines.searcher.search_constants import (
    ENTITY_STATUS_ACTIVE,
    FIELD_MARKET_ENTITY_ID,
    FIELD_NAME,
    FIELD_TICKER,
    FIELD_STATUS,
    FIELD_IDENTIFIERS,
    FIELD_DISCOVERED_AT,
    FIELD_SOURCE_URL
)
from engines.searcher.entity_updater import EntityUpdater

logger = get_logger(__name__, 'engine')


class EntitySaver:
    """
    Saves entity records to database.
    
    Responsibilities:
    - Create new entity records
    - Check for existing entities
    - Delegate updates to EntityUpdater
    - Handle database transactions
    """
    
    def __init__(
        self, 
        db_coordinator,
        path_generator,
        validator
    ) -> None:
        """
        Initialize entity saver.
        
        Args:
            db_coordinator: Database coordinator instance
            path_generator: Path generator instance
            validator: Data validator instance
        """
        self.db_coordinator = db_coordinator
        self.path_generator = path_generator
        self.validator = validator
        self.entity_updater = EntityUpdater()
        
        logger.debug("Entity saver initialized")
    
    async def save(
        self, 
        company_info: Dict[str, Any], 
        market_type: str
    ) -> str:
        """
        Save entity to core database.
        
        Args:
            company_info: Standardized company information
            market_type: Market type identifier
            
        Returns:
            Entity universal ID (UUID as string)
            
        Raises:
            DatabaseError: If save operation fails
        """
        try:
            with self.db_coordinator.get_session('core') as session:
                existing_entity = self._find_existing_entity(
                    session, 
                    market_type, 
                    company_info[FIELD_MARKET_ENTITY_ID]
                )
                
                if existing_entity:
                    return self._handle_existing_entity(
                        session, 
                        existing_entity, 
                        company_info
                    )
                
                return self._create_new_entity(
                    session, 
                    company_info, 
                    market_type
                )
                
        except IntegrityError as e:
            logger.error(f"Entity integrity error: {e}")
            raise DatabaseError(
                "Failed to save entity: duplicate or constraint violation"
            )
        except Exception as e:
            logger.error(f"Failed to save entity: {e}")
            raise DatabaseError(f"Failed to save entity: {str(e)}")
    
    def _find_existing_entity(
        self, 
        session, 
        market_type: str, 
        market_entity_id: str
    ) -> Optional[Entity]:
        """
        Find existing entity by market identifiers.
        
        Args:
            session: Database session
            market_type: Market type
            market_entity_id: Market-specific entity ID
            
        Returns:
            Existing entity or None
        """
        return session.query(Entity).filter_by(
            market_type=market_type,
            market_entity_id=market_entity_id
        ).first()
    
    def _handle_existing_entity(
        self, 
        session, 
        existing_entity: Entity, 
        company_info: Dict[str, Any]
    ) -> str:
        """
        Handle update of existing entity.
        
        Args:
            session: Database session
            existing_entity: Existing entity record
            company_info: New company information
            
        Returns:
            Entity universal ID (UUID as string)
        """
        logger.info(
            f"Entity already exists: {existing_entity.entity_universal_id}"
        )
        
        updated = self.entity_updater.update_if_changed(
            existing_entity, 
            company_info
        )
        
        if updated:
            session.commit()
            logger.info(
                f"Updated entity: {existing_entity.entity_universal_id}"
            )
        
        return str(existing_entity.entity_universal_id)
    
    def _create_new_entity(
        self, 
        session, 
        company_info: Dict[str, Any], 
        market_type: str
    ) -> str:
        """
        Create new entity record.
        
        Args:
            session: Database session
            company_info: Company information
            market_type: Market type
            
        Returns:
            Entity universal ID (UUID as string)
        """
        entity = self._build_entity_record(company_info, market_type)
        
        session.add(entity)
        session.commit()
        
        logger.info(
            f"Created new entity: {entity.entity_universal_id} "
            f"({company_info[FIELD_NAME]})"
        )
        
        return str(entity.entity_universal_id)
    
    def _build_entity_record(
        self, 
        company_info: Dict[str, Any], 
        market_type: str
    ) -> Entity:
        """
        Build entity record from company information.
        
        Args:
            company_info: Company information
            market_type: Market type
            
        Returns:
            Entity instance
        """
        entity_id = uuid_module.uuid4()
        
        return Entity(
            entity_universal_id=entity_id,
            market_type=market_type,
            market_entity_id=company_info[FIELD_MARKET_ENTITY_ID],
            primary_name=company_info[FIELD_NAME],
            ticker_symbol=company_info.get(FIELD_TICKER),
            entity_status=company_info.get(FIELD_STATUS, ENTITY_STATUS_ACTIVE),
            data_directory_path=self.path_generator.generate_entity_path(
                market_type, 
                company_info[FIELD_NAME]
            ),
            identifiers=company_info.get(FIELD_IDENTIFIERS),
            search_history=self._build_search_history(company_info)
        )
    
    def _build_search_history(
        self, 
        company_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build search history metadata.
        
        Args:
            company_info: Company information
            
        Returns:
            Search history dictionary
        """
        discovered_at = company_info.get(FIELD_DISCOVERED_AT)
        if discovered_at is None:
            discovered_at = datetime.now(timezone.utc)
        
        if isinstance(discovered_at, datetime):
            discovered_at = discovered_at.isoformat()
        
        return {
            'discovered_at': discovered_at,
            'source_url': company_info.get(FIELD_SOURCE_URL)
        }