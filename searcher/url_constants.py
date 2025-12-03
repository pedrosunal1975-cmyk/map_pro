"""
File: engines/searcher/url_constants.py
Path: engines/searcher/url_constants.py

URL Validation Constants
========================

Central location for all URL validation constants.
Extracted from url_validation.py to eliminate magic values.
"""

from typing import Dict, List, Set

# Valid URL schemes
VALID_URL_SCHEMES: Set[str] = {'http', 'https'}

# Default ports to remove during normalization
DEFAULT_PORTS: Set[str] = {':80', ':443'}

# Maximum file extension length (characters)
MAX_EXTENSION_LENGTH: int = 10

# Trusted domains by market type
# TODO: These should be moved to market-specific configuration files in /map_pro/markets/<market_name>/
# or loaded from database/config files rather than hardcoded here.
# This implementation is for reference/backward compatibility only.
# New markets should define their trusted domains in their market plugin configuration.
TRUSTED_DOMAINS: Dict[str, List[str]] = {
    'sec': [  # US SEC market
        'sec.gov',
        'data.sec.gov',
        'www.sec.gov'
    ],
    'fca': [  # UK FCA market
        'fca.org.uk',
        'api.fca.org.uk'
    ],
    'esma': [  # EU ESMA market
        'esma.europa.eu',
        'api.esma.europa.eu'
    ]
}

# Common downloadable file extensions
DOWNLOADABLE_FILE_EXTENSIONS: List[str] = [
    '.zip',
    '.tar',
    '.gz',
    '.xbrl',
    '.xml',
    '.htm',
    '.html',
    '.pdf',
    '.json',
    '.txt',
    '.ixbrl'
]

# Domain validation constants
MAX_DOMAIN_LABEL_LENGTH: int = 61
MIN_DOMAIN_LABEL_LENGTH: int = 1

# Domain pattern components
DOMAIN_LABEL_START_CHARS: str = 'a-zA-Z0-9'
DOMAIN_LABEL_MIDDLE_CHARS: str = 'a-zA-Z0-9\\-'
DOMAIN_LABEL_END_CHARS: str = 'a-zA-Z0-9'

# URL component separators
URL_PATH_SEPARATOR: str = '/'
URL_PORT_SEPARATOR: str = ':'
URL_EXTENSION_SEPARATOR: str = '.'

# Default URL scheme for normalization
DEFAULT_URL_SCHEME: str = 'https'