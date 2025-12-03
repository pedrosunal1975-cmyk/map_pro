"""
Document-level Namespace Extraction.

Handles extraction from document structure, metadata, and schema references.

Location: engines/librarian/namespace_document_extractor.py
"""

from typing import Dict, Any, Set, List

from .scanner_models import ScannerConstants
from .namespace_matching import NamespaceNormalizer


class DocumentNamespaceExtractor:
    """
    Extracts namespaces from document-level structures.
    
    Handles metadata, schema references, and namespace declarations.
    """
    
    def __init__(self, logger):
        """
        Initialize document namespace extractor.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def extract_from_parsed_document(self, parsed_data: Dict[str, Any]) -> Set[str]:
        """
        Extract all namespaces from a complete parsed document.
        
        Checks multiple sources:
        1. Metadata section
        2. Schema references
        3. Namespace declarations
        4. Taxonomy references
        
        Args:
            parsed_data: Complete parsed document data
            
        Returns:
            Set of all unique namespaces found
        """
        if not parsed_data:
            return set()
        
        namespaces = set()
        
        # Extract from metadata
        namespaces.update(self._extract_from_metadata_section(parsed_data))
        
        # Extract from schema references
        namespaces.update(self._extract_from_schema_refs(parsed_data))
        
        # Extract from namespace map
        namespaces.update(self._extract_from_namespace_map(parsed_data))
        
        # Extract from taxonomy references
        namespaces.update(self._extract_from_taxonomy_refs(parsed_data))
        
        return namespaces
    
    def _extract_from_metadata_section(self, parsed_data: Dict[str, Any]) -> Set[str]:
        """Extract namespaces from metadata section."""
        metadata = parsed_data.get('metadata', {})
        if not metadata:
            return set()
        
        namespaces = self._extract_from_metadata(metadata)
        
        if namespaces:
            self.logger.debug(
                f"Found {len(namespaces)} namespaces in metadata"
            )
        
        return namespaces
    
    def _extract_from_schema_refs(self, parsed_data: Dict[str, Any]) -> Set[str]:
        """Extract namespaces from schema references."""
        namespaces = set()
        schema_refs = parsed_data.get('schema_references', [])
        
        for ref in schema_refs:
            namespace = NamespaceNormalizer.normalize(ref)
            if namespace:
                namespaces.add(namespace)
        
        return namespaces
    
    def _extract_from_namespace_map(self, parsed_data: Dict[str, Any]) -> Set[str]:
        """Extract namespaces from namespace declarations."""
        namespaces = set()
        namespace_map = parsed_data.get('namespaces', {})
        
        for prefix, uri in namespace_map.items():
            namespace = NamespaceNormalizer.normalize(uri)
            if namespace:
                namespaces.add(namespace)
        
        return namespaces
    
    def _extract_from_taxonomy_refs(self, parsed_data: Dict[str, Any]) -> Set[str]:
        """Extract namespaces from taxonomy references."""
        namespaces = set()
        taxonomy_refs = parsed_data.get('taxonomy_refs', [])
        
        for ref in taxonomy_refs:
            if isinstance(ref, str):
                namespace = NamespaceNormalizer.normalize(ref)
                if namespace:
                    namespaces.add(namespace)
            elif isinstance(ref, dict):
                uri = ref.get('namespace') or ref.get('uri') or ref.get('url')
                if uri:
                    namespace = NamespaceNormalizer.normalize(uri)
                    if namespace:
                        namespaces.add(namespace)
        
        return namespaces
    
    def _extract_from_metadata(self, metadata: Dict[str, Any]) -> Set[str]:
        """
        Extract namespaces from metadata dictionary.
        
        Simplified version with separate extraction methods.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Set of namespaces
        """
        namespaces = set()
        
        # Extract from each metadata source
        namespaces.update(self._extract_direct_namespace_list(metadata))
        namespaces.update(self._extract_from_taxonomies_field(metadata))
        namespaces.update(self._extract_from_schema_refs_field(metadata))
        namespaces.update(self._extract_document_namespace(metadata))
        namespaces.update(self._extract_esef_taxonomy(metadata))
        
        return namespaces
    
    def _extract_direct_namespace_list(self, metadata: Dict[str, Any]) -> Set[str]:
        """Extract from direct namespace list."""
        namespaces = set()
        taxonomy_namespaces = metadata.get('taxonomy_namespaces', [])
        
        if isinstance(taxonomy_namespaces, list):
            for ns in taxonomy_namespaces:
                namespace = NamespaceNormalizer.normalize(ns)
                if namespace:
                    namespaces.add(namespace)
        
        return namespaces
    
    def _extract_from_taxonomies_field(self, metadata: Dict[str, Any]) -> Set[str]:
        """Extract from taxonomies field (list or dict)."""
        namespaces = set()
        taxonomies = metadata.get('taxonomies', [])
        
        if isinstance(taxonomies, list):
            namespaces.update(self._extract_from_taxonomy_list(taxonomies))
        elif isinstance(taxonomies, dict):
            namespaces.update(self._extract_from_taxonomy_dict(taxonomies))
        
        return namespaces
    
    def _extract_from_taxonomy_list(self, taxonomies: List) -> Set[str]:
        """Extract from list of taxonomies."""
        namespaces = set()
        
        for tax in taxonomies:
            if isinstance(tax, str):
                namespace = NamespaceNormalizer.normalize(tax)
                if namespace:
                    namespaces.add(namespace)
            elif isinstance(tax, dict):
                ns = self._extract_namespace_from_dict(tax)
                if ns:
                    namespaces.add(ns)
        
        return namespaces
    
    def _extract_from_taxonomy_dict(self, taxonomies: Dict[str, Any]) -> Set[str]:
        """Extract from dictionary of taxonomies."""
        namespaces = set()
        
        for key, value in taxonomies.items():
            if isinstance(value, str):
                namespace = NamespaceNormalizer.normalize(value)
                if namespace:
                    namespaces.add(namespace)
        
        return namespaces
    
    def _extract_namespace_from_dict(self, tax_dict: Dict[str, Any]) -> str:
        """Extract namespace from a taxonomy dictionary."""
        ns = (tax_dict.get('namespace') or 
              tax_dict.get('uri') or 
              tax_dict.get('url') or
              tax_dict.get('schema_location'))
        
        if ns:
            return NamespaceNormalizer.normalize(ns)
        
        return None
    
    def _extract_from_schema_refs_field(self, metadata: Dict[str, Any]) -> Set[str]:
        """Extract from schema references in metadata."""
        namespaces = set()
        schema_refs = metadata.get('schema_refs', []) or metadata.get('schemaRefs', [])
        
        for ref in schema_refs:
            namespace = NamespaceNormalizer.normalize(ref)
            if namespace:
                namespaces.add(namespace)
        
        return namespaces
    
    def _extract_document_namespace(self, metadata: Dict[str, Any]) -> Set[str]:
        """Extract main document namespace."""
        namespaces = set()
        doc_namespace = (metadata.get('document_namespace') or 
                        metadata.get('documentNamespace') or
                        metadata.get('namespace'))
        
        if doc_namespace:
            namespace = NamespaceNormalizer.normalize(doc_namespace)
            if namespace:
                namespaces.add(namespace)
        
        return namespaces
    
    def _extract_esef_taxonomy(self, metadata: Dict[str, Any]) -> Set[str]:
        """Extract ESMA/ESEF specific taxonomy."""
        namespaces = set()
        esef_taxonomy = metadata.get('esef_taxonomy') or metadata.get('reporting_taxonomy')
        
        if esef_taxonomy:
            namespace = NamespaceNormalizer.normalize(esef_taxonomy)
            if namespace:
                namespaces.add(namespace)
        
        return namespaces
    
    def extract_from_xml_attributes(self, attrib: Dict[str, str]) -> Set[str]:
        """
        Extract namespaces from XML element attributes.
        
        Looks for xmlns declarations.
        
        Args:
            attrib: Dictionary of XML element attributes
            
        Returns:
            Set of normalized namespaces
        """
        namespaces = set()
        
        for key, value in attrib.items():
            if key.startswith(ScannerConstants.XMLNS_PREFIX):
                namespace = NamespaceNormalizer.normalize(value)
                if namespace:
                    namespaces.add(namespace)
        
        return namespaces
    
    def extract_from_schema_location(self, schema_location: str) -> Set[str]:
        """
        Extract namespaces from schemaLocation attribute.
        
        Args:
            schema_location: Value of schemaLocation attribute
            
        Returns:
            Set of normalized taxonomy namespaces
        """
        if not schema_location:
            return set()
        
        namespaces = set()
        urls = schema_location.split()
        
        for url in urls:
            if NamespaceNormalizer.is_taxonomy_url(url):
                namespace = NamespaceNormalizer.normalize(url)
                if namespace:
                    namespaces.add(namespace)
        
        return namespaces


__all__ = ['DocumentNamespaceExtractor']