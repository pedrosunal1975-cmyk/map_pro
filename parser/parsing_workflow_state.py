# File: /map_pro/engines/parser/parsing_workflow_state.py

"""
Parsing Workflow State Manager
===============================

Manages document state transitions during the parsing workflow.

Responsibilities:
- Update document parsing status
- Commit state changes to database
- Log state transitions
- Ensure state consistency

Related Files:
- parsing_workflow_executor.py: Main workflow orchestrator
- core_models.py: Document model definition
"""

from typing import Any

from core.system_logger import get_logger
from database.models.core_models import Document

logger = get_logger(__name__, 'engine')


class ParsingStatus:
    """Constants for document parsing status values."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    DATA_ISSUE = 'data_issue'
    NOT_APPLICABLE = 'not_applicable'


class ParsingWorkflowState:
    """
    Manages document state during the parsing workflow.
    
    This class provides a centralized interface for updating document
    parsing status and ensures consistent state management throughout
    the workflow.
    """
    
    def __init__(self, logger):
        """
        Initialize state manager.
        
        Args:
            logger: Logger instance for state transition logging
        """
        self.logger = logger
    
    def update_document_status(
        self,
        document: Document,
        session: Any,
        status: str
    ) -> None:
        """
        Update document parsing status and commit to database.
        
        Args:
            document: Document whose status should be updated
            session: SQLAlchemy database session
            status: New parsing status value (use ParsingStatus constants)
            
        Raises:
            ValueError: If status is not a valid parsing status
            Exception: If database commit fails (re-raised after logging)
        """
        # Validate status value
        valid_statuses = {
            ParsingStatus.PENDING,
            ParsingStatus.PROCESSING,
            ParsingStatus.COMPLETED,
            ParsingStatus.FAILED,
            ParsingStatus.DATA_ISSUE,
            ParsingStatus.NOT_APPLICABLE
        }
        
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid parsing status '{status}'. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )
        
        old_status = document.parsed_status
        
        try:
            document.parsed_status = status
            session.commit()
            
            self.logger.info(
                f"Document {document.document_universal_id} status updated: "
                f"{old_status} -> {status}"
            )
            
        except Exception as exception:
            self.logger.error(
                f"Failed to update document status for "
                f"{document.document_universal_id}: {exception}",
                exc_info=True
            )
            session.rollback()
            raise
    
    def get_current_status(self, document: Document) -> str:
        """
        Get current parsing status of a document.
        
        Args:
            document: Document to check
            
        Returns:
            Current parsing status value
        """
        return document.parsed_status
    
    def is_processing_complete(self, document: Document) -> bool:
        """
        Check if document processing is complete (success or terminal failure).
        
        Args:
            document: Document to check
            
        Returns:
            True if document is in a terminal state, False otherwise
        """
        terminal_statuses = {
            ParsingStatus.COMPLETED,
            ParsingStatus.DATA_ISSUE,
            ParsingStatus.NOT_APPLICABLE
        }
        
        return document.parsed_status in terminal_statuses
    
    def is_retryable(self, document: Document) -> bool:
        """
        Check if document can be retried based on current status.
        
        Args:
            document: Document to check
            
        Returns:
            True if document can be retried, False otherwise
        """
        retryable_statuses = {
            ParsingStatus.PENDING,
            ParsingStatus.FAILED
        }
        
        return document.parsed_status in retryable_statuses


__all__ = ['ParsingWorkflowState', 'ParsingStatus']