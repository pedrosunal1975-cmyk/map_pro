# Path: library/engine/constants.py
"""
Library Engine Constants

Centralized configuration for all hardcoded values in library engine.
All constants, patterns, URLs, and configuration values live here.

NO HARDCODED VALUES in other engine/ files - they import from here.
"""

import re

# ============================================================================
# TAXONOMY AUTHORITY CONFIGURATION
# ============================================================================

# Known standard XBRL taxonomy authorities
# These are recognized as official taxonomy sources
STANDARD_AUTHORITIES = {
    'xbrl.sec.gov',
    'sec.gov',
    'fasb.org',
    'xbrl.fasb.org',
    'xbrl.org',
    'www.xbrl.org',
    'ifrs.org',
    'xbrl.ifrs.org',
    'esma.europa.eu',
    'www.esma.europa.eu',
    'frc.org.uk',
}

# Authority domain transformations
# Maps declared authority → actual download authority
# Example: fasb.org → xbrl.fasb.org
AUTHORITY_TRANSFORMS = {
    'fasb.org': 'xbrl.fasb.org',
    'sec.gov': 'xbrl.sec.gov',
    'ifrs.org': 'xbrl.ifrs.org',
    'xbrl.org': 'xbrl.org',
    'esma.europa.eu': 'www.esma.europa.eu',
}

# Authority variations for URL discovery
# Primary variations listed first (most likely to work)
AUTHORITY_VARIATIONS = {
    'fasb.org': ['xbrl.fasb.org', 'fasb.org'],
    'sec.gov': ['xbrl.sec.gov', 'sec.gov'],
    'xbrl.org': ['xbrl.org', 'www.xbrl.org'],
    'ifrs.org': ['xbrl.ifrs.org', 'ifrs.org'],
    'esma.europa.eu': ['www.esma.europa.eu', 'esma.europa.eu'],
}

# ============================================================================
# COMPANY EXTENSION DETECTION
# ============================================================================

# Regex patterns to identify company-specific extensions
# These namespaces should be SKIPPED (data already in filing)
COMPANY_EXTENSION_PATTERNS = [
    r'https?://(?:www\.)?[^/]+\.com/',      # .com domains
    r'https?://(?:www\.)?[^/]+\.net/',      # .net domains
    r'https?://(?:www\.)?[^/]+\.co\.uk/',   # .co.uk domains
    r'https?://(?:www\.)?[^/]+\.org/(?!xbrl)',  # .org except xbrl.org
]

# Compile patterns for performance
COMPILED_COMPANY_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) 
    for pattern in COMPANY_EXTENSION_PATTERNS
]

# ============================================================================
# URL CONSTRUCTION PATTERNS
# ============================================================================

# Standard URL construction templates
# These are tried in order during URL discovery

# Primary pattern: {authority}/{taxonomy}/{version}/{taxonomy}-{version}.zip
URL_PATTERN_PRIMARY = "https://{authority}/{taxonomy}/{version}/{taxonomy}-{version}.zip"

# Alternative patterns (for fallback)
URL_PATTERN_NO_VERSION_FOLDER = "https://{authority}/{taxonomy}/{taxonomy}-{version}.zip"
URL_PATTERN_TAXONOMIES_FOLDER = "https://{authority}/taxonomies/{taxonomy}-{version}.zip"
URL_PATTERN_SIMPLE = "https://{authority}/{taxonomy}-{version}.zip"

# All URL patterns in priority order
URL_CONSTRUCTION_PATTERNS = [
    URL_PATTERN_PRIMARY,
    URL_PATTERN_NO_VERSION_FOLDER,
    URL_PATTERN_TAXONOMIES_FOLDER,
    URL_PATTERN_SIMPLE,
]

# ============================================================================
# URL DISCOVERY CONFIGURATION
# ============================================================================

# HTTP request timeout (seconds)
URL_DISCOVERY_TIMEOUT = 10

# Maximum HTTP redirects to follow
URL_DISCOVERY_MAX_REDIRECTS = 3

# Maximum candidate URLs to test per taxonomy
URL_DISCOVERY_MAX_CANDIDATES = 50

# Protocols to try (in order)
URL_PROTOCOLS = ['https', 'http']

# ============================================================================
# VERSION VALIDATION
# ============================================================================

# Regex pattern for valid taxonomy version
# Must be 4-digit year (2020-2099)
VERSION_PATTERN = r'^\d{4}$'
COMPILED_VERSION_PATTERN = re.compile(VERSION_PATTERN)

# Valid version range
VERSION_MIN = 2000
VERSION_MAX = 2099

# ============================================================================
# TAXONOMY NAMING
# ============================================================================

# Reserved taxonomy names (should be skipped or handled specially)
RESERVED_TAXONOMY_NAMES = {
    'unknown',
    'company-extension',
    'custom',
    'private',
}

# Included taxonomies (bundled within parent taxonomies like us-gaap/dei)
# These don't need separate downloads - they're already included in larger taxonomies
INCLUDED_TAXONOMIES = {
    'country',      # Country codes (included in dei/us-gaap)
    'currency',     # Currency codes (included in dei/us-gaap)
    'exch',         # Exchange codes (included in dei/us-gaap)
    'naics',        # Industry codes (included in us-gaap)
    'sic',          # Industry codes legacy (included in us-gaap)
    'stpr',         # State/province codes (included in dei/us-gaap)
}

# Parent taxonomies that include smaller taxonomies
PARENT_TAXONOMIES = {
    'us-gaap',
    'dei',
}

# ============================================================================
# DATABASE STATUS VALUES
# ============================================================================

# Taxonomy library download status
STATUS_PENDING = 'pending'
STATUS_DOWNLOADING = 'downloading'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'
STATUS_VALIDATING = 'validating'
STATUS_VALID = 'valid'
STATUS_INVALID = 'invalid'

# All valid status values
VALID_STATUSES = {
    STATUS_PENDING,
    STATUS_DOWNLOADING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_VALIDATING,
    STATUS_VALID,
    STATUS_INVALID,
}

# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

# Maximum retry attempts for downloads
MAX_RETRY_ATTEMPTS = 3

# Retry delay (seconds) - exponential backoff
RETRY_INITIAL_DELAY = 2
RETRY_MAX_DELAY = 60
RETRY_BACKOFF_MULTIPLIER = 2

# ============================================================================
# FILE VALIDATION
# ============================================================================

# Valid taxonomy file extensions
VALID_TAXONOMY_EXTENSIONS = {
    '.xsd',   # XML Schema Definition
    '.xml',   # XML files
    '.zip',   # Archive files
}

# Minimum file size for valid download (bytes)
MIN_VALID_FILE_SIZE = 100

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log message prefixes (from library/constants.py)
# Note: These are defined in library/constants.py and imported there
# Listed here for reference only

# LOG_INPUT = "[INPUT]"
# LOG_PROCESS = "[PROCESS]"
# LOG_OUTPUT = "[OUTPUT]"

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Cache TTL (time-to-live) in seconds
CACHE_TTL_DEFAULT = 3600  # 1 hour
CACHE_TTL_LONG = 86400    # 24 hours

# Maximum cache entries
CACHE_MAX_ENTRIES = 1000

# ============================================================================
# NAMESPACE PARSING
# ============================================================================

# Minimum path components required in namespace
MIN_NAMESPACE_PATH_COMPONENTS = 1

# Maximum namespace URI length
MAX_NAMESPACE_LENGTH = 500

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_valid_version(version: str) -> bool:
    """
    Check if version string is valid.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid version format
    """
    if not version or not isinstance(version, str):
        return False
    
    if not COMPILED_VERSION_PATTERN.match(version):
        return False
    
    try:
        year = int(version)
        return VERSION_MIN <= year <= VERSION_MAX
    except ValueError:
        return False


def is_reserved_taxonomy_name(name: str) -> bool:
    """
    Check if taxonomy name is reserved.
    
    Args:
        name: Taxonomy name to check
        
    Returns:
        True if reserved name
    """
    return name.lower() in RESERVED_TAXONOMY_NAMES


def is_included_taxonomy(name: str) -> bool:
    """
    Check if taxonomy is included within parent taxonomies.
    
    These taxonomies (like country, currency, exch) are bundled inside
    larger taxonomies (us-gaap, dei) and don't need separate downloads.
    
    Args:
        name: Taxonomy name to check
        
    Returns:
        True if this is an included taxonomy
    """
    return name.lower() in INCLUDED_TAXONOMIES


def is_company_extension(namespace: str, authority: str = None) -> bool:
    """
    Check if namespace is a company-specific extension.
    
    Args:
        namespace: Namespace URI
        authority: Optional authority domain
        
    Returns:
        True if company extension
    """
    # Check against company extension patterns
    for pattern in COMPILED_COMPANY_PATTERNS:
        if pattern.match(namespace):
            # Additional check: not a standard authority
            if authority and authority not in STANDARD_AUTHORITIES:
                return True
            elif not authority:
                return True
    
    return False


def get_authority_transform(authority: str) -> str:
    """
    Get transformed authority domain.
    
    Args:
        authority: Original authority domain
        
    Returns:
        Transformed authority or original if no transform
    """
    # Check exact match
    if authority in AUTHORITY_TRANSFORMS:
        return AUTHORITY_TRANSFORMS[authority]
    
    # Check if authority contains any known base domain
    for base, transformed in AUTHORITY_TRANSFORMS.items():
        if base in authority:
            return transformed
    
    # No transform, return original
    return authority


def get_authority_variations(authority: str) -> list:
    """
    Get all authority domain variations to try.
    
    Args:
        authority: Base authority domain
        
    Returns:
        List of authority variations (ordered by priority)
    """
    # Check if we have known variations
    for base_domain, variants in AUTHORITY_VARIATIONS.items():
        if base_domain in authority or authority in base_domain:
            return variants.copy()
    
    # Generate variations for unknown authority
    variants = [authority]
    
    if authority.startswith('xbrl.'):
        # Remove xbrl. subdomain
        variants.append(authority[5:])
    else:
        # Add xbrl. subdomain (try first)
        variants.insert(0, f"xbrl.{authority}")
    
    return variants


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Authority configuration
    'STANDARD_AUTHORITIES',
    'AUTHORITY_TRANSFORMS',
    'AUTHORITY_VARIATIONS',
    
    # Company extensions
    'COMPANY_EXTENSION_PATTERNS',
    'COMPILED_COMPANY_PATTERNS',
    
    # URL patterns
    'URL_PATTERN_PRIMARY',
    'URL_PATTERN_NO_VERSION_FOLDER',
    'URL_PATTERN_TAXONOMIES_FOLDER',
    'URL_PATTERN_SIMPLE',
    'URL_CONSTRUCTION_PATTERNS',
    
    # Discovery config
    'URL_DISCOVERY_TIMEOUT',
    'URL_DISCOVERY_MAX_REDIRECTS',
    'URL_DISCOVERY_MAX_CANDIDATES',
    'URL_PROTOCOLS',
    
    # Validation
    'VERSION_PATTERN',
    'COMPILED_VERSION_PATTERN',
    'VERSION_MIN',
    'VERSION_MAX',
    
    # Taxonomy naming
    'RESERVED_TAXONOMY_NAMES',
    'INCLUDED_TAXONOMIES',
    'PARENT_TAXONOMIES',
    
    # Database status
    'STATUS_PENDING',
    'STATUS_DOWNLOADING',
    'STATUS_COMPLETED',
    'STATUS_FAILED',
    'STATUS_VALIDATING',
    'STATUS_VALID',
    'STATUS_INVALID',
    'VALID_STATUSES',
    
    # Retry config
    'MAX_RETRY_ATTEMPTS',
    'RETRY_INITIAL_DELAY',
    'RETRY_MAX_DELAY',
    'RETRY_BACKOFF_MULTIPLIER',
    
    # File validation
    'VALID_TAXONOMY_EXTENSIONS',
    'MIN_VALID_FILE_SIZE',
    
    # Cache config
    'CACHE_TTL_DEFAULT',
    'CACHE_TTL_LONG',
    'CACHE_MAX_ENTRIES',
    
    # Namespace parsing
    'MIN_NAMESPACE_PATH_COMPONENTS',
    'MAX_NAMESPACE_LENGTH',
    
    # Utility functions
    'is_valid_version',
    'is_reserved_taxonomy_name',
    'is_included_taxonomy',
    'is_company_extension',
    'get_authority_transform',
    'get_authority_variations',
]