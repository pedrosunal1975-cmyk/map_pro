"""
Map Pro Searcher Engine
======================

Market-agnostic search engine for discovering companies and filings across
different regulatory markets (SEC, FCA, ESMA, etc.).

Components:
- SearcherCoordinator: Main engine that inherits from BaseEngine
- CompanyDiscovery: Market-agnostic company search coordination
- FilingIdentification: Market-agnostic filing discovery coordination
- SearchResultsProcessor: Database operations for search results
- URLValidator: URL validation and normalization utilities

Architecture:
- Core engine components are market-agnostic
- Market-specific logic delegated to plugins in markets/{market}/ directory
- Follows Map Pro's plugin architecture with dynamic market loading

Usage:
    from engines.searcher import create_searcher_engine
    
    engine = create_searcher_engine()
    engine.initialize()
    engine.start()

Location: /map_pro/engines/searcher/__init__.py
"""

from .searcher_coordinator import SearcherCoordinator, create_searcher_engine
from .company_discovery import CompanyDiscovery
from .filing_identification import FilingIdentification
from .search_results_processor import SearchResultsProcessor
from .url_validation import (
    URLValidator,
    url_validator,
    validate_url,
    normalize_url,
    get_file_extension,
    validate_filing_url
)

__all__ = [
    'SearcherCoordinator',
    'create_searcher_engine',
    'CompanyDiscovery',
    'FilingIdentification',
    'SearchResultsProcessor',
    'URLValidator',
    'url_validator',
    'validate_url',
    'normalize_url',
    'get_file_extension',
    'validate_filing_url',
]

__version__ = '1.0.0'
__author__ = 'Map Pro Team'