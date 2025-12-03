# File: /map_pro/engines/parser/parsing_job_resolver.py

"""
Parsing Job Resolver
====================

Resolves document_id from various job data formats.
Handles both direct extractor jobs and workflow jobs.

Responsibilities:
- Extract document_id from job data
- Resolve filing_id to document_id
- Query database for parsing-eligible documents
- Handle multiple job data formats
- Intelligently select XBRL instance documents
"""

from typing import Dict, Any, Optional, Callable

from core.system_logger import get_logger
from database.models.core_models import Document

logger = get_logger(__name__, 'engine')


class ParsingJobResolver:
    """Resolves document_id from job data."""
    
    def __init__(self, get_session_func: Callable):
        """
        Initialize job resolver.
        
        Args:
            get_session_func: Function to get database session
        """
        self.get_session = get_session_func
    
    def resolve_document_id(self, job_data: Dict[str, Any]) -> Optional[str]:
        """
        Resolve document_id from job data.
        
        Tries multiple strategies:
        1. Direct document_id (from extractor jobs)
        2. Filing_id lookup (from workflow jobs)
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Document ID or None if not found
        """
        # Try direct document_id first
        document_id = self._get_direct_document_id(job_data)
        if document_id:
            return document_id
        
        # Try resolving from filing_id
        document_id = self._resolve_from_filing_id(job_data)
        if document_id:
            return document_id
        
        return None
    
    def _get_direct_document_id(self, job_data: Dict[str, Any]) -> Optional[str]:
        """
        Get document_id directly from job data.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Document ID or None
        """
        parameters = job_data.get('parameters', {})
        return parameters.get('document_id')
    
    def _resolve_from_filing_id(self, job_data: Dict[str, Any]) -> Optional[str]:
        """
        Resolve document_id from filing_id.
        
        CRITICAL FIX: Intelligently selects the XBRL instance document,
        not schema/linkbase/exhibit files.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Document ID or None
        """
        filing_id = self._extract_filing_id(job_data)
        
        if not filing_id:
            return None
        
        # Query for all parsing-eligible documents
        with self.get_session() as session:
            documents = session.query(Document).filter(
                Document.filing_universal_id == filing_id,
                Document.parsing_eligible == True
            ).all()
            
            if not documents:
                logger.warning(
                    f"No parsing-eligible documents found for filing {filing_id}"
                )
                return None
            
            # Select the instance document (not schema/linkbase/exhibit)
            instance_doc = self._select_instance_document(documents)
            
            if instance_doc:
                document_id = str(instance_doc.document_universal_id)
                logger.info(
                    f"Resolved filing {filing_id} to instance document "
                    f"{instance_doc.document_name} ({document_id})"
                )
                return document_id
            
            logger.warning(
                f"No instance document found in {len(documents)} "
                f"parsing-eligible documents for filing {filing_id}"
            )
            return None
    
    def _select_instance_document(self, documents: list) -> Optional[Document]:
        """
        Select the XBRL instance document from a list of documents.
        
        Strategy:
        1. CRITICAL: Skip exhibit files (ex*.htm, exhibit*.htm)
        2. Skip schema files (.xsd)
        3. Skip linkbase files (*_cal.xml, *_def.xml, *_lab.xml, *_pre.xml)
        4. Prefer .htm or .xml files with company ticker/identifier
        5. Prefer files without linkbase suffixes
        6. Return first remaining valid document
        
        Args:
            documents: List of Document objects
            
        Returns:
            Instance Document or None
        """
        if not documents:
            return None
        
        # CRITICAL FIX: Filter out exhibit files first (ex*.htm, exhibit*.htm)
        non_exhibit = [
            doc for doc in documents
            if not (
                doc.document_name.lower().startswith('ex') or
                doc.document_name.lower().startswith('exhibit')
            )
        ]
        
        if not non_exhibit:
            logger.warning(
                f"All {len(documents)} documents are exhibit files. "
                f"Document names: {[d.document_name for d in documents]}"
            )
            return None
        
        logger.info(
            f"Filtered out {len(documents) - len(non_exhibit)} exhibit files. "
            f"Remaining: {[d.document_name for d in non_exhibit]}"
        )
        
        # Filter out schema files
        non_schema = [
            doc for doc in non_exhibit
            if not doc.document_name.endswith('.xsd')
        ]
        
        if not non_schema:
            logger.warning("All non-exhibit documents are schema files (.xsd)")
            return None
        
        # Filter out linkbase files
        linkbase_suffixes = ('_cal.xml', '_def.xml', '_lab.xml', '_pre.xml')
        non_linkbase = [
            doc for doc in non_schema
            if not any(doc.document_name.endswith(suffix) for suffix in linkbase_suffixes)
        ]
        
        if not non_linkbase:
            logger.warning("All non-schema documents are linkbase files")
            return None
        
        # Prefer .htm or .xml instance documents
        # Instance documents typically have the company identifier in the filename
        # Examples: aci-20250222.htm, plug-20241231x10k.htm, v-20240930.xml
        instance_candidates = [
            doc for doc in non_linkbase
            if doc.document_name.endswith(('.htm', '.xml'))
        ]
        
        if instance_candidates:
            # Sort by filename length (shorter names are typically main instance)
            # and prefer .htm over .xml
            instance_candidates.sort(
                key=lambda d: (
                    0 if d.document_name.endswith('.htm') else 1,
                    len(d.document_name)
                )
            )
            selected = instance_candidates[0]
            logger.info(
                f"Selected instance document: {selected.document_name} "
                f"from {len(documents)} total documents"
            )
            return selected
        
        # Fallback: return first non-linkbase document
        if non_linkbase:
            fallback = non_linkbase[0]
            logger.warning(
                f"Using fallback document selection: {fallback.document_name}"
            )
            return fallback
        
        return None
    
    def _extract_filing_id(self, job_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract filing_id from various parameter names.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            Filing ID or None
        """
        parameters = job_data.get('parameters', {})
        
        # Try common parameter names
        return (
            parameters.get('filing_id') or
            parameters.get('filing_universal_id')
        )


__all__ = ['ParsingJobResolver']