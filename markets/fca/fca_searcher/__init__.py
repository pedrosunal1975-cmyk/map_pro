"""
FCA Searcher Module (STUB)
==========================

Stub implementation for UK FCA to validate market-agnostic abstraction.

This minimal implementation exposes differences between markets:
- Company numbers vs CIK
- Different filing types
- Direct files (.ixbrl) vs ZIP archives
- No public API like EDGAR

Usage:
    from markets.fca.fca_searcher import FCASearcher
    
    searcher = FCASearcher()
    company_info = await searcher.search_company('00000001')
"""

from .fca_searcher import FCASearcher, create_fca_searcher
from .fca_validators import (
    FCAValidator,
    validate_company_number,
    normalize_company_number,
    identify_identifier_type
)
from .fca_constants import (
    FCA_FILING_TYPES,
    MAJOR_FILING_TYPES,
    ANNUAL_FILINGS,
    INTERIM_FILINGS
)

__all__ = [
    # Main classes
    'FCASearcher',
    'FCAValidator',
    
    # Factory functions
    'create_fca_searcher',
    
    # Validation functions
    'validate_company_number',
    'normalize_company_number',
    'identify_identifier_type',
    
    # Constants
    'FCA_FILING_TYPES',
    'MAJOR_FILING_TYPES',
    'ANNUAL_FILINGS',
    'INTERIM_FILINGS',
]

__version__ = '1.0.0'
__author__ = 'Map Pro Team'