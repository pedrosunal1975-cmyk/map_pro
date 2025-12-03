"""
Map Pro Performance Metrics Collector
=====================================

Collects detailed performance metrics from all system components.
Handles the actual data gathering without coordination logic.

Architecture: Specialized component focused solely on metrics collection.
"""

import time
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

from .system_logger import get_logger
from .database_coordinator import get_database_session, check_database_health
from shared.constants.job_constants import JobType, JobStatus

logger = get_logger(__name__, 'core')


class MetricsCollector:
    """
    Specialized component for collecting performance metrics from all system components.
    
    Responsibilities:
    - Database performance metrics collection
    - Job queue metrics collection
    - Job processing performance metrics
    - System resource metrics collection
    
    Does NOT handle:
    - Metrics storage (performance_monitor handles this)
    - Alert generation (alert_manager handles this)
    - Monitoring coordination (performance_monitor handles this)
    """
    
    def __init__(self):
        logger.info("Performance metrics collector initializing")
    
    def collect_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Collect all system performance metrics.
        
        Returns:
            Dictionary with metrics organized by category
        """
        all_metrics = {}
        
        try:
            all_metrics['database'] = self.collect_database_metrics()
            all_metrics['queue'] = self.collect_queue_metrics()
            all_metrics['processing'] = self.collect_processing_metrics()
            
        except Exception as e:
            logger.error(f"Failed to collect all metrics: {e}")
            all_metrics['error'] = {'collection_error': str(e)}
            
        return all_metrics
    
    def collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database performance metrics."""
        metrics = {}
        
        try:
            start_time = time.time()
            health_status = check_database_health()
            response_time = time.time() - start_time
            
            metrics['response_time'] = response_time
            metrics['health_status'] = health_status
            metrics['databases_healthy'] = all(
                db.get('status') == 'healthy' 
                for db in health_status.get('databases', {}).values()
            )
            
            # Count database connections if available
            metrics['coordinator_initialized'] = health_status.get('coordinator_initialized', False)
            
        except Exception as e:
            metrics['error'] = str(e)
            metrics['databases_healthy'] = False
            
        return metrics
    
    def collect_queue_metrics(self) -> Dict[str, Any]:
        """Collect job queue performance metrics."""
        metrics = {}
        
        try:
            with get_database_session('core') as session:
                # Count jobs by status
                for status in JobStatus:
                    result = session.execute(
                        "SELECT COUNT(*) FROM processing_jobs WHERE job_status = :status",
                        {'status': status.value}
                    ).fetchone()
                    metrics[f"jobs_{status.value}"] = result[0] if result else 0
                
                # Calculate derived metrics
                metrics['total_jobs'] = sum(
                    v for k, v in metrics.items() 
                    if k.startswith('jobs_') and isinstance(v, int)
                )
                metrics['active_jobs'] = metrics.get('jobs_running', 0) + metrics.get('jobs_queued', 0)
                
                # Get oldest queued job age
                oldest_queued = session.execute(
                    """
                    SELECT MIN(created_at) FROM processing_jobs 
                    WHERE job_status = 'queued'
                    """
                ).fetchone()
                
                if oldest_queued and oldest_queued[0]:
                    age_seconds = (datetime.now(timezone.utc) - oldest_queued[0]).total_seconds()
                    metrics['oldest_queued_job_age'] = age_seconds
                else:
                    metrics['oldest_queued_job_age'] = 0
                
                # Get average queue wait time
                avg_wait_time = session.execute(
                    """
                    SELECT AVG(EXTRACT(EPOCH FROM (started_at - created_at)))
                    FROM processing_jobs 
                    WHERE started_at IS NOT NULL 
                    AND created_at >= :yesterday
                    """,
                    {'yesterday': datetime.now(timezone.utc) - timedelta(hours=24)}
                ).fetchone()
                
                if avg_wait_time and avg_wait_time[0]:
                    metrics['avg_queue_wait_time'] = float(avg_wait_time[0])
                else:
                    metrics['avg_queue_wait_time'] = 0
                    
        except Exception as e:
            metrics['error'] = str(e)
            
        return metrics
    
    def collect_processing_metrics(self) -> Dict[str, Any]:
        """Collect job processing performance metrics."""
        metrics = {}
        
        try:
            with get_database_session('core') as session:
                yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
                
                # Calculate success rate for last 24 hours
                total_completed = session.execute(
                    """
                    SELECT COUNT(*) FROM processing_jobs 
                    WHERE completed_at >= :yesterday 
                    AND job_status IN ('completed', 'failed')
                    """,
                    {'yesterday': yesterday}
                ).fetchone()
                
                successful_completed = session.execute(
                    """
                    SELECT COUNT(*) FROM processing_jobs 
                    WHERE completed_at >= :yesterday 
                    AND job_status = 'completed'
                    """,
                    {'yesterday': yesterday}
                ).fetchone()
                
                total_count = total_completed[0] if total_completed else 0
                success_count = successful_completed[0] if successful_completed else 0
                
                if total_count > 0:
                    metrics['success_rate_24h'] = success_count / total_count
                else:
                    metrics['success_rate_24h'] = 1.0  # No jobs means no failures
                
                metrics['total_jobs_24h'] = total_count
                metrics['successful_jobs_24h'] = success_count
                metrics['failed_jobs_24h'] = total_count - success_count
                
                # Calculate average processing time by job type
                for job_type in JobType:
                    avg_time = session.execute(
                        """
                        SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
                        FROM processing_jobs 
                        WHERE job_type = :job_type 
                        AND job_status = 'completed'
                        AND completed_at >= :yesterday
                        AND started_at IS NOT NULL
                        """,
                        {'job_type': job_type.value, 'yesterday': yesterday}
                    ).fetchone()
                    
                    if avg_time and avg_time[0]:
                        metrics[f'avg_processing_time_{job_type.value}'] = float(avg_time[0])
                
                # Calculate retry statistics
                retry_stats = session.execute(
                    """
                    SELECT 
                        COUNT(*) as total_retries,
                        AVG(retry_count) as avg_retry_count,
                        MAX(retry_count) as max_retry_count
                    FROM processing_jobs 
                    WHERE retry_count > 0 
                    AND updated_at >= :yesterday
                    """,
                    {'yesterday': yesterday}
                ).fetchone()
                
                if retry_stats:
                    metrics['total_retries_24h'] = retry_stats[0] or 0
                    metrics['avg_retry_count_24h'] = float(retry_stats[1]) if retry_stats[1] else 0
                    metrics['max_retry_count_24h'] = retry_stats[2] or 0
                else:
                    metrics['total_retries_24h'] = 0
                    metrics['avg_retry_count_24h'] = 0
                    metrics['max_retry_count_24h'] = 0
                    
        except Exception as e:
            metrics['error'] = str(e)
            
        return metrics
    
    def collect_engine_specific_metrics(self, engine_name: str) -> Dict[str, Any]:
        """
        Collect metrics specific to a particular engine.
        
        Args:
            engine_name: Name of the engine to collect metrics for
            
        Returns:
            Engine-specific metrics
        """
        metrics = {}
        
        try:
            with get_database_session('core') as session:
                yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
                
                # Get job types typically handled by this engine
                engine_job_types = self._get_engine_job_types(engine_name)
                
                for job_type in engine_job_types:
                    # Count jobs by status for this engine's job types
                    for status in JobStatus:
                        result = session.execute(
                            """
                            SELECT COUNT(*) FROM processing_jobs 
                            WHERE job_type = :job_type 
                            AND job_status = :status
                            AND updated_at >= :yesterday
                            """,
                            {
                                'job_type': job_type.value,
                                'status': status.value,
                                'yesterday': yesterday
                            }
                        ).fetchone()
                        
                        metrics[f"{job_type.value}_{status.value}_24h"] = result[0] if result else 0
                        
        except Exception as e:
            metrics['error'] = str(e)
            
        return metrics
    
    def _get_engine_job_types(self, engine_name: str) -> list:
        """Get job types typically handled by specific engine."""
        engine_job_mapping = {
            'searcher': [JobType.SEARCH_ENTITY, JobType.FIND_FILINGS],
            'downloader': [JobType.DOWNLOAD_FILING],
            'extractor': [JobType.EXTRACT_FILES],
            'parser': [JobType.PARSE_XBRL],
            'mapper': [JobType.MAP_FACTS],
            'librarian': []  # Librarian doesn't process standard workflow jobs
        }
        
        return engine_job_mapping.get(engine_name, [])