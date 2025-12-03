# File: /map_pro/engines/extractor/extraction_orchestrator.py

"""
Extraction Orchestrator
=======================

Orchestrates the extraction workflow: validation, extraction, and post-processing.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from database.models.core_models import Filing
from .archive_handlers import ArchiveHandlerFactory
from .extraction_validators import ExtractionValidator
from .format_detectors import FormatDetector
from core.data_paths import map_pro_paths


class ExtractionOrchestrator:
    """
    Orchestrates the complete extraction workflow.
    
    Responsibilities:
    - Validate filing and archive
    - Detect archive format
    - Execute extraction
    - Validate extraction results
    """
    
    def __init__(
        self,
        archive_factory: ArchiveHandlerFactory,
        validator: ExtractionValidator,
        format_detector: FormatDetector,
        logger,
        error_handler
    ):
        """
        Initialize extraction orchestrator.
        
        Args:
            archive_factory: Factory for archive handlers
            validator: Extraction validator
            format_detector: Archive format detector
            logger: Logger instance
            error_handler: Error handler instance
        """
        self.archive_factory = archive_factory
        self.validator = validator
        self.format_detector = format_detector
        self.logger = logger
        self.error_handler = error_handler
    
    async def execute_extraction(
        self,
        filing: Filing,
        session
    ) -> Dict[str, Any]:
        """
        Execute complete extraction workflow.
        
        Args:
            filing: Filing database object
            session: Database session
            
        Returns:
            Dictionary with extraction results
        """
        # Step 1: Get and validate filing directory
        filing_dir = self._get_filing_directory(filing)
        if not filing_dir:
            return self._create_failure_result(
                filing=filing,
                error_msg=f"No filing_directory_path for filing {filing.filing_universal_id}"
            )
        
        # Step 2: Find archive file
        archive_path = self._find_archive_file(filing_dir)
        if not archive_path:
            return self._create_failure_result(
                filing=filing,
                error_msg=f"No ZIP file found in {filing_dir}"
            )
        
        # Step 3: Validate archive exists
        if not archive_path.exists():
            return self._create_failure_result(
                filing=filing,
                error_msg=f"Archive file not found: {archive_path}"
            )
        
        # Step 4: Detect format
        archive_format = self._detect_archive_format(archive_path)
        if not archive_format:
            return self._create_failure_result(
                filing=filing,
                error_msg=f"Could not detect archive format: {archive_path}"
            )
        
        # Step 5: Perform extraction
        return await self._perform_extraction(
            filing=filing,
            archive_path=archive_path,
            archive_format=archive_format
        )
    
    def _get_filing_directory(self, filing: Filing) -> Optional[Path]:
        """
        Get filing directory path, handling both absolute and relative paths.
        
        Args:
            filing: Filing object
            
        Returns:
            Path to filing directory or None if not set
        """
        if not filing.filing_directory_path:
            return None
        
        filing_dir_str = filing.filing_directory_path
        
        if Path(filing_dir_str).is_absolute():
            filing_dir = Path(filing_dir_str)
            self.logger.debug(f"Using absolute filing_directory_path: {filing_dir}")
        else:
            filing_dir = map_pro_paths.data_root / filing_dir_str
            self.logger.debug(f"Constructed filing path: {filing_dir}")
        
        return filing_dir
    
    def _find_archive_file(self, filing_dir: Path) -> Optional[Path]:
        """
        Find archive file in filing directory.
        
        Args:
            filing_dir: Filing directory path
            
        Returns:
            Path to archive file or None if not found
        """
        archive_files = list(filing_dir.glob('*.zip'))
        
        if not archive_files:
            return None
        
        return archive_files[0]
    
    def _detect_archive_format(self, archive_path: Path) -> Optional[str]:
        """
        Detect archive format using format detector.
        
        Args:
            archive_path: Path to archive file
            
        Returns:
            Archive format string or None if detection fails
        """
        archive_format = self.format_detector.detect_format(archive_path)
        
        if archive_format:
            self.logger.info(
                f"Detected archive format: {archive_format} for {archive_path.name}"
            )
        
        return archive_format
    
    def _create_failure_result(
        self,
        filing: Filing,
        error_msg: str
    ) -> Dict[str, Any]:
        """
        Create failure result and update filing status.
        
        Args:
            filing: Filing object
            error_msg: Error message
            
        Returns:
            Failure result dictionary
        """
        self.logger.error(error_msg)
        filing.extraction_status = 'failed'
        
        return {
            'success': False,
            'error': error_msg
        }
    
    async def _perform_extraction(
        self,
        filing: Filing,
        archive_path: Path,
        archive_format: str
    ) -> Dict[str, Any]:
        """
        Perform the actual extraction process with validation.
        
        Args:
            filing: Filing object
            archive_path: Path to archive file
            archive_format: Detected archive format
            
        Returns:
            Extraction result dictionary
        """
        extraction_path = self._generate_extraction_path(archive_path)
        
        # Pre-extraction validation
        if not self._validate_pre_extraction(archive_path, extraction_path, filing):
            return {
                'success': False,
                'error': 'Pre-extraction validation failed'
            }
        
        # Extract archive
        extraction_result = await self._extract_archive(
            archive_path=archive_path,
            extraction_path=extraction_path,
            archive_format=archive_format,
            filing=filing
        )
        
        if not extraction_result['success']:
            return extraction_result
        
        # Post-extraction validation
        if not self._validate_post_extraction(extraction_path, filing):
            return {
                'success': False,
                'error': 'Post-extraction validation failed'
            }
        
        return extraction_result
    
    def _generate_extraction_path(self, archive_path: Path) -> Path:
        """
        Generate extraction path for archive.
        
        Args:
            archive_path: Path to archive file
            
        Returns:
            Path for extraction directory
        """
        return archive_path.parent / 'extracted'
    
    def _validate_pre_extraction(
        self,
        archive_path: Path,
        extraction_path: Path,
        filing: Filing
    ) -> bool:
        """
        Validate before extraction.
        
        Args:
            archive_path: Path to archive
            extraction_path: Target extraction path
            filing: Filing object
            
        Returns:
            True if valid, False otherwise
        """
        pre_check = self.validator.validate_pre_extraction(
            archive_path,
            extraction_path
        )
        
        if not pre_check['valid']:
            error_msg = f"Pre-extraction validation failed: {', '.join(pre_check['errors'])}"
            self.logger.warning(error_msg)
            filing.extraction_status = 'failed'
            return False
        
        return True
    
    async def _extract_archive(
        self,
        archive_path: Path,
        extraction_path: Path,
        archive_format: str,
        filing: Filing
    ) -> Dict[str, Any]:
        """
        Extract archive using appropriate handler.
        
        Args:
            archive_path: Path to archive
            extraction_path: Target extraction path
            archive_format: Archive format
            filing: Filing object
            
        Returns:
            Extraction result dictionary
        """
        handler = self.archive_factory.get_handler(archive_format)
        
        self._log_extraction_debug_info(handler)
        
        self.logger.info(f"Extracting {archive_path.name} to {extraction_path}")
        
        extraction_result = await handler.extract(archive_path, extraction_path)
        
        if not extraction_result['success']:
            error_msg = f"Extraction failed: {extraction_result.get('error', 'Unknown error')}"
            self.logger.error(error_msg)
            filing.extraction_status = 'failed'
            return {
                'success': False,
                'error': error_msg
            }
        
        extraction_result['extraction_path'] = str(extraction_path)        
        return extraction_result
    
    def _log_extraction_debug_info(self, handler):
        """
        Log debug information about the handler.
        
        Args:
            handler: Archive handler instance
        """
        self.logger.info(f"DEBUG: About to call handler.extract() - Handler type: {type(handler)}")
        self.logger.info(f"DEBUG: Handler methods: {[m for m in dir(handler) if not m.startswith('_')]}")
        self.logger.info(f"DEBUG: Has extract method: {hasattr(handler, 'extract')}")
        self.logger.info(f"DEBUG: Has extract_to_directory method: {hasattr(handler, 'extract_to_directory')}")
    
    def _validate_post_extraction(
        self,
        extraction_path: Path,
        filing: Filing
    ) -> bool:
        """
        Validate after extraction.
        
        Args:
            extraction_path: Extraction path
            filing: Filing object
            
        Returns:
            True if valid, False otherwise
        """
        post_check = self.validator.validate_post_extraction(extraction_path)
        
        if not post_check['valid']:
            error_msg = f"Post-extraction validation failed: {', '.join(post_check['errors'])}"
            self.logger.warning(error_msg)
            filing.extraction_status = 'failed'
            return False
        
        return True