# File: /map_pro/engines/mapper/loaders/company_xsd_parser.py

"""
Company XSD Parser
==================

Parses company XSD files to extract extension concepts.
Uses ConceptResolver for actual parsing logic.
"""

from typing import List, Dict, Any
from pathlib import Path

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class CompanyXSDParser:
    """
    Parses company XSD files to extract concepts.
    
    Responsibilities:
    - Parse multiple XSD files
    - Handle parsing errors gracefully
    - Aggregate concepts from all files
    """
    
    def __init__(self):
        """Initialize company XSD parser."""
        self.logger = logger
    
    def parse_company_xsd_files(self, xsd_files: List[Path]) -> List[Dict[str, Any]]:
        """
        Parse company concepts from XSD files.
        
        Args:
            xsd_files: List of XSD file paths to parse
            
        Returns:
            List of concept dictionaries (aggregated from all files)
        """
        all_concepts = []
        
        for xsd_file in xsd_files:
            concepts = self._parse_single_xsd_file(xsd_file)
            all_concepts.extend(concepts)
        
        if all_concepts:
            self.logger.info(
                f"Parsed total of {len(all_concepts)} concepts from "
                f"{len(xsd_files)} XSD files"
            )
        
        return all_concepts
    
    def _parse_single_xsd_file(self, xsd_path: Path) -> List[Dict[str, Any]]:
        """
        Parse a single company XSD file.
        
        CRITICAL: This method properly handles exceptions during parsing,
        fixing the empty except block issue identified in code quality report.
        
        Args:
            xsd_path: Path to XSD file
            
        Returns:
            List of concept dictionaries (empty list on error)
        """
        try:
            self.logger.debug(f"Parsing XSD: {xsd_path}")
            
            if not xsd_path.exists():
                self.logger.warning(f"XSD file does not exist: {xsd_path}")
                return []
            
            concepts = self._parse_xsd_with_resolver(xsd_path)
            
            self.logger.debug(
                f"Parsed {len(concepts)} concepts from {xsd_path.name}"
            )
            
            return concepts
            
        except (OSError, IOError) as io_exception:
            self.logger.error(
                f"I/O error parsing {xsd_path.name}: {io_exception}",
                exc_info=True
            )
            return []
        
        except ValueError as value_exception:
            self.logger.error(
                f"Invalid XSD format in {xsd_path.name}: {value_exception}",
                exc_info=True
            )
            return []
        
        except Exception as exception:
            self.logger.error(
                f"Unexpected error parsing {xsd_path.name}: {exception}",
                exc_info=True
            )
            return []
    
    def _parse_xsd_with_resolver(self, xsd_path: Path) -> List[Dict[str, Any]]:
        """
        Parse XSD file using ConceptResolver.
        
        Args:
            xsd_path: Path to XSD file
            
        Returns:
            List of concept dictionaries
            
        Raises:
            Various exceptions from ConceptResolver parsing
        """
        from ..concept_resolver import ConceptResolver
        
        resolver = ConceptResolver()
        concepts = resolver.parse_company_xsd_file(xsd_path)
        
        return concepts


__all__ = ['CompanyXSDParser']