# engines/downloader/download_orchestrator.py
"""
Download Orchestrator
=====================

Core download orchestration logic.
Coordinates protocol handlers, validators, and database operations.

Responsibilities:
- Download workflow orchestration
- Market coordinator delegation
- Protocol handler selection
- Result processing

Design Pattern: Orchestrator Pattern
Benefits: Clear workflow, single responsibility, testable
"""

from pathlib import Path
from typing import Dict, Any, Optional

from database.models.core_models import Filing
from .download_result import DownloadResult
from .download_path_manager import DownloadPathManager
from .download_validation_coordinator import DownloadValidationCoordinator
from .download_database_operations import DownloadDatabaseOperations
from .protocol_handlers import ProtocolHandlerFactory
from .market_coordinator_factory import MarketCoordinatorFactory


class DownloadOrchestrator:
    """
    Orchestrates the complete download workflow.
    
    Handles delegation to market coordinators, protocol selection,
    validation, and database updates.
    """
    
    def __init__(
        self,
        protocol_factory: ProtocolHandlerFactory,
        validation_coordinator: DownloadValidationCoordinator,
        path_manager: DownloadPathManager,
        db_operations: DownloadDatabaseOperations,
        market_factory: MarketCoordinatorFactory,
        logger
    ):
        """
        Initialize download orchestrator.
        
        Args:
            protocol_factory: Factory for protocol handlers
            validation_coordinator: Validation coordinator
            path_manager: Download path manager
            db_operations: Database operations handler
            market_factory: Market coordinator factory
            logger: Logger instance
        """
        self.protocol_factory = protocol_factory
        self.validation_coordinator = validation_coordinator
        self.path_manager = path_manager
        self.db_operations = db_operations
        self.market_factory = market_factory
        self.logger = logger
    
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
        
        Args:
            filing: Filing database object
            session: Database session
            custom_headers: Market-specific headers (User-Agent, auth, etc.)
            override_url: Override filing.original_url (for ZIP identification)
            _from_market_coordinator: Flag to prevent infinite delegation loops
            
        Returns:
            DownloadResult with success/failure status
        """
        filing_id = filing.filing_universal_id
        self.logger.info(f"Starting download for filing: {filing_id}")
        
        # Try market-specific delegation first
        if not _from_market_coordinator:
            market_result = await self._try_market_delegation(filing, session)
            if market_result is not None:
                return market_result
        
        # Proceed with generic download
        return await self._execute_generic_download(
            filing=filing,
            session=session,
            custom_headers=custom_headers,
            override_url=override_url,
            from_market_coordinator=_from_market_coordinator
        )
    
    async def _try_market_delegation(
        self,
        filing: Filing,
        session
    ) -> Optional[DownloadResult]:
        """
        Attempt to delegate to market-specific coordinator.
        
        Args:
            filing: Filing database object
            session: Database session
            
        Returns:
            DownloadResult if delegation succeeded, None if no coordinator found
        """
        if not filing.entity:
            return None
        
        market_type = filing.entity.market_type
        coordinator = self.market_factory.get_coordinator(market_type, self)
        
        if not coordinator:
            self.logger.debug(
                f"No market coordinator found for {market_type} - handling directly"
            )
            return None
        
        self.logger.info(
            f"{market_type.upper()} market detected - routing to market coordinator"
        )
        
        try:
            return await coordinator.download_filing(filing, session)
        except Exception as e:
            error_msg = (
                f"{market_type.upper()} coordinator delegation failed: {str(e)}"
            )
            self.logger.error(error_msg)
            self.db_operations.update_filing_status(filing, 'failed', error_msg)
            return DownloadResult(success=False, error_message=error_msg)
    
    async def _execute_generic_download(
        self,
        filing: Filing,
        session,
        custom_headers: Optional[Dict[str, str]],
        override_url: Optional[str],
        from_market_coordinator: bool
    ) -> DownloadResult:
        """
        Execute generic download process.
        
        Args:
            filing: Filing database object
            session: Database session
            custom_headers: Optional custom headers
            override_url: Optional URL override
            from_market_coordinator: Whether called from market coordinator
            
        Returns:
            DownloadResult with success/failure status
        """
        filing_id = filing.filing_universal_id
        
        # Log download source
        self._log_download_source(filing, from_market_coordinator)
        
        # Validate and get URL
        url = override_url or filing.original_url
        if not self._validate_url(url, filing):
            return DownloadResult(
                success=False,
                error_message=f"No URL available for filing {filing_id}"
            )
        
        self.logger.info(f"Download URL: {url}")
        
        try:
            return await self._download_and_validate(
                filing=filing,
                session=session,
                url=url,
                custom_headers=custom_headers
            )
        except Exception as e:
            return self._handle_download_exception(filing, e)
    
    def _log_download_source(self, filing: Filing, from_market_coordinator: bool) -> None:
        """
        Log the source of the download request.
        
        Args:
            filing: Filing database object
            from_market_coordinator: Whether called from market coordinator
        """
        if from_market_coordinator:
            self.logger.info("Called from market coordinator - processing directly")
        else:
            market_type = filing.entity.market_type if filing.entity else 'unknown'
            self.logger.info(f"Market: {market_type} - handling with generic downloader")
    
    def _validate_url(self, url: Optional[str], filing: Filing) -> bool:
        """
        Validate download URL.
        
        Args:
            url: URL to validate
            filing: Filing object to update on failure
            
        Returns:
            True if URL is valid, False otherwise
        """
        if not url or not url.strip():
            filing_id = filing.filing_universal_id
            self.logger.error(f"No URL available for filing {filing_id}")
            self.db_operations.update_filing_status(filing, 'failed')
            return False
        return True
    
    async def _download_and_validate(
        self,
        filing: Filing,
        session,
        url: str,
        custom_headers: Optional[Dict[str, str]]
    ) -> DownloadResult:
        """
        Execute download with pre/post validation.
        
        Args:
            filing: Filing database object
            session: Database session
            url: Download URL
            custom_headers: Optional custom headers
            
        Returns:
            DownloadResult with success/failure status
        """
        # Generate download path
        save_path = self.path_manager.generate_download_path(filing, url)
        self.logger.debug(f"Download path: {save_path}")
        
        # Pre-download validation
        is_valid, error_msg = self.validation_coordinator.validate_pre_download(
            url, save_path
        )
        if not is_valid:
            self.db_operations.update_filing_status(filing, 'failed', error_msg)
            return DownloadResult(success=False, error_message=error_msg)
        
        # Execute download
        handler = self.protocol_factory.get_handler(url)
        self.logger.debug(f"Using protocol handler: {type(handler).__name__}")
        
        self.db_operations.update_filing_status(filing, 'downloading')
        result = await handler.download(
            url=url,
            save_path=save_path,
            custom_headers=custom_headers
        )
        
        # Handle result
        return await self._process_download_result(
            result=result,
            filing=filing,
            session=session,
            save_path=save_path
        )
    
    async def _process_download_result(
        self,
        result: DownloadResult,
        filing: Filing,
        session,
        save_path: Path
    ) -> DownloadResult:
        """
        Process download result with post-validation and database updates.
        
        Args:
            result: Download result from handler
            filing: Filing database object
            session: Database session
            save_path: Path where file was saved
            
        Returns:
            Updated DownloadResult
        """
        if not result.success:
            self.db_operations.update_filing_status(
                filing, 'failed', result.error_message
            )
            return result
        
        # Post-download validation
        is_valid, error_msg = self.validation_coordinator.validate_post_download(
            save_path
        )
        
        if not is_valid:
            self.validation_coordinator.cleanup_failed_download(save_path)
            self.db_operations.update_filing_status(filing, 'failed', error_msg)
            result.success = False
            result.error_message = error_msg
            return result
        
        # Update database on success
        file_size_mb = getattr(result, 'file_size_mb', 0.0)
        self.db_operations.update_successful_download(filing, save_path, file_size_mb)
        
        # Create extraction job if needed
        if save_path.suffix.lower() == '.zip':
            self.db_operations.create_extraction_job(filing.filing_universal_id, session)
        
        self.logger.info(
            f"Download completed: {filing.market_filing_id} - {file_size_mb:.2f}MB"
        )
        
        return result
    
    def _handle_download_exception(
        self,
        filing: Filing,
        exception: Exception
    ) -> DownloadResult:
        """
        Handle download exception.
        
        Args:
            filing: Filing object to update
            exception: Exception that occurred
            
        Returns:
            DownloadResult with failure status
        """
        error_msg = f"Download error: {str(exception)}"
        self.logger.error(error_msg)
        self.db_operations.update_filing_status(filing, 'failed', error_msg)
        return DownloadResult(success=False, error_message=error_msg)