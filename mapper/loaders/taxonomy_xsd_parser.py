# File: engines/mapper/loaders/taxonomy_xsd_parser.py
"""
Taxonomy XSD Parser
===================

Parses taxonomy XSD files to extract concept definitions.

Responsibilities:
- Parse XSD files using ElementTree
- Extract concept elements
- Create concept dictionaries
- Handle parsing errors gracefully
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from pathlib import Path

from core.system_logger import get_logger
from .taxonomy_constants import (
    XSD_NS_MAP,
    XSD_ELEMENT_PATH,
    XSD_ATTR_NAME
)
from .taxonomy_concept_builder import TaxonomyConceptBuilder

logger = get_logger(__name__, 'engine')


class TaxonomyXSDParser:
    """
    Parses XSD files to extract taxonomy concepts.
    
    Attributes:
        logger: System logger instance
        concept_builder: Builds concept dictionaries from XML elements
    """
    
    def __init__(
        self,
        concept_builder: TaxonomyConceptBuilder = None
    ) -> None:
        """
        Initialize XSD parser with optional dependency injection.
        
        Args:
            concept_builder: Optional concept builder instance
        """
        self.logger = logger
        self.concept_builder = concept_builder or TaxonomyConceptBuilder()
    
    def parse_xsd_file(
        self,
        xsd_path: Path,
        taxonomy_prefix: str
    ) -> List[Dict[str, Any]]:
        """
        Parse taxonomy XSD file for concepts.
        
        Args:
            xsd_path: Path to XSD file
            taxonomy_prefix: Taxonomy prefix (e.g., 'us-gaap')
            
        Returns:
            List of concept dictionaries
        """
        try:
            tree = self._parse_xml_tree(xsd_path)
            elements = self._extract_elements(tree)
            concepts = self._build_concepts(elements, taxonomy_prefix)
            
            if concepts:
                self.logger.info(
                    "Parsed %d concepts from %s",
                    len(concepts),
                    xsd_path.name
                )
            
            return concepts
            
        except ET.ParseError as error:
            self.logger.debug(
                "XML parsing failed for %s: %s",
                str(xsd_path),
                str(error)
            )
            return []
        except Exception as error:
            self.logger.debug(
                "Failed to parse XSD %s: %s",
                str(xsd_path),
                str(error)
            )
            return []
    
    def _parse_xml_tree(self, xsd_path: Path) -> ET.ElementTree:
        """
        Parse XML file into ElementTree.
        
        Args:
            xsd_path: Path to XSD file
            
        Returns:
            Parsed ElementTree
            
        Raises:
            ET.ParseError: If XML parsing fails
        """
        return ET.parse(xsd_path)
    
    def _extract_elements(self, tree: ET.ElementTree) -> List[ET.Element]:
        """
        Extract element definitions from XSD tree.
        
        Args:
            tree: Parsed ElementTree
            
        Returns:
            List of element XML nodes with 'name' attribute
        """
        root = tree.getroot()
        elements = root.findall(XSD_ELEMENT_PATH, XSD_NS_MAP)
        
        # Filter to only elements with name attribute
        return [elem for elem in elements if elem.get(XSD_ATTR_NAME)]
    
    def _build_concepts(
        self,
        elements: List[ET.Element],
        taxonomy_prefix: str
    ) -> List[Dict[str, Any]]:
        """
        Build concept dictionaries from XML elements.
        
        Args:
            elements: List of XML element nodes
            taxonomy_prefix: Taxonomy prefix
            
        Returns:
            List of concept dictionaries
        """
        return [
            self.concept_builder.build_concept(elem, taxonomy_prefix)
            for elem in elements
        ]


__all__ = ['TaxonomyXSDParser']