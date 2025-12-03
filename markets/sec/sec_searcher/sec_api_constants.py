# File: /map_pro/markets/sec/sec_searcher/sec_api_constants.py

"""
SEC API Configuration Constants
================================

Centralized constants for SEC EDGAR API client configuration.
Eliminates magic numbers and provides clear, maintainable configuration values.
"""

# HTTP Configuration
DEFAULT_TIMEOUT_SECONDS = 30
MAX_REQUEST_RETRIES = 3
BASE_RETRY_DELAY_SECONDS = 2
RATE_LIMIT_RETRY_MULTIPLIER = 2

# Response Processing
MAX_RESPONSE_PREVIEW_LENGTH = 200

# SEC API Endpoints
SEC_BASE_URL = "https://data.sec.gov"
SEC_ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data/"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Rate Limiting
SEC_RATE_LIMIT_PER_SECOND = 10

# CIK Format
CIK_LENGTH = 10
CIK_PADDING_CHAR = '0'

# HTTP Status Codes
HTTP_STATUS_OK = 200
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_TOO_MANY_REQUESTS = 429

# Content Types
CONTENT_TYPE_HTML = 'text/html'
CONTENT_TYPE_JSON = 'application/json'

# HTML Markers
HTML_DOCTYPE_PREFIX = '<!DOCTYPE'
HTML_TAG_PREFIX = '<html'

# Error Detection Keywords
ERROR_KEYWORD_NOT_FOUND = 'not found'
ERROR_KEYWORD_404 = '404'
ERROR_KEYWORD_RATE_LIMIT = 'rate limit'
ERROR_KEYWORD_TOO_MANY_REQUESTS = 'too many requests'

# Default User Agent
DEFAULT_USER_AGENT = "MapPro/1.0 (system@mappro.com)"
ENV_USER_AGENT_KEY = 'MAP_PRO_SEC_USER_AGENT'

# URL Formats
SUBMISSIONS_URL_FORMAT = "{base}/submissions/CIK{cik}.json"
COMPANY_FACTS_URL_FORMAT = "{base}/api/xbrl/companyfacts/CIK{cik}.json"
FILING_INDEX_URL_FORMAT = "{archives_base}{cik_no_zeros}/{accession_no_dashes}/index.json"

# Error Messages
ERROR_MSG_RESOURCE_NOT_FOUND = "Resource not found: {url}"
ERROR_MSG_RATE_LIMIT_EXCEEDED = "Rate limit exceeded: {url}"
ERROR_MSG_HTML_RESPONSE = "HTML response received (file likely doesn't exist): {url}"
ERROR_MSG_INVALID_JSON = "Invalid JSON response: {error}"
ERROR_MSG_HTTP_ERROR = "HTTP {status}"
ERROR_MSG_INDEX_NOT_FOUND = "index.json not found (404)"
ERROR_MSG_INDEX_HTML = "index.json returned HTML"
ERROR_MSG_FAILED_AFTER_RETRIES = "Failed after {retries} attempts"

# SEC Error Messages by Status Code
SEC_ERROR_MESSAGES = {
    400: "Bad Request - Invalid parameters",
    401: "Unauthorized - Authentication required",
    403: "Forbidden - Access denied",
    404: "Not Found - Resource does not exist",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Internal Server Error - SEC service error",
    502: "Bad Gateway - SEC service unavailable",
    503: "Service Unavailable - SEC temporarily unavailable",
    504: "Gateway Timeout - SEC service timeout"
}

__all__ = [
    'DEFAULT_TIMEOUT_SECONDS',
    'MAX_REQUEST_RETRIES',
    'BASE_RETRY_DELAY_SECONDS',
    'RATE_LIMIT_RETRY_MULTIPLIER',
    'MAX_RESPONSE_PREVIEW_LENGTH',
    'SEC_BASE_URL',
    'SEC_ARCHIVES_BASE_URL',
    'SEC_COMPANY_TICKERS_URL',
    'SEC_RATE_LIMIT_PER_SECOND',
    'CIK_LENGTH',
    'CIK_PADDING_CHAR',
    'HTTP_STATUS_OK',
    'HTTP_STATUS_NOT_FOUND',
    'HTTP_STATUS_TOO_MANY_REQUESTS',
    'CONTENT_TYPE_HTML',
    'CONTENT_TYPE_JSON',
    'HTML_DOCTYPE_PREFIX',
    'HTML_TAG_PREFIX',
    'ERROR_KEYWORD_NOT_FOUND',
    'ERROR_KEYWORD_404',
    'ERROR_KEYWORD_RATE_LIMIT',
    'ERROR_KEYWORD_TOO_MANY_REQUESTS',
    'DEFAULT_USER_AGENT',
    'ENV_USER_AGENT_KEY',
    'SUBMISSIONS_URL_FORMAT',
    'COMPANY_FACTS_URL_FORMAT',
    'FILING_INDEX_URL_FORMAT',
    'ERROR_MSG_RESOURCE_NOT_FOUND',
    'ERROR_MSG_RATE_LIMIT_EXCEEDED',
    'ERROR_MSG_HTML_RESPONSE',
    'ERROR_MSG_INVALID_JSON',
    'ERROR_MSG_HTTP_ERROR',
    'ERROR_MSG_INDEX_NOT_FOUND',
    'ERROR_MSG_INDEX_HTML',
    'ERROR_MSG_FAILED_AFTER_RETRIES',
    'SEC_ERROR_MESSAGES'
]