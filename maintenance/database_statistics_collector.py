"""
Map Pro Database Statistics Collector
======================================

Collects database cleanup statistics.

Save location: tools/maintenance/database_statistics_collector.py
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from core.system_logger import get_logger
from .cleanup_statistics_config import CleanupStatisticsConfig

logger = get_logger(__name__, 'maintenance')


class DatabaseStatisticsCollector:
    """
    Collects database cleanup statistics.
    
    Responsibilities:
    - Count old jobs eligible for cleanup
    - Count failed jobs
    - Provide job statistics by status
    """
    
    def __init__(self, db_coordinator) -> None:
        """
        Initialize database statistics collector.
        
        Args:
            db_coordinator: Database coordinator instance
        """
        self.db_coordinator = db_coordinator
        self.logger = logger
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database cleanup statistics.
        
        Returns:
            Dictionary with database statistics
        """
        stats = self._initialize_stats()
        
        try:
            old_cutoff = self._calculate_old_jobs_cutoff()
            failed_cutoff = self._calculate_failed_jobs_cutoff()
            
            with self.db_coordinator.get_connection('core') as conn:
                with conn.cursor() as cursor:
                    stats['old_jobs_count'] = self._count_old_jobs(
                        cursor=cursor,
                        cutoff=old_cutoff
                    )
                    
                    stats['failed_jobs_count'] = self._count_failed_jobs(
                        cursor=cursor,
                        cutoff=failed_cutoff
                    )
                    
                    stats['total_jobs_count'] = self._count_total_jobs(cursor)
                    
                    # Get counts by status
                    status_counts = self._get_status_counts(cursor)
                    stats.update(status_counts)
        
        except Exception as e:
            self.logger.warning(f"Could not get database statistics: {e}")
        
        return stats
    
    def _initialize_stats(self) -> Dict[str, Any]:
        """
        Initialize statistics structure.
        
        Returns:
            Dictionary with default values
        """
        return {
            'old_jobs_count': 0,
            'failed_jobs_count': 0,
            'total_jobs_count': 0,
            'completed_jobs_count': 0,
            'running_jobs_count': 0
        }
    
    def _calculate_old_jobs_cutoff(self) -> datetime:
        """
        Calculate cutoff date for old jobs.
        
        Returns:
            Cutoff datetime for old jobs
        """
        return datetime.now(timezone.utc) - timedelta(
            days=CleanupStatisticsConfig.OLD_JOBS_RETENTION_DAYS
        )
    
    def _calculate_failed_jobs_cutoff(self) -> datetime:
        """
        Calculate cutoff date for failed jobs.
        
        Returns:
            Cutoff datetime for failed jobs
        """
        return datetime.now(timezone.utc) - timedelta(
            days=CleanupStatisticsConfig.FAILED_JOBS_RETENTION_DAYS
        )
    
    def _count_old_jobs(self, cursor, cutoff: datetime) -> int:
        """
        Count old completed jobs.
        
        Args:
            cursor: Database cursor
            cutoff: Cutoff datetime
            
        Returns:
            Number of old completed jobs
        """
        cursor.execute(
            """
            SELECT COUNT(*) FROM jobs 
            WHERE status = 'completed' AND updated_at < %s
            """,
            (cutoff,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def _count_failed_jobs(self, cursor, cutoff: datetime) -> int:
        """
        Count old failed jobs.
        
        Args:
            cursor: Database cursor
            cutoff: Cutoff datetime
            
        Returns:
            Number of old failed jobs
        """
        cursor.execute(
            """
            SELECT COUNT(*) FROM jobs 
            WHERE status IN ('failed', 'error') AND updated_at < %s
            """,
            (cutoff,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def _count_total_jobs(self, cursor) -> int:
        """
        Count total jobs.
        
        Args:
            cursor: Database cursor
            
        Returns:
            Total number of jobs
        """
        cursor.execute("SELECT COUNT(*) FROM jobs")
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def _get_status_counts(self, cursor) -> Dict[str, int]:
        """
        Get job counts by status.
        
        Args:
            cursor: Database cursor
            
        Returns:
            Dictionary with counts for each status
        """
        cursor.execute(
            """
            SELECT status, COUNT(*) 
            FROM jobs 
            GROUP BY status
            """
        )
        
        status_counts = {}
        for status, count in cursor.fetchall():
            status_counts[f'{status}_jobs_count'] = count
        
        return status_counts


__all__ = ['DatabaseStatisticsCollector']