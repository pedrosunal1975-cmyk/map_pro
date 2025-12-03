# File: /map_pro/core/job_retry_manager.py

"""
Job Retry Manager
=================

Manages retry logic for failed jobs.
Determines retry eligibility and tracks retry attempts.
"""

from typing import Tuple

from .system_logger import get_logger
from shared.constants.job_constants import JobType, MAX_RETRY_ATTEMPTS

from .job_orchestrator_constants import DEFAULT_MAX_RETRIES

logger = get_logger(__name__, 'core')


class JobRetryManager:
    """
    Manages job retry logic.
    
    Responsibilities:
    - Determine if job should be retried
    - Track retry attempts
    - Get max retry limits by job type
    - Calculate next retry attempt number
    """
    
    def __init__(self):
        """Initialize job retry manager."""
        self.logger = logger
    
    def should_retry_job(
        self,
        job_type: str,
        current_retry_count: int
    ) -> Tuple[bool, int]:
        """
        Determine if job should be retried.
        
        Args:
            job_type: Job type string
            current_retry_count: Current number of retries
            
        Returns:
            Tuple of (should_retry, next_attempt_number)
        """
        # Get max retries for this job type
        max_retries = self._get_max_retries_for_type(job_type)
        
        # Ensure retry count is valid
        retry_count = current_retry_count if current_retry_count else 0
        
        # Calculate next attempt
        next_attempt = retry_count + 1
        
        # Determine if should retry
        should_retry = next_attempt <= max_retries
        
        return should_retry, next_attempt
    
    def get_max_retries(self, job_type: str) -> int:
        """
        Get maximum retry attempts for job type.
        
        Args:
            job_type: Job type string
            
        Returns:
            Maximum number of retry attempts
        """
        return self._get_max_retries_for_type(job_type)
    
    def _get_max_retries_for_type(self, job_type: str) -> int:
        """
        Get max retry attempts for specific job type.
        
        Args:
            job_type: Job type string
            
        Returns:
            Maximum number of retries for this job type
        """
        try:
            job_type_enum = JobType(job_type)
            return MAX_RETRY_ATTEMPTS.get(job_type_enum, DEFAULT_MAX_RETRIES)
        except ValueError:
            self.logger.warning(
                f"Unknown job type {job_type}, using default max retries: {DEFAULT_MAX_RETRIES}"
            )
            return DEFAULT_MAX_RETRIES


__all__ = ['JobRetryManager']