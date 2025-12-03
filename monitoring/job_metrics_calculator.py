"""
Job Metrics Calculator
=====================

File: tools/monitoring/job_metrics_calculator.py

Calculates detailed metrics for job types.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from statistics import mean, median

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from shared.constants.job_constants import JobType, JobStatus

from .performance_config import PerformanceConfig

logger = get_logger(__name__, 'monitoring')


class JobMetricsCalculator:
    """
    Calculate job performance metrics.
    
    Responsibilities:
    - Query job data from database
    - Calculate processing time statistics
    - Calculate failure rates
    - Compute percentiles
    """
    
    def __init__(self, config: PerformanceConfig):
        """
        Initialize metrics calculator.
        
        Args:
            config: Performance configuration
        """
        self.config = config
        self.logger = get_logger(__name__, 'monitoring')
    
    async def get_job_type_metrics(self, job_type: JobType) -> Dict[str, Any]:
        """
        Get performance metrics for a specific job type.
        
        Args:
            job_type: Type of job to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            cutoff_time = self._get_cutoff_time()
            
            with db_coordinator.get_session('core') as session:
                # Get completed jobs
                jobs = self._query_completed_jobs(session, job_type, cutoff_time)
                
                if not jobs:
                    return self._empty_metrics()
                
                # Calculate time metrics
                processing_times, queue_times = self._extract_times(jobs)
                
                # Calculate statistics
                metrics = self._calculate_metrics(processing_times, queue_times, jobs)
                
                # Add failure rate
                metrics['failure_rate'] = await self._calculate_failure_rate(
                    session,
                    job_type,
                    cutoff_time,
                    len(jobs)
                )
                
                return metrics
                
        except Exception as e:
            self.logger.error(
                f"Failed to get performance for {job_type.value}: {e}"
            )
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
    
    def _query_completed_jobs(
        self,
        session,
        job_type: JobType,
        cutoff_time: datetime
    ) -> List:
        """
        Query completed jobs from database.
        
        Args:
            session: Database session
            job_type: Type of job
            cutoff_time: Earliest time to include
            
        Returns:
            List of job records
        """
        result = session.execute(
            """
            SELECT 
                job_id,
                created_at,
                started_at,
                completed_at,
                retry_count
            FROM processing_jobs 
            WHERE job_type = :job_type 
            AND job_status = :status
            AND completed_at >= :cutoff_time
            ORDER BY completed_at DESC
            """,
            {
                'job_type': job_type.value,
                'status': JobStatus.COMPLETED.value,
                'cutoff_time': cutoff_time
            }
        ).fetchall()
        
        return result
    
    def _extract_times(self, jobs: List) -> tuple:
        """
        Extract processing and queue times from job records.
        
        Args:
            jobs: List of job records
            
        Returns:
            Tuple of (processing_times, queue_times)
        """
        processing_times = []
        queue_times = []
        
        for row in jobs:
            job_id, created_at, started_at, completed_at, retry_count = row
            
            if started_at and completed_at:
                # Ensure timezone awareness
                started_at = self._ensure_timezone(started_at)
                completed_at = self._ensure_timezone(completed_at)
                
                processing_time = (completed_at - started_at).total_seconds()
                processing_times.append(processing_time)
                
                if created_at:
                    created_at = self._ensure_timezone(created_at)
                    queue_time = (started_at - created_at).total_seconds()
                    queue_times.append(queue_time)
        
        return processing_times, queue_times
    
    def _ensure_timezone(self, dt: datetime) -> datetime:
        """
        Ensure datetime has timezone information.
        
        Args:
            dt: Datetime to check
            
        Returns:
            Timezone-aware datetime
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def _calculate_metrics(
        self,
        processing_times: List[float],
        queue_times: List[float],
        jobs: List
    ) -> Dict[str, Any]:
        """
        Calculate statistical metrics from times.
        
        Args:
            processing_times: List of processing times
            queue_times: List of queue times
            jobs: Original job records
            
        Returns:
            Dictionary of metrics
        """
        return {
            'jobs_completed': len(jobs),
            'average_time': (
                round(mean(processing_times), 2) if processing_times else None
            ),
            'median_time': (
                round(median(processing_times), 2) if processing_times else None
            ),
            'p95_time': (
                round(self._calculate_percentile(processing_times, 95), 2)
                if processing_times else None
            ),
            'p99_time': (
                round(self._calculate_percentile(processing_times, 99), 2)
                if processing_times else None
            ),
            'min_time': (
                round(min(processing_times), 2) if processing_times else None
            ),
            'max_time': (
                round(max(processing_times), 2) if processing_times else None
            ),
            'average_queue_time': (
                round(mean(queue_times), 2) if queue_times else None
            )
        }
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """
        Calculate percentile from list of values.
        
        Args:
            values: List of numeric values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]
    
    async def _calculate_failure_rate(
        self,
        session,
        job_type: JobType,
        cutoff_time: datetime,
        completed_count: int
    ) -> float:
        """
        Calculate failure rate for job type.
        
        Args:
            session: Database session
            job_type: Type of job
            cutoff_time: Earliest time to include
            completed_count: Number of completed jobs
            
        Returns:
            Failure rate (0.0 to 1.0)
        """
        failure_result = session.execute(
            """
            SELECT COUNT(*) FROM processing_jobs 
            WHERE job_type = :job_type 
            AND job_status = :status
            AND updated_at >= :cutoff_time
            """,
            {
                'job_type': job_type.value,
                'status': JobStatus.FAILED.value,
                'cutoff_time': cutoff_time
            }
        ).fetchone()
        
        failed_count = failure_result[0] if failure_result else 0
        total_jobs = completed_count + failed_count
        
        return round(failed_count / total_jobs, 4) if total_jobs > 0 else 0.0
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """
        Get empty metrics structure.
        
        Returns:
            Dictionary with null metrics
        """
        return {
            'jobs_completed': 0,
            'average_time': None,
            'median_time': None,
            'p95_time': None,
            'p99_time': None
        }