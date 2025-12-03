"""
Map Pro Job Processor - Job Status Manager
===========================================

Location: engines/base/job_status_manager.py

Manages job lifecycle status updates (completed, failed).
"""

from typing import Dict, Any, TYPE_CHECKING

from core.system_logger import get_logger
from core.job_orchestrator import job_orchestrator

if TYPE_CHECKING:
    from .engine_base import BaseEngine


class JobStatusManager:
    """
    Manages job status updates in the job orchestrator.
    
    Responsibilities:
    - Marking jobs as completed
    - Marking jobs as failed
    - Error handling for status updates
    """
    
    def __init__(self, engine: 'BaseEngine') -> None:
        """
        Initialize job status manager.
        
        Args:
            engine: The engine instance
        """
        self.engine = engine
        self.logger = get_logger(
            f"engines.{engine.engine_name}.status_manager", 
            'engine'
        )
    
    def mark_job_completed(
        self, 
        job_data: Dict[str, Any], 
        result: Dict[str, Any]
    ) -> None:
        """
        Mark job as completed in the orchestrator.
        
        Args:
            job_data: Original job data
            result: Processing result data
        """
        try:
            job_id = job_data['job_id']
            job_orchestrator.complete_job(job_id, result)
            
            self.logger.debug(f"Job {job_id} marked as completed")
            
        except Exception as e:
            self.logger.error(
                f"Failed to mark job {job_data.get('job_id')} as completed: {e}"
            )
    
    def mark_job_failed(
        self, 
        job_data: Dict[str, Any], 
        error_message: str
    ) -> None:
        """
        Mark job as failed in the orchestrator.
        
        Args:
            job_data: Original job data
            error_message: Error description
        """
        try:
            job_id = job_data['job_id']
            job_orchestrator.fail_job(job_id, error_message)
            
            self.logger.debug(f"Job {job_id} marked as failed: {error_message}")
            
        except Exception as e:
            self.logger.error(
                f"Failed to mark job {job_data.get('job_id')} as failed: {e}"
            )