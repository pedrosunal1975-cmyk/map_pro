# File: core/filing_stages/parsing_job_manager.py

"""
Parsing Job Manager
===================

Manages parsing job creation and discovery for filing documents.
Handles multi-document job orchestration.

CRITICAL: This module handles the core fix for parsing stage:
- Finds ALL parsing jobs for a filing (not just one)
- Creates jobs for ALL documents if missing
- Properly tracks multiple concurrent parsing jobs

Architecture: Single Responsibility - Focuses only on job management.
"""

from typing import List, Optional, Tuple

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.job_orchestrator import job_orchestrator
from database.models.core_models import Filing, Document, ProcessingJob
from shared.constants.job_constants import JobType
from core.filing_stages.parsing_stage_constants import (
    STATUS_COMPLETED,
    STATUS_NOT_APPLICABLE,
    VALID_JOB_STATUSES
)

logger = get_logger(__name__, 'core')


class ParsingJobManager:
    """
    Manages parsing job lifecycle for filing documents.
    
    Responsibilities:
    - Find existing parsing jobs for filing
    - Create parsing jobs for all filing documents
    - Query filing and document metadata
    
    Does NOT handle:
    - Job execution (job_orchestrator handles this)
    - Job waiting (job_waiter handles this)
    - Prerequisites checking (parsing_prerequisites handles this)
    - Output verification (output_verifier handles this)
    """
    
    def __init__(self):
        """Initialize parsing job manager."""
        self.logger = logger
    
    def ensure_parsing_jobs(self, filing_id: str) -> Optional[List[str]]:
        """
        Find ALL existing parsing jobs or create them if missing.
        
        CRITICAL: This method handles multiple jobs per filing (one per document).
        This is the key fix that ensures ALL documents are parsed.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            List of job IDs if successful, None otherwise
        """
        try:
            # First, find all existing jobs for this filing
            existing_job_ids = self.find_all_parsing_jobs(filing_id)
            
            if existing_job_ids:
                self.logger.info(
                    "Found %d existing parsing jobs for filing %s",
                    len(existing_job_ids),
                    filing_id
                )
                return existing_job_ids
            
            # No jobs found - create them for all documents
            self.logger.info(
                "No existing jobs found. Creating parsing jobs for all documents in filing %s",
                filing_id
            )
            
            created_job_ids = self.create_parsing_jobs_for_all_documents(filing_id)
            
            if created_job_ids:
                self.logger.info(
                    "Created %d parsing jobs for filing %s",
                    len(created_job_ids),
                    filing_id
                )
                return created_job_ids
            else:
                self.logger.error(
                    "Failed to create parsing jobs for filing %s",
                    filing_id
                )
                return None
                
        except Exception as error:
            self.logger.error(
                "Error ensuring parsing jobs for filing %s: %s",
                filing_id,
                str(error),
                exc_info=True
            )
            return None
    
    def find_all_parsing_jobs(self, filing_id: str) -> List[str]:
        """
        Find ALL parsing jobs for filing (not just one).
        
        CRITICAL FIX: Returns ALL jobs, not just the first one found.
        Looks for queued, running, or recently completed parsing jobs.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            List of job IDs (may be empty)
        """
        try:
            with db_coordinator.get_session('core') as session:
                jobs = session.query(ProcessingJob).filter(
                    ProcessingJob.filing_universal_id == filing_id,
                    ProcessingJob.job_type == JobType.PARSE_XBRL.value,
                    ProcessingJob.job_status.in_(VALID_JOB_STATUSES)
                ).order_by(ProcessingJob.created_at.desc()).all()
                
                job_ids = [str(job.job_id) for job in jobs]
                
                if jobs:
                    # Log status breakdown for debugging
                    status_counts = self._count_job_statuses(jobs)
                    status_str = ", ".join(
                        [f"{count} {status}" for status, count in status_counts.items()]
                    )
                    self.logger.debug(
                        "Found %d parsing jobs for filing %s: %s",
                        len(jobs),
                        filing_id,
                        status_str
                    )
                else:
                    self.logger.debug(
                        "No parsing jobs found for filing %s",
                        filing_id
                    )
                
                return job_ids
                
        except Exception as error:
            self.logger.error(
                "Error finding parsing jobs for filing %s: %s",
                filing_id,
                str(error)
            )
            return []
    
    def _count_job_statuses(self, jobs: List[ProcessingJob]) -> dict:
        """
        Count jobs by status for logging.
        
        Args:
            jobs: List of ProcessingJob objects
            
        Returns:
            Dictionary mapping status to count
        """
        status_counts = {}
        for job in jobs:
            status = job.job_status
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def create_parsing_jobs_for_all_documents(self, filing_id: str) -> List[str]:
        """
        Create parsing jobs for all documents in the filing.
        
        CRITICAL: Creates one job per document, not just one job for the filing.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            List of created job IDs
        """
        try:
            # Get all documents for this filing
            documents = self._get_filing_documents(filing_id)
            
            if not documents:
                self.logger.warning(
                    "No documents found for filing %s",
                    filing_id
                )
                return []
            
            # Get filing metadata
            entity_id, market_type = self._get_filing_metadata(filing_id)
            
            if not entity_id:
                self.logger.error(
                    "Cannot get entity_id for filing %s",
                    filing_id
                )
                return []
            
            # Create a job for each document that needs parsing
            job_ids = []
            for document in documents:
                job_id = self._create_job_for_document(
                    document,
                    filing_id,
                    entity_id,
                    market_type
                )
                if job_id:
                    job_ids.append(job_id)
            
            return job_ids
            
        except Exception as error:
            self.logger.error(
                "Error creating parsing jobs for filing %s: %s",
                filing_id,
                str(error),
                exc_info=True
            )
            return []
    
    def _create_job_for_document(
        self,
        document: Document,
        filing_id: str,
        entity_id: str,
        market_type: str
    ) -> Optional[str]:
        """
        Create a parsing job for a single document if needed.
        
        Args:
            document: Document object
            filing_id: Filing universal ID
            entity_id: Entity universal ID
            market_type: Market type string
            
        Returns:
            Job ID if created, None if skipped
        """
        # Skip documents that are already parsed
        if document.parsed_status in [STATUS_COMPLETED, STATUS_NOT_APPLICABLE]:
            self.logger.debug(
                "Skipping document %s - already %s",
                document.document_name,
                document.parsed_status
            )
            return None
        
        try:
            job_id = job_orchestrator.create_job(
                job_type=JobType.PARSE_XBRL,
                entity_id=entity_id,
                market_type=market_type,
                parameters={
                    'filing_universal_id': filing_id,
                    'document_id': str(document.document_universal_id)
                }
            )
            
            if job_id:
                self.logger.debug(
                    "Created parsing job %s for document %s",
                    job_id,
                    document.document_name
                )
            
            return job_id
            
        except Exception as error:
            self.logger.error(
                "Error creating job for document %s: %s",
                document.document_name,
                str(error)
            )
            return None
    
    def _get_filing_documents(self, filing_id: str) -> List[Document]:
        """
        Get all documents for a filing from database.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            List of Document objects
        """
        try:
            with db_coordinator.get_session('core') as session:
                documents = session.query(Document).filter_by(
                    filing_universal_id=filing_id
                ).all()
                
                return documents
                
        except Exception as error:
            self.logger.error(
                "Error getting documents for filing %s: %s",
                filing_id,
                str(error)
            )
            return []
    
    def _get_filing_metadata(self, filing_id: str) -> Tuple[Optional[str], str]:
        """
        Get filing metadata from database.
        
        Database as journalist: Just reading reported metadata.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Tuple of (entity_id, market_type) where entity_id may be None
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter_by(
                    filing_universal_id=filing_id
                ).first()
                
                if not filing:
                    self.logger.error(
                        "Filing %s not found in database",
                        filing_id
                    )
                    return None, 'unknown'
                
                if not filing.entity:
                    self.logger.error(
                        "Filing %s has no associated entity",
                        filing_id
                    )
                    return None, 'unknown'
                
                if not filing.entity.market_type:
                    self.logger.error(
                        "Filing %s entity has no market_type specified",
                        filing_id
                    )
                    return None, 'unknown'
                
                entity_id = str(filing.entity_universal_id)
                market_type = filing.entity.market_type
                
                return entity_id, market_type
                
        except Exception as error:
            self.logger.error(
                "Error getting metadata for filing %s: %s",
                filing_id,
                str(error)
            )
            return None, 'unknown'


__all__ = [
    'ParsingJobManager'
]