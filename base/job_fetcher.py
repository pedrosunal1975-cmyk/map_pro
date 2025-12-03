"""
Map Pro Job Processor - Job Fetcher (FIXED)
============================================

Location: engines/base/job_fetcher.py

FIXED: Logger now uses parent logger to avoid duplication.
"""

from typing import Dict, Any, List, TYPE_CHECKING, Optional
import logging

from core.job_orchestrator import job_orchestrator
from shared.constants.job_constants import JobType

if TYPE_CHECKING:
    from .engine_base import BaseEngine


class JobFetcher:
    """
    Fetches available jobs for an engine from the job orchestrator.
    
    Responsibilities:
    - Retrieving jobs this engine can handle
    - Smart logging (only log when jobs found)
    - Batch size management
    """
    
    def __init__(self, engine: 'BaseEngine', batch_size: int, parent_logger: logging.Logger) -> None:
        """
        Initialize job fetcher.
        
        Args:
            engine: The engine instance
            batch_size: Maximum number of jobs to fetch per iteration
            parent_logger: Parent logger to use (avoids creating duplicate loggers)
        """
        self.engine = engine
        self.batch_size = batch_size
        self.logger = parent_logger  # Use parent logger, don't create new one
        self._no_job_types_warned = False
    
    def get_available_jobs(self) -> List[Dict[str, Any]]:
        """
        Get available jobs this engine can process.
        
        FIXED: Only log when there's something interesting.
        Don't log routine checks at all to reduce noise.
        
        Returns:
            List of job dictionaries
        """
        try:
            supported_types = self.engine.get_supported_job_types()
            
            if not supported_types:
                self._log_no_supported_types()
                return []
            
            jobs = self._fetch_jobs_by_type(supported_types)
            
            if not jobs:
                self.logger.debug(f"No jobs found for engine {self.engine.engine_name}")
            
            return jobs
        
        except Exception as e:
            self.logger.error(f"Failed to get available jobs: {e}")
            self._log_detailed_error(e)
            return []
    
    def _log_no_supported_types(self) -> None:
        """
        Log warning about no supported job types (only once per session).
        """
        if not self._no_job_types_warned:
            self.logger.warning(
                f"Engine {self.engine.engine_name} has no supported job types"
            )
            self._no_job_types_warned = True
    
    def _fetch_jobs_by_type(self, supported_types: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch jobs for each supported job type.
        
        Args:
            supported_types: List of job type strings this engine supports
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        for job_type_str in supported_types:
            try:
                job_type = JobType(job_type_str)
                job_data = job_orchestrator.get_next_job(
                    [job_type], 
                    self.engine.engine_name
                )
                
                if job_data:
                    self._log_job_found(job_data)
                    jobs.append(job_data)
                    
                    if len(jobs) >= self.batch_size:
                        break
                        
            except ValueError:
                self.logger.warning(f"Invalid job type: {job_type_str}")
                continue
        
        return jobs
    
    def _log_job_found(self, job_data: Dict[str, Any]) -> None:
        """
        Log when a job is found (ONLY log when jobs are actually found).
        
        Args:
            job_data: The job data that was found
        """
        self.logger.info(
            f"Found job: {job_data['job_id']} of type {job_data['job_type']}"
        )
    
    def _log_detailed_error(self, error: Exception) -> None:
        """
        Log detailed error information including traceback.
        
        Args:
            error: The exception that occurred
        """
        import traceback
        self.logger.error(f"Full traceback:\n{traceback.format_exc()}")