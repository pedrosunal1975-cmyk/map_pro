"""
FCA (UK Financial Conduct Authority) Constants
==============================================

Constants for FCA API integration.
"""

from typing import Dict, List

# FCA API Endpoints (these are placeholder URLs - FCA doesn't have a public API like SEC)
FCA_BASE_URL = "https://api.fca.org.uk"  # Placeholder
FCA_COMPANY_SEARCH_URL = f"{FCA_BASE_URL}/companies/search"  # Placeholder

# Rate Limiting (assume conservative limits)
FCA_RATE_LIMIT_PER_SECOND = 5
FCA_RATE_LIMIT_PER_MINUTE = 300

# Request Configuration
FCA_REQUEST_TIMEOUT = 30
FCA_MAX_RETRIES = 3

# Company Number Format
COMPANY_NUMBER_LENGTH = 8  # UK company numbers are typically 8 digits

# FCA Filing Types (different from SEC)
FCA_FILING_TYPES = {
    'ANNUAL': 'Annual Report',
    'HALF': 'Half-Yearly Report',
    'QUARTERLY': 'Quarterly Report',
    'PROSPECTUS': 'Prospectus',
    'ANNOUNCEMENT': 'Regulatory Announcement',
    'TR-1': 'Transparency Rule 1 (Shareholding)',
}

# Filing Type Categories
ANNUAL_FILINGS = ['ANNUAL']
INTERIM_FILINGS = ['HALF', 'QUARTERLY']
DISCLOSURE_FILINGS = ['TR-1', 'ANNOUNCEMENT']

# All major filing types
MAJOR_FILING_TYPES = ANNUAL_FILINGS + INTERIM_FILINGS + DISCLOSURE_FILINGS

# FCA Error Messages
FCA_ERROR_MESSAGES = {
    403: "Access forbidden",
    404: "Company or filing not found",
    429: "Rate limit exceeded",
    500: "FCA server error",
    503: "FCA service unavailable",
}

# Identifier Types (different from SEC - no "CIK", use company registration number)
IDENTIFIER_TYPES = ['company_number', 'name']