# File: /map_pro/markets/sec/sec_searcher/sec_url_builder.py

"""
SEC URL Builder
===============

Constructs URLs for SEC EDGAR API endpoints.
Centralizes URL building logic and format validation.

Responsibilities:
- Build endpoint-specific URLs
- Format CIK and accession numbers
- Validate URL components
- Apply consistent formatting rules
"""

from core.system_logger import get_logger
from .sec_api_constants import (
    SEC_BASE_URL,
    SEC_ARCHIVES_BASE_URL,
    SEC_COMPANY_TICKERS_URL,
    SUBMISSIONS_URL_FORMAT,
    COMPANY_FACTS_URL_FORMAT,
    FILING_INDEX_URL_FORMAT,
    CIK_LENGTH,
    CIK_PADDING_CHAR
)

logger = get_logger(__name__, 'market')


class SECURLBuilder:
    """
    Builder for SEC EDGAR API URLs.
    
    Handles:
    - Endpoint URL construction
    - CIK formatting and validation
    - Accession number formatting
    - URL component validation
    """
    
    def __init__(self, base_url: str = SEC_BASE_URL):
        """
        Initialize URL builder.
        
        Args:
            base_url: Base URL for SEC API
        """
        self.base_url = base_url
        self.archives_base_url = SEC_ARCHIVES_BASE_URL
        self.logger = logger
    
    def build_company_tickers_url(self) -> str:
        """
        Build URL for company tickers file.
        
        Returns:
            Full URL to company_tickers.json
        """
        return SEC_COMPANY_TICKERS_URL
    
    def build_submissions_url(self, cik: str) -> str:
        """
        Build URL for company submissions.
        
        Args:
            cik: CIK (will be formatted to 10 digits with leading zeros)
            
        Returns:
            Full URL to submissions JSON
        """
        formatted_cik = self.format_cik(cik)
        return SUBMISSIONS_URL_FORMAT.format(
            base=self.base_url,
            cik=formatted_cik
        )
    
    def build_company_facts_url(self, cik: str) -> str:
        """
        Build URL for company XBRL facts.
        
        Args:
            cik: CIK (will be formatted to 10 digits with leading zeros)
            
        Returns:
            Full URL to company facts JSON
        """
        formatted_cik = self.format_cik(cik)
        return COMPANY_FACTS_URL_FORMAT.format(
            base=self.base_url,
            cik=formatted_cik
        )
    
    def build_filing_index_url(
        self,
        cik: str,
        accession_number: str
    ) -> str:
        """
        Build URL for filing index.json.
        
        Args:
            cik: CIK with leading zeros
            accession_number: Filing accession number (with dashes)
            
        Returns:
            Full URL to filing index.json
        """
        cik_no_zeros = self.strip_leading_zeros(cik)
        accession_no_dashes = self.remove_dashes(accession_number)
        
        return FILING_INDEX_URL_FORMAT.format(
            archives_base=self.archives_base_url,
            cik_no_zeros=cik_no_zeros,
            accession_no_dashes=accession_no_dashes
        )
    
    def format_cik(self, cik: str) -> str:
        """
        Format CIK to 10 digits with leading zeros.
        
        Args:
            cik: CIK string (any length)
            
        Returns:
            10-digit CIK with leading zeros
        """
        return str(cik).zfill(CIK_LENGTH)
    
    def strip_leading_zeros(self, cik: str) -> str:
        """
        Remove leading zeros from CIK.
        
        Args:
            cik: CIK with potential leading zeros
            
        Returns:
            CIK without leading zeros
        """
        return str(int(cik))
    
    def remove_dashes(self, accession_number: str) -> str:
        """
        Remove dashes from accession number.
        
        Args:
            accession_number: Accession number with dashes
            
        Returns:
            Accession number without dashes
        """
        return accession_number.replace('-', '')
    
    def validate_cik_format(self, cik: str) -> bool:
        """
        Validate CIK format.
        
        Args:
            cik: CIK to validate
            
        Returns:
            True if CIK is valid format
        """
        try:
            # Check if CIK is numeric
            int(cik)
            return True
        except (ValueError, TypeError):
            return False
    
    def validate_accession_number_format(self, accession_number: str) -> bool:
        """
        Validate accession number format.
        
        Args:
            accession_number: Accession number to validate
            
        Returns:
            True if accession number is valid format
        """
        # Accession numbers typically have format: 0000000000-00-000000
        if not accession_number:
            return False
        
        # Remove dashes and check if remaining is numeric
        no_dashes = self.remove_dashes(accession_number)
        try:
            int(no_dashes)
            return True
        except (ValueError, TypeError):
            return False


__all__ = ['SECURLBuilder']