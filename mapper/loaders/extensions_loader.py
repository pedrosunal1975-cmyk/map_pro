# File: /map_pro/engines/mapper/loaders/extensions_loader.py

"""
Map Pro Extensions Loader
========================

Handles loading company-specific XBRL extension concepts.

Responsibilities:
- Orchestrate company extension loading workflow
- Coordinate between specialized components

This module has been refactored into:
- extensions_loader.py (this file) - Main orchestration
- extraction_directory_finder.py - Find extraction directories
- company_xsd_filter.py - Filter company XSD files
- company_xsd_parser.py - Parse company XSD files
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from core.system_logger import get_logger

from .extraction_directory_finder import ExtractionDirectoryFinder
from .company_xsd_filter import CompanyXSDFilter
from .company_xsd_parser import CompanyXSDParser

logger = get_logger(__name__, 'engine')


class ExtensionsLoader:
    """
    Loads company extension concepts from XSD files.
    
    Strategy:
    1. Find extraction directory (database then filesystem)
    2. Locate company XSD files (exclude standard taxonomies)
    3. Parse company concepts using ConceptResolver
    
    This class orchestrates the workflow by delegating to specialized components.
    """
    
    def __init__(
        self,
        directory_finder: Optional[ExtractionDirectoryFinder] = None,
        xsd_filter: Optional[CompanyXSDFilter] = None,
        xsd_parser: Optional[CompanyXSDParser] = None
    ):
        """
        Initialize extensions loader with optional dependencies.
        
        Args:
            directory_finder: Finder for extraction directories (created if None)
            xsd_filter: Filter for company XSD files (created if None)
            xsd_parser: Parser for company XSD files (created if None)
        """
        self.directory_finder = directory_finder or ExtractionDirectoryFinder()
        self.xsd_filter = xsd_filter or CompanyXSDFilter()
        self.xsd_parser = xsd_parser or CompanyXSDParser()
        self.logger = logger
    
    def load_company_extensions(self, filing_id: str) -> List[Dict[str, Any]]:
        """
        Load company extension concepts for a filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            List of company concept dictionaries (empty list on error)
        """
        try:
            extraction_dir = self._find_extraction_directory(filing_id)
            if not extraction_dir:
                return []
            
            company_xsd_files = self._find_company_xsd_files(extraction_dir)
            if not company_xsd_files:
                return []
            
            company_concepts = self._parse_company_concepts(company_xsd_files)
            
            self.logger.info(
                f"Loaded {len(company_concepts)} company extension concepts for {filing_id}"
            )
            return company_concepts
        
        except Exception as exception:
            self.logger.error(
                f"Error loading company extensions for {filing_id}: {exception}",
                exc_info=True
            )
            return []
    
    def _find_extraction_directory(self, filing_id: str) -> Optional[Path]:
        """
        Find extraction directory for filing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Path to extraction directory or None if not found
        """
        extraction_dir = self.directory_finder.find_extraction_directory(filing_id)
        
        if not extraction_dir or not extraction_dir.exists():
            self.logger.debug(f"No extraction directory found for {filing_id}")
            return None
        
        return extraction_dir
    
    def _find_company_xsd_files(self, extraction_dir: Path) -> List[Path]:
        """
        Find company XSD files in extraction directory.
        
        Args:
            extraction_dir: Path to extraction directory
            
        Returns:
            List of company XSD file paths (empty if none found)
        """
        company_xsd_files = self.xsd_filter.filter_company_xsd_files(extraction_dir)
        
        if not company_xsd_files:
            self.logger.debug(f"No company extension files found in {extraction_dir}")
            return []
        
        self.logger.info(
            f"Found {len(company_xsd_files)} company extension files in {extraction_dir}"
        )
        return company_xsd_files
    
    def _parse_company_concepts(self, xsd_files: List[Path]) -> List[Dict[str, Any]]:
        """
        Parse company concepts from XSD files.
        
        Args:
            xsd_files: List of XSD file paths
            
        Returns:
            List of concept dictionaries
        """
        return self.xsd_parser.parse_company_xsd_files(xsd_files)


__all__ = ['ExtensionsLoader']