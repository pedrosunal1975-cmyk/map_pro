"""
Job Statistics Calculator
=========================

File: tools/monitoring/job_statistics_calculator.py

Calculates overall job processing statistics.
"""

from typing import Dict, Any
from datetime import datetime, timedelta, timezone

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from shared.constants.job_constants import JobStatus

from .performance_config import PerformanceConfig

logger = get_logger(__name__, 'monitoring')


class JobStatisticsCalculator:
    """
    Calculate overall job statistics.
    
    Responsibilities:
    - Query job counts by status
    - Calculate success/failure rates
    - Aggregate system-wide statistics
    """
    
    def __init__(self, config: PerformanceConfig):
        """
        Initialize statistics calculator.
        
        Args:
            config: Performance configuration
        """
        self.config = config
        self.logger = get_logger(__name__, 'monitoring')
    
    async def calculate(self) -> Dict[str, Any]:
        """
        Calculate overall job processing statistics.
        
        Returns:
            Dictionary with job statistics
        """
        try:
            cutoff_time = self._get_cutoff_time()
            
            with db_coordinator.get_session('core') as session:
                # Get counts by status
                status_counts = self._get_status_counts(session, cutoff_time)
                
                # Calculate rates
                stats = self._calculate_statistics(status_counts)
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to calculate job statistics: {e}")
            return {'error': str(e)}
    
    def _get_cutoff_time(self) -> datetime:
        """
        Get cutoff time for analysis window.
        
        Returns:
            Cutoff datetime
        """
        return datetime.now(timezone.utc) - timedelta(
            hours=self.config.analysis_window_hours
        )
    
    def _get_status_counts(self, session, cutoff_time: datetime) -> Dict[str, int]:
        """
        Get job counts by status.
        
        Args:
            session: Database session
            cutoff_time: Earliest time to include
            
        Returns:
            Dictionary mapping status to count
        """
        status_counts = {}
        
        for status in JobStatus:
            result = session.execute(
                """
                SELECT COUNT(*) FROM processing_jobs 
                WHERE updated_at >= :cutoff_time AND job_status = :status
                """,
                {'cutoff_time': cutoff_time, 'status': status.value}
            ).fetchone()
            
            status_counts[status.value] = result[0] if result else 0
        
        return status_counts
    
    def _calculate_statistics(self, status_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Calculate statistics from status counts.
        
        Args:
            status_counts: Dictionary of status counts
            
        Returns:
            Dictionary with calculated statistics
        """
        total_jobs = sum(status_counts.values())
        completed_jobs = status_counts.get(JobStatus.COMPLETED.value, 0)
        failed_jobs = status_counts.get(JobStatus.FAILED.value, 0)
        
        # Calculate success rate
        processed_jobs = completed_jobs + failed_jobs
        success_rate = (
            (completed_jobs / processed_jobs) if processed_jobs > 0 else 0.0
        )
        
        return {
            'total_jobs': total_jobs,
            'completed': completed_jobs,
            'failed': failed_jobs,
            'running': status_counts.get(JobStatus.RUNNING.value, 0),
            'queued': status_counts.get(JobStatus.QUEUED.value, 0),
            'success_rate': round(success_rate, 4),
            'failure_rate': round(1.0 - success_rate, 4)
        }