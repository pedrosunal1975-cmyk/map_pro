"""
Map Pro Queue Metrics Collector
================================

Collects job queue metrics across all engines.

Save location: tools/monitoring/queue_metrics_collector.py
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger
from shared.constants.job_constants import JobType, JobStatus

logger = get_logger(__name__, 'monitoring')


class QueueMetricsCollector:
    """
    Collects job queue metrics.
    
    Responsibilities:
    - Collect overall queue status
    - Collect metrics by job type
    - Calculate queue health indicators
    """
    
    def __init__(
        self,
        db_coordinator,
        job_orchestrator
    ) -> None:
        """
        Initialize queue metrics collector.
        
        Args:
            db_coordinator: Database coordinator instance
            job_orchestrator: Job orchestrator instance
        """
        self.db_coordinator = db_coordinator
        self.job_orchestrator = job_orchestrator
    
    async def collect(self) -> Dict[str, Any]:
        """
        Collect job queue metrics.
        
        Returns:
            Dictionary with queue metrics
        """
        try:
            queue_status = self.job_orchestrator.get_queue_status()
            
            queue_metrics = {
                'overall': queue_status,
                'by_job_type': await self._collect_by_job_type(),
                'health_indicators': await self._collect_health_indicators(
                    queue_status=queue_status
                )
            }
            
            return queue_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect queue metrics: {e}")
            return {'error': str(e)}
    
    async def _collect_by_job_type(self) -> Dict[str, Any]:
        """
        Collect metrics for each job type.
        
        Returns:
            Dictionary with metrics per job type
        """
        by_job_type = {}
        
        for job_type in JobType:
            type_metrics = await self._get_job_type_metrics(job_type)
            by_job_type[job_type.value] = type_metrics
        
        return by_job_type
    
    async def _get_job_type_metrics(
        self,
        job_type: JobType
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific job type.
        
        Args:
            job_type: Job type to get metrics for
            
        Returns:
            Dictionary with metrics for the job type
        """
        try:
            with self.db_coordinator.get_session('core') as session:
                status_counts = {}
                
                for status in JobStatus:
                    result = session.execute(
                        """
                        SELECT COUNT(*) FROM processing_jobs 
                        WHERE job_type = :job_type AND job_status = :status
                        """,
                        {'job_type': job_type.value, 'status': status.value}
                    ).fetchone()
                    status_counts[status.value] = result[0] if result else 0
                
                active_count = (
                    status_counts.get(JobStatus.QUEUED.value, 0) +
                    status_counts.get(JobStatus.RUNNING.value, 0)
                )
                
                return {
                    'status_counts': status_counts,
                    'total': sum(status_counts.values()),
                    'active': active_count
                }
                
        except Exception as e:
            logger.error(f"Failed to get metrics for {job_type.value}: {e}")
            return {'error': str(e)}
    
    async def _collect_health_indicators(
        self,
        queue_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate queue health indicators.
        
        Args:
            queue_status: Overall queue status
            
        Returns:
            Dictionary with health indicators
        """
        return {
            'queue_depth': queue_status.get('active_jobs', 0),
            'oldest_job_age_seconds': await self._get_oldest_job_age(),
            'processing_rate': await self._calculate_processing_rate()
        }
    
    async def _get_oldest_job_age(self) -> Optional[float]:
        """
        Get age of oldest queued job in seconds.
        
        Returns:
            Age in seconds, or None if no queued jobs
        """
        try:
            with self.db_coordinator.get_session('core') as session:
                result = session.execute(
                    """
                    SELECT MIN(created_at) FROM processing_jobs 
                    WHERE job_status = :status
                    """,
                    {'status': JobStatus.QUEUED.value}
                ).fetchone()
                
                if result and result[0]:
                    oldest_time = result[0]
                    if oldest_time.tzinfo is None:
                        oldest_time = oldest_time.replace(tzinfo=timezone.utc)
                    age_seconds = (
                        datetime.now(timezone.utc) - oldest_time
                    ).total_seconds()
                    return round(age_seconds, 2)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get oldest job age: {e}")
            return None
    
    async def _calculate_processing_rate(self) -> Optional[float]:
        """
        Calculate recent job processing rate (jobs per minute).
        
        Returns:
            Processing rate in jobs per minute, or None on error
        """
        try:
            with self.db_coordinator.get_session('core') as session:
                result = session.execute(
                    """
                    SELECT COUNT(*) FROM processing_jobs 
                    WHERE job_status = :status 
                    AND completed_at >= NOW() - INTERVAL '5 minutes'
                    """,
                    {'status': JobStatus.COMPLETED.value}
                ).fetchone()
                
                completed_count = result[0] if result else 0
                # Divide by 5 minutes to get per-minute rate
                return round(completed_count / 5.0, 2)
                
        except Exception as e:
            logger.error(f"Failed to calculate processing rate: {e}")
            return None