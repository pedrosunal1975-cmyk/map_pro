# File: /map_pro/core/job_orchestrator.py

"""
Map Pro Job Orchestrator
========================

Central coordination for PostgreSQL-based job queue system across all engines.
Manages job queue operations without implementing specific engine operations.

Architecture: Core oversight/coordination only - engines handle their own job processing.
Stages create their own jobs - no follow-up job creation needed.

This module has been refactored into:
- job_orchestrator.py (this file) - Main orchestration
- job_database_operations.py - Database operations abstraction
- job_retry_manager.py - Retry logic management
- job_parameter_handler.py - Parameter processing
- job_orchestrator_constants.py - Constants

FIXED: UUID JSON serialization error by converting UUID objects to strings
FIXED: Duplicate exception handling and entity_id extraction issues
FIXED: Missing session.commit() calls causing job status updates to not persist
"""

from typing import Dict, List, Optional, Any

from .system_logger import get_logger
from shared.constants.job_constants import JobType, JobStatus, JobPriority

from .job_database_operations import JobDatabaseOperations
from .job_retry_manager import JobRetryManager
from .job_parameter_handler import JobParameterHandler

logger = get_logger(__name__, 'core')


class JobOrchestrator:
    """
    Central coordinator for job processing across all Map Pro engines.
    
    Responsibilities:
    - Orchestrate job lifecycle operations
    - Coordinate between specialized handlers
    - Provide high-level job management interface
    
    Does NOT handle:
    - Actual job processing (engines do their own work)
    - Workflow logic (stages handle their own workflow)
    - Database schema management (migration system handles this)
    - Direct database operations (delegated to JobDatabaseOperations)
    """
    
    def __init__(
        self,
        db_operations: Optional[JobDatabaseOperations] = None,
        retry_manager: Optional[JobRetryManager] = None,
        parameter_handler: Optional[JobParameterHandler] = None
    ):
        """
        Initialize job orchestrator with optional dependencies.
        
        Args:
            db_operations: Database operations handler (created if None)
            retry_manager: Retry logic manager (created if None)
            parameter_handler: Parameter processing handler (created if None)
        """
        self.db_operations = db_operations or JobDatabaseOperations()
        self.retry_manager = retry_manager or JobRetryManager()
        self.parameter_handler = parameter_handler or JobParameterHandler()
        
        self.logger = logger
        self.logger.info("Job orchestrator initialized")
    
    def create_job(
        self,
        job_type: JobType,
        entity_id: str,
        market_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: JobPriority = JobPriority.NORMAL
    ) -> str:
        """
        Create new job in the queue.
        
        Args:
            job_type: Type of job to create
            entity_id: Entity universal ID
            market_type: Market type (SEC, FCA, etc.)
            parameters: Optional job parameters
            priority: Job priority level
            
        Returns:
            Job ID (UUID string)
        """
        # Process parameters
        processed_params = self.parameter_handler.process_parameters(parameters or {})
        
        # Extract filing ID from parameters
        filing_id = self.parameter_handler.extract_filing_id(processed_params)
        
        # Create job in database
        job_id = self.db_operations.create_job(
            job_type=job_type,
            entity_id=entity_id,
            filing_id=filing_id,
            market_type=market_type,
            parameters=processed_params,
            priority=priority
        )
        
        self.logger.info(
            f"Created job {job_id} of type {job_type.value} "
            f"for entity {entity_id}, filing {filing_id}"
        )
        
        return job_id
    
    def get_next_job(
        self,
        job_types: List[JobType],
        engine_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get next available job for processing by specified engine.
        
        Args:
            job_types: List of job types this engine can process
            engine_name: Name of the requesting engine
            
        Returns:
            Job dictionary with details or None if no jobs available
        """
        # Fetch and lock job
        job_data = self.db_operations.fetch_and_lock_job(job_types)
        
        if not job_data:
            return None
        
        # Ensure entity_id is in parameters
        job_data = self.parameter_handler.ensure_entity_in_parameters(job_data)
        
        # Mark job as running
        self.db_operations.mark_job_running(job_data['job_id'])
        
        self.logger.info(
            f"Engine {engine_name} claimed job {job_data['job_id']} "
            f"of type {job_data['job_type']}"
        )
        
        return job_data
    
    def complete_job(
        self,
        job_id: str,
        result_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark job as completed and log completion.
        
        Args:
            job_id: Job ID to complete
            result_data: Optional result data from job execution
        """
        # Process result data
        processed_result = self.parameter_handler.process_parameters(result_data or {})
        
        # Mark job as completed
        self.db_operations.mark_job_completed(job_id, processed_result)
        
        self.logger.info(
            f"Job {job_id} completed successfully. "
            f"Stages handle their own workflow."
        )
    
    def fail_job(self, job_id: str, error_message: str) -> None:
        """
        Mark job as failed and handle retry logic.
        
        Args:
            job_id: Job ID to fail
            error_message: Error description
        """
        # Get job info
        job_info = self.db_operations.get_job_info(job_id)
        
        if not job_info:
            self.logger.error(f"Job {job_id} not found for failure")
            return
        
        # Determine if job should be retried
        should_retry, attempt_number = self.retry_manager.should_retry_job(
            job_type=job_info['job_type'],
            current_retry_count=job_info['retry_count']
        )
        
        if should_retry:
            self._retry_job(job_id, job_info, error_message, attempt_number)
        else:
            self._permanently_fail_job(job_id, job_info, error_message)
    
    def _retry_job(
        self,
        job_id: str,
        job_info: Dict[str, Any],
        error_message: str,
        attempt_number: int
    ) -> None:
        """
        Queue job for retry.
        
        Args:
            job_id: Job ID
            job_info: Job information
            error_message: Error that occurred
            attempt_number: Retry attempt number
        """
        max_retries = self.retry_manager.get_max_retries(job_info['job_type'])
        
        self.db_operations.mark_job_for_retry(
            job_id=job_id,
            retry_count=attempt_number,
            error_message=error_message
        )
        
        self.logger.info(
            f"Job {job_id} ({job_info['job_type']}) queued for retry "
            f"(attempt {attempt_number}/{max_retries})"
        )
    
    def _permanently_fail_job(
        self,
        job_id: str,
        job_info: Dict[str, Any],
        error_message: str
    ) -> None:
        """
        Permanently fail a job.
        
        Args:
            job_id: Job ID
            job_info: Job information
            error_message: Final error message
        """
        retry_count = job_info['retry_count']
        
        self.db_operations.mark_job_failed(
            job_id=job_id,
            error_message=error_message
        )
        
        self.logger.error(
            f"Job {job_id} ({job_info['job_type']}) permanently failed "
            f"after {retry_count} retries: {error_message}"
        )
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a job.
        
        Args:
            job_id: Job ID to query
            
        Returns:
            Job status dictionary or None if not found
        """
        return self.db_operations.get_job_status(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a queued job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled, False if job not queued
        """
        success = self.db_operations.cancel_job(job_id)
        
        if success:
            self.logger.info(f"Cancelled job {job_id}")
        else:
            self.logger.warning(f"Could not cancel job {job_id} - may not be queued")
        
        return success
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the job queue.
        
        Returns:
            Dictionary with queue statistics
        """
        return self.db_operations.get_queue_statistics()


# Global instance
job_orchestrator = JobOrchestrator()

__all__ = ['JobOrchestrator', 'job_orchestrator']