"""
SEC Searcher Module
==================

SEC EDGAR integration for company and filing search.

Components:
- SECSearcher: Main searcher class implementing MarketInterface
- SECAPIClient: HTTP client for SEC EDGAR API
- SECValidator: Validation functions for SEC-specific formats
- SECZipFinder: XBRL ZIP file identification (SEC-specific)
- Constants: SEC-specific constants and configurations

Usage:
    from markets.sec.sec_searcher import SECSearcher
    
    searcher = SECSearcher()
    company_info = await searcher.search_company('AAPL')
    filings = await searcher.find_filings(company_info['market_entity_id'])
    
    # Filings will contain ONLY XBRL ZIP URLs
"""

from .sec_searcher import SECSearcher, create_sec_searcher
from .sec_api_client import SECAPIClient, create_sec_client
from .sec_validators import (
    SECValidator,
    validate_cik,
    normalize_cik,
    validate_ticker,
    normalize_ticker,
    identify_identifier_type
)
from .sec_zip_finder import SECZipFinder, find_xbrl_zip_url
from .sec_constants import (
    SEC_BASE_URL,
    SEC_ARCHIVES_BASE_URL,
    SEC_FILING_TYPES,
    MAJOR_FILING_TYPES,
    ANNUAL_FILINGS,
    QUARTERLY_FILINGS,
    CURRENT_FILINGS,
    XBRL_ZIP_SUFFIXES
)

__all__ = [
    # Main classes
    'SECSearcher',
    'SECAPIClient',
    'SECValidator',
    'SECZipFinder',
    
    # Factory functions
    'create_sec_searcher',
    'create_sec_client',
    
    # Validation functions
    'validate_cik',
    'normalize_cik',
    'validate_ticker',
    'normalize_ticker',
    'identify_identifier_type',
    
    # ZIP finding
    'find_xbrl_zip_url',
    
    # Constants
    'SEC_BASE_URL',
    'SEC_ARCHIVES_BASE_URL',
    'SEC_FILING_TYPES',
    'MAJOR_FILING_TYPES',
    'ANNUAL_FILINGS',
    'QUARTERLY_FILINGS',
    'CURRENT_FILINGS',
    'XBRL_ZIP_SUFFIXES',
]

__version__ = '2.0.0'
__author__ = 'Map Pro Team'