"""
Map Pro Job Processor - Job Statistics
=======================================

Location: engines/base/job_statistics.py

Collects and manages job processing statistics.
"""

from typing import Dict, Any, List, TYPE_CHECKING
from sqlalchemy import text

from core.system_logger import get_logger
from shared.constants.job_constants import JobStatus
from .job_processor_constants import CLEANUP_DEFAULT_DAYS

if TYPE_CHECKING:
    from .engine_base import BaseEngine


class JobStatistics:
    """
    Collects and manages job processing statistics.
    
    Responsibilities:
    - Collecting job counts by status
    - Tracking recent activity
    - Cleaning up old jobs
    """
    
    def __init__(self, engine: 'BaseEngine') -> None:
        """
        Initialize job statistics collector.
        
        Args:
            engine: The engine instance
        """
        self.engine = engine
        self.logger = get_logger(
            f"engines.{engine.engine_name}.statistics", 
            'engine'
        )
    
    def collect_statistics(self) -> Dict[str, Any]:
        """
        Get job processing statistics for this engine.
        
        Returns:
            Dictionary with processing statistics including:
                - engine_name: Name of the engine
                - supported_job_types: List of supported job types
                - job_counts: Counts by job type and status
                - recent_activity: Activity in last 24 hours
        """
        try:
            with self.engine.get_session('core') as session:
                supported_types = self.engine.get_supported_job_types()
                
                stats = {
                    'engine_name': self.engine.engine_name,
                    'supported_job_types': supported_types,
                    'job_counts': {},
                    'recent_activity': {}
                }
                
                self._collect_job_counts(session, supported_types, stats)
                self._collect_recent_activity(session, supported_types, stats)
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get processing statistics: {e}")
            return {
                'engine_name': self.engine.engine_name,
                'error': str(e)
            }
    
    def _collect_job_counts(
        self, 
        session: Any, 
        supported_types: List[str], 
        stats: Dict[str, Any]
    ) -> None:
        """
        Collect job counts by status for each supported job type.
        
        Args:
            session: Database session
            supported_types: List of supported job types
            stats: Statistics dictionary to populate
        """
        for job_type in supported_types:
            for status in JobStatus:
                count = self._query_job_count(session, job_type, status)
                
                if job_type not in stats['job_counts']:
                    stats['job_counts'][job_type] = {}
                
                stats['job_counts'][job_type][status.value] = count
    
    def _query_job_count(
        self, 
        session: Any, 
        job_type: str, 
        status: JobStatus
    ) -> int:
        """
        Query count of jobs for a specific type and status.
        
        Args:
            session: Database session
            job_type: Job type to count
            status: Job status to count
            
        Returns:
            Count of matching jobs
        """
        count_query = text("""
            SELECT COUNT(*) FROM processing_jobs 
            WHERE job_type = :job_type AND job_status = :status
        """)
        
        result = session.execute(count_query, {
            'job_type': job_type,
            'status': status.value
        }).fetchone()
        
        return result[0] if result else 0
    
    def _collect_recent_activity(
        self, 
        session: Any, 
        supported_types: List[str], 
        stats: Dict[str, Any]
    ) -> None:
        """
        Collect recent activity (last 24 hours) for supported job types.
        
        Args:
            session: Database session
            supported_types: List of supported job types
            stats: Statistics dictionary to populate
        """
        recent_query = text("""
            SELECT job_type, job_status, COUNT(*) as count
            FROM processing_jobs 
            WHERE job_type = ANY(:job_types)
            AND updated_at >= NOW() - INTERVAL '24 hours'
            GROUP BY job_type, job_status
        """)
        
        recent_results = session.execute(recent_query, {
            'job_types': supported_types
        }).fetchall()
        
        for job_type, status, count in recent_results:
            if job_type not in stats['recent_activity']:
                stats['recent_activity'][job_type] = {}
            stats['recent_activity'][job_type][status] = count
    
    def cleanup_old_jobs(self, days_old: int = CLEANUP_DEFAULT_DAYS) -> int:
        """
        Clean up old completed/failed jobs to manage database size.
        
        Args:
            days_old: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        try:
            with self.engine.get_session('core') as session:
                delete_query = text("""
                    DELETE FROM processing_jobs
                    WHERE job_status IN ('completed', 'failed')
                    AND completed_at < NOW() - INTERVAL ':days days'
                    RETURNING job_id
                """)
                
                result = session.execute(delete_query, {'days': days_old})
                deleted_count = len(result.fetchall())
                
                self.logger.info(
                    f"Cleaned up {deleted_count} old jobs (>{days_old} days)"
                )
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old jobs: {e}")
            return 0