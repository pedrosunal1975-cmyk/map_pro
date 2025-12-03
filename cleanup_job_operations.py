# File: /map_pro/tools/cleanup_job_operations.py

"""
Cleanup Job Operations
======================

Handles all job-related cleanup operations including job deletion,
status resets, and job filtering.

Responsibilities:
- Clean up processing jobs with flexible filtering
- Reset stuck job and filing statuses
- Handle job status transitions safely
- Track job cleanup statistics

Related Files:
- cleanup_orchestrator.py: Main orchestration
- database_cleanup.py: Entry point
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from core.database_coordinator import db_coordinator
from database.models.core_models import ProcessingJob, Filing
from shared.constants.job_constants import JobStatus


class TimeConstants:
    """Constants for time-based calculations."""
    HOURS_FOR_STUCK_STATUS = 2


class CleanupJobOperations:
    """
    Handles job-related cleanup operations.
    
    This class provides methods for cleaning up processing jobs based on
    various criteria such as status, age, and job type.
    """
    
    def __init__(self, logger, dry_run: bool = False):
        """
        Initialize job cleanup operations.
        
        Args:
            logger: Logger instance for operation logging
            dry_run: If True, preview changes without applying them
        """
        self.logger = logger
        self.dry_run = dry_run
    
    def cleanup_jobs(
        self,
        status_filter: Optional[List[str]] = None,
        days_old: Optional[int] = None,
        job_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Clean up processing jobs with flexible filtering.
        
        Args:
            status_filter: List of job statuses to filter (e.g., ['failed', 'completed'])
            days_old: Only clean jobs older than this many days
            job_types: List of job types to filter (optional)
            
        Returns:
            Dictionary with cleanup results containing:
                - jobs_removed (int): Number of jobs removed
                - summary (str): Summary of operation
                - errors (list): List of error messages if any
        """
        result = {
            'jobs_removed': 0,
            'summary': '',
            'errors': []
        }
        
        try:
            with db_coordinator.get_session('core') as session:
                query = session.query(ProcessingJob)
                
                # Apply status filter
                if status_filter:
                    query = query.filter(ProcessingJob.job_status.in_(status_filter))
                
                # Apply age filter
                if days_old:
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
                    query = query.filter(ProcessingJob.updated_at < cutoff_date)
                
                # Apply job type filter
                if job_types:
                    query = query.filter(ProcessingJob.job_type.in_(job_types))
                
                jobs_to_remove = query.all()
                count = len(jobs_to_remove)
                
                # Remove jobs if not dry run
                if not self.dry_run:
                    for job in jobs_to_remove:
                        session.delete(job)
                    session.commit()
                
                result['jobs_removed'] = count
                result['summary'] = f"Removed {count} jobs"
                
                self.logger.info(f"Jobs cleanup: {count} jobs processed")
                
        except Exception as exception:
            error_msg = f"Jobs cleanup failed: {exception}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def cleanup_failed_jobs(self) -> Dict[str, Any]:
        """
        Clean up jobs with failed, error, or cancelled status.
        
        Returns:
            Dictionary with cleanup results
        """
        failed_statuses = ['failed', 'error', 'cancelled']
        return self.cleanup_jobs(status_filter=failed_statuses)
    
    def cleanup_old_jobs(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old completed jobs.
        
        Args:
            days_old: Age threshold in days (default: 30)
            
        Returns:
            Dictionary with cleanup results
        """
        return self.cleanup_jobs(
            status_filter=['completed'],
            days_old=days_old
        )
    
    def reset_pending_statuses(self) -> Dict[str, Any]:
        """
        Reset stuck pending/running statuses to allow reprocessing.
        
        Identifies jobs and filings that have been in transient states
        (running, retry, downloading) for too long and resets them to
        allow reprocessing.
        
        Returns:
            Dictionary with reset results containing:
                - statuses_reset (int): Number of statuses reset
                - summary (str): Summary of operation
                - errors (list): List of error messages if any
        """
        result = {
            'statuses_reset': 0,
            'summary': '',
            'errors': []
        }
        
        try:
            with db_coordinator.get_session('core') as session:
                # Find stuck jobs
                stuck_threshold = datetime.now(timezone.utc) - timedelta(
                    hours=TimeConstants.HOURS_FOR_STUCK_STATUS
                )
                
                stuck_jobs = session.query(ProcessingJob).filter(
                    ProcessingJob.job_status.in_(['running', 'retry']),
                    ProcessingJob.updated_at < stuck_threshold
                ).all()
                
                # Find stuck filings
                stuck_filings = session.query(Filing).filter(
                    Filing.download_status == 'downloading'
                ).all()
                
                # Reset statuses if not dry run
                if not self.dry_run:
                    for job in stuck_jobs:
                        job.job_status = JobStatus.QUEUED.value
                        job.started_at = None
                        job.error_message = "Reset by cleanup tool"
                    
                    for filing in stuck_filings:
                        filing.download_status = 'pending'
                    
                    session.commit()
                
                total_reset = len(stuck_jobs) + len(stuck_filings)
                result['statuses_reset'] = total_reset
                result['summary'] = f"Reset {total_reset} stuck statuses"
                
                self.logger.info(
                    f"Status reset: {len(stuck_jobs)} jobs, "
                    f"{len(stuck_filings)} filings"
                )
                
        except Exception as exception:
            error_msg = f"Status reset failed: {exception}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result


__all__ = ['CleanupJobOperations', 'TimeConstants']