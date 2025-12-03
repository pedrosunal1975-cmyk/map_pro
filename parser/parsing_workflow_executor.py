# File: /map_pro/engines/parser/parsing_workflow_executor.py

"""
Parsing Workflow Executor
==========================

Orchestrates the complete XBRL parsing workflow by coordinating
validation, extraction, and database update operations.

Responsibilities:
- Execute multi-step parsing workflow
- Coordinate component interactions
- Delegate validation and database operations
- Handle high-level workflow errors

Related Files:
- parsing_workflow_validator.py: Document and model validation
- parsing_workflow_state.py: Workflow state management
- parsing_database_updater.py: Database update operations
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from database.models.core_models import Document

from engines.parser.parsing_workflow_validator import ParsingWorkflowValidator
from engines.parser.parsing_workflow_state import ParsingWorkflowState
from engines.parser.parsing_database_updater import ParsingDatabaseUpdater

logger = get_logger(__name__, 'engine')


class ParsingWorkflowExecutor:
    """
    Orchestrates the complete XBRL parsing workflow.
    
    This class coordinates the parsing process by delegating to specialized
    components for validation, state management, and database operations.
    """
    
    def __init__(
        self,
        arelle_controller,
        fact_extractor,
        context_processor,
        output_formatter,
        validation_engine,
        document_manager,
        error_handler,
        logger
    ):
        """
        Initialize workflow executor with dependencies.
        
        Args:
            arelle_controller: ArelleController instance for XBRL model loading
            fact_extractor: FactExtractor instance for fact extraction
            context_processor: ContextProcessor instance for context/unit extraction
            output_formatter: OutputFormatter instance for JSON output creation
            validation_engine: ValidationEngine instance for XBRL validation
            document_manager: ParsedDocumentManager instance for parsed DB operations
            error_handler: ErrorHandler instance for error classification
            logger: Logger instance for workflow logging
        """
        self.arelle_controller = arelle_controller
        self.fact_extractor = fact_extractor
        self.context_processor = context_processor
        self.output_formatter = output_formatter
        self.validation_engine = validation_engine
        self.document_manager = document_manager
        self.error_handler = error_handler
        self.logger = logger
        
        # Initialize specialized workflow components
        self.validator = ParsingWorkflowValidator(
            validation_engine=validation_engine,
            error_handler=error_handler,
            logger=logger
        )
        
        self.state_manager = ParsingWorkflowState(logger=logger)
        
        self.database_updater = ParsingDatabaseUpdater(
            document_manager=document_manager,
            error_handler=error_handler,
            logger=logger
        )
    
    async def execute_parsing_workflow(
        self,
        document: Document,
        session
    ) -> Dict[str, Any]:
        """
        Execute the complete parsing workflow.
        
        Workflow steps:
        1. Validate document and file paths
        2. Update status to processing
        3. Load XBRL model with Arelle
        4. Validate XBRL model
        5. Extract facts, contexts, units
        6. Create JSON output
        7. Update core database
        8. Update parsed database
        9. Verify database records
        
        Args:
            document: Document database object to be parsed
            session: SQLAlchemy database session for core database operations
            
        Returns:
            Dictionary containing parsing results with keys:
                - success (bool): Whether parsing completed successfully
                - facts_extracted (int): Number of facts extracted (if successful)
                - contexts_extracted (int): Number of contexts extracted (if successful)
                - units_extracted (int): Number of units extracted (if successful)
                - json_path (str): Path to output JSON file (if successful)
                - parsing_time (float): Time taken for parsing in seconds (if successful)
                - error (str): Error message (if failed)
                - error_type (str): Type of error (if failed)
                - should_retry (bool): Whether operation should be retried (if failed)
        """
        start_time = time.time()
        xbrl_file: Optional[Path] = None
        
        try:
            # Step 1: Validate pre-parsing requirements
            validation_result = self.validator.validate_document_requirements(
                document=document,
                session=session
            )
            if not validation_result['valid']:
                return validation_result['result']
            
            xbrl_file = validation_result['xbrl_file']
            
            # Step 2: Update status to processing
            self.state_manager.update_document_status(
                document=document,
                session=session,
                status='processing'
            )
            
            # Step 3: Parse XBRL file
            parsing_result = await self._parse_xbrl_file(
                document=document,
                xbrl_file=xbrl_file,
                session=session,
                start_time=start_time
            )
            
            return parsing_result
            
        except Exception as exception:
            return self._handle_parsing_error(
                exception=exception,
                document=document,
                session=session,
                xbrl_file=xbrl_file
            )
    
    async def _parse_xbrl_file(
        self,
        document: Document,
        xbrl_file: Path,
        session,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Parse XBRL file and create output.
        
        Args:
            document: Document to parse
            xbrl_file: Path to XBRL file
            session: Database session for core database operations
            start_time: Workflow start time for duration calculation
            
        Returns:
            Dictionary with parsing results
            
        Raises:
            ValueError: If XBRL model cannot be loaded
        """
        self.logger.info(f"Parsing XBRL file: {xbrl_file.name}")
        
        # Load XBRL model
        with self.arelle_controller.load_xbrl_context(xbrl_file) as model_xbrl:
            if not model_xbrl:
                raise ValueError(f"Failed to load XBRL model from {xbrl_file}")
            
            # Validate model
            validation_result = self.validator.validate_xbrl_model(
                model_xbrl=model_xbrl,
                document=document,
                session=session
            )
            if not validation_result['valid']:
                return validation_result['result']
            
            # Extract data
            extraction_result = self._extract_xbrl_data(
                model_xbrl=model_xbrl,
                document=document
            )
            
            # Create JSON output
            json_path = await self.output_formatter.create_json_output(
                filing=document.filing,
                document=document,
                facts=extraction_result['facts'],
                contexts=extraction_result['contexts'],
                units=extraction_result['units']
            )
            
            # Update databases
            update_result = await self.database_updater.update_databases_after_parsing(
                document=document,
                session=session,
                extraction_result=extraction_result,
                json_path=json_path,
                start_time=start_time
            )
            
            if not update_result['success']:
                return update_result
            
            # Log success
            parsing_time = time.time() - start_time
            self.logger.info(
                f"Parsing completed: {document.document_name} - "
                f"{extraction_result['facts_count']} facts in {parsing_time:.2f}s"
            )
            
            return {
                'success': True,
                'facts_extracted': extraction_result['facts_count'],
                'contexts_extracted': extraction_result['contexts_count'],
                'units_extracted': extraction_result['units_count'],
                'json_path': str(json_path),
                'parsing_time': parsing_time
            }
    
    def _extract_xbrl_data(
        self,
        model_xbrl,
        document: Document
    ) -> Dict[str, Any]:
        """
        Extract facts, contexts, and units from XBRL model.
        
        Args:
            model_xbrl: Loaded XBRL model from Arelle
            document: Document being parsed
            
        Returns:
            Dictionary with extracted data containing:
                - facts (list): Extracted facts
                - contexts (list): Extracted contexts
                - units (list): Extracted units
                - facts_count (int): Number of facts extracted
                - contexts_count (int): Number of contexts extracted
                - units_count (int): Number of units extracted
        """
        document_id = str(document.document_universal_id)
        
        # Extract facts
        facts = self.fact_extractor.extract_facts(model_xbrl, document_id)
        
        # Extract contexts
        contexts = self.context_processor.extract_contexts(model_xbrl, document_id)
        
        # Extract units
        units = self.context_processor.extract_units(model_xbrl, document_id)
        
        self.logger.info(
            f"Extracted {len(facts)} facts, {len(contexts)} contexts, "
            f"{len(units)} units"
        )
        
        return {
            'facts': facts,
            'contexts': contexts,
            'units': units,
            'facts_count': len(facts),
            'contexts_count': len(contexts),
            'units_count': len(units)
        }
    
    def _handle_parsing_error(
        self,
        exception: Exception,
        document: Document,
        session,
        xbrl_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Handle parsing error with classification and database update.
        
        Args:
            exception: Exception that occurred during parsing
            document: Document being parsed
            session: Database session for status update
            xbrl_file: Path to XBRL file if available
            
        Returns:
            Dictionary with error result containing:
                - success (bool): False
                - error (str): Error message
                - error_type (str): Classified error type
        """
        error_msg = f"Parsing error: {str(exception)}"
        
        context = {'document_id': str(document.document_universal_id)}
        if xbrl_file:
            context['xbrl_file'] = str(xbrl_file)
        
        error_report = self.error_handler.handle_engine_processing_error(
            exception,
            context=context
        )
        
        self.state_manager.update_document_status(
            document=document,
            session=session,
            status=error_report['status_label']
        )
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': error_report['error_type']
        }


__all__ = ['ParsingWorkflowExecutor']