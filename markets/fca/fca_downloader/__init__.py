"""
FCA Downloader Module
====================

Market-specific downloader configuration for UK FCA.
Uses the generic engines/downloader/ engine with FCA-specific constants.

Key Differences from SEC:
- Direct file downloads (no ZIP extraction)
- Different URL patterns  
- Smaller file sizes
- Different validation rules
"""

from .fca_constants import (
    # URLs
    FCA_BASE_URL,
    FCA_DOCUMENTS_BASE_URL,
    
    # File formats
    FCA_FILE_FORMATS,
    FCA_PRIMARY_FORMAT,
    FCA_REQUIRES_EXTRACTION,
    
    # Configuration
    FCA_DOWNLOAD_TIMEOUT,
    FCA_MAX_FILE_SIZE_MB,
    FCA_CHUNK_SIZE,
    
    # Protocol support
    FCA_SUPPORTED_PROTOCOLS,
    
    # Retry settings
    FCA_MAX_RETRIES,
    FCA_RETRY_DELAY,
    FCA_BACKOFF_FACTOR,
    
    # Patterns
    FCA_URL_PATTERNS,
    FCA_FILE_NAME_PATTERN,
    FCA_DOWNLOAD_PATH_PATTERN,
    
    # Error handling
    FCA_ERROR_MESSAGES,
    
    # Validation
    FCA_VALIDATION_RULES,
    
    # Status tracking
    FCA_DOWNLOAD_STATUSES
)

from .fca_download_helper import (
    FCADownloadHelper,
    create_fca_download_helper,
    build_fca_download_url,
    validate_fca_file
)

__all__ = [
    # Constants
    'FCA_BASE_URL',
    'FCA_DOCUMENTS_BASE_URL',
    'FCA_FILE_FORMATS',
    'FCA_PRIMARY_FORMAT',
    'FCA_REQUIRES_EXTRACTION',
    'FCA_DOWNLOAD_TIMEOUT',
    'FCA_MAX_FILE_SIZE_MB',
    'FCA_CHUNK_SIZE',
    'FCA_SUPPORTED_PROTOCOLS',
    'FCA_MAX_RETRIES',
    'FCA_RETRY_DELAY',
    'FCA_BACKOFF_FACTOR',
    'FCA_URL_PATTERNS',
    'FCA_FILE_NAME_PATTERN',
    'FCA_DOWNLOAD_PATH_PATTERN',
    'FCA_ERROR_MESSAGES',
    'FCA_VALIDATION_RULES',
    'FCA_DOWNLOAD_STATUSES',
    
    # Helper classes and functions
    'FCADownloadHelper',
    'create_fca_download_helper',
    'build_fca_download_url',
    'validate_fca_file'
]

__version__ = '1.0.0'
__author__ = 'Map Pro Team'