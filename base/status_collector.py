# File: /map_pro/engines/base/status_collector.py

"""
Map Pro Status Collector
========================

Handles detailed status data collection and performance metrics.
Specialized component for gathering comprehensive engine status information.

Architecture: Specialized component focused on status data collection.
"""

import time
from typing import Dict, Any, TYPE_CHECKING
from collections import deque
from sqlalchemy import text
from core.system_logger import get_logger
from core.performance_monitor import record_metric

if TYPE_CHECKING:
    from .engine_base import BaseEngine

logger = get_logger(__name__, 'engine')

MAX_PERFORMANCE_HISTORY = 100
RECENT_REPORTS_COUNT = 10
MILLISECONDS_PER_SECOND = 1000
SECONDS_PER_MINUTE = 60.0
BYTES_PER_MB = 1024 * 1024
MIN_REPORTS_FOR_METRICS = 2


class StatusCollector:
    """
    Handles detailed status data collection for engines.
    
    Responsibilities:
    - Comprehensive status data collection
    - Performance metrics calculation
    - Database health checking
    - Resource usage monitoring
    - Performance history tracking
    
    Does NOT handle:
    - Status reporting timing (status_reporter handles this)
    - Health monitoring logic (health_monitor handles this)
    - Report coordination (status_reporter handles this)
    """
    
    def __init__(self, engine: 'BaseEngine'):
        """
        Initialize status collector for specific engine.
        
        Args:
            engine: The engine instance this collector belongs to
        """
        self.engine = engine
        self.logger = get_logger(f"engines.{engine.engine_name}.status_collector", 'engine')
        self.performance_history = deque(maxlen=MAX_PERFORMANCE_HISTORY)
        
        self.logger.debug(f"Status collector initialized for {engine.engine_name}")
    
    def collect_comprehensive_status(self) -> Dict[str, Any]:
        """
        Collect comprehensive status information from engine.
        
        Returns:
            Dictionary with complete status information
        """
        status = self.engine.get_status()
        status['performance_metrics'] = self._collect_performance_metrics()
        
        if hasattr(self.engine, 'job_processor'):
            status['job_statistics'] = self.engine.job_processor.get_processing_statistics()
        
        status['database_health'] = self._check_database_health()
        status['resource_usage'] = self._collect_resource_usage()
        
        return status
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """
        Collect performance metrics for the engine.
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = {
            'jobs_per_minute': 0,
            'average_processing_time': 0,
            'success_rate': 1.0,
            'error_rate': 0.0
        }
        
        try:
            if len(self.performance_history) >= MIN_REPORTS_FOR_METRICS:
                recent_reports = list(self.performance_history)[-RECENT_REPORTS_COUNT:]
                
                if len(recent_reports) >= MIN_REPORTS_FOR_METRICS:
                    first_report = recent_reports[0]
                    last_report = recent_reports[-1]
                    
                    time_diff = (last_report['timestamp'] - first_report['timestamp']) / SECONDS_PER_MINUTE
                    jobs_diff = last_report['jobs_processed'] - first_report['jobs_processed']
                    
                    if time_diff > 0:
                        metrics['jobs_per_minute'] = jobs_diff / time_diff
                
                total_jobs = sum(r.get('jobs_processed', 0) for r in recent_reports)
                total_failed = sum(r.get('jobs_failed', 0) for r in recent_reports)
                
                if total_jobs > 0:
                    metrics['success_rate'] = 1.0 - (total_failed / total_jobs)
                    metrics['error_rate'] = total_failed / total_jobs
            
            return metrics
            
        except Exception as e:
            self.logger.warning(f"Failed to collect performance metrics: {e}")
            return metrics
    
    def _check_database_health(self) -> Dict[str, Any]:
        """
        Check database connectivity and health.
        
        Returns:
            Dictionary with database health information
        """
        health = {
            'primary_db_accessible': False,
            'response_time_ms': None,
            'connection_pool_status': 'unknown'
        }
        
        try:
            start_time = time.time()
            
            with self.engine.get_session() as session:
                session.execute(text("SELECT 1")) 
                
            response_time = (time.time() - start_time) * MILLISECONDS_PER_SECOND
            
            health.update({
                'primary_db_accessible': True,
                'response_time_ms': round(response_time, 2),
                'connection_pool_status': 'healthy'
            })
            
        except Exception as e:
            health['error'] = str(e)
            self.logger.warning(f"Database health check failed: {e}")
        
        return health
    
    def _collect_resource_usage(self) -> Dict[str, Any]:
        """
        Collect resource usage information.
        
        Returns:
            Dictionary with resource usage metrics
        """
        usage = {
            'thread_count': 0,
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0
        }
        
        try:
            import threading
            import psutil
            import os
            
            usage['thread_count'] = threading.active_count()
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            usage['memory_usage_mb'] = round(memory_info.rss / BYTES_PER_MB, 2)
            
            usage['cpu_usage_percent'] = round(process.cpu_percent(), 2)
            
        except ImportError:
            usage['note'] = 'psutil not available for resource monitoring'
        except Exception as e:
            usage['error'] = str(e)
        
        return usage
    
    def send_to_performance_monitor(self, status_data: Dict[str, Any]):
        """
        Send status data to performance monitoring system.
        
        Args:
            status_data: Status information to send
        """
        try:
            metrics = status_data.get('performance_metrics', {})
            
            if 'jobs_per_minute' in metrics:
                record_metric(
                    self.engine.engine_name,
                    'jobs_per_minute',
                    metrics['jobs_per_minute']
                )
            
            if 'success_rate' in metrics:
                record_metric(
                    self.engine.engine_name,
                    'success_rate',
                    metrics['success_rate']
                )
            
            db_health = status_data.get('database_health', {})
            if 'response_time_ms' in db_health and db_health['response_time_ms'] is not None:
                record_metric(
                    self.engine.engine_name,
                    'db_response_time_ms',
                    db_health['response_time_ms']
                )
            
        except Exception as e:
            self.logger.warning(f"Failed to send metrics to performance monitor: {e}")
    
    def update_performance_history(self, performance_data: Dict[str, Any]):
        """
        Update performance history with new data point.
        
        Args:
            performance_data: Performance data to add to history
        """
        try:
            self.performance_history.append(performance_data)
        except Exception as e:
            self.logger.warning(f"Failed to update performance history: {e}")
    
    def get_collector_status(self) -> Dict[str, Any]:
        """
        Get status of the status collector itself.
        
        Returns:
            Dictionary with collector status information
        """
        return {
            'performance_history_size': len(self.performance_history),
            'max_history_size': self.performance_history.maxlen,
            'latest_metrics_available': len(self.performance_history) > 0
        }