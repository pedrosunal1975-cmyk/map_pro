# File: /map_pro/engines/mapper/loaders/extraction_directory_finder.py

"""
Extraction Directory Finder
===========================

Finds extraction directories for filings using hybrid approach:
1. Database lookup (fast, preferred)
2. Filesystem scan (fallback)
"""

from typing import Optional
from pathlib import Path

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.core_models import Filing

logger = get_logger(__name__, 'engine')

# Constants
EXTRACTED_DIR_NAME = 'extracted'


class ExtractionDirectoryFinder:
    """
    Finds extraction directories for filings.
    
    Responsibilities:
    - Query database for filing directory path
    - Fall back to filesystem scanning
    - Validate directory existence
    """
    
    def __init__(self):
        """Initialize extraction directory finder."""
        self.logger = logger
    
    def find_extraction_directory(self, filing_id: str) -> Optional[Path]:
        """
        Find extraction directory using hybrid approach.
        
        Strategy:
        1. Try database lookup first (fast)
        2. Fall back to filesystem scan if database fails
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Path to extraction directory or None if not found
        """
        extraction_dir = self._find_via_database(filing_id)
        if extraction_dir and extraction_dir.exists():
            return extraction_dir
        
        self.logger.debug(
            f"Database lookup failed for {filing_id}, scanning filesystem"
        )
        return self._find_via_filesystem_scan(filing_id)
    
    def _find_via_database(self, filing_id: str) -> Optional[Path]:
        """
        Find extraction directory via database lookup.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Path to extraction directory or None if lookup fails
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter(
                    Filing.filing_universal_id == filing_id
                ).first()
                
                if not filing:
                    self.logger.debug(f"No filing found with ID {filing_id}")
                    return None
                
                if not filing.filing_directory_path:
                    self.logger.debug(f"Filing {filing_id} has no directory path")
                    return None
                
                extraction_dir = (
                    map_pro_paths.data_root / 
                    filing.filing_directory_path / 
                    EXTRACTED_DIR_NAME
                )
                
                return extraction_dir
                
        except Exception as exception:
            self.logger.debug(
                f"Database filing lookup failed for {filing_id}: {exception}"
            )
            return None
    
    def _find_via_filesystem_scan(self, filing_id: str) -> Optional[Path]:
        """
        Find extraction directory by scanning filesystem.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Path to extraction directory or None if not found
        """
        try:
            search_root = map_pro_paths.data_entities
            
            if not search_root.exists():
                self.logger.debug(f"Entities directory missing: {search_root}")
                return None
            
            for extracted_dir in search_root.rglob(EXTRACTED_DIR_NAME):
                if not extracted_dir.is_dir():
                    continue
                
                if self._directory_contains_filing(extracted_dir, filing_id):
                    self.logger.info(f"Found extraction directory: {extracted_dir}")
                    return extracted_dir
            
            self.logger.debug(f"No extraction directory found for {filing_id}")
            return None
            
        except Exception as exception:
            self.logger.error(
                f"Filesystem extraction scan failed for {filing_id}: {exception}",
                exc_info=True
            )
            return None
    
    def _directory_contains_filing(self, directory: Path, filing_id: str) -> bool:
        """
        Check if directory contains files for this filing.
        
        Args:
            directory: Directory to check
            filing_id: Filing UUID to search for
            
        Returns:
            True if filing files found, False otherwise
        """
        try:
            for file_path in directory.iterdir():
                if filing_id in file_path.name:
                    return True
        except (OSError, PermissionError) as exception:
            self.logger.debug(
                f"Cannot read directory {directory}: {exception}"
            )
        
        return False


__all__ = ['ExtractionDirectoryFinder']