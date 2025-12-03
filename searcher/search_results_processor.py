"""
File: engines/searcher/search_results_processor.py
Path: engines/searcher/search_results_processor.py

Map Pro Search Results Processor
================================

Processes and saves search results to the core database.
Handles entity and filing record creation with proper data validation.

Architecture: Specialized component for database operations without search logic.
"""

import uuid as uuid_module
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.core_models import Entity, Filing
from shared.exceptions.custom_exceptions import DatabaseError
from engines.searcher.search_constants import (
    ENTITY_STATUS_ACTIVE,
    MAX_COMPANY_NAME_LENGTH,
    MAX_FILING_ID_LENGTH
)
from engines.searcher.entity_saver import EntitySaver
from engines.searcher.filing_saver import FilingSaver
from engines.searcher.data_validator import SearchDataValidator
from engines.searcher.path_generator import DataPathGenerator

logger = get_logger(__name__, 'engine')


class SearchResultsProcessor:
    """
    Processes and saves search results to database.
    
    Responsibilities:
    - Coordinate entity and filing save operations
    - Delegate to specialized savers
    - Provide high-level save interface
    
    Does NOT handle:
    - Search operations (company_discovery/filing_identification handle this)
    - Market-specific logic (market plugins handle this)
    - File downloading (downloader engine handles this)
    """
    
    def __init__(self) -> None:
        """Initialize search results processor with specialized components."""
        self.entity_saver = EntitySaver(
            db_coordinator=db_coordinator,
            path_generator=DataPathGenerator(),
            validator=SearchDataValidator()
        )
        self.filing_saver = FilingSaver(
            db_coordinator=db_coordinator,
            path_generator=DataPathGenerator(),
            validator=SearchDataValidator()
        )
        self.validator = SearchDataValidator()
        
        logger.info("Search results processor initialized with specialized components")
    
    async def save_entity(
        self, 
        company_info: Dict[str, Any], 
        market_type: str
    ) -> str:
        """
        Save entity to core database.
        
        Args:
            company_info: Standardized company information containing:
                - market_entity_id: Market-specific entity identifier (required)
                - name: Company name (required)
                - ticker: Stock ticker symbol (optional)
                - status: Entity status (optional, defaults to 'active')
                - identifiers: Additional identifiers (optional)
                - discovered_at: Discovery timestamp (optional)
                - source_url: Source URL (optional)
            market_type: Market type identifier (e.g., 'sec', 'fca', 'esma')
            
        Returns:
            Entity universal ID (UUID as string)
            
        Raises:
            DatabaseError: If save operation fails
            ValueError: If company_info or market_type validation fails
        """
        if not isinstance(company_info, dict):
            raise ValueError("company_info must be a dictionary")
        
        if not isinstance(market_type, str) or not market_type.strip():
            raise ValueError("market_type must be a non-empty string")
        
        if not self.validator.validate_company_info(company_info):
            raise ValueError("Invalid company information")
        
        return await self.entity_saver.save(company_info, market_type)
    
    async def save_filings(
        self, 
        entity_id: str, 
        filings_info: List[Dict[str, Any]],
        market_type: str
    ) -> List[str]:
        """
        Save filing records to core database.
        
        Args:
            entity_id: Entity universal ID (UUID string)
            filings_info: List of standardized filing information, each containing:
                - market_filing_id: Market-specific filing identifier (required)
                - filing_type: Type of filing (required)
                - filing_date: Date of filing (required)
                - period_start_date: Reporting period start (optional)
                - period_end_date: Reporting period end (optional)
                - filing_title: Filing title (optional)
                - download_url or url: Filing URL (optional)
            market_type: Market type identifier
            
        Returns:
            List of filing universal IDs (UUIDs as strings)
            
        Raises:
            DatabaseError: If save operation fails
            ValueError: If validation fails
        """
        if not isinstance(entity_id, str) or not entity_id.strip():
            raise ValueError("entity_id must be a non-empty string")
        
        if not isinstance(filings_info, list):
            raise ValueError("filings_info must be a list")
        
        if not isinstance(market_type, str) or not market_type.strip():
            raise ValueError("market_type must be a non-empty string")
        
        # Validate each filing
        for filing_info in filings_info:
            if not self.validator.validate_filing_info(filing_info):
                logger.warning(f"Skipping invalid filing: {filing_info.get('market_filing_id')}")
        
        return await self.filing_saver.save_batch(entity_id, filings_info, market_type)
    
    def validate_company_info(self, company_info: Dict[str, Any]) -> bool:
        """
        Validate company information before saving.
        
        Args:
            company_info: Company information to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self.validator.validate_company_info(company_info)
    
    def validate_filing_info(self, filing_info: Dict[str, Any]) -> bool:
        """
        Validate filing information before saving.
        
        Args:
            filing_info: Filing information to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self.validator.validate_filing_info(filing_info)


__all__ = ['SearchResultsProcessor']