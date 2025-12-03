# File: /map_pro/core/job_deduplication_checker.py

"""
Job Deduplication Checker
==========================

Prevents duplicate job creation by checking for existing jobs before
creating new ones. Used by job_workflow_manager to avoid cascading duplicates.

Architecture: Pure database query module with no side effects.
"""

from typing import Optional
from sqlalchemy import text

from .database_coordinator import get_database_session
from .system_logger import get_logger

logger = get_logger(__name__, 'core')


class JobDeduplicationChecker:
    """
    Checks for existing jobs before creating duplicates.
    
    Responsibilities:
    - Query for existing jobs by type and filing/entity
    - Check job status (queued, running, or completed)
    - Provide fast lookups using database indexes
    
    Does NOT:
    - Create or modify jobs (read-only queries)
    - Make decisions about whether to create jobs (caller decides)
    - Handle job orchestration (job_orchestrator handles this)
    """
    
    def __init__(self):
        logger.debug("Job deduplication checker initialized")
    
    def check_filing_job_exists(
        self,
        job_type: str,
        filing_id: str,
        active_only: bool = True
    ) -> bool:
        """
        Check if a job already exists for a specific filing.
        
        Args:
            job_type: Type of job (e.g., 'extract_files', 'parse_xbrl')
            filing_id: Filing universal ID
            active_only: If True, only check queued/running jobs.
                        If False, also check completed jobs.
        
        Returns:
            bool: True if matching job exists, False otherwise
        """
        try:
            with get_database_session('core') as session:
                if active_only:
                    status_filter = "AND job_status IN ('queued', 'running')"
                else:
                    status_filter = "AND job_status IN ('queued', 'running', 'completed')"
                
                query = text(f"""
                    SELECT COUNT(*) 
                    FROM processing_jobs 
                    WHERE job_type = :job_type 
                    AND job_parameters::jsonb->>'filing_universal_id' = :filing_id
                    {status_filter}
                """)
                
                count = session.execute(
                    query,
                    {'job_type': job_type, 'filing_id': filing_id}
                ).scalar()
                
                exists = count > 0
                
                if exists:
                    logger.debug(
                        f"Found {count} existing {job_type} job(s) for filing {filing_id}"
                    )
                
                return exists
                
        except Exception as e:
            logger.error(f"Error checking filing job existence: {e}")
            # Return True to be safe (don't create duplicate if check fails)
            return True
    
    def check_entity_job_exists(
        self,
        job_type: str,
        entity_id: str,
        active_only: bool = True
    ) -> bool:
        """
        Check if a job already exists for a specific entity.
        
        Used for entity-level jobs like search_entity, find_filings.
        
        Args:
            job_type: Type of job
            entity_id: Entity universal ID
            active_only: If True, only check queued/running jobs
        
        Returns:
            bool: True if matching job exists, False otherwise
        """
        try:
            with get_database_session('core') as session:
                if active_only:
                    status_filter = "AND job_status IN ('queued', 'running')"
                else:
                    status_filter = "AND job_status IN ('queued', 'running', 'completed')"
                
                query = text(f"""
                    SELECT COUNT(*) 
                    FROM processing_jobs 
                    WHERE job_type = :job_type 
                    AND entity_universal_id::text = :entity_id
                    {status_filter}
                """)
                
                count = session.execute(
                    query,
                    {'job_type': job_type, 'entity_id': entity_id}
                ).scalar()
                
                exists = count > 0
                
                if exists:
                    logger.debug(
                        f"Found {count} existing {job_type} job(s) for entity {entity_id}"
                    )
                
                return exists
                
        except Exception as e:
            logger.error(f"Error checking entity job existence: {e}")
            return True
    
    def get_job_count(
        self,
        job_type: str,
        filing_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Get count of jobs matching criteria.
        
        Useful for diagnostics and logging.
        
        Args:
            job_type: Type of job
            filing_id: Optional filing ID filter
            entity_id: Optional entity ID filter
            status: Optional status filter (queued, running, completed, failed)
        
        Returns:
            int: Number of matching jobs
        """
        try:
            with get_database_session('core') as session:
                query_parts = ["SELECT COUNT(*) FROM processing_jobs WHERE job_type = :job_type"]
                params = {'job_type': job_type}
                
                if filing_id:
                    query_parts.append("AND job_parameters::jsonb->>'filing_universal_id' = :filing_id")
                    params['filing_id'] = filing_id
                
                if entity_id:
                    query_parts.append("AND entity_universal_id::text = :entity_id")
                    params['entity_id'] = entity_id
                
                if status:
                    query_parts.append("AND job_status = :status")
                    params['status'] = status
                
                query = text(" ".join(query_parts))
                count = session.execute(query, params).scalar()
                
                return count or 0
                
        except Exception as e:
            logger.error(f"Error getting job count: {e}")
            return 0
    
    def should_create_job(
        self,
        job_type: str,
        filing_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        allow_if_completed: bool = False
    ) -> tuple[bool, str]:
        """
        Determine if a job should be created based on existing jobs.
        
        Convenience method that combines checks and provides reasoning.
        
        Args:
            job_type: Type of job to create
            filing_id: Filing ID (for filing-level jobs)
            entity_id: Entity ID (for entity-level jobs)
            allow_if_completed: Allow creation if only completed jobs exist
        
        Returns:
            tuple: (should_create: bool, reason: str)
        """
        try:
            # Check filing-level jobs
            if filing_id:
                active_exists = self.check_filing_job_exists(
                    job_type, filing_id, active_only=True
                )
                
                if active_exists:
                    return False, f"Active {job_type} job already exists for filing"
                
                if not allow_if_completed:
                    completed_exists = self.check_filing_job_exists(
                        job_type, filing_id, active_only=False
                    )
                    
                    if completed_exists:
                        return False, f"Completed {job_type} job already exists for filing"
            
            # Check entity-level jobs
            if entity_id:
                active_exists = self.check_entity_job_exists(
                    job_type, entity_id, active_only=True
                )
                
                if active_exists:
                    return False, f"Active {job_type} job already exists for entity"
                
                if not allow_if_completed:
                    completed_exists = self.check_entity_job_exists(
                        job_type, entity_id, active_only=False
                    )
                    
                    if completed_exists:
                        return False, f"Completed {job_type} job already exists for entity"
            
            return True, "No duplicate jobs found"
            
        except Exception as e:
            logger.error(f"Error in should_create_job: {e}")
            return False, f"Check failed: {str(e)}"


# Module-level singleton instance
_checker_instance = None


def get_deduplication_checker() -> JobDeduplicationChecker:
    """
    Get singleton instance of JobDeduplicationChecker.
    
    Returns:
        JobDeduplicationChecker: Shared checker instance
    """
    global _checker_instance
    
    if _checker_instance is None:
        _checker_instance = JobDeduplicationChecker()
    
    return _checker_instance