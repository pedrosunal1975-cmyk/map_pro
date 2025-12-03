"""
File: engines/mapper/resolvers/xsd_parser.py
Path: engines/mapper/resolvers/xsd_parser.py

XSD Parser
==========

Parses company XSD schema files to extract extension concept definitions.
Handles namespace resolution, type normalization, and documentation extraction.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.system_logger import get_logger
from engines.mapper.resolvers.text_utils import generate_label_from_name

logger = get_logger(__name__, 'engine')


# XML Schema namespace
XML_SCHEMA_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'
XBRL_INSTANCE_NAMESPACE = 'http://www.xbrl.org/2003/instance'

# XML namespace dictionary
NAMESPACES = {
    'xs': XML_SCHEMA_NAMESPACE
}


class XSDParser:
    """
    Parses XSD schema files to extract XBRL concept definitions.
    
    Handles:
    - Namespace extraction and prefix resolution
    - Element definition parsing
    - Type normalization
    - Documentation extraction
    - XBRL-specific attributes (periodType, balance)
    """
    
    def __init__(self):
        """Initialize XSD parser."""
        self.logger = logger
    
    def parse_company_xsd_file(self, xsd_path: Path) -> List[Dict[str, Any]]:
        """
        Parse company XSD file for extension concepts.
        
        Extracts all element definitions from the XSD schema and converts
        them to concept dictionaries compatible with the resolver.
        
        Args:
            xsd_path: Path to company XSD schema file
            
        Returns:
            List of concept dictionaries extracted from XSD
        """
        try:
            tree = ET.parse(xsd_path)
            root = tree.getroot()
            
            # Extract target namespace
            target_namespace = root.get('targetNamespace', '')
            if not target_namespace:
                self.logger.warning(f"Target namespace not found in {xsd_path.name}")
                return []
            
            # Resolve company prefix
            company_prefix = self._resolve_company_prefix(root, target_namespace, xsd_path)
            
            # Extract all element definitions
            concepts = self._extract_elements(root, company_prefix, target_namespace)
            
            self.logger.info(f"Parsed {len(concepts)} concepts from {xsd_path.name}")
            return concepts
            
        except ET.ParseError as parse_error:
            self.logger.error(f"XML parse error in {xsd_path}: {parse_error}")
            return []
        except Exception as error:
            self.logger.error(f"Failed to parse company XSD {xsd_path}: {error}")
            return []
    
    def _resolve_company_prefix(
        self,
        root: ET.Element,
        target_namespace: str,
        xsd_path: Path
    ) -> str:
        """
        Resolve the company namespace prefix.
        
        First attempts to find it in the xmlns declarations, then falls
        back to deriving it from the filename.
        
        Args:
            root: XML root element
            target_namespace: Target namespace URI
            xsd_path: Path to XSD file
            
        Returns:
            Company namespace prefix
        """
        # Try to find prefix in xmlns declarations
        for key, value in root.attrib.items():
            if key.startswith('xmlns:') and value == target_namespace:
                return key.split(':', 1)[1]
        
        # Fallback: derive from filename
        prefix = self._derive_prefix_from_filename(xsd_path)
        self.logger.info(f"Using derived prefix: {prefix} for {xsd_path.name}")
        return prefix
    
    def _derive_prefix_from_filename(self, xsd_path: Path) -> str:
        """
        Derive namespace prefix from XSD filename.
        
        Args:
            xsd_path: Path to XSD file
            
        Returns:
            Derived prefix
        """
        stem = xsd_path.stem
        if '-' in stem:
            return stem.split('-')[0].lower()
        return stem.lower()
    
    def _extract_elements(
        self,
        root: ET.Element,
        company_prefix: str,
        target_namespace: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all element definitions from schema.
        
        Args:
            root: XML root element
            company_prefix: Company namespace prefix
            target_namespace: Target namespace URI
            
        Returns:
            List of concept dictionaries
        """
        concepts = []
        elements = root.findall('.//xs:element', NAMESPACES)
        
        for elem in elements:
            concept = self._parse_element(elem, company_prefix, target_namespace)
            if concept:
                concepts.append(concept)
        
        return concepts
    
    def _parse_element(
        self,
        elem: ET.Element,
        company_prefix: str,
        target_namespace: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single element definition.
        
        Args:
            elem: XML element node
            company_prefix: Company namespace prefix
            target_namespace: Target namespace URI
            
        Returns:
            Concept dictionary if valid, None if missing required attributes
        """
        name = elem.get('name')
        if not name:
            return None
        
        # Extract documentation
        documentation = self._extract_documentation(elem)
        
        # Build concept dictionary
        concept = {
            'concept_qname': f"{company_prefix}:{name}",
            'concept_local_name': name,
            'concept_namespace': target_namespace,
            'concept_type': self._normalize_type(elem.get('type', 'string')),
            'concept_label': documentation or generate_label_from_name(name),
            'period_type': elem.get(f'{{{XBRL_INSTANCE_NAMESPACE}}}periodType', 'duration'),
            'balance_type': elem.get(f'{{{XBRL_INSTANCE_NAMESPACE}}}balance'),
            'is_abstract': elem.get('abstract', 'false').lower() == 'true',
            'is_extension': True
        }
        
        return concept
    
    def _extract_documentation(self, elem: ET.Element) -> Optional[str]:
        """
        Extract documentation text from element annotation.
        
        Args:
            elem: XML element node
            
        Returns:
            Documentation text if found, None otherwise
        """
        annotation = elem.find('xs:annotation', NAMESPACES)
        if annotation is None:
            return None
        
        documentation_elem = annotation.find('xs:documentation', NAMESPACES)
        if documentation_elem is None or not documentation_elem.text:
            return None
        
        return documentation_elem.text.strip()
    
    def _normalize_type(self, type_attr: str) -> str:
        """
        Normalize XBRL type to simple category.
        
        Maps complex XBRL data types to simplified categories for
        easier processing.
        
        Args:
            type_attr: Type attribute value from XSD
            
        Returns:
            Normalized type category
        """
        if not type_attr:
            return 'string'
        
        type_lower = type_attr.lower()
        
        # Numeric types
        if any(t in type_lower for t in ['monetary', 'decimal', 'integer', 'float', 'num']):
            return 'numeric'
        
        # Boolean type
        if 'boolean' in type_lower:
            return 'boolean'
        
        # Date/time types
        if any(t in type_lower for t in ['date', 'time']):
            return 'date'
        
        # Percentage/ratio types
        if any(t in type_lower for t in ['percent', 'ratio']):
            return 'percent'
        
        # Shares type
        if 'shares' in type_lower:
            return 'shares'
        
        # Default to string
        return 'string'


__all__ = ['XSDParser']