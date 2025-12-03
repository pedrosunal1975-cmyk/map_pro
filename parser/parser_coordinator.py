"""
Map Pro Parser Coordinator
==========================

Main XBRL parsing engine - inherits from BaseEngine.
Processes XBRL files, extracts facts/contexts, creates JSON output.

Architecture: Universal parser - market-agnostic XBRL processing.

Responsibilities:
- Process parsing jobs from database queue
- Coordinate XBRL parsing workflow
- Update database with results

Delegates detailed work to:
- ParsingWorkflowExecutor: Execute parsing workflow
- ParsedDocumentManager: Manage parsed database records
- ParsingJobResolver: Resolve job parameters
- ParsingValidator: Pre-parse validation
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import joinedload

from engines.base.engine_base import BaseEngine
from core.system_logger import get_logger
from database.models.core_models import Document, Filing
from shared.constants.job_constants import JobType
from shared.exceptions.custom_exceptions import EngineError

from .arelle_controller import ArelleController, ARELLE_AVAILABLE
from .fact_extractor import FactExtractor
from .context_processor import ContextProcessor
from .output_formatter import OutputFormatter
from .validation_engine import ValidationEngine
from .parsing_workflow_executor import ParsingWorkflowExecutor
from .parsed_document_manager import ParsedDocumentManager
from .parsing_job_resolver import ParsingJobResolver
from .parsing_validator import ParsingValidator

logger = get_logger(__name__, 'engine')


class ParserCoordinator(BaseEngine):
    """
    Universal XBRL parser engine.
    
    Responsibilities:
    - Process parsing jobs from database queue
    - Coordinate component initialization
    - Delegate parsing workflow execution
    
    Does NOT handle:
    - File downloads (downloader handles this)
    - Archive extraction (extractor handles this)
    - Concept mapping (mapper handles this)
    - Detailed parsing logic (workflow executor handles this)
    """
    
    def __init__(self):
        """Initialize parser engine."""
        super().__init__("parser")
        
        # Initialize parsing components
        self.arelle_controller: Optional[ArelleController] = None
        self.fact_extractor: Optional[FactExtractor] = None
        self.context_processor: Optional[ContextProcessor] = None
        self.output_formatter: Optional[OutputFormatter] = None
        self.validation_engine: Optional[ValidationEngine] = None
        
        # Initialize workflow components
        self.workflow_executor: Optional[ParsingWorkflowExecutor] = None
        self.document_manager: Optional[ParsedDocumentManager] = None
        self.job_resolver: Optional[ParsingJobResolver] = None
        self.parsing_validator: Optional[ParsingValidator] = None
        
        self.logger.info("Parser coordinator initialized")
    
    def get_primary_database(self) -> str:
        """Return primary database name."""
        return 'core'
    
    def get_supported_job_types(self) -> List[str]:
        """Return supported job types."""
        return [JobType.PARSE_XBRL.value]
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process parsing job.
        
        Args:
            job_data: Job information with document_id or filing_id
            
        Returns:
            Result dictionary with parsing status
            
        Raises:
            EngineError: If job processing fails
        """
        try:
            # Resolve document_id from job data
            document_id = self.job_resolver.resolve_document_id(job_data)
            
            if not document_id:
                raise EngineError("Missing document_id in job data")
            
            self.logger.info(f"Processing parsing job for document: {document_id}")
            
            # Get document with EAGER LOADING of relationships
            with self.get_session() as session:
                document = session.query(Document).options(
                    joinedload(Document.filing).joinedload(Filing.entity)
                ).filter_by(
                    document_universal_id=document_id
                ).first()
                
                if not document:
                    raise EngineError(f"Document not found: {document_id}")
                
                # Verify critical relationships are loaded
                if not document.filing:
                    raise EngineError(
                        f"Document {document_id} has no associated filing. "
                        "Cannot proceed with parsing."
                    )
                
                if not document.filing.entity:
                    raise EngineError(
                        f"Filing {document.filing_universal_id} has no associated entity. "
                        "Cannot proceed with parsing."
                    )
                
                self.logger.debug(
                    f"Document relationships loaded: "
                    f"Filing={document.filing_universal_id}, "
                    f"Entity={document.filing.entity.primary_name}"
                )
                
                # Execute parsing workflow
                result = await self.parse_document(document, session)
                
                # Format result for job system
                return self._format_job_result(result, document, job_data)
        
        except Exception as e:
            self.logger.error(
                f"Parsing job failed for document {job_data.get('parameters', {}).get('document_id')}: {e}",
                exc_info=True
            )
            raise EngineError(f"Parsing job failed: {str(e)}")
    
    async def parse_document(
        self, 
        document: Document, 
        session
    ) -> Dict[str, Any]:
        """
        Parse a single XBRL document.
        
        Args:
            document: Document database object (with filing and entity loaded)
            session: Database session
            
        Returns:
            Dictionary with parsing results
        """
        # Delegate to workflow executor
        return await self.workflow_executor.execute_parsing_workflow(
            document=document,
            session=session
        )
    
    def _format_job_result(
        self,
        result: Dict[str, Any],
        document: Document,
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format parsing result for job system.
        
        Args:
            result: Parsing workflow result
            document: Document that was parsed
            job_data: Original job data
            
        Returns:
            Formatted job result
        """
        return {
            'success': result['success'],
            'document_id': str(document.document_universal_id),
            'filing_universal_id': str(document.filing_universal_id),
            'facts_extracted': result.get('facts_extracted', 0),
            'json_path': result.get('json_path'),
            'error_type': result.get('error_type'),
            'job_id': job_data.get('job_id')
        }
    
    def _engine_specific_initialization(self) -> bool:
        """
        Parser-specific initialization.
        
        Returns:
            True if initialization successful
        """
        try:
            # Check Arelle availability
            if not ARELLE_AVAILABLE:
                self.logger.error("Arelle library not available")
                return False
            
            # Initialize core components
            if not self._initialize_parsing_components():
                return False
            
            # Initialize workflow components
            if not self._initialize_workflow_components():
                return False
            
            # Validate environment
            if not self.parsing_validator.validate_environment():
                return False
            
            self.logger.info("Parser initialization successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Parser initialization failed: {e}", exc_info=True)
            return False
    
    def _initialize_parsing_components(self) -> bool:
        """
        Initialize core parsing components.
        
        Returns:
            True if successful
        """
        try:
            self.arelle_controller = ArelleController()
            if not self.arelle_controller.initialize():
                return False
            
            self.fact_extractor = FactExtractor()
            self.context_processor = ContextProcessor()
            self.output_formatter = OutputFormatter()
            self.validation_engine = ValidationEngine()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize parsing components: {e}")
            return False
    
    def _initialize_workflow_components(self) -> bool:
        """
        Initialize workflow coordination components.
        
        Returns:
            True if successful
        """
        try:
            # Initialize components
            self.document_manager = ParsedDocumentManager()
            self.job_resolver = ParsingJobResolver(self.get_session)
            self.parsing_validator = ParsingValidator()
            
            # Initialize workflow executor with dependencies
            self.workflow_executor = ParsingWorkflowExecutor(
                arelle_controller=self.arelle_controller,
                fact_extractor=self.fact_extractor,
                context_processor=self.context_processor,
                output_formatter=self.output_formatter,
                validation_engine=self.validation_engine,
                document_manager=self.document_manager,
                error_handler=self.error_handler,
                logger=self.logger
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow components: {e}")
            return False
    
    def _get_engine_specific_status(self) -> Dict[str, Any]:
        """
        Get parser-specific status.
        
        Returns:
            Dictionary with parser status information
        """
        status = {
            'arelle_available': ARELLE_AVAILABLE
        }
        
        if self.arelle_controller:
            status['arelle_stats'] = self.arelle_controller.get_statistics()
        
        if self.fact_extractor:
            status['extraction_stats'] = self.fact_extractor.get_statistics()
        
        if self.context_processor:
            status['context_stats'] = self.context_processor.get_statistics()
        
        return status
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.arelle_controller:
            self.arelle_controller.shutdown()
        
        self.logger.info("Parser cleanup completed")


def create_parser_engine() -> ParserCoordinator:
    """Factory function to create parser engine."""
    return ParserCoordinator()


__all__ = [
    'ParserCoordinator',
    'create_parser_engine'
]