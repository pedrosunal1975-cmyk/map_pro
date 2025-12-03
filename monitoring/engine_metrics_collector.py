"""
Map Pro Engine Metrics Collector
=================================

Collects engine-specific metrics.

Save location: tools/monitoring/engine_metrics_collector.py
"""

from typing import Dict, Any

from core.system_logger import get_logger
from shared.constants.job_constants import JobType
from .monitoring_constants import ENGINE_JOB_TYPE_MAPPING

logger = get_logger(__name__, 'monitoring')


class EngineMetricsCollector:
    """
    Collects engine-specific metrics.
    
    Responsibilities:
    - Collect metrics for each engine
    - Map engines to their job types
    - Calculate queue depth per engine
    """
    
    def __init__(self, db_coordinator) -> None:
        """
        Initialize engine metrics collector.
        
        Args:
            db_coordinator: Database coordinator instance
        """
        self.db_coordinator = db_coordinator
    
    async def collect(self) -> Dict[str, Any]:
        """
        Collect engine-specific metrics.
        
        Returns:
            Dictionary with metrics for each engine
        """
        try:
            engine_metrics = {}
            
            for engine_name, job_types in ENGINE_JOB_TYPE_MAPPING.items():
                engine_metrics[engine_name] = await self._collect_engine_metrics(
                    engine_name=engine_name,
                    job_types=job_types
                )
            
            return engine_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect engine metrics: {e}")
            return {'error': str(e)}
    
    async def _collect_engine_metrics(
        self,
        engine_name: str,
        job_types: list
    ) -> Dict[str, Any]:
        """
        Collect metrics for a specific engine.
        
        Args:
            engine_name: Name of the engine
            job_types: List of job types handled by this engine
            
        Returns:
            Dictionary with engine metrics
        """
        queue_depth = await self._calculate_queue_depth(job_types)
        
        return {
            'status': 'active',
            'job_types': [jt.value for jt in job_types],
            'queue_depth': queue_depth
        }
    
    async def _calculate_queue_depth(
        self,
        job_types: list
    ) -> int:
        """
        Calculate total queue depth for given job types.
        
        Args:
            job_types: List of job types to calculate depth for
            
        Returns:
            Total queue depth
        """
        total_depth = 0
        
        for job_type in job_types:
            type_metrics = await self._get_job_type_metrics(job_type)
            total_depth += type_metrics.get('active', 0)
        
        return total_depth
    
    async def _get_job_type_metrics(
        self,
        job_type: JobType
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific job type.
        
        Args:
            job_type: Job type to get metrics for
            
        Returns:
            Dictionary with job type metrics
        """
        try:
            from shared.constants.job_constants import JobStatus
            
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