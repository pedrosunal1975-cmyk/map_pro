# engines/downloader/download_coordinator.py
"""
Map Pro Download Coordinator
============================

Generic market-agnostic downloader engine - inherits from BaseEngine.
Downloads files from URLs stored in database, validates, and updates status.

Market-Agnostic Design:
- Works with any URL from any regulatory market
- Delegates market-specific logic to market coordinators
- Accepts custom headers from market coordinators
- Protocol-flexible: HTTP, HTTPS, FTP support
- Memory-safe: Streams large files without loading to RAM

Market-Specific Delegation Pattern:
- Automatically detects if market has a coordinator (e.g., SEC, FCA, ESMA)
- Pattern: markets/{market}/{market}_downloader/create_{market}_downloader()  
- Market coordinators handle: rate limiting, user-agents, URL identification
- Generic coordinator handles: actual download, validation, database updates
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from engines.base.engine_base import BaseEngine
from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from database.models.core_models import Filing
from shared.constants.job_constants import JobType

from .protocol_handlers import ProtocolHandlerFactory
from .download_validator import DownloadValidator
from .download_result import DownloadResult
from .download_path_manager import DownloadPathManager
from .download_job_processor import DownloadJobProcessor
from .market_coordinator_factory import MarketCoordinatorFactory
from .download_config import DownloadConfig, DEFAULT_DOWNLOAD_CONFIG
from .download_database_operations import DownloadDatabaseOperations
from .download_validation_coordinator import DownloadValidationCoordinator
from .download_orchestrator import DownloadOrchestrator

logger = get_logger(__name__, 'engine')


class DownloadCoordinator(BaseEngine):
    """
    Market-agnostic downloader engine.
    
    Responsibilities:
    - Coordinate download workflow
    - Manage dependencies between components
    - Provide engine interface for job processing
    - Handle initialization and cleanup
    
    Does NOT handle:
    - URL discovery (searcher engine handles this)
    - Archive extraction (extractor engine handles this)
    - Market-specific logic (market coordinators handle this)
    - Direct database operations (database operations handler)
    - Direct validation (validation coordinator handles this)
    
    Design Pattern: Facade + Dependency Injection
    Benefits: Clear interface, testable, maintainable
    """
    
    def __init__(
        self,
        user_agent: Optional[str] = None,
        config: Optional[DownloadConfig] = None
    ):
        """
        Initialize downloader engine.
        
        Args:
            user_agent: Default user-agent (can be overridden by market coordinators)
            config: Download configuration (uses defaults if not provided)
        """
        super().__init__("downloader")
        
        # Use provided config or default
        self.config = config or DEFAULT_DOWNLOAD_CONFIG
        
        # Initialize core components
        self.protocol_factory = self._create_protocol_factory(user_agent)
        self.validator = self._create_validator()
        self.path_manager = DownloadPathManager(map_pro_paths)
        self.data_formatter = DownloadJobProcessor(self.logger)
        self.market_factory = MarketCoordinatorFactory(self.logger)
        
        # Initialize operation handlers
        self.db_operations = DownloadDatabaseOperations(self.logger)
        self.validation_coordinator = DownloadValidationCoordinator(
            self.validator,
            self.logger
        )
        
        # Initialize orchestrator with all dependencies
        self.orchestrator = DownloadOrchestrator(
            protocol_factory=self.protocol_factory,
            validation_coordinator=self.validation_coordinator,
            path_manager=self.path_manager,
            db_operations=self.db_operations,
            market_factory=self.market_factory,
            logger=self.logger
        )
        
        self.logger.info("Download coordinator initialized (market-agnostic)")
    
    def _create_protocol_factory(self, user_agent: Optional[str]) -> ProtocolHandlerFactory:
        """
        Create protocol handler factory with configuration.
        
        Args:
            user_agent: Optional user agent string
            
        Returns:
            Configured ProtocolHandlerFactory instance
        """
        return ProtocolHandlerFactory(
            default_timeout=self.config.protocol.DEFAULT_TIMEOUT_SECONDS,
            default_chunk_size=self.config.protocol.DEFAULT_CHUNK_SIZE_BYTES,
            user_agent=user_agent
        )
    
    def _create_validator(self) -> DownloadValidator:
        """
        Create download validator with configuration.
        
        Returns:
            Configured DownloadValidator instance
        """
        return DownloadValidator(
            max_file_size_mb=self.config.validation.MAX_FILE_SIZE_MB,
            min_free_space_mb=self.config.validation.MIN_FREE_SPACE_MB,
            verify_checksums=self.config.validation.VERIFY_CHECKSUMS
        )
    
    def get_primary_database(self) -> str:
        """
        Return primary database name.
        
        Returns:
            Database name string
        """
        return 'core'
    
    def get_supported_job_types(self) -> List[str]:
        """
        Return supported job types.
        
        Returns:
            List of supported job type strings
        """
        return [JobType.DOWNLOAD_FILING.value]
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process download job.
        
        This is the main entry point when used as a standalone engine.
        Market coordinators should call download_filing() directly.
        
        Args:
            job_data: Job information with filing_id
            
        Returns:
            Result dictionary with download status
            
        Raises:
            EngineError: If filing_id is missing or invalid
        """
        filing_id = self.data_formatter.extract_filing_id(job_data)
        self.logger.debug(f"Processing download job for filing: {filing_id}")
        
        try:
            with self.get_session() as session:
                filing = self.db_operations.get_filing_by_id(filing_id, session)
                result = await self.download_filing(filing, session)
                
                return self.data_formatter.create_result_dict(
                    result=result,
                    filing_id=filing_id
                )
                
        except Exception as e:
            self.logger.error(f"Download processing failed for {filing_id}: {str(e)}")
            return self.data_formatter.create_error_dict(filing_id, str(e))
    
    async def download_filing(
        self,
        filing: Filing,
        session,
        custom_headers: Optional[Dict[str, str]] = None,
        override_url: Optional[str] = None,
        _from_market_coordinator: bool = False
    ) -> DownloadResult:
        """
        Download filing from URL.
        
        Market-agnostic with dynamic delegation to market coordinators.
        This method is the main public interface for downloading filings.
        
        Args:
            filing: Filing database object
            session: Database session
            custom_headers: Market-specific headers (User-Agent, auth, etc.)
            override_url: Override filing.original_url (for ZIP identification)
            _from_market_coordinator: Internal flag to prevent infinite loops
            
        Returns:
            DownloadResult with success/failure status
        """
        return await self.orchestrator.download_filing(
            filing=filing,
            session=session,
            custom_headers=custom_headers,
            override_url=override_url,
            _from_market_coordinator=_from_market_coordinator
        )
    
    def _engine_specific_initialization(self) -> bool:
        """
        Downloader-specific initialization.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Validate downloads directory exists
            downloads_dir = map_pro_paths.data_root / 'downloads'
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Downloader initialization successful")
            return True
            
        except OSError as e:
            self.logger.error(f"Failed to create downloads directory: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Downloader initialization failed: {e}")
            return False
    
    def _get_engine_specific_status(self) -> Dict[str, Any]:
        """
        Get downloader-specific status.
        
        Returns:
            Dictionary containing engine status information
        """
        return {
            'protocols_supported': self.config.protocol.SUPPORTED_PROTOCOLS,
            'max_file_size_mb': self.config.validation.MAX_FILE_SIZE_MB,
            'verify_checksums': self.config.validation.VERIFY_CHECKSUMS,
            'market_agnostic': True,
            'timeout_seconds': self.config.protocol.DEFAULT_TIMEOUT_SECONDS,
            'chunk_size_bytes': self.config.protocol.DEFAULT_CHUNK_SIZE_BYTES
        }
    
    async def cleanup(self) -> None:
        """
        Cleanup resources.
        
        Closes all protocol handlers and releases resources.
        """
        try:
            await self.protocol_factory.close_all()
            self.logger.info("Downloader cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during downloader cleanup: {e}")


def create_downloader_engine(
    user_agent: Optional[str] = None,
    config: Optional[DownloadConfig] = None
) -> DownloadCoordinator:
    """
    Factory function to create downloader engine.
    
    Args:
        user_agent: Default user-agent for downloads
        config: Download configuration (uses defaults if not provided)
        
    Returns:
        DownloadCoordinator instance
    """
    return DownloadCoordinator(user_agent=user_agent, config=config)