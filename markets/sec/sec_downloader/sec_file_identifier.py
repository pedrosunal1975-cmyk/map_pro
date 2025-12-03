"""
SEC File Identifier
==================

Identifies XBRL ZIP files within SEC filings using multiple strategies.
SEC XBRL filings are packaged as ZIP files with various naming patterns.

Common Patterns:
- {accession}_htm.zip      (most common, newer filings)
- {accession}_xbrl.zip     (alternative)
- {accession}-xbrl.zip     (alternative with hyphen)
- {accession}r2.zip        (revision 2)

Save location: markets/sec/sec_downloader/sec_file_identifier.py
"""

from typing import Dict, Any, List, Optional

from core.system_logger import get_logger
from markets.sec.sec_searcher.sec_constants import XBRL_ZIP_SUFFIXES, SEC_ARCHIVES_BASE_URL

logger = get_logger(__name__, 'market')


class SECFileIdentifier:
    """
    Identifies XBRL ZIP files in SEC filings.
    
    Uses multiple strategies to find the correct ZIP file:
    1. Index.json-based (preferred for newer filings)
    2. Pattern-based (fallback for older filings)
    3. Common patterns (last resort)
    """
    
    def __init__(self, zip_suffixes: Optional[List[str]] = None):
        """
        Initialize file identifier.
        
        Args:
            zip_suffixes: List of ZIP suffixes to try (uses defaults if None)
        """
        self.zip_suffixes = zip_suffixes or XBRL_ZIP_SUFFIXES
        logger.debug(f"SEC file identifier initialized with {len(self.zip_suffixes)} patterns")
    
    def identify_from_index(
        self,
        index_data: Dict[str, Any],
        cik: str,
        accession_number: str
    ) -> Optional[str]:
        """
        Identify XBRL ZIP from parsed index.json.
        
        Args:
            index_data: Parsed index.json content
            cik: Company CIK (with or without leading zeros)
            accession_number: Accession number (with dashes)
            
        Returns:
            Complete URL to ZIP file or None if not found
        """
        try:
            # Get document list
            documents = index_data.get('directory', {}).get('item', [])
            
            if not documents:
                logger.debug("No documents in index.json")
                return None
            
            # Find ZIP files matching our patterns
            zip_candidates = []
            
            for doc in documents:
                doc_name = doc.get('name', '').lower()
                
                # Must be a ZIP file
                if not doc_name.endswith('.zip'):
                    continue
                
                # Check against our known patterns
                for priority, suffix in enumerate(self.zip_suffixes):
                    if doc_name.endswith(suffix.lower()):
                        zip_candidates.append({
                            'name': doc.get('name'),  # Original case
                            'priority': priority,
                            'size': doc.get('size', '0')
                        })
                        break
            
            if not zip_candidates:
                logger.debug("No XBRL ZIP files found in index.json")
                return None
            
            # Sort by priority (lower is better)
            zip_candidates.sort(key=lambda x: x['priority'])
            
            # Use highest priority ZIP
            best_zip = zip_candidates[0]
            zip_filename = best_zip['name']
            
            # Construct full URL
            zip_url = self._construct_url(cik, accession_number, zip_filename)
            
            logger.info(
                f"Found XBRL ZIP via index.json: {zip_filename} "
                f"(pattern: {self.zip_suffixes[best_zip['priority']]})"
            )
            
            return zip_url
            
        except Exception as e:
            logger.error(f"Error identifying ZIP from index: {e}")
            return None
    
    def identify_from_pattern(
        self,
        cik: str,
        accession_number: str,
        filing_date: Optional[str] = None
    ) -> List[str]:
        """
        Generate potential ZIP URLs using common patterns.
        
        Args:
            cik: Company CIK
            accession_number: Accession number (with dashes)
            filing_date: Optional filing date (not currently used)
            
        Returns:
            List of potential ZIP URLs (ordered by likelihood)
        """
        urls = []
        
        # Normalize accession number formats
        accession_underscore = accession_number.replace('-', '_')
        accession_no_dashes = accession_number.replace('-', '')
        
        # Try each pattern
        for suffix in self.zip_suffixes:
            # Pattern 1: accession_underscore + suffix
            # CRITICAL: Keep suffix AS IS! Don't remove underscores!
            # Example: "0001403161_24_000058" + "_htm.zip" = "0001403161_24_000058_htm.zip"
            if '_' in suffix:
                filename = accession_underscore + suffix
                urls.append(self._construct_url(cik, accession_number, filename))
            
            # Pattern 2: accession_no_dashes + suffix
            if '-' in suffix or suffix.startswith('.'):
                filename = accession_no_dashes + suffix
                urls.append(self._construct_url(cik, accession_number, filename))
        
        # Add most common specific patterns
        common_patterns = [
            f"{accession_underscore}_htm.zip",
            f"{accession_no_dashes}-xbrl.zip",
            f"{accession_underscore}_xbrl.zip",
            f"{accession_no_dashes}.zip"
        ]
        
        for pattern in common_patterns:
            url = self._construct_url(cik, accession_number, pattern)
            if url not in urls:
                urls.append(url)
        
        logger.debug(f"Generated {len(urls)} potential ZIP URLs from patterns")
        
        return urls
    
    def identify_best_match(
        self,
        index_data: Optional[Dict[str, Any]],
        cik: str,
        accession_number: str,
        filing_date: Optional[str] = None
    ) -> Optional[str]:
        """
        Identify XBRL ZIP using best available strategy.
        
        Tries strategies in order:
        1. Index.json-based (if index_data provided)
        2. Pattern-based (first pattern as best guess)
        
        Args:
            index_data: Optional parsed index.json
            cik: Company CIK
            accession_number: Accession number (with dashes)
            filing_date: Optional filing date
            
        Returns:
            Best guess ZIP URL or None
        """
        # Strategy 1: Use index.json if available
        if index_data:
            zip_url = self.identify_from_index(index_data, cik, accession_number)
            if zip_url:
                return zip_url
            
            logger.debug("No ZIP found in index.json, trying pattern-based")
        
        # Strategy 2: Use most common pattern
        pattern_urls = self.identify_from_pattern(cik, accession_number, filing_date)
        
        if pattern_urls:
            best_url = pattern_urls[0]
            logger.info(f"Using pattern-based ZIP URL: {best_url.split('/')[-1]}")
            return best_url
        
        logger.warning(f"Could not identify ZIP file for {accession_number}")
        return None
    
    def _construct_url(self, cik: str, accession_number: str, filename: str) -> str:
        """
        Construct full SEC Archives URL.
        
        Args:
            cik: Company CIK
            accession_number: Accession number (with dashes)
            filename: ZIP filename
            
        Returns:
            Complete URL
        """
        # Remove leading zeros from CIK for URL
        cik_no_zeros = str(int(cik)) if cik.isdigit() else cik
        
        # Remove dashes from accession for path
        accession_no_dashes = accession_number.replace('-', '')
        
        # Construct URL: https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filename}
        url = f"{SEC_ARCHIVES_BASE_URL}{cik_no_zeros}/{accession_no_dashes}/{filename}"
        
        return url
    
    def validate_filename(self, filename: str) -> bool:
        """
        Validate if filename matches XBRL ZIP patterns.
        
        Args:
            filename: Filename to validate
            
        Returns:
            True if matches known patterns
        """
        filename_lower = filename.lower()
        
        # Must be a ZIP
        if not filename_lower.endswith('.zip'):
            return False
        
        # Check against known patterns
        for suffix in self.zip_suffixes:
            if suffix.lower() in filename_lower:
                return True
        
        return False
    
    def get_pattern_priority(self, filename: str) -> int:
        """
        Get priority score for a filename (lower is better).
        
        Args:
            filename: Filename to score
            
        Returns:
            Priority score (0 = highest priority)
        """
        filename_lower = filename.lower()
        
        for priority, suffix in enumerate(self.zip_suffixes):
            if filename_lower.endswith(suffix.lower()):
                return priority
        
        return len(self.zip_suffixes)  # Lowest priority


# Convenience functions

def identify_xbrl_zip(
    index_data: Optional[Dict[str, Any]],
    cik: str,
    accession_number: str
) -> Optional[str]:
    """
    Convenience function to identify XBRL ZIP file.
    
    Args:
        index_data: Optional parsed index.json
        cik: Company CIK
        accession_number: Accession number
        
    Returns:
        ZIP URL or None
    """
    identifier = SECFileIdentifier()
    return identifier.identify_best_match(index_data, cik, accession_number)


def generate_zip_urls(cik: str, accession_number: str) -> List[str]:
    """
    Convenience function to generate potential ZIP URLs.
    
    Args:
        cik: Company CIK
        accession_number: Accession number
        
    Returns:
        List of potential ZIP URLs
    """
    identifier = SECFileIdentifier()
    return identifier.identify_from_pattern(cik, accession_number)