"""
Bottleneck Detector
==================

File: tools/monitoring/bottleneck_detector.py

Identifies performance bottlenecks in the system.
"""

from typing import Dict, Any, List

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from shared.constants.job_constants import JobType, JobStatus

from .performance_config import PerformanceConfig
from .job_metrics_calculator import JobMetricsCalculator

logger = get_logger(__name__, 'monitoring')


class BottleneckDetector:
    """
    Detect performance bottlenecks.
    
    Responsibilities:
    - Check for queue bottlenecks
    - Identify slow processing
    - Categorize bottleneck severity
    """
    
    def __init__(self, config: PerformanceConfig):
        """
        Initialize bottleneck detector.
        
        Args:
            config: Performance configuration
        """
        self.config = config
        self.metrics_calculator = JobMetricsCalculator(config)
        self.logger = get_logger(__name__, 'monitoring')
    
    async def detect(self) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks in the system.
        
        Returns:
            List of bottleneck dictionaries
        """
        bottlenecks = []
        
        try:
            # Check for queue bottlenecks
            queue_bottlenecks = await self._detect_queue_bottlenecks()
            bottlenecks.extend(queue_bottlenecks)
            
            # Check for slow processing bottlenecks
            slow_bottlenecks = await self._detect_slow_processing()
            bottlenecks.extend(slow_bottlenecks)
            
            return bottlenecks
            
        except Exception as e:
            self.logger.error(f"Failed to identify bottlenecks: {e}")
            return []
    
    async def _detect_queue_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Detect queue bottlenecks.
        
        Returns:
            List of queue bottleneck issues
        """
        bottlenecks = []
        
        with db_coordinator.get_session('core') as session:
            for job_type in JobType:
                queued_count = self._get_queued_count(session, job_type)
                
                if queued_count > self.config.bottleneck_queue_threshold:
                    bottlenecks.append(
                        self._create_queue_bottleneck(job_type, queued_count)
                    )
        
        return bottlenecks
    
    def _get_queued_count(self, session, job_type: JobType) -> int:
        """
        Get count of queued jobs for job type.
        
        Args:
            session: Database session
            job_type: Type of job
            
        Returns:
            Count of queued jobs
        """
        result = session.execute(
            """
            SELECT COUNT(*) FROM processing_jobs 
            WHERE job_type = :job_type AND job_status = :status
            """,
            {'job_type': job_type.value, 'status': JobStatus.QUEUED.value}
        ).fetchone()
        
        return result[0] if result else 0
    
    def _create_queue_bottleneck(
        self,
        job_type: JobType,
        queued_count: int
    ) -> Dict[str, Any]:
        """
        Create queue bottleneck dictionary.
        
        Args:
            job_type: Type of job
            queued_count: Number of queued jobs
            
        Returns:
            Bottleneck dictionary
        """
        severity = self._determine_queue_severity(queued_count)
        
        return {
            'type': 'queue_bottleneck',
            'job_type': job_type.value,
            'severity': severity,
            'queued_jobs': queued_count,
            'description': (
                f"Large queue for {job_type.value}: {queued_count} jobs"
            )
        }
    
    def _determine_queue_severity(self, queued_count: int) -> str:
        """
        Determine severity of queue bottleneck.
        
        Args:
            queued_count: Number of queued jobs
            
        Returns:
            Severity level ('high' or 'medium')
        """
        threshold = self.config.bottleneck_queue_threshold
        return 'high' if queued_count > threshold * 2 else 'medium'
    
    async def _detect_slow_processing(self) -> List[Dict[str, Any]]:
        """
        Detect slow processing bottlenecks.
        
        Returns:
            List of slow processing issues
        """
        bottlenecks = []
        
        for job_type in JobType:
            type_metrics = await self.metrics_calculator.get_job_type_metrics(
                job_type
            )
            
            avg_time = type_metrics.get('average_time')
            if avg_time and avg_time > self.config.slow_job_threshold_seconds:
                bottlenecks.append(
                    self._create_slow_processing_bottleneck(job_type, avg_time)
                )
        
        return bottlenecks
    
    def _create_slow_processing_bottleneck(
        self,
        job_type: JobType,
        avg_time: float
    ) -> Dict[str, Any]:
        """
        Create slow processing bottleneck dictionary.
        
        Args:
            job_type: Type of job
            avg_time: Average processing time
            
        Returns:
            Bottleneck dictionary
        """
        severity = self._determine_processing_severity(avg_time)
        
        return {
            'type': 'slow_processing',
            'job_type': job_type.value,
            'severity': severity,
            'average_time': avg_time,
            'description': (
                f"Slow processing for {job_type.value}: {avg_time}s average"
            )
        }
    
    def _determine_processing_severity(self, avg_time: float) -> str:
        """
        Determine severity of slow processing.
        
        Args:
            avg_time: Average processing time
            
        Returns:
            Severity level ('high' or 'medium')
        """
        threshold = self.config.slow_job_threshold_seconds
        return 'high' if avg_time > threshold * 2 else 'medium'