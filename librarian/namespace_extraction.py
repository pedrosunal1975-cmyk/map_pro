"""
Namespace Extraction for Library Dependency Scanner.

ENHANCED VERSION: Multi-source, multi-format namespace extraction with
intelligent fallbacks for different market types and filing formats.

Main entry point that delegates to specialized extractors.

Location: engines/librarian/namespace_extraction.py
"""

from typing import Dict, Any, Set, Optional, List

from .scanner_models import ScannerConstants
from .namespace_matching import NamespaceNormalizer
from .namespace_document_extractor import DocumentNamespaceExtractor
from .namespace_fact_extractor import FactNamespaceExtractor


class NamespaceExtractor:
    """
    Intelligent namespace extractor with multi-format support.
    
    This is the main interface that coordinates between document-level
    and fact-level extraction strategies.
    """
    
    def __init__(self, logger):
        """
        Initialize namespace extractor.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.document_extractor = DocumentNamespaceExtractor(logger)
        self.fact_extractor = FactNamespaceExtractor(logger)
    
    def extract_from_parsed_document(self, parsed_data: Dict[str, Any]) -> Set[str]:
        """
        Extract all namespaces from a complete parsed document.
        
        Delegates to DocumentNamespaceExtractor for document-level extraction.
        
        Args:
            parsed_data: Complete parsed document data
            
        Returns:
            Set of all unique namespaces found
        """
        return self.document_extractor.extract_from_parsed_document(parsed_data)
    
    def extract_from_concept_name(self, concept_name: str) -> Optional[str]:
        """
        Extract namespace prefix from concept qualified name.
        
        Args:
            concept_name: Qualified concept name (e.g., 'us-gaap:Assets')
            
        Returns:
            Normalized namespace prefix or None
        """
        return self.fact_extractor.extract_from_concept_name(concept_name)
    
    def extract_from_fact(self, fact: Dict[str, Any]) -> Set[str]:
        """
        Extract all namespaces from a single fact dictionary.
        
        Delegates to FactNamespaceExtractor for fact-level extraction.
        
        Args:
            fact: Fact dictionary from parsed data
            
        Returns:
            Set of normalized namespaces found in fact
        """
        return self.fact_extractor.extract_from_fact(fact)
    
    def extract_namespace_prefixes_from_facts(
        self, 
        facts: List[Dict[str, Any]]
    ) -> Set[str]:
        """
        Extract unique namespace prefixes from a list of facts.
        
        Args:
            facts: List of fact dictionaries
            
        Returns:
            Set of unique namespace prefixes
        """
        return self.fact_extractor.extract_namespace_prefixes_from_facts(facts)
    
    def map_prefixes_to_namespaces(
        self, 
        prefixes: Set[str]
    ) -> Dict[str, str]:
        """
        Map namespace prefixes to full namespace URLs.
        
        Args:
            prefixes: Set of namespace prefixes
            
        Returns:
            Dictionary mapping prefix to full namespace URL
        """
        return self.fact_extractor.map_prefixes_to_namespaces(prefixes)
    
    def extract_from_xml_attributes(self, attrib: Dict[str, str]) -> Set[str]:
        """
        Extract namespaces from XML element attributes.
        
        Args:
            attrib: Dictionary of XML element attributes
            
        Returns:
            Set of normalized namespaces
        """
        return self.document_extractor.extract_from_xml_attributes(attrib)
    
    def extract_from_schema_location(self, schema_location: str) -> Set[str]:
        """
        Extract namespaces from schemaLocation attribute.
        
        Args:
            schema_location: Value of schemaLocation attribute
            
        Returns:
            Set of normalized taxonomy namespaces
        """
        return self.document_extractor.extract_from_schema_location(schema_location)


__all__ = ['NamespaceExtractor']