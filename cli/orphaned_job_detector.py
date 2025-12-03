"""
Database Schema Verification - Orphaned Job Detector
=====================================================

Location: tools/cli/orphaned_job_detector.py

Detects and reports orphaned jobs.
"""

from typing import List
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db_check_constants import DiagnosticConstants, DiagnosticMessages, SQLQueries
from .db_check_models import OrphanedJobInfo


class OrphanedJobDetector:
    """Detects and reports orphaned jobs."""
    
    def __init__(self, session: Session):
        """
        Initialize the orphaned job detector.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def count_orphaned_jobs(self) -> int:
        """
        Count jobs with entity IDs that don't exist in entities table.
        
        Returns:
            Number of orphaned jobs
        """
        query = text(
            SQLQueries.ORPHANED_JOBS_COUNT.format(
                jobs_table=DiagnosticConstants.PROCESSING_JOBS_TABLE,
                entities_table=DiagnosticConstants.ENTITIES_TABLE
            )
        )
        return self.session.execute(query).fetchone()[0]
    
    def get_orphaned_job_details(
        self, 
        limit: int = DiagnosticConstants.DEFAULT_LIMIT
    ) -> List[OrphanedJobInfo]:
        """
        Get detailed information about orphaned jobs.
        
        Args:
            limit: Maximum number of records to retrieve
            
        Returns:
            List of OrphanedJobInfo objects
        """
        query = text(
            SQLQueries.ORPHANED_JOBS_DETAILS.format(
                jobs_table=DiagnosticConstants.PROCESSING_JOBS_TABLE,
                entities_table=DiagnosticConstants.ENTITIES_TABLE
            )
        )
        
        results = self.session.execute(query, {'limit': limit}).fetchall()
        
        return [
            OrphanedJobInfo(
                job_id=row[0],
                entity_id=row[1],
                job_type=row[2],
                created_at=str(row[3])
            )
            for row in results
        ]
    
    def print_orphaned_job_summary(
        self, 
        count: int, 
        details: List[OrphanedJobInfo]
    ) -> None:
        """
        Print summary of orphaned jobs.
        
        Args:
            count: Total number of orphaned jobs
            details: List of orphaned job details
        """
        print(DiagnosticMessages.RESULT_ORPHANED_COUNT.format(count))
        
        if count > 0:
            print(DiagnosticMessages.RESULT_ORPHANED_DETAILS)
            for job in details:
                print(f"  Job {job.job_id}: entity_id={job.entity_id}, "
                      f"type={job.job_type}, created={job.created_at}")