"""
File: engines/searcher/search_constants.py
Path: engines/searcher/search_constants.py

Search Results Processing Constants
===================================

Central location for all search results processing constants.
Extracted to eliminate magic values and improve maintainability.
"""

from typing import List

# Entity status values
ENTITY_STATUS_ACTIVE: str = 'active'
ENTITY_STATUS_INACTIVE: str = 'inactive'
ENTITY_STATUS_DELISTED: str = 'delisted'

# Filing status values
FILING_STATUS_PENDING: str = 'pending'
FILING_STATUS_DOWNLOADED: str = 'downloaded'
FILING_STATUS_EXTRACTED: str = 'extracted'
FILING_STATUS_PARSED: str = 'parsed'
FILING_STATUS_MAPPED: str = 'mapped'
FILING_STATUS_FAILED: str = 'failed'

# Field length limits
MAX_COMPANY_NAME_LENGTH: int = 255
MAX_TICKER_LENGTH: int = 20
MAX_FILING_TYPE_LENGTH: int = 50
MAX_FILING_ID_LENGTH: int = 50
MAX_FILING_TITLE_LENGTH: int = 500
MAX_CLEAN_NAME_LENGTH: int = 100

# Path generation constants
PATH_SEPARATOR: str = '/'
FILING_SUBDIRECTORY: str = 'filings'

# Character replacements for path generation
PATH_INVALID_CHARS: str = '/<>:"|?*\\'
PATH_REPLACEMENT_CHAR: str = '_'
PATH_SPACE_REPLACEMENT: str = '_'

# Validation constants
REQUIRED_ENTITY_FIELDS: List[str] = ['market_entity_id', 'name', 'market_type']
REQUIRED_FILING_FIELDS: List[str] = ['market_filing_id', 'filing_type', 'filing_date']

# Database field names
FIELD_MARKET_ENTITY_ID: str = 'market_entity_id'
FIELD_NAME: str = 'name'
FIELD_MARKET_TYPE: str = 'market_type'
FIELD_MARKET_FILING_ID: str = 'market_filing_id'
FIELD_FILING_TYPE: str = 'filing_type'
FIELD_FILING_DATE: str = 'filing_date'
FIELD_TICKER: str = 'ticker'
FIELD_STATUS: str = 'status'
FIELD_IDENTIFIERS: str = 'identifiers'
FIELD_DISCOVERED_AT: str = 'discovered_at'
FIELD_SOURCE_URL: str = 'source_url'
FIELD_PERIOD_START_DATE: str = 'period_start_date'
FIELD_PERIOD_END_DATE: str = 'period_end_date'
FIELD_FILING_TITLE: str = 'filing_title'
FIELD_DOWNLOAD_URL: str = 'download_url'
FIELD_URL: str = 'url'

# Allowed characters for filesystem names
ALLOWED_PATH_CHARS_PATTERN: str = r'[a-zA-Z0-9\-_ ]'