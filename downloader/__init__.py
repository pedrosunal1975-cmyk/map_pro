"""
Map Pro Downloader Engine
=========================

Market-agnostic file downloader for all regulatory markets.
Downloads files from URLs discovered by searcher engine.

Components:
- DownloadCoordinator: Main engine (inherits BaseEngine)
- ProtocolHandlers: HTTP/HTTPS/FTP download handlers
- StreamHandler: Memory-efficient streaming
- RetryManager: Exponential backoff retry logic
- DownloadValidator: Pre/post download validation
- DownloadResult: Standardized result objects

Architecture:
- Market-agnostic: Works with any URL from any market
- Protocol-flexible: HTTP, HTTPS, FTP support
- Memory-safe: Streams large files without loading to RAM
- Database-integrated: Updates filings.download_status
- Retry-resilient: Handles network failures gracefully

Usage:
    from engines.downloader import create_downloader_engine
    
    engine = create_downloader_engine()
    engine.initialize()
    engine.start()
    
    # Or process single job:
    job_data = {'filing_universal_id': filing_id}
    result = await engine.process_job(job_data)
"""

from .download_job_processor import DownloadJobProcessor
from .download_path_manager import DownloadPathManager
from .market_coordinator_factory import MarketCoordinatorFactory
from .download_coordinator import DownloadCoordinator, create_downloader_engine
from .download_result import DownloadResult, BatchDownloadResult, ValidationResult
from .download_validator import DownloadValidator, validate_download_ready, validate_download_complete
from .protocol_handlers import (
    BaseProtocolHandler,
    HTTPHandler,
    HTTPSHandler,
    FTPHandler,
    ProtocolHandlerFactory
)
from .stream_handler import StreamHandler
from .retry_manager import RetryManager, RetryConfig, RetryStrategy, retry_async, retry_sync

__all__ = [
    # Main engine
    'DownloadCoordinator',
    'create_downloader_engine',
    
    # Result objects
    'DownloadResult',
    'BatchDownloadResult',
    'ValidationResult',
    
    # Validator
    'DownloadValidator',
    'validate_download_ready',
    'validate_download_complete',
    
    # Protocol handlers
    'BaseProtocolHandler',
    'HTTPHandler',
    'HTTPSHandler',
    'FTPHandler',
    'ProtocolHandlerFactory',
    
    # Stream handler
    'StreamHandler',
    
    # Retry logic
    'RetryManager',
    'RetryConfig',
    'RetryStrategy',
    'retry_async',
    'retry_sync',

    # --- New Components ---
    'DownloadJobProcessor',
    'DownloadPathManager',
    'MarketCoordinatorFactory',
]

__version__ = '1.0.0'
__author__ = 'Map Pro Team'