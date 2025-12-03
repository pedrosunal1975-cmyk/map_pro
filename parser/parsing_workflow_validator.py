# File: /map_pro/engines/parser/parsing_workflow_validator.py

"""
Parsing Workflow Validator
===========================

Handles all validation operations for the parsing workflow including
document requirements validation and XBRL model validation.

Responsibilities:
- Validate document prerequisites (paths, files)
- Validate XBRL models (instance documents, validity)
- Classify validation failures
- Update document status on validation failures

Related Files:
- parsing_workflow_executor.py: Main workflow orchestrator
- validation_engine.py: Core XBRL validation logic
"""

from pathlib import Path
from typing import Dict, Any

from core.system_logger import get_logger
from database.models.core_models import Document

logger = get_logger(__name__, 'engine')


class ValidationErrorType:
    """Constants for validation error types."""
    DATA_ERROR = 'data_error'
    FILE_NOT_FOUND = 'file_not_found'
    VALIDATION_FAILED = 'validation_failed'


class DocumentStatus:
    """Constants for document status values."""
    DATA_ISSUE = 'data_issue'
    NOT_APPLICABLE = 'not_applicable'


class ParsingWorkflowValidator:
    """
    Validates documents and XBRL models during the parsing workflow.
    
    This class encapsulates all validation logic for the parsing process,
    ensuring documents meet prerequisites and XBRL models are valid before
    processing continues.
    """
    
    def __init__(
        self,
        validation_engine,
        error_handler,
        logger
    ):
        """
        Initialize validator with dependencies.
        
        Args:
            validation_engine: ValidationEngine instance for XBRL validation
            error_handler: ErrorHandler instance for error classification
            logger: Logger instance for validation logging
        """
        self.validation_engine = validation_engine
        self.error_handler = error_handler
        self.logger = logger
    
    def validate_document_requirements(
        self,
        document: Document,
        session
    ) -> Dict[str, Any]:
        """
        Validate document has required paths and files.
        
        Checks that:
        1. Document has an extraction_path
        2. The file at extraction_path exists
        
        Args:
            document: Document to validate
            session: Database session for status updates
            
        Returns:
            Dictionary with validation result containing:
                - valid (bool): Whether validation passed
                - result (dict): Error result if validation failed
                - xbrl_file (Path): Path to XBRL file if validation passed
        """
        # Check extraction_path exists
        if not document.extraction_path:
            return self._handle_missing_extraction_path(
                document=document,
                session=session
            )
        
        # Check file exists
        xbrl_file = Path(document.extraction_path)
        if not xbrl_file.exists():
            return self._handle_missing_file(
                document=document,
                session=session,
                xbrl_file=xbrl_file
            )
        
        # Validation passed
        return {
            'valid': True,
            'xbrl_file': xbrl_file
        }
    
    def _handle_missing_extraction_path(
        self,
        document: Document,
        session
    ) -> Dict[str, Any]:
        """
        Handle case where document has no extraction_path.
        
        Missing extraction_path indicates extraction did not complete
        successfully. This is marked as a data_issue to prevent retry loops.
        
        Args:
            document: Document with missing extraction_path
            session: Database session for status update
            
        Returns:
            Dictionary with validation failure result
        """
        error_message = (
            f"No extraction_path for document {document.document_universal_id} "
            f"(filing: {document.filing_universal_id}). "
            f"This indicates extraction did not complete successfully."
        )
        
        self.logger.warning(error_message)
        
        # Mark document status to prevent future retry attempts
        document.parsed_status = DocumentStatus.DATA_ISSUE
        session.commit()
        
        return {
            'valid': False,
            'result': {
                'success': False,
                'error': error_message,
                'error_type': ValidationErrorType.DATA_ERROR,
                'should_retry': False
            }
        }
    
    def _handle_missing_file(
        self,
        document: Document,
        session,
        xbrl_file: Path
    ) -> Dict[str, Any]:
        """
        Handle case where XBRL file does not exist at extraction_path.
        
        Args:
            document: Document being validated
            session: Database session for status update
            xbrl_file: Path where file should exist
            
        Returns:
            Dictionary with validation failure result
        """
        error_message = f"XBRL file not found: {xbrl_file}"
        self.logger.error(error_message)
        
        error_report = self.error_handler.handle_engine_processing_error(
            FileNotFoundError(error_message),
            context={'document_id': str(document.document_universal_id)}
        )
        
        document.parsed_status = error_report['status_label']
        session.commit()
        
        return {
            'valid': False,
            'result': {
                'success': False,
                'error': error_message,
                'error_type': error_report['error_type']
            }
        }
    
    def validate_xbrl_model(
        self,
        model_xbrl,
        document: Document,
        session
    ) -> Dict[str, Any]:
        """
        Validate XBRL model is a valid instance document.
        
        Checks that:
        1. Model is an XBRL instance document (not taxonomy/linkbase)
        2. Model passes XBRL validation rules
        
        Args:
            model_xbrl: Loaded XBRL model from Arelle
            document: Document being parsed
            session: Database session for status updates
            
        Returns:
            Dictionary with validation result containing:
                - valid (bool): Whether validation passed
                - result (dict): Result information if validation failed
        """
        validation = self.validation_engine.validate_xbrl_model(model_xbrl)
        
        # Check if instance document
        if not validation['is_instance']:
            return self._handle_non_instance_document(
                document=document,
                session=session
            )
        
        # Check if valid
        if not validation['valid']:
            return self._handle_invalid_xbrl_model(
                document=document,
                session=session,
                validation=validation
            )
        
        return {'valid': True}
    
    def _handle_non_instance_document(
        self,
        document: Document,
        session
    ) -> Dict[str, Any]:
        """
        Handle case where file is not an XBRL instance document.
        
        Non-instance documents (taxonomies, linkbases) are marked as
        'not_applicable' and are not considered failures.
        
        Args:
            document: Document being validated
            session: Database session for status update
            
        Returns:
            Dictionary with validation result
        """
        self.logger.info(
            f"File {document.document_name} is not an XBRL instance document "
            f"(likely taxonomy/linkbase file)"
        )
        document.parsed_status = DocumentStatus.NOT_APPLICABLE
        session.commit()
        
        return {
            'valid': False,
            'result': {
                'success': True,
                'not_instance': True,
                'message': 'Not an XBRL instance document'
            }
        }
    
    def _handle_invalid_xbrl_model(
        self,
        document: Document,
        session,
        validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle case where XBRL model fails validation.
        
        Args:
            document: Document being validated
            session: Database session for status update
            validation: Validation result from validation_engine
            
        Returns:
            Dictionary with validation failure result
        """
        error_message = f"XBRL validation failed: {validation.get('errors', [])}"
        self.logger.error(error_message)
        
        error_report = self.error_handler.handle_engine_processing_error(
            ValueError(error_message),
            context={'document_id': str(document.document_universal_id)}
        )
        
        document.parsed_status = error_report['status_label']
        session.commit()
        
        return {
            'valid': False,
            'result': {
                'success': False,
                'error': error_message,
                'error_type': error_report['error_type']
            }
        }


__all__ = ['ParsingWorkflowValidator', 'ValidationErrorType', 'DocumentStatus']