"""
Library Operations.

Library management and dependency analysis operations.

Location: tools/cli/library_operations.py
"""

import asyncio
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from tools.cli.engine_display import (
    ExitCode,
    LibraryDisplay,
    MessageDisplay
)


logger = get_logger(__name__, 'maintenance')


class LibraryOperationError(Exception):
    """Base exception for library operations."""
    pass


class LibraryAnalyzerNotAvailableError(LibraryOperationError):
    """Library analyzer not available."""
    pass


class InvalidFilingIdError(LibraryOperationError):
    """Invalid filing ID."""
    pass


class LibraryOperations:
    """Library management operations."""
    
    def __init__(self, library_analyzer=None):
        """
        Initialize library operations.
        
        Args:
            library_analyzer: Library dependency analyzer instance (optional)
        """
        self.library_analyzer = library_analyzer
        self.logger = logger
        self.display = LibraryDisplay()
        self.message = MessageDisplay()
    
    def analyze_dependencies(self, filing_id: str, market_type: str = 'sec') -> int:
        """
        Analyze library dependencies for a filing.
        
        Args:
            filing_id: Filing ID to analyze
            market_type: Market type (default: 'sec')
            
        Returns:
            Exit code
        """
        try:
            self._validate_filing_id(filing_id)
            self._ensure_library_analyzer()
            
            print(f"[SEARCH] Analyzing library dependencies for filing {filing_id}...")
            
            # Create job data
            job_data = {
                'market_type': market_type,
                'parameters': {
                    'filing_universal_id': filing_id,
                    'market_type': market_type
                }
            }
            
            # Run analysis (async)
            result = asyncio.run(self.library_analyzer.process_job(job_data))
            
            if result.get('success'):
                self.display.print_analysis_results(result)
                
                # Return partial success if libraries not ready
                report = result.get('analysis_report', {})
                if not report.get('libraries_ready', False):
                    return ExitCode.PARTIAL_SUCCESS
                
                return ExitCode.SUCCESS
            else:
                error_msg = result.get('error', 'Unknown error')
                self.message.error(f"Analysis failed: {error_msg}")
                return ExitCode.ERROR
        
        except InvalidFilingIdError as e:
            self.message.error(str(e))
            return ExitCode.ERROR
        except LibraryAnalyzerNotAvailableError as e:
            self.message.error(str(e))
            return ExitCode.NOT_AVAILABLE
        except Exception as e:
            self.logger.error(f"Analysis error: {e}", exc_info=True)
            self.message.error(f"Analysis error: {e}")
            return ExitCode.ERROR
    
    def show_library_status(self) -> int:
        """
        Show library status.
        
        Returns:
            Exit code
        """
        try:
            print("📚 Library Status")
            print("=" * 50)
            
            # This would integrate with actual library status tracking
            self.message.info("Library status functionality to be implemented")
            self.message.info("Will show: installed libraries, versions, integrity checks")
            
            return ExitCode.SUCCESS
        
        except Exception as e:
            self.logger.error(f"Failed to get library status: {e}", exc_info=True)
            self.message.error(f"Failed to get library status: {e}")
            return ExitCode.ERROR
    
    def download_libraries(
        self,
        market_type: Optional[str] = None,
        download_all: bool = False
    ) -> int:
        """
        Download libraries.
        
        Args:
            market_type: Specific market type to download
            download_all: Download all configured libraries
            
        Returns:
            Exit code
        """
        try:
            if not market_type and not download_all:
                self.message.error("Must specify either --market or --all")
                return ExitCode.ERROR
            
            if download_all:
                print("📥 Downloading all configured libraries...")
                self.message.info("Download all functionality to be implemented")
                self.message.info("Will download: all taxonomies in system configuration")
            elif market_type:
                print(f"📥 Downloading libraries for {market_type.upper()} market...")
                self.message.info(f"Market-specific download for {market_type} to be implemented")
                self.message.info(f"Will download: taxonomies required for {market_type}")
            
            return ExitCode.SUCCESS
        
        except Exception as e:
            self.logger.error(f"Download failed: {e}", exc_info=True)
            self.message.error(f"Download failed: {e}")
            return ExitCode.ERROR
    
    def process_manual_downloads(
        self,
        list_files: bool = False,
        process_file: Optional[str] = None
    ) -> int:
        """
        Process manual downloads.
        
        Args:
            list_files: List files in manual directory
            process_file: Specific file to process
            
        Returns:
            Exit code
        """
        try:
            if list_files:
                print("[DIR] Listing manual download directory...")
                self.message.info("List files functionality to be implemented")
                self.message.info("Will show: files in manual_taxonomies directory")
            elif process_file:
                print(f"[CONFIG]️  Processing manual download: {process_file}...")
                self.message.info(f"Process file functionality to be implemented")
                self.message.info(f"Will process: {process_file}")
            else:
                self.message.error("Must specify either --list or --process")
                return ExitCode.ERROR
            
            return ExitCode.SUCCESS
        
        except Exception as e:
            self.logger.error(f"Manual processing failed: {e}", exc_info=True)
            self.message.error(f"Manual processing failed: {e}")
            return ExitCode.ERROR
    
    def validate_libraries(self) -> int:
        """
        Validate all libraries.
        
        Returns:
            Exit code
        """
        try:
            print("[SEARCH] Validating all libraries...")
            self.message.info("Library validation functionality to be implemented")
            self.message.info("Will check: library integrity, versions, completeness")
            
            return ExitCode.SUCCESS
        
        except Exception as e:
            self.logger.error(f"Validation failed: {e}", exc_info=True)
            self.message.error(f"Validation failed: {e}")
            return ExitCode.ERROR
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def _validate_filing_id(self, filing_id: str) -> None:
        """
        Validate filing ID format.
        
        Args:
            filing_id: Filing ID to validate
            
        Raises:
            InvalidFilingIdError: If filing ID is invalid
        """
        if not filing_id:
            raise InvalidFilingIdError("Filing ID cannot be empty")
        
        if len(filing_id) < 10:
            raise InvalidFilingIdError(
                f"Filing ID too short: {filing_id} (expected at least 10 characters)"
            )
        
        # Could add more validation here (format, UUID check, etc.)
    
    def _ensure_library_analyzer(self) -> None:
        """
        Ensure library analyzer is available.
        
        Raises:
            LibraryAnalyzerNotAvailableError: If analyzer not available
        """
        if not self.library_analyzer:
            raise LibraryAnalyzerNotAvailableError(
                "Library dependency analyzer not available"
            )


__all__ = [
    'LibraryOperations',
    'LibraryOperationError',
    'LibraryAnalyzerNotAvailableError',
    'InvalidFilingIdError'
]