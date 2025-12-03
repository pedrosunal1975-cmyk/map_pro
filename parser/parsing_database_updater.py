# File: /map_pro/engines/parser/parsing_database_updater.py

"""
Parsing Database Updater
=========================

Handles all database update operations after successful XBRL parsing.

Responsibilities:
- Verify output file existence and integrity
- Update core database with parsing results
- Update parsed database with extraction data
- Ensure atomic database updates

Related Files:
- parsing_workflow_executor.py: Main workflow orchestrator
- parsed_document_manager.py: Parsed database operations
"""

import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

from core.system_logger import get_logger
from database.models.core_models import Document

logger = get_logger(__name__, 'engine')


class FileVerificationConstants:
    """Constants for file verification operations."""
    MIN_FILE_SIZE_BYTES = 0
    EMPTY_FILE_SIZE_BYTES = 0


class ParsingMetadataKeys:
    """Constants for parsing metadata dictionary keys."""
    FACTS_EXTRACTED = 'facts_extracted'
    CONTEXTS_EXTRACTED = 'contexts_extracted'
    UNITS_EXTRACTED = 'units_extracted'
    PARSING_TIME_SECONDS = 'parsing_time_seconds'
    PARSED_AT = 'parsed_at'
    FILE_SIZE_BYTES = 'file_size_bytes'
    FILE_VERIFIED = 'file_verified'


class ParsingDatabaseUpdater:
    """
    Updates databases after successful XBRL parsing.
    
    This class ensures that database updates only occur after verifying
    the physical existence and integrity of output files, preventing
    race conditions with downstream components.
    """
    
    def __init__(
        self,
        document_manager,
        error_handler,
        logger
    ):
        """
        Initialize database updater with dependencies.
        
        Args:
            document_manager: ParsedDocumentManager instance for parsed DB operations
            error_handler: ErrorHandler instance for error classification
            logger: Logger instance for operation logging
        """
        self.document_manager = document_manager
        self.error_handler = error_handler
        self.logger = logger
    
    async def update_databases_after_parsing(
        self,
        document: Document,
        session,
        extraction_result: Dict[str, Any],
        json_path: Path,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Update both core and parsed databases after successful parsing.
        
        CRITICAL: Only commits to database AFTER verifying physical file exists.
        This prevents race conditions where mapper tries to read non-existent files.
        
        Workflow:
        1. Verify JSON file physically exists
        2. Verify JSON file is not empty
        3. Update core database (after verification passes)
        4. Update parsed database
        
        Args:
            document: Parsed document
            session: Core database session
            extraction_result: Extraction results containing facts/contexts/units
            json_path: Path to JSON output file
            start_time: Parsing start time for duration calculation
            
        Returns:
            Dictionary with update result containing:
                - success (bool): Whether update succeeded
                - error (str): Error message if update failed
                - error_type (str): Error type if update failed
        """
        parsing_time = time.time() - start_time
        
        # Step 1: Verify the JSON file physically exists
        file_verification_result = self._verify_output_file(json_path)
        if not file_verification_result['verified']:
            return {
                'success': False,
                'error': file_verification_result['error'],
                'error_type': 'file_verification_failed'
            }
        
        file_size = file_verification_result['file_size']
        
        self.logger.info(
            f"File verification passed: {json_path} ({file_size} bytes)"
        )
        
        # Step 2: Update core database (only after file verification passes)
        core_update_result = self._update_core_database(
            document=document,
            session=session,
            extraction_result=extraction_result,
            json_path=json_path,
            parsing_time=parsing_time,
            file_size=file_size
        )
        
        if not core_update_result['success']:
            return core_update_result
        
        # Step 3: Update parsed database
        parsed_update_result = self._update_parsed_database(
            document=document,
            extraction_result=extraction_result,
            json_path=json_path,
            parsing_time=parsing_time
        )
        
        return parsed_update_result
    
    def _verify_output_file(self, json_path: Path) -> Dict[str, Any]:
        """
        Verify output JSON file exists and has valid content.
        
        Args:
            json_path: Path to output JSON file
            
        Returns:
            Dictionary containing:
                - verified (bool): Whether verification passed
                - file_size (int): Size of file in bytes (if verified)
                - error (str): Error message (if verification failed)
        """
        # Check file exists
        if not json_path.exists():
            error_msg = f"CRITICAL: Facts JSON file does not exist: {json_path}"
            self.logger.error(error_msg)
            return {
                'verified': False,
                'error': error_msg
            }
        
        # Check file is not empty
        file_size = json_path.stat().st_size
        if file_size == FileVerificationConstants.EMPTY_FILE_SIZE_BYTES:
            error_msg = f"CRITICAL: Facts JSON file is empty: {json_path}"
            self.logger.error(error_msg)
            return {
                'verified': False,
                'error': error_msg
            }
        
        return {
            'verified': True,
            'file_size': file_size
        }
    
    def _update_core_database(
        self,
        document: Document,
        session,
        extraction_result: Dict[str, Any],
        json_path: Path,
        parsing_time: float,
        file_size: int
    ) -> Dict[str, Any]:
        """
        Update core database with parsing results.
        
        Args:
            document: Document being updated
            session: Database session
            extraction_result: Extraction results
            json_path: Path to JSON output
            parsing_time: Time taken for parsing
            file_size: Size of output file in bytes
            
        Returns:
            Dictionary with update result
        """
        try:
            document.parsed_status = 'completed'
            document.facts_json_path = str(json_path.absolute())
            document.facts_count = extraction_result['facts_count']
            document.parsing_metadata = self._build_parsing_metadata(
                extraction_result=extraction_result,
                parsing_time=parsing_time,
                file_size=file_size
            )
            session.commit()
            
            self.logger.info(
                f"Core database updated: {document.document_name} marked as completed"
            )
            
            return {'success': True}
            
        except Exception as exception:
            self.logger.error(
                f"Failed to update core database: {exception}",
                exc_info=True
            )
            session.rollback()
            return {
                'success': False,
                'error': f"Core database update failed: {str(exception)}",
                'error_type': 'database_error'
            }
    
    def _build_parsing_metadata(
        self,
        extraction_result: Dict[str, Any],
        parsing_time: float,
        file_size: int
    ) -> Dict[str, Any]:
        """
        Build parsing metadata dictionary for core database.
        
        Args:
            extraction_result: Extraction results
            parsing_time: Time taken for parsing in seconds
            file_size: Size of output file in bytes
            
        Returns:
            Dictionary with parsing metadata
        """
        return {
            ParsingMetadataKeys.FACTS_EXTRACTED: extraction_result['facts_count'],
            ParsingMetadataKeys.CONTEXTS_EXTRACTED: extraction_result['contexts_count'],
            ParsingMetadataKeys.UNITS_EXTRACTED: extraction_result['units_count'],
            ParsingMetadataKeys.PARSING_TIME_SECONDS: parsing_time,
            ParsingMetadataKeys.PARSED_AT: datetime.now(timezone.utc).isoformat(),
            ParsingMetadataKeys.FILE_SIZE_BYTES: file_size,
            ParsingMetadataKeys.FILE_VERIFIED: True
        }
    
    def _update_parsed_database(
        self,
        document: Document,
        extraction_result: Dict[str, Any],
        json_path: Path,
        parsing_time: float
    ) -> Dict[str, Any]:
        """
        Update parsed database with extraction data.
        
        Args:
            document: Document being updated
            extraction_result: Extraction results
            json_path: Path to JSON output
            parsing_time: Time taken for parsing
            
        Returns:
            Dictionary with update result
        """
        try:
            self.document_manager.create_or_update_parsed_document(
                document=document,
                extraction_result=extraction_result,
                json_path=json_path,
                parsing_time=parsing_time
            )
            
            self.logger.info(
                f"Parsed database updated: {document.document_name}"
            )
            
            return {'success': True}
            
        except Exception as exception:
            self.logger.error(
                f"Failed to update parsed database: {exception}",
                exc_info=True
            )
            return {
                'success': False,
                'error': f"Parsed database update failed: {str(exception)}",
                'error_type': 'database_error'
            }


__all__ = [
    'ParsingDatabaseUpdater',
    'FileVerificationConstants',
    'ParsingMetadataKeys'
]