"""
FCA Downloader Constants
========================

FCA-specific constants for the downloader.
Ensures engines/downloader/ remains market-agnostic.

Key FCA Differences from SEC:
- Direct files (.ixbrl, .html) instead of ZIP archives
- Different URL patterns
- Different file naming conventions
- No extraction needed
"""

from typing import Dict, List

# Base URLs
FCA_BASE_URL = "https://api.fca.org.uk"  # Placeholder - would be real FCA endpoint
FCA_DOCUMENTS_BASE_URL = "https://documents.fca.org.uk"  # Placeholder

# File Formats
FCA_FILE_FORMATS = {
    '.ixbrl': 'Inline XBRL',
    '.xbrl': 'XBRL Instance',
    '.html': 'HTML Report',
    '.pdf': 'PDF Report',
    '.xml': 'XML Document'
}

# Primary format for financial reports
FCA_PRIMARY_FORMAT = '.ixbrl'

# FCA never uses ZIP files for financial reports
FCA_REQUIRES_EXTRACTION = False

# Download Configuration
FCA_DOWNLOAD_TIMEOUT = 30  # seconds
FCA_MAX_FILE_SIZE_MB = 50   # FCA files are typically smaller than SEC ZIPs
FCA_CHUNK_SIZE = 8192       # bytes for streaming

# Protocol Support
FCA_SUPPORTED_PROTOCOLS = ['http', 'https']  # FCA uses standard HTTP(S)

# Retry Configuration
FCA_MAX_RETRIES = 3
FCA_RETRY_DELAY = 2  # seconds
FCA_BACKOFF_FACTOR = 2  # exponential backoff multiplier

# URL Patterns
FCA_URL_PATTERNS = {
    'annual_report': '{base_url}/company/{company_number}/annual/{year}.ixbrl',
    'interim_report': '{base_url}/company/{company_number}/interim/{year}-{period}.ixbrl',
    'announcement': '{base_url}/company/{company_number}/announcement/{date}/{id}.html'
}

# File Naming Convention
FCA_FILE_NAME_PATTERN = "{company_number}_{filing_type}_{date}.{extension}"

# Download Path Structure
# FCA files go directly to parsed data directory (no extraction needed)
FCA_DOWNLOAD_PATH_PATTERN = "{market_type}/{company_number}/{filing_type}/{filename}"

# Error Messages
FCA_ERROR_MESSAGES = {
    'invalid_format': 'FCA filing format not recognized',
    'file_too_large': 'File exceeds maximum size limit',
    'download_timeout': 'Download timed out',
    'invalid_company_number': 'Invalid UK company number format'
}

# Validation Rules
FCA_VALIDATION_RULES = {
    'min_file_size': 1024,  # 1KB minimum
    'max_file_size': FCA_MAX_FILE_SIZE_MB * 1024 * 1024,
    'allowed_extensions': list(FCA_FILE_FORMATS.keys()),
    'require_checksum': False  # FCA doesn't provide checksums typically
}

# Status Tracking
FCA_DOWNLOAD_STATUSES = {
    'pending': 'Waiting to download',
    'downloading': 'Download in progress',
    'completed': 'Download successful',
    'failed': 'Download failed',
    'validated': 'File validated successfully'
}