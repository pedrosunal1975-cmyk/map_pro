# PATH: /map_pro/core/filing_stages/job_waiter.py

"""
Job Waiter
==========

Simple utility for waiting on job completion.

Revolutionary Architecture:
- NO job finding (stages create their own jobs)
- ONLY job waiting (monitor job status until complete)
- Clean, focused responsibility

Replaces: job_finder.py (which waited for dictator to create jobs)
New Purpose: Wait for jobs that stages create themselves

Responsibilities:
- Wait for job completion with timeout
- Poll job status periodically
- Parse and return job results
- Handle timeouts gracefully

Does NOT:
- Find jobs created by others
- Create jobs
- Make workflow decisions
- Wait for dictator (deleted!)

FIXED: Convert database string status to JobStatus enum for proper comparison
"""

import asyncio
import time
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from database.models.core_models import ProcessingJob
from shared.constants.job_constants import JobStatus

logger = get_logger(__name__, 'core')

# Wait configuration constants
DEFAULT_POLL_INTERVAL = 2  # seconds between status checks
DEFAULT_MAX_WAIT_PER_STAGE = 600  # 10 minutes max wait
POLL_SLEEP_INTERVAL = 1  # sleep between polls


class JobWaiter:
    """
    Waits for jobs to complete and monitors their status.
    
    Simple utility focused on ONE task: waiting for job completion.
    Stages create their own jobs, this just waits for them to finish.
    """
    
    def __init__(
        self,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        max_wait_per_stage: int = DEFAULT_MAX_WAIT_PER_STAGE
    ):
        """
        Initialize job waiter.
        
        Args:
            poll_interval: Seconds between status checks
            max_wait_per_stage: Maximum seconds to wait for completion
        """
        self.logger = logger
        self.poll_interval = poll_interval
        self.max_wait_per_stage = max_wait_per_stage
    
    async def wait_for_job_completion(
        self,
        job_id: str,
        stage_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for job to complete.
        
        Polls job status until completion or timeout.
        
        Args:
            job_id: Job ID to wait for
            stage_name: Stage name for logging
            
        Returns:
            Job result dictionary if successful, None if timeout
        """
        self.logger.info(f"Waiting for {stage_name} job {job_id} to complete")
        
        start_time = time.time()
        last_log_time = start_time
        
        while time.time() - start_time < self.max_wait_per_stage:
            try:
                # Check job status
                job_status = self._check_job_status(job_id)
                
                if not job_status:
                    self.logger.warning(f"Job {job_id} not found in database")
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                status = job_status['status']
                
                # Job completed successfully
                if status == JobStatus.COMPLETED:
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"{stage_name.capitalize()} job {job_id} completed "
                        f"successfully in {elapsed:.1f}s"
                    )
                    return self._parse_job_result(job_status['job'])
                
                # Job failed
                if status == JobStatus.FAILED:
                    self.logger.error(f"{stage_name.capitalize()} job {job_id} failed")
                    return self._parse_job_result(job_status['job'])
                
                # Job still running - log progress periodically
                elapsed = time.time() - start_time
                if elapsed - (last_log_time - start_time) >= 30:  # Log every 30s
                    self.logger.info(
                        f"Still waiting for {stage_name} job {job_id} "
                        f"({elapsed:.0f}s elapsed)"
                    )
                    last_log_time = time.time()
                
            except Exception as e:
                self.logger.error(
                    f"Error checking job status for {job_id}: {e}",
                    exc_info=True
                )
            
            # Sleep before next check
            await asyncio.sleep(self.poll_interval)
        
        # Timeout
        elapsed = time.time() - start_time
        self.logger.error(
            f"Timeout waiting for {stage_name} job {job_id} "
            f"after {elapsed:.0f}s"
        )
        return None
    
    def _check_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Check current status of job.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            Dictionary with job status and job object, or None if not found
        """
        try:
            with db_coordinator.get_session('core') as session:
                job = session.query(ProcessingJob).filter_by(
                    job_id=job_id
                ).first()
                
                if not job:
                    return None
                
                # CRITICAL FIX: Convert database string to JobStatus enum
                try:
                    job_status_enum = JobStatus(job.job_status)
                except ValueError:
                    self.logger.error(
                        f"Invalid job status '{job.job_status}' for job {job_id}, "
                        f"treating as FAILED"
                    )
                    job_status_enum = JobStatus.FAILED
                
                return {
                    'status': job_status_enum,  # Now returns enum, not string
                    'job': job
                }
                
        except Exception as e:
            self.logger.error(f"Error querying job {job_id}: {e}")
            return None
    
    def _parse_job_result(self, job: ProcessingJob) -> Dict[str, Any]:
        """
        Parse job result into dictionary.
        
        Args:
            job: ProcessingJob database object
            
        Returns:
            Dictionary with job results
        """
        try:
            # CRITICAL FIX: Convert database string to JobStatus enum for comparison
            try:
                job_status_enum = JobStatus(job.job_status)
            except ValueError:
                self.logger.error(
                    f"Invalid job status '{job.job_status}' for job {job.job_id}, "
                    f"treating as FAILED"
                )
                job_status_enum = JobStatus.FAILED
            
            result = {
                'success': job_status_enum == JobStatus.COMPLETED,
                'status': job_status_enum,
                'job_id': job.job_id,
                'job_type': job.job_type
            }
            
            # Add result data if available
            if job.job_result:
                import json
                try:
                    result_data = json.loads(job.job_result) if isinstance(job.job_result, str) else job.job_result
                    result.update(result_data)
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(
                        f"Could not parse job_result for job {job.job_id}: {e}"
                    )
            
            # Add error if job failed
            if job_status_enum == JobStatus.FAILED and job.error_message:
                result['error'] = job.error_message
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing job result: {e}")
            return {
                'success': False,
                'status': JobStatus.FAILED,
                'error': f'Error parsing result: {str(e)}'
            }


__all__ = ['JobWaiter']