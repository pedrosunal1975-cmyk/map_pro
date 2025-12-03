"""
File: engines/searcher/path_generator.py
Path: engines/searcher/path_generator.py

Data Path Generator
==================

Generates filesystem paths for entities and filings.
Extracted from SearchResultsProcessor to follow Single Responsibility Principle.
"""

from typing import Optional
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from engines.searcher.search_constants import (
    MAX_CLEAN_NAME_LENGTH,
    MAX_FILING_ID_LENGTH,
    PATH_SEPARATOR,
    FILING_SUBDIRECTORY,
    PATH_INVALID_CHARS,
    PATH_REPLACEMENT_CHAR,
    PATH_SPACE_REPLACEMENT
)

logger = get_logger(__name__, 'engine')


class DataPathGenerator:
    """
    Generates filesystem paths for data storage.
    
    Responsibilities:
    - Generate entity data directory paths
    - Generate filing directory paths
    - Sanitize names for filesystem use
    - Ensure path portability
    """
    
    def __init__(self) -> None:
        """Initialize data path generator."""
        logger.debug("Data path generator initialized")
    
    def generate_entity_path(
        self, 
        market_type: str, 
        company_name: str
    ) -> str:
        """
        Generate data directory path for entity.
        
        Args:
            market_type: Market type identifier
            company_name: Company name
            
        Returns:
            Relative path string for database storage
        """
        clean_name = self._sanitize_name_for_path(
            company_name, 
            MAX_CLEAN_NAME_LENGTH
        )
        
        full_path = map_pro_paths.get_entity_data_path(market_type, clean_name)
        
        relative_path = self._make_relative_path(full_path)
        
        return str(relative_path)
    
    def generate_filing_path(
        self, 
        entity_path: str, 
        filing_type: str,
        filing_id: str
    ) -> str:
        """
        Generate filing directory path.
        
        Args:
            entity_path: Entity data directory path (relative)
            filing_type: Filing type
            filing_id: Market filing ID
            
        Returns:
            Relative path string for database storage
        """
        clean_type = self._sanitize_name_for_path(filing_type)
        clean_id = self._sanitize_name_for_path(filing_id, MAX_FILING_ID_LENGTH)
        
        path_parts = [
            entity_path,
            FILING_SUBDIRECTORY,
            clean_type,
            clean_id
        ]
        
        return PATH_SEPARATOR.join(path_parts)
    
    def _sanitize_name_for_path(
        self, 
        name: str, 
        max_length: Optional[int] = None
    ) -> str:
        """
        Sanitize name for use in filesystem paths.
        
        Args:
            name: Name to sanitize
            max_length: Maximum length (optional)
            
        Returns:
            Sanitized name safe for filesystem use
        """
        # Strip whitespace
        clean = name.strip()
        
        # Replace invalid characters
        clean = self._replace_invalid_chars(clean)
        
        # Replace spaces with underscores
        clean = clean.replace(' ', PATH_SPACE_REPLACEMENT)
        
        # Limit length if specified
        if max_length:
            clean = clean[:max_length]
        
        # Remove trailing separators/underscores
        clean = clean.rstrip(PATH_REPLACEMENT_CHAR + PATH_SEPARATOR)
        
        return clean
    
    def _replace_invalid_chars(self, name: str) -> str:
        """
        Replace invalid filesystem characters.
        
        Args:
            name: Name to process
            
        Returns:
            Name with invalid chars replaced
        """
        clean = name
        
        for invalid_char in PATH_INVALID_CHARS:
            clean = clean.replace(invalid_char, PATH_REPLACEMENT_CHAR)
        
        return clean
    
    def _make_relative_path(self, full_path: Path) -> Path:
        """
        Convert full path to relative path for database storage.
        
        Args:
            full_path: Full absolute path
            
        Returns:
            Relative path from data root
        """
        try:
            return full_path.relative_to(map_pro_paths.data_root)
        except ValueError as e:
            logger.warning(
                f"Could not make path relative to data root: {e}. "
                f"Using path as-is."
            )
            return full_path