"""
SEC EDGAR Constants
==================

Constants for SEC EDGAR API integration.
Includes URLs, filing types, rate limits, and other SEC-specific values.
"""

from typing import Dict, List

# API Endpoints
SEC_BASE_URL = "https://data.sec.gov"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = f"{SEC_BASE_URL}/submissions/CIK{{cik}}.json"
SEC_FACTS_URL = f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{{cik}}.json"
SEC_ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data/"

# Rate Limiting (SEC allows 10 requests per second)
SEC_RATE_LIMIT_PER_SECOND = 10
SEC_RATE_LIMIT_PER_MINUTE = 600

# Request Configuration
SEC_REQUEST_TIMEOUT = 30  # seconds
SEC_MAX_RETRIES = 3

# CIK Format
CIK_LENGTH = 10  # CIKs are 10 digits with leading zeros

# XBRL ZIP File Identification Patterns
# SEC XBRL filings are packaged in ZIP files with these naming patterns
XBRL_ZIP_SUFFIXES = [
    '_htm.zip',      # Most common: accession_number_htm.zip
    '_xbrl.zip',     # Alternative: accession_number_xbrl.zip
    '-xbrl.zip',     # Alternative: accession_number-xbrl.zip
    'r2.zip',        # Revision 2 pattern
    '.zip'           # Generic fallback
]

# Minimum JSON size for valid index.json files
MIN_JSON_SIZE_BYTES = 500

# Common SEC Filing Types
SEC_FILING_TYPES = {
    # Annual Reports
    '10-K': 'Annual Report',
    '10-K/A': 'Annual Report Amendment',
    '20-F': 'Annual Report (Foreign)',
    '40-F': 'Annual Report (Canadian)',
    
    # Quarterly Reports
    '10-Q': 'Quarterly Report',
    '10-Q/A': 'Quarterly Report Amendment',
    '6-K': 'Current Report (Foreign)',
    
    # Current Reports
    '8-K': 'Current Report',
    '8-K/A': 'Current Report Amendment',
    
    # Proxy Statements
    'DEF 14A': 'Definitive Proxy Statement',
    'DEFA14A': 'Additional Proxy Materials',
    
    # Registration Statements
    'S-1': 'Registration Statement',
    'S-3': 'Registration Statement',
    'S-4': 'Registration Statement',
    'S-8': 'Registration Statement',
    
    # Other Common Forms
    '3': 'Initial Statement of Ownership',
    '4': 'Statement of Changes in Ownership',
    '5': 'Annual Statement of Changes in Ownership',
    '13F-HR': 'Institutional Investment Manager Holdings Report',
    'SC 13G': 'Beneficial Ownership Report',
    'SC 13D': 'Beneficial Ownership Report',
}

# Filing Type Categories
ANNUAL_FILINGS = ['10-K', '10-K/A', '20-F', '40-F']
QUARTERLY_FILINGS = ['10-Q', '10-Q/A', '6-K']
CURRENT_FILINGS = ['8-K', '8-K/A']
PROXY_FILINGS = ['DEF 14A', 'DEFA14A', 'DEFR14A', 'PREC14A']

# All major filing types for filtering
MAJOR_FILING_TYPES = ANNUAL_FILINGS + QUARTERLY_FILINGS + CURRENT_FILINGS + PROXY_FILINGS

# SEC Error Messages
SEC_ERROR_MESSAGES = {
    403: "Access forbidden - check user-agent header",
    404: "Company or filing not found",
    429: "Rate limit exceeded",
    500: "SEC server error",
    503: "SEC service unavailable",
}

# Identifier Types
IDENTIFIER_TYPES = ['ticker', 'cik', 'name']

# Maximum results per request
MAX_FILINGS_PER_REQUEST = 1000  # SEC's practical limit