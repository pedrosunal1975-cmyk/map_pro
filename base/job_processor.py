"""
Map Pro Job Processor - FINAL FIXED VERSION
============================================

Location: engines/base/job_processor.py

FIXES:
1. Return format matches original exactly (no nested results)
2. Single logger passed to all components (no duplication)
3. Maintains all original functionality

FIXED: Reduced excessive logging when no jobs are available.
- Changed "Checking for X jobs..." from INFO to DEBUG
- Changed "No X jobs available" from INFO to DEBUG  
- Only logs at INFO level when jobs are actually found
- Prevents log spam during idle periods

Refactored: Split into modular components for better maintainability
- JobProcessor: Main coordinator
- JobFetcher: Handles job retrieval
- JobExecutor: Handles job execution
- JobValidator: Validates job data
- JobStatusManager: Manages job lifecycle
- JobStatistics: Collects processing statistics
"""

from typing import Dict, Any, List, TYPE_CHECKING

from core.system_logger import get_logger
from .job_fetcher import JobFetcher
from .job_executor import JobExecutor
from .job_validator import JobValidator
from .job_status_manager import JobStatusManager
from .job_statistics import JobStatistics
from .job_processor_constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_PROCESSING_TIMEOUT,
    CLEANUP_DEFAULT_DAYS
)

if TYPE_CHECKING:
    from .engine_base import BaseEngine

logger = get_logger(__name__, 'engine')


class JobProcessor:
    """
    Handles job processing workflow for engines.
    
    Responsibilities:
    - Coordinating job processing workflow
    - Delegating to specialized components
    - Managing job lifecycle through status manager
    
    Does NOT handle:
    - Actual job processing logic (engines implement this)
    - Job creation (job_orchestrator handles this)
    - Cross-engine coordination (core handles this)
    """
    
    def __init__(self, engine: 'BaseEngine') -> None:
        """
        Initialize job processor for specific engine.
        
        Args:
            engine: The engine instance this processor belongs to
        """
        self.engine = engine
        # Create ONE logger for this processor and share it with all components
        self.logger = get_logger(f"engines.{engine.engine_name}.job_processor", 'engine')
        
        # Processing configuration
        self.batch_size = DEFAULT_BATCH_SIZE
        self.processing_timeout = DEFAULT_PROCESSING_TIMEOUT
        
        # Initialize components - pass logger to avoid duplication
        self._fetcher = JobFetcher(engine, self.batch_size, self.logger)
        self._executor = JobExecutor(engine, self.processing_timeout)
        self._validator = JobValidator(engine)
        self._status_manager = JobStatusManager(engine)
        self._statistics = JobStatistics(engine)
        
        self.logger.debug(f"Job processor initialized for {engine.engine_name}")
    
    def process_pending_jobs(self) -> int:
        """
        Process pending jobs from the queue.
        
        Returns:
            Number of jobs processed in this iteration
        """
        try:
            jobs = self._fetcher.get_available_jobs()
            
            if not jobs:
                return 0
            
            processed_count = 0
            
            for job_data in jobs:
                try:
                    if self.engine._shutdown_requested:
                        break
                    
                    if self._process_single_job(job_data):
                        processed_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to process job {job_data.get('job_id')}: {e}")
                    self._status_manager.mark_job_failed(job_data, str(e))
            
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error in process_pending_jobs: {e}")
            return 0
    
    def _process_single_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Process a single job using the engine's implementation.
        
        Args:
            job_data: Job information from queue
            
        Returns:
            True if job processed successfully, False otherwise
        """
        job_id = job_data.get('job_id')
        
        # Validate job data
        if not self._validator.validate_job_data(job_data):
            error_msg = f"Invalid job data for job {job_id}"
            self._status_manager.mark_job_failed(job_data, error_msg)
            return False
        
        # Execute job - returns raw engine result
        result = self._executor.execute_job(job_data)
        
        # Check success using same logic as original
        if result and result.get('success', True):
            self._status_manager.mark_job_completed(job_data, result)
            return True
        else:
            error_msg = result.get('error', 'Job processing returned failure') if result else 'No result returned'
            self._status_manager.mark_job_failed(job_data, error_msg)
            return False
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get job processing statistics for this engine.
        
        Returns:
            Dictionary with processing statistics
        """
        return self._statistics.collect_statistics()
    
    def cleanup_old_jobs(self, days_old: int = CLEANUP_DEFAULT_DAYS) -> int:
        """
        Clean up old completed/failed jobs to manage database size.
        
        Args:
            days_old: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        return self._statistics.cleanup_old_jobs(days_old)