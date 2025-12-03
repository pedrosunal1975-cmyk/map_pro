# File: /map_pro/engines/parser/parsed_document_manager.py

"""
Parsed Document Manager
========================

Manages ParsedDocument records in the parsed database.
Handles idempotent create/update operations with verification.

Responsibilities:
- Create/update ParsedDocument records
- Verify file existence before database updates
- Perform post-commit verification
- Handle idempotent operations
"""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.core_models import Document
from database.models.parsed_models import ParsedDocument

logger = get_logger(__name__, 'engine')


class ParsedDocumentManager:
    """Manages ParsedDocument records in the parsed database."""
    
    def create_or_update_parsed_document(
        self,
        document: Document,
        extraction_result: Dict[str, Any],
        json_path: Path,
        parsing_time: float
    ) -> str:
        """
        Create or update ParsedDocument record with verification.
        
        This is an idempotent operation - safe to call multiple times.
        
        Args:
            document: Core database document
            extraction_result: Extraction results
            json_path: Path to JSON output file
            parsing_time: Time taken to parse
            
        Returns:
            ParsedDocument ID
            
        Raises:
            IOError: If file verification fails
            RuntimeError: If database verification fails
        """
        # Step 1: Verify file exists before updating database
        self._verify_json_file(json_path)
        
        # Step 2: Create or update database record
        with db_coordinator.get_session('parsed') as session:
            record_id = self._create_or_update_record(
                session=session,
                document=document,
                extraction_result=extraction_result,
                json_path=json_path,
                parsing_time=parsing_time
            )
            
            # Step 3: Commit transaction
            session.commit()
            
            # Step 4: Verify database record
            self._verify_database_record(
                session=session,
                record_id=record_id,
                expected_facts=extraction_result['facts_count']
            )
            
            # Step 5: Log success
            self._log_success(
                document=document,
                json_path=json_path,
                record_id=record_id,
                facts_count=extraction_result['facts_count']
            )
            
            return record_id
    
    def _verify_json_file(self, json_path: Path) -> None:
        """
        Verify JSON file exists and is not empty.
        
        Args:
            json_path: Path to JSON file
            
        Raises:
            IOError: If file doesn't exist or is empty
        """
        if not json_path.exists():
            raise IOError(f"JSON file verification failed: {json_path}")
        
        if json_path.stat().st_size == 0:
            raise IOError(f"JSON file is empty: {json_path}")
    
    def _create_or_update_record(
        self,
        session,
        document: Document,
        extraction_result: Dict[str, Any],
        json_path: Path,
        parsing_time: float
    ) -> str:
        """
        Create new or update existing ParsedDocument record.
        
        Args:
            session: Database session
            document: Core document
            extraction_result: Extraction results
            json_path: Path to JSON file
            parsing_time: Parsing duration
            
        Returns:
            Record ID
        """
        document_id = document.document_universal_id

        # Check if record exists using UNIQUE constraint fields
        # This prevents duplicate key violations
        existing = session.query(ParsedDocument).filter_by(
            filing_universal_id=document.filing_universal_id,
            document_name=document.document_name
        ).first()
        
        if existing:
            return self._update_existing_record(
                existing=existing,
                extraction_result=extraction_result,
                json_path=json_path,
                parsing_time=parsing_time
            )
        else:
            return self._create_new_record(
                session=session,
                document=document,
                extraction_result=extraction_result,
                json_path=json_path,
                parsing_time=parsing_time
            )
    
    def _update_existing_record(
        self,
        existing: ParsedDocument,
        extraction_result: Dict[str, Any],
        json_path: Path,
        parsing_time: float
    ) -> str:
        """
        Update existing ParsedDocument record.
        
        Args:
            existing: Existing ParsedDocument
            extraction_result: New extraction results
            json_path: New JSON path
            parsing_time: New parsing time
            
        Returns:
            Record ID
        """
        logger.info(
            f"ParsedDocument already exists, updating: "
            f"{existing.parsed_document_id}"
        )
        
        existing.facts_extracted = extraction_result['facts_count']
        existing.contexts_extracted = extraction_result['contexts_count']
        existing.units_extracted = extraction_result['units_count']
        existing.parsing_duration_seconds = parsing_time
        existing.facts_json_path = str(json_path.absolute())
        existing.validation_status = 'completed'
        existing.parsed_at = datetime.now(timezone.utc)
        
        return existing.parsed_document_id
    
    def _create_new_record(
        self,
        session,
        document: Document,
        extraction_result: Dict[str, Any],
        json_path: Path,
        parsing_time: float
    ) -> str:
        """
        Create new ParsedDocument record.
        
        Args:
            session: Database session
            document: Core document
            extraction_result: Extraction results
            json_path: Path to JSON file
            parsing_time: Parsing duration
            
        Returns:
            Record ID
        """
        parsed_doc = ParsedDocument(
            parsed_document_id=document.document_universal_id,
            entity_universal_id=document.filing.entity_universal_id,
            filing_universal_id=document.filing_universal_id,
            document_name=document.document_name,
            source_file_path=document.extraction_path,
            facts_json_path=str(json_path.absolute()),
            parsing_engine='arelle',
            facts_extracted=extraction_result['facts_count'],
            contexts_extracted=extraction_result['contexts_count'],
            units_extracted=extraction_result['units_count'],
            parsing_duration_seconds=parsing_time,
            validation_status='completed'
        )
        
        session.add(parsed_doc)
        
        logger.info(
            f"Created ParsedDocument record: {document.document_universal_id}"
        )
        
        return parsed_doc.parsed_document_id
    
    def _verify_database_record(
        self,
        session,
        record_id: str,
        expected_facts: int
    ) -> None:
        """
        Verify database record was committed correctly.
        
        Args:
            session: Database session
            record_id: Record ID to verify
            expected_facts: Expected number of facts
            
        Raises:
            RuntimeError: If verification fails
        """
        verification = session.query(ParsedDocument).filter_by(
            parsed_document_id=record_id
        ).first()
        
        if not verification:
            raise RuntimeError(
                f"CRITICAL: ParsedDocument commit verification failed for {record_id}"
            )
        
        if verification.facts_extracted != expected_facts:
            raise RuntimeError(
                f"CRITICAL: ParsedDocument facts count mismatch: "
                f"expected {expected_facts}, got {verification.facts_extracted}"
            )
    
    def _log_success(
        self,
        document: Document,
        json_path: Path,
        record_id: str,
        facts_count: int
    ) -> None:
        """
        Log successful database update with verification details.
        
        Args:
            document: Parsed document
            json_path: Path to JSON file
            record_id: Database record ID
            facts_count: Number of facts extracted
        """
        logger.info(
            f"[VERIFIED] File + Database synchronized for {document.document_name}"
        )
        logger.info(f"   File: {json_path.absolute()}")
        logger.info(f"   DB Record: {record_id}")
        logger.info(f"   Facts: {facts_count}")


__all__ = ['ParsedDocumentManager']