# File: /map_pro/markets/sec/sec_downloader/sec_metadata_extractor.py

"""
SEC Metadata Extractor
======================

Extracts and validates CIK and accession number from Filing objects.
Handles normalization and validation of SEC identifiers.
"""

from typing import Optional, Tuple

from core.system_logger import get_logger
from database.models.core_models import Filing
from markets.sec.sec_searcher import SECValidator

logger = get_logger(__name__, 'market')


class SECMetadataExtractor:
    """
    Extracts filing metadata required for SEC downloads.
    
    Responsibilities:
    - Extract CIK from filing entity
    - Validate and normalize CIK format
    - Extract accession number from filing
    """
    
    def __init__(self):
        """Initialize metadata extractor."""
        self.logger = logger
    
    def extract_metadata(self, filing: Filing) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract CIK and accession number from filing.
        
        Args:
            filing: Filing object containing entity and filing information
            
        Returns:
            Tuple of (cik, accession_number)
            Returns (None, None) if extraction fails
        """
        try:
            cik = self._extract_cik(filing)
            accession_number = self._extract_accession_number(filing)
            
            if not cik or not accession_number:
                self.logger.error(
                    f"Missing metadata for filing {filing.market_filing_id}: "
                    f"CIK={cik}, Accession={accession_number}"
                )
                return None, None
            
            return cik, accession_number
            
        except Exception as exception:
            self.logger.error(f"Failed to extract filing metadata: {exception}")
            return None, None
    
    def _extract_cik(self, filing: Filing) -> Optional[str]:
        """
        Extract and validate CIK from filing entity.
        
        Args:
            filing: Filing object with entity relationship
            
        Returns:
            Normalized CIK string or None if invalid
        """
        if not filing.entity:
            self.logger.error(f"Filing {filing.market_filing_id} has no entity")
            return None
        
        cik = filing.entity.market_entity_id
        
        if not cik:
            self.logger.error(f"Entity has no market_entity_id")
            return None
        
        if not SECValidator.validate_cik(cik):
            self.logger.error(f"Invalid CIK format: {cik}")
            return None
        
        return SECValidator.normalize_cik(cik)
    
    def _extract_accession_number(self, filing: Filing) -> Optional[str]:
        """
        Extract accession number from filing.
        
        Args:
            filing: Filing object
            
        Returns:
            Accession number string or None if missing
        """
        accession_number = filing.market_filing_id
        
        if not accession_number:
            self.logger.error("Filing has no market_filing_id")
            return None
        
        return accession_number