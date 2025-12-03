# File: /map_pro/engines/extractor/extraction_coordinator.py

"""
Map Pro Extraction Coordinator
==============================

Main extraction engine - inherits from BaseEngine.
Orchestrates archive extraction workflow and coordinates with specialized components.

Architecture: Universal extraction engine - market-agnostic archive processing.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

from engines.base.engine_base import BaseEngine
from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.data_paths import map_pro_paths
from database.models.core_models import Filing, Document, ProcessingJob
from shared.constants.job_constants import JobType, JobStatus
from shared.exceptions.custom_exceptions import EngineError

from .archive_handlers import ArchiveHandlerFactory
from .extraction_validators import ExtractionValidator
from .format_detectors import FormatDetector
from .extraction_orchestrator import ExtractionOrchestrator
from .document_processor import DocumentProcessor
from .parsing_job_creator import ParsingJobCreator

logger = get_logger(__name__, 'engine')


class ExtractionCoordinator(BaseEngine):
    """
    Universal extraction engine for all archive formats.
    
    Responsibilities:
    - Coordinate extraction workflow
    - Delegate to specialized components
    - Update database with extraction status
    - Integrate with other engines via job system
    
    Does NOT handle:
    - File downloads (downloader engine handles this)
    - XBRL parsing (parser engine handles this)
    - Market-specific logic (path structure already set by downloader)
    """
    
    def __init__(self):
        """Initialize extraction engine with required components."""
        super().__init__("extractor")
        
        # Core components
        self.archive_factory = ArchiveHandlerFactory()
        self.validator = ExtractionValidator()
        self.format_detector = FormatDetector()
        
        # Specialized orchestrators
        self.orchestrator = ExtractionOrchestrator(
            archive_factory=self.archive_factory,
            validator=self.validator,
            format_detector=self.format_detector,
            logger=self.logger,
            error_handler=self.error_handler
        )
        
        self.document_processor = DocumentProcessor(logger=self.logger)
        self.job_creator = ParsingJobCreator(logger=self.logger)
        
        self.logger.info("Extraction coordinator initialized")
    
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
        return [JobType.EXTRACT_FILES.value]
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process extraction job.
        
        Args:
            job_data: Job information with filing_id
            
        Returns:
            Result dictionary with extraction status
            
        Raises:
            EngineError: If job processing fails
        """
        filing_id = self._extract_filing_id_from_job(job_data)
        
        self.logger.info(f"Processing extraction job for filing: {filing_id}")
        
        try:
            return await self._process_extraction_job(filing_id, job_data)
        
        except Exception as e:
            self.logger.error(f"Extraction job failed for filing {filing_id}: {e}")
            raise EngineError(f"Extraction job failed: {str(e)}")
    
    def _extract_filing_id_from_job(self, job_data: Dict[str, Any]) -> str:
        """
        Extract filing ID from job data.
        
        Args:
            job_data: Job data dictionary containing parameters
            
        Returns:
            Filing ID string
            
        Raises:
            EngineError: If filing_id not found in job data
        """
        filing_id = job_data.get('parameters', {}).get('filing_universal_id')
        
        if not filing_id:
            raise EngineError("Missing filing_universal_id in job data")
        
        return filing_id
    
    async def _process_extraction_job(
        self, 
        filing_id: str, 
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process extraction job for a filing.
        
        Args:
            filing_id: Filing universal ID
            job_data: Job data dictionary
            
        Returns:
            Result dictionary with success status and details
        """
        with self.get_session() as session:
            filing = self._get_filing_from_database(filing_id, session)
            result = await self.extract_filing(filing, session)
            
            return self._build_job_result(result, filing_id, job_data)
    
    def _get_filing_from_database(self, filing_id: str, session) -> Filing:
        """
        Get filing object from database.
        
        Args:
            filing_id: Filing universal ID
            session: Database session
            
        Returns:
            Filing object
            
        Raises:
            EngineError: If filing not found
        """
        filing = session.query(Filing).filter_by(
            filing_universal_id=filing_id
        ).first()
        
        if not filing:
            raise EngineError(f"Filing not found: {filing_id}")
        
        return filing
    
    def _build_job_result(
        self, 
        result: Dict[str, Any], 
        filing_id: str, 
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build job result dictionary.
        
        Args:
            result: Extraction result dictionary
            filing_id: Filing ID
            job_data: Original job data
            
        Returns:
            Formatted job result dictionary
        """
        return {
            'success': result['success'],
            'filing_id': filing_id,
            'files_extracted': result.get('files_extracted', 0),
            'extraction_path': result.get('extraction_path'),
            'job_id': job_data.get('job_id')
        }
    
    async def extract_filing(self, filing: Filing, session) -> Dict[str, Any]:
        """
        Extract archive for a single filing.
        
        Args:
            filing: Filing database object
            session: Database session
            
        Returns:
            Dictionary with extraction results including success status
        """
        try:
            # Delegate to orchestrator for extraction workflow
            extraction_result = await self.orchestrator.execute_extraction(
                filing=filing,
                session=session
            )
            
            if not extraction_result['success']:
                return extraction_result
            
            # Process documents and create parsing jobs
            return self._finalize_extraction(
                filing=filing,
                extraction_result=extraction_result,
                session=session
            )
            
        except Exception as e:
            return self._handle_extraction_error(exception=e, filing=filing)
    
    def _finalize_extraction(
        self,
        filing: Filing,
        extraction_result: Dict[str, Any],
        session
    ) -> Dict[str, Any]:
        """
        Finalize extraction by updating database records.
        
        Args:
            filing: Filing object
            extraction_result: Result from extraction workflow
            session: Database session
            
        Returns:
            Final result dictionary with document and job counts
        """
        # Safely extract extraction_path with validation
        extraction_path_str = extraction_result.get('extraction_path')
        if not extraction_path_str:
            error_msg = "Extraction result missing extraction_path"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        extraction_path = Path(extraction_path_str)
        extracted_files = extraction_result.get('files', [])
        
        # Update filing status
        filing.extraction_status = 'completed'
        filing.extraction_completed_at = datetime.now(timezone.utc)
        
        # Create document records
        documents_created = self.document_processor.create_document_records(
            filing=filing,
            extraction_path=extraction_path,
            extracted_files=extracted_files,
            session=session
        )
        
        session.commit()
        
        # Create parsing jobs for eligible documents
        parsing_jobs_created = self.job_creator.create_parsing_jobs_for_filing(
            filing=filing,
            session=session
        )
        
        session.commit()
        
        self.logger.info(
            f"Extraction completed: {filing.market_filing_id} - "
            f"{extraction_result.get('files_extracted', 0)} files extracted, "
            f"{documents_created} documents committed to database, "
            f"{parsing_jobs_created} parsing jobs created"
        )
        
        return {
            'success': True,
            'extraction_path': str(extraction_path),
            'files_extracted': extraction_result.get('files_extracted', 0),
            'documents_created': documents_created,
            'parsing_jobs_created': parsing_jobs_created
        }
    
    def _handle_extraction_error(
        self,
        exception: Exception,
        filing: Filing
    ) -> Dict[str, Any]:
        """
        Handle extraction error with proper error classification.
        
        Args:
            exception: Exception that occurred
            filing: Filing object
            
        Returns:
            Error result dictionary with error details
        """
        error_msg = f"Extraction error: {str(exception)}"
        
        error_report = self.error_handler.handle_engine_processing_error(
            exception,
            context={
                'filing_id': str(filing.filing_universal_id),
                'market_filing_id': filing.market_filing_id
            }
        )
        
        filing.extraction_status = error_report['status_label']
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': error_report['error_type']
        }
    
    def _engine_specific_initialization(self) -> bool:
        """
        Extractor-specific initialization.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            temp_extraction = map_pro_paths.data_root / 'temp_extractions'
            temp_extraction.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Extractor initialization successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Extractor initialization failed: {e}")
            return False
    
    def _get_engine_specific_status(self) -> Dict[str, Any]:
        """
        Get extractor-specific status information.
        
        Returns:
            Dictionary containing extractor status details
        """
        return {
            'supported_formats': self.archive_factory.get_supported_formats(),
            'max_extraction_size_mb': self.validator.max_extraction_size_mb
        }
    
    async def cleanup(self):
        """Cleanup resources used by the extraction coordinator."""
        self.logger.info("Extractor cleanup completed")


def create_extractor_engine() -> ExtractionCoordinator:
    """
    Factory function to create extractor engine.
    
    Returns:
        Configured ExtractionCoordinator instance
    """
    return ExtractionCoordinator()