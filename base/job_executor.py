"""
Map Pro Job Processor - Job Executor (FIXED)
=============================================

Location: engines/base/job_executor.py

CRITICAL FIX: Return format must match exactly what the original returned.
The workflow expects the raw engine result, not wrapped in additional metadata.
"""

import asyncio
import inspect
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timezone

from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import JobProcessingError

if TYPE_CHECKING:
    from .engine_base import BaseEngine


class JobExecutor:
    """
    Executes jobs using the engine's process_job method.
    
    Responsibilities:
    - Executing job processing
    - Handling both async and sync engines
    - Timing job execution
    - Error handling during execution
    
    CRITICAL: Returns the raw engine result to maintain compatibility.
    """
    
    def __init__(self, engine: 'BaseEngine', processing_timeout: int) -> None:
        """
        Initialize job executor.
        
        Args:
            engine: The engine instance
            processing_timeout: Maximum time allowed for job processing (seconds)
        """
        self.engine = engine
        self.processing_timeout = processing_timeout
        self.logger = get_logger(f"engines.{engine.engine_name}.executor", 'engine')
    
    def execute_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single job using the engine's implementation.
        
        CRITICAL FIX: Returns the raw result from engine.process_job()
        to maintain compatibility with workflow expectations.
        
        Args:
            job_data: Job information from queue
            
        Returns:
            The raw result dictionary from engine.process_job(), which may contain:
                - success: bool (optional, defaults to True if not present)
                - error: str (optional, present if failed)
                - entity_id: str (for search jobs)
                - filing_id: str (for other jobs)
                - ... other job-specific data
        """
        job_id = job_data.get('job_id')
        job_type = job_data.get('job_type')
        
        self.logger.info(f"Processing job {job_id} of type {job_type}")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Execute the job
            result = self._execute_with_proper_async_handling(job_data)
            
            # Calculate processing time for logging
            processing_time = self._calculate_processing_time(start_time)
            
            # Log completion
            if result and result.get('success', True):
                self.logger.info(
                    f"Job {job_id} completed in {processing_time:.2f}s"
                )
            else:
                error_msg = self._extract_error_message(result)
                self.logger.warning(
                    f"Job {job_id} returned failure in {processing_time:.2f}s: {error_msg}"
                )
            
            # CRITICAL: Return the raw result, not wrapped
            # The workflow expects engine.process_job() format directly
            return result if result else {'success': False, 'error': 'No result returned'}
                
        except Exception as e:
            self.logger.error(f"Job {job_id} processing failed: {e}")
            processing_time = self._calculate_processing_time(start_time)
            
            # Return error in the expected format
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_with_proper_async_handling(
        self, 
        job_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute job with proper async/sync handling.
        
        Args:
            job_data: Job information from queue
            
        Returns:
            Result from engine's process_job method
        """
        if inspect.iscoroutinefunction(self.engine.process_job):
            return self._execute_async_job(job_data)
        else:
            return self._execute_sync_job(job_data)
    
    def _execute_async_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute async job with proper event loop handling.
        
        Args:
            job_data: Job information from queue
            
        Returns:
            Result from engine's async process_job method
        """
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.engine.process_job(job_data))
            return result
        except RuntimeError:
            # No event loop exists, create one
            result = asyncio.run(self.engine.process_job(job_data))
            return result
    
    def _execute_sync_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute sync job directly.
        
        Args:
            job_data: Job information from queue
            
        Returns:
            Result from engine's sync process_job method
        """
        return self.engine.process_job(job_data)
    
    def _calculate_processing_time(self, start_time: datetime) -> float:
        """
        Calculate time elapsed since start time.
        
        Args:
            start_time: When processing started
            
        Returns:
            Time elapsed in seconds
        """
        return (datetime.now(timezone.utc) - start_time).total_seconds()
    
    def _extract_error_message(self, result: Optional[Dict[str, Any]]) -> str:
        """
        Extract error message from result.
        
        Args:
            result: Result dictionary from job processing
            
        Returns:
            Error message string
        """
        if result:
            return result.get('error', 'Job processing returned failure')
        else:
            return 'No result returned'