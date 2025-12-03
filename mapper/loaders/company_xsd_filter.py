# File: /map_pro/engines/mapper/loaders/company_xsd_filter.py

"""
Company XSD Filter
==================

Filters XSD files to identify company-specific extensions.
Excludes standard taxonomy files (US-GAAP, DEI, SRT, IFRS).
"""

from typing import List
from pathlib import Path

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')

# Constants for standard taxonomies
STANDARD_TAXONOMIES = frozenset([
    'us-gaap',
    'dei',
    'srt',
    'ifrs'
])

XSD_FILE_EXTENSION = '.xsd'


class CompanyXSDFilter:
    """
    Filters XSD files to find company extensions.
    
    Responsibilities:
    - Find all XSD files in directory
    - Filter out standard taxonomy files
    - Return only company-specific XSD files
    """
    
    def __init__(self, standard_taxonomies: frozenset = STANDARD_TAXONOMIES):
        """
        Initialize XSD filter.
        
        Args:
            standard_taxonomies: Set of standard taxonomy identifiers to exclude
        """
        self.standard_taxonomies = standard_taxonomies
        self.logger = logger
    
    def filter_company_xsd_files(self, extraction_dir: Path) -> List[Path]:
        """
        Find company XSD files (exclude standard taxonomies).
        
        Args:
            extraction_dir: Directory containing extracted files
            
        Returns:
            List of company XSD file paths (empty if none found)
        """
        all_xsd_files = self._find_all_xsd_files(extraction_dir)
        
        if not all_xsd_files:
            self.logger.debug(f"No XSD files found in {extraction_dir}")
            return []
        
        company_xsd_files = [
            xsd_file for xsd_file in all_xsd_files
            if not self._is_standard_taxonomy_file(xsd_file)
        ]
        
        if company_xsd_files:
            self.logger.debug(
                f"Filtered {len(company_xsd_files)} company files from "
                f"{len(all_xsd_files)} total XSD files"
            )
        
        return company_xsd_files
    
    def _find_all_xsd_files(self, extraction_dir: Path) -> List[Path]:
        """
        Find all XSD files in directory.
        
        Args:
            extraction_dir: Directory to search
            
        Returns:
            List of all XSD file paths
        """
        try:
            xsd_pattern = f'*{XSD_FILE_EXTENSION}'
            return list(extraction_dir.glob(xsd_pattern))
        except (OSError, PermissionError) as exception:
            self.logger.error(
                f"Cannot read directory {extraction_dir}: {exception}",
                exc_info=True
            )
            return []
    
    def _is_standard_taxonomy_file(self, xsd_file: Path) -> bool:
        """
        Check if XSD file is a standard taxonomy.
        
        Args:
            xsd_file: Path to XSD file
            
        Returns:
            True if standard taxonomy file, False if company extension
        """
        filename_lower = xsd_file.name.lower()
        
        for taxonomy_identifier in self.standard_taxonomies:
            if taxonomy_identifier in filename_lower:
                self.logger.debug(
                    f"Excluding standard taxonomy file: {xsd_file.name}"
                )
                return True
        
        return False


__all__ = ['CompanyXSDFilter', 'STANDARD_TAXONOMIES']