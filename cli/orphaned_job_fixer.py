"""
Database Schema Verification - Orphaned Job Fixer
==================================================

Location: tools/cli/orphaned_job_fixer.py

Fixes orphaned jobs by removing invalid references.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from .db_check_constants import DiagnosticConstants, SQLQueries


class OrphanedJobFixer:
    """Fixes orphaned jobs by removing invalid references."""
    
    def __init__(self, session: Session):
        """
        Initialize the orphaned job fixer.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def remove_orphaned_jobs(self) -> int:
        """
        Remove jobs that reference non-existent entities.
        
        Returns:
            Number of jobs removed
            
        Raises:
            Exception: If removal operation fails
        """
        query = text(
            SQLQueries.DELETE_ORPHANED_JOBS.format(
                jobs_table=DiagnosticConstants.PROCESSING_JOBS_TABLE,
                entities_table=DiagnosticConstants.ENTITIES_TABLE
            )
        )
        
        result = self.session.execute(query)
        return result.rowcount