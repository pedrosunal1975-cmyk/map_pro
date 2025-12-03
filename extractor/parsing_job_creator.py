# File: /map_pro/engines/extractor/parsing_job_creator.py

"""
Parsing Job Creator
===================

Creates parsing jobs for extracted XBRL documents.
"""

from typing import List

from database.models.core_models import Filing, Document, ProcessingJob
from shared.constants.job_constants import JobType, JobStatus


class ParsingJobCreator:
    """
    Creates parsing jobs for XBRL documents.
    
    Responsibilities:
    - Query parsing-eligible documents
    - Create parsing jobs in database
    - Track job creation statistics
    """
    
    def __init__(self, logger):
        """
        Initialize parsing job creator.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def create_parsing_jobs_for_filing(
        self,
        filing: Filing,
        session
    ) -> int:
        """
        Create parsing jobs for all parsing-eligible documents in a filing.
        Called AFTER extraction is complete and committed.
        
        Args:
            filing: Filing object
            session: Database session
            
        Returns:
            Number of parsing jobs created
        """
        documents = self._get_parsing_eligible_documents(
            filing=filing,
            session=session
        )
        
        jobs_created = 0
        for document in documents:
            if document.extraction_path:
                try:
                    self._create_parsing_job(
                        filing_id=filing.filing_universal_id,
                        document=document,
                        session=session
                    )
                    jobs_created += 1
                except Exception as e:
                    self.logger.warning(
                        f"Failed to create parsing job for {document.document_name}: {e}"
                    )
        
        self.logger.info(
            f"Created {jobs_created} parsing jobs for filing {filing.filing_universal_id}"
        )
        return jobs_created
    
    def _get_parsing_eligible_documents(
        self,
        filing: Filing,
        session
    ) -> List[Document]:
        """
        Get all parsing-eligible documents for a filing.
        
        Args:
            filing: Filing object
            session: Database session
            
        Returns:
            List of Document objects eligible for parsing
        """
        return session.query(Document).filter_by(
            filing_universal_id=filing.filing_universal_id,
            parsing_eligible=True
        ).all()
    
    def _create_parsing_job(
        self,
        filing_id: str,
        document: Document,
        session
    ):
        """
        Create parsing job for XBRL document.
        
        Args:
            filing_id: Filing UUID
            document: Document object
            session: Database session
        """
        parsing_job = ProcessingJob(
            job_type=JobType.PARSE_XBRL.value,
            job_status=JobStatus.QUEUED.value,
            filing_universal_id=filing_id,
            job_parameters={
                'document_id': str(document.document_universal_id)
            }
        )
        
        session.add(parsing_job)
        self.logger.debug(f"Created parsing job for document {document.document_name}")