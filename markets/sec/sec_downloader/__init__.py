"""
SEC Downloader Module
=====================

Provides comprehensive, SEC EDGAR-specific download functionality.
It adheres to SEC guidelines including rate limiting (10 requests/second) and user-agent requirements.

Architecture Components (Refactored):
- SECDownloadCoordinator: Main orchestration and download flow control.
- SECValidationHandler: Handles core SEC download validation rules.
- SECMetadataExtractor: Extracts filing metadata (e.g., CIK, accession number).
- SECURLResolver: Resolves the XBRL ZIP file URL using various strategies.
- SECDownloadDelegator: Delegates the actual file transfer to the generic downloader.
- SECMetricsRecorder: Records download metrics and outcomes.

Supporting Utilities:
- SECRateLimiter: Enforces 10 req/sec rate limit.
- SECDownloadMonitor: Tracks metrics and download history.
- SECIndexParser: Parses the index.json manifest.
- SECFileIdentifier: Logic for identifying XBRL ZIP patterns and URLs.
- ZIPIdentificationStrategy: Core pattern-matching and index-based strategies.

Usage:
    from markets.sec.sec_downloader import create_sec_downloader
    
    downloader = create_sec_downloader()
    await downloader.initialize()
    result = await downloader.download_filing(filing_id)
"""

# Core Coordinator and Factory
from .sec_download_coordinator import (
    SECDownloadCoordinator,
    create_sec_downloader,
    SEC_USER_AGENT_ENV,
    STRATEGY_SEARCHER_PROVIDED
)

# New Specialized Architecture Components
from .sec_metadata_extractor import SECMetadataExtractor
from .sec_url_resolver import SECURLResolver
from .sec_validation_handler import SECValidationHandler, ValidationResult
from .sec_download_delegator import SECDownloadDelegator
from .sec_metrics_recorder import SECMetricsRecorder

# Supporting Utilities (Rate Limiting, Monitoring, etc.)
from .sec_rate_limiter import (
    SECRateLimiter, 
    get_shared_sec_rate_limiter, 
    reset_shared_rate_limiter,
    RateLimitContext
)
from .sec_download_validator import SECDownloadValidator, validate_sec_download_ready
from .sec_index_parser import SECIndexParser, parse_index_json, parse_index_json_file
from .sec_file_identifier import SECFileIdentifier, identify_xbrl_zip, generate_zip_urls
from .sec_download_monitor import (
    SECDownloadMonitor, 
    get_sec_download_monitor, 
    reset_sec_download_monitor,
    SECDownloadMetrics
)
from .sec_download_strategies import (
    ZIPIdentificationStrategy,
    ZIPIdentificationResult,
    IndexBasedStrategy,
    PatternBasedStrategy,
    FallbackStrategy,
    StrategyChain,
    create_default_strategy_chain
)

__all__ = [
    # Main Coordinator & Core Factories
    'SECDownloadCoordinator',
    'create_sec_downloader',
    
    # New Specialized Components (Refactored Architecture)
    'SECMetadataExtractor',
    'SECURLResolver',
    'SECValidationHandler',
    'SECDownloadDelegator',
    'SECMetricsRecorder',
    
    # Validation
    'SECDownloadValidator',
    'validate_sec_download_ready',
    'ValidationResult',
    
    # Rate limiting
    'SECRateLimiter',
    'get_shared_sec_rate_limiter',
    'reset_shared_rate_limiter',
    'RateLimitContext',
    
    # Index parsing & File Identification
    'SECIndexParser',
    'parse_index_json',
    'parse_index_json_file',
    'SECFileIdentifier',
    'identify_xbrl_zip',
    'generate_zip_urls',
    
    # Monitoring
    'SECDownloadMonitor',
    'get_sec_download_monitor',
    'reset_sec_download_monitor',
    'SECDownloadMetrics',
    
    # Strategies
    'ZIPIdentificationStrategy',
    'ZIPIdentificationResult',
    'IndexBasedStrategy',
    'PatternBasedStrategy',
    'FallbackStrategy',
    'StrategyChain',
    'create_default_strategy_chain',

    # Constants
    'SEC_USER_AGENT_ENV',
    'STRATEGY_SEARCHER_PROVIDED',
]

__version__ = '1.0.0'
__author__ = 'Map Pro Team'
__market__ = 'sec'