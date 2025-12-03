"""
SEC ZIP File Finder
==================

Specialized logic for identifying XBRL ZIP files within SEC filings.
This is SEC-specific and should not be in the market-agnostic base.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from core.system_logger import get_logger
from .sec_constants import XBRL_ZIP_SUFFIXES

logger = get_logger(__name__, 'market')


class SECZipFinder:
    """
    Identifies XBRL ZIP files within SEC filing packages.
    
    SEC XBRL filings are distributed as ZIP files containing:
    - XBRL instance (.xml)
    - Schema files (.xsd)
    - Linkbase files (_cal.xml, _def.xml, _lab.xml, _pre.xml)
    - HTML rendering
    """
    
    def __init__(self):
        """Initialize ZIP finder with SEC-specific patterns."""
        self.zip_suffixes = XBRL_ZIP_SUFFIXES
        logger.debug("SEC ZIP finder initialized")
    
    def find_xbrl_zip(
        self,
        filing_index: Dict[str, Any],
        cik: str,
        accession_number: str,
        archives_base_url: str
    ) -> Optional[str]:
        """
        Find the XBRL ZIP file URL from a filing's index.json.
        
        Args:
            filing_index: Parsed index.json content
            cik: Company CIK (no leading zeros)
            accession_number: Filing accession number (with dashes)
            archives_base_url: Base URL for SEC archives
            
        Returns:
            Complete URL to XBRL ZIP file, or None if not found
        """
        # Get list of all documents in the filing
        documents = filing_index.get('directory', {}).get('item', [])
        
        if not documents:
            logger.warning(f"No documents found in index for {accession_number}")
            return None
        
        # Strategy 1: Look for explicit ZIP files with XBRL patterns
        zip_candidates = []
        
        for doc in documents:
            doc_name = doc.get('name', '').lower()
            
            # Check if it's a ZIP file
            if not doc_name.endswith('.zip'):
                continue
            
            # Check if it matches XBRL patterns
            for suffix in self.zip_suffixes:
                if doc_name.endswith(suffix.lower()):
                    zip_candidates.append({
                        'name': doc.get('name'),
                        'priority': self.zip_suffixes.index(suffix)
                    })
                    break
        
        if not zip_candidates:
            logger.info(f"No XBRL ZIP files found for {accession_number}")
            return None
        
        # Sort by priority (earlier suffixes in list are preferred)
        zip_candidates.sort(key=lambda x: x['priority'])
        
        # Use the highest priority ZIP
        best_zip = zip_candidates[0]['name']
        
        # Construct full URL
        cik_no_leading_zeros = str(int(cik))
        accession_no_dashes = accession_number.replace('-', '')
        
        zip_url = f"{archives_base_url}{cik_no_leading_zeros}/{accession_no_dashes}/{best_zip}"
        
        logger.info(f"Found XBRL ZIP: {best_zip}")
        
        return zip_url
    
    def get_all_documents(
        self,
        filing_index: Dict[str, Any],
        cik: str,
        accession_number: str,
        archives_base_url: str
    ) -> List[Dict[str, str]]:
        """
        Get ALL documents from a filing (for internal analysis).
        
        This finds everything but searcher will only return ZIP URLs.
        
        Args:
            filing_index: Parsed index.json content
            cik: Company CIK
            accession_number: Filing accession number
            archives_base_url: Base URL for SEC archives
            
        Returns:
            List of all documents with their URLs
        """
        documents = filing_index.get('directory', {}).get('item', [])
        
        cik_no_leading_zeros = str(int(cik))
        accession_no_dashes = accession_number.replace('-', '')
        base_dir_url = f"{archives_base_url}{cik_no_leading_zeros}/{accession_no_dashes}/"
        
        all_docs = []
        for doc in documents:
            doc_name = doc.get('name', '')
            if doc_name:
                all_docs.append({
                    'name': doc_name,
                    'type': Path(doc_name).suffix.lstrip('.').lower(),
                    'url': f"{base_dir_url}{doc_name}"
                })
        
        return all_docs


# Convenience function
def find_xbrl_zip_url(
    filing_index: Dict[str, Any],
    cik: str,
    accession_number: str,
    archives_base_url: str
) -> Optional[str]:
    """Convenience function to find XBRL ZIP URL."""
    finder = SECZipFinder()
    return finder.find_xbrl_zip(filing_index, cik, accession_number, archives_base_url)