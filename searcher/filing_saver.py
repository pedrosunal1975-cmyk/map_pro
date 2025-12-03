"""
File: engines/searcher/filing_saver.py
Path: engines/searcher/filing_saver.py

Filing Database Saver
====================

Handles saving filing records to the database.
Extracted from SearchResultsProcessor to follow Single Responsibility Principle.
"""

import uuid as uuid_module
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger
from database.models.core_models import Entity, Filing
from shared.exceptions.custom_exceptions import DatabaseError
from engines.searcher.search_constants import (
    FILING_STATUS_PENDING,
    FIELD_MARKET_FILING_ID,
    FIELD_FILING_TYPE,
    FIELD_FILING_DATE,
    FIELD_PERIOD_START_DATE,
    FIELD_PERIOD_END_DATE,
    FIELD_FILING_TITLE,
    FIELD_DOWNLOAD_URL,
    FIELD_URL
)
from engines.searcher.entity_statistics_updater import EntityStatisticsUpdater

logger = get_logger(__name__, 'engine')


class FilingSaver:
    """
    Saves filing records to database.
    
    Responsibilities:
    - Create new filing records
    - Check for existing filings
    - Update filing URLs if changed
    - Handle batch saves
    - Update entity statistics
    """
    
    def __init__(
        self, 
        db_coordinator,
        path_generator,
        validator
    ) -> None:
        """
        Initialize filing saver.
        
        Args:
            db_coordinator: Database coordinator instance
            path_generator: Path generator instance
            validator: Data validator instance
        """
        self.db_coordinator = db_coordinator
        self.path_generator = path_generator
        self.validator = validator
        self.statistics_updater = EntityStatisticsUpdater()
        
        logger.debug("Filing saver initialized")
    
    async def save_batch(
        self, 
        entity_id: str, 
        filings_info: List[Dict[str, Any]],
        market_type: str
    ) -> List[str]:
        """
        Save multiple filing records to core database.
        
        Args:
            entity_id: Entity universal ID
            filings_info: List of standardized filing information
            market_type: Market type identifier
            
        Returns:
            List of filing universal IDs (UUIDs as strings)
            
        Raises:
            DatabaseError: If save operation fails
        """
        try:
            with self.db_coordinator.get_session('core') as session:
                entity = self._verify_entity_exists(session, entity_id)
                
                saved_filing_ids = self._save_filings(
                    session, 
                    entity, 
                    filings_info
                )
                
                self.statistics_updater.update_entity_statistics(
                    session, 
                    entity
                )
                
                session.commit()
                
                logger.info(
                    f"Saved {len(saved_filing_ids)} filings for entity {entity_id}"
                )
                
                return saved_filing_ids
                
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to save filings: {e}")
            raise DatabaseError(f"Failed to save filings: {str(e)}")
    
    def _verify_entity_exists(self, session, entity_id: str) -> Entity:
        """
        Verify that entity exists in database.
        
        Args:
            session: Database session
            entity_id: Entity universal ID
            
        Returns:
            Entity instance
            
        Raises:
            DatabaseError: If entity not found
        """
        entity = session.query(Entity).filter_by(
            entity_universal_id=entity_id
        ).first()
        
        if not entity:
            raise DatabaseError(f"Entity not found: {entity_id}")
        
        return entity
    
    def _save_filings(
        self, 
        session, 
        entity: Entity, 
        filings_info: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Save individual filings from list.
        
        Args:
            session: Database session
            entity: Entity record
            filings_info: List of filing information
            
        Returns:
            List of saved filing IDs
        """
        saved_filing_ids = []
        
        for filing_info in filings_info:
            try:
                if not self.validator.validate_filing_info(filing_info):
                    logger.warning(
                        f"Skipping invalid filing: {filing_info.get(FIELD_MARKET_FILING_ID)}"
                    )
                    continue
                
                filing_id = self._save_single_filing(
                    session, 
                    entity, 
                    filing_info
                )
                
                if filing_id:
                    saved_filing_ids.append(filing_id)
                    
            except Exception as e:
                logger.warning(
                    f"Failed to save individual filing "
                    f"{filing_info.get(FIELD_MARKET_FILING_ID)}: {e}"
                )
                continue
        
        return saved_filing_ids
    
    def _save_single_filing(
        self, 
        session, 
        entity: Entity, 
        filing_info: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save or update a single filing record.
        
        Args:
            session: Database session
            entity: Entity record
            filing_info: Filing information
            
        Returns:
            Filing universal ID or None
        """
        existing_filing = self._find_existing_filing(
            session, 
            entity.entity_universal_id, 
            filing_info[FIELD_MARKET_FILING_ID]
        )
        
        if existing_filing:
            return self._handle_existing_filing(
                existing_filing, 
                filing_info
            )
        
        return self._create_new_filing(
            session, 
            entity, 
            filing_info
        )
    
    def _find_existing_filing(
        self, 
        session, 
        entity_id: str, 
        market_filing_id: str
    ) -> Optional[Filing]:
        """
        Find existing filing by identifiers.
        
        Args:
            session: Database session
            entity_id: Entity universal ID
            market_filing_id: Market-specific filing ID
            
        Returns:
            Existing filing or None
        """
        return session.query(Filing).filter_by(
            entity_universal_id=entity_id,
            market_filing_id=market_filing_id
        ).first()
    
    def _handle_existing_filing(
        self, 
        existing_filing: Filing, 
        filing_info: Dict[str, Any]
    ) -> str:
        """
        Handle existing filing (update URL if changed).
        
        Args:
            existing_filing: Existing filing record
            filing_info: New filing information
            
        Returns:
            Filing universal ID (UUID as string)
        """
        new_url = self._extract_filing_url(filing_info)
        
        if new_url and existing_filing.original_url != new_url:
            existing_filing.original_url = new_url
            logger.info(
                f"Updated URL for filing {existing_filing.filing_universal_id}"
            )
        else:
            logger.debug(
                f"Filing already exists: {existing_filing.filing_universal_id}"
            )
        
        return str(existing_filing.filing_universal_id)
    
    def _create_new_filing(
        self, 
        session, 
        entity: Entity, 
        filing_info: Dict[str, Any]
    ) -> str:
        """
        Create new filing record.
        
        Args:
            session: Database session
            entity: Entity record
            filing_info: Filing information
            
        Returns:
            Filing universal ID (UUID as string)
        """
        filing = self._build_filing_record(entity, filing_info)
        
        session.add(filing)
        
        logger.debug(
            f"Created new filing: {filing.filing_universal_id} "
            f"({filing_info[FIELD_FILING_TYPE]})"
        )
        
        return str(filing.filing_universal_id)
    
    def _build_filing_record(
        self, 
        entity: Entity, 
        filing_info: Dict[str, Any]
    ) -> Filing:
        """
        Build filing record from information.
        
        Args:
            entity: Entity record
            filing_info: Filing information
            
        Returns:
            Filing instance
        """
        filing_id = uuid_module.uuid4()
        
        return Filing(
            filing_universal_id=filing_id,
            entity_universal_id=entity.entity_universal_id,
            market_filing_id=filing_info[FIELD_MARKET_FILING_ID],
            filing_type=filing_info[FIELD_FILING_TYPE],
            filing_date=filing_info[FIELD_FILING_DATE],
            period_start_date=filing_info.get(FIELD_PERIOD_START_DATE),
            period_end_date=filing_info.get(FIELD_PERIOD_END_DATE),
            filing_title=filing_info.get(FIELD_FILING_TITLE),
            download_status=FILING_STATUS_PENDING,
            extraction_status=FILING_STATUS_PENDING,
            original_url=self._extract_filing_url(filing_info),
            filing_directory_path=self.path_generator.generate_filing_path(
                entity.data_directory_path,
                filing_info[FIELD_FILING_TYPE],
                filing_info[FIELD_MARKET_FILING_ID]
            )
        )
    
    def _extract_filing_url(self, filing_info: Dict[str, Any]) -> Optional[str]:
        """
        Extract filing URL from information.
        
        Args:
            filing_info: Filing information
            
        Returns:
            Filing URL or None
        """
        return filing_info.get(FIELD_DOWNLOAD_URL) or filing_info.get(FIELD_URL)