# File: /map_pro/core/workflow_status_tracker.py

"""
Workflow Status Tracker
=======================

Tracks and manages workflow execution status across all stages.
Provides status updates and completion tracking.

100% market-agnostic status tracking.
"""

from typing import Dict, Any, List
import time

from .system_logger import get_logger
from .interactive_interface import (
    display_workflow_progress,
    display_entity_found,
    display_filings_found,
    display_stage_separator
)

logger = get_logger(__name__, 'core')

# Stage status constants
STATUS_PENDING = 'pending'
STATUS_RUNNING = 'running'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'


class WorkflowStatusTracker:
    """
    Tracks workflow execution status.
    
    Responsibilities:
    - Track stage completion status
    - Manage workflow state
    - Display progress updates
    - Track timing information
    
    100% market-agnostic implementation.
    """
    
    def __init__(self):
        """Initialize workflow status tracker."""
        self.workflow_status = {
            'search': STATUS_PENDING,
            'download': STATUS_PENDING,
            'extract': STATUS_PENDING,
            'parse': STATUS_PENDING,
            'map': STATUS_PENDING
        }
        
        self.stages_completed = []
        self.start_time = None
        
        logger.debug("Workflow status tracker initialized")
    
    def start_workflow(self) -> None:
        """Mark workflow as started and record start time."""
        self.start_time = time.time()
        logger.debug("Workflow timing started")
    
    def get_status(self) -> Dict[str, str]:
        """
        Get current workflow status.
        
        Returns:
            Dictionary with stage statuses
        """
        return self.workflow_status.copy()
    
    def get_stages_completed(self) -> List[str]:
        """
        Get list of completed stages.
        
        Returns:
            List of completed stage names
        """
        return self.stages_completed.copy()
    
    def get_duration(self) -> float:
        """
        Get workflow duration in seconds.
        
        Returns:
            Duration in seconds, or 0 if not started
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    def mark_stage_running(self, stage: str) -> None:
        """
        Mark a stage as running.
        
        Args:
            stage: Stage name to mark as running
        """
        if stage in self.workflow_status:
            self.workflow_status[stage] = STATUS_RUNNING
            logger.info(f"Stage '{stage}' marked as running")
            self._display_progress()
    
    def mark_stage_completed(self, stage: str) -> None:
        """
        Mark a stage as completed.
        
        Args:
            stage: Stage name to mark as completed
        """
        if stage in self.workflow_status:
            self.workflow_status[stage] = STATUS_COMPLETED
            
            if stage not in self.stages_completed:
                self.stages_completed.append(stage)
            
            logger.info(f"Stage '{stage}' marked as completed")
            self._display_progress()
    
    def mark_stage_failed(self, stage: str) -> None:
        """
        Mark a stage as failed.
        
        Args:
            stage: Stage name to mark as failed
        """
        if stage in self.workflow_status:
            self.workflow_status[stage] = STATUS_FAILED
            logger.warning(f"Stage '{stage}' marked as failed")
            self._display_progress()
    
    def mark_processing_stages_completed(
        self,
        results: List[Dict[str, Any]]
    ) -> None:
        """
        Mark processing stages as completed if any filing succeeded.
        
        Args:
            results: List of filing processing results
        """
        if any(r.get('success') for r in results):
            processing_stages = ['download', 'extract', 'parse', 'map']
            
            for stage in processing_stages:
                if stage not in self.stages_completed:
                    self.mark_stage_completed(stage)
            
            logger.info(f"All processing stages completed: {self.stages_completed}")
    
    def _display_progress(self) -> None:
        """Display current workflow progress."""
        try:
            display_workflow_progress(self.workflow_status)
        except Exception as e:
            logger.warning(f"Failed to display progress: {e}")
    
    def display_entity_info(self, entity_info: Dict[str, Any]) -> None:
        """
        Display entity information.
        
        Args:
            entity_info: Entity information dictionary
        """
        try:
            display_entity_found(entity_info)
            display_stage_separator()
        except Exception as e:
            logger.warning(f"Failed to display entity info: {e}")
    
    def display_filings_info(self, filing_count: int, filing_type: str) -> None:
        """
        Display filings found information.
        
        Args:
            filing_count: Number of filings found
            filing_type: Type of filings
        """
        try:
            display_filings_found(filing_count, filing_type)
            display_stage_separator()
        except Exception as e:
            logger.warning(f"Failed to display filings info: {e}")


__all__ = ['WorkflowStatusTracker']