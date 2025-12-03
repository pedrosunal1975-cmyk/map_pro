# File: /map_pro/engines/base/status_reporter.py

"""
Map Pro Status Reporter
======================

Main status reporting coordination for engines to the core system.
Provides periodic status updates and health monitoring for engine coordination.

Architecture: Specialized component focused on status reporting coordination.
"""

import time
import json
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from collections import deque

from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import StatusReportingError
from .status_collector import StatusCollector
from .health_monitor import HealthMonitor

if TYPE_CHECKING:
    from .engine_base import BaseEngine

logger = get_logger(__name__, 'engine')

DEFAULT_REPORTING_INTERVAL_SECONDS = 60
STATUS_CHANGE_THRESHOLD = 0.1
DECIMAL_PRECISION_JOBS_PER_MINUTE = 1
DECIMAL_PRECISION_DB_RESPONSE_MS = 1


class StatusReporter:
    """
    Main status reporting coordinator for engines.
    
    Responsibilities:
    - Periodic status reporting coordination
    - Integration with status collection and health monitoring
    - Report timing and caching management
    - Core system communication
    
    Does NOT handle:
    - Detailed status collection (status_collector handles this)
    - Health checking logic (health_monitor handles this)
    - Performance metrics calculation (status_collector handles this)
    """
    
    def __init__(self, engine: 'BaseEngine'):
        """
        Initialize status reporter for specific engine.
        
        Args:
            engine: The engine instance this reporter belongs to
        """
        self.engine = engine
        self.logger = get_logger(f"engines.{engine.engine_name}.status_reporter", 'engine')
        
        self.status_collector = StatusCollector(engine)
        self.health_monitor = HealthMonitor(engine)
        
        self.reporting_interval = DEFAULT_REPORTING_INTERVAL_SECONDS
        self.last_report_time = None
        self.report_counter = 0
        
        self.last_status_hash = None
        self.status_change_threshold = STATUS_CHANGE_THRESHOLD
        
        self.logger.debug(f"Status reporter initialized for {engine.engine_name}")
    
    def report_status(self):
        """
        Report engine status if reporting interval has elapsed.
        Called from the main engine loop.
        """
        try:
            current_time = time.time()
            
            if self._should_report_status(current_time):
                self._generate_and_send_status_report(current_time)
                
            if self.health_monitor.should_perform_health_check(current_time):
                self.health_monitor.perform_health_check(current_time)
                
        except Exception as e:
            self.logger.error(f"Status reporting failed: {e}")
    
    def _should_report_status(self, current_time: float) -> bool:
        """
        Determine if status should be reported now.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if status should be reported
        """
        if self.last_report_time is None:
            return True
        
        if (current_time - self.last_report_time) >= self.reporting_interval:
            return True
        
        if self._has_significant_status_change():
            return True
        
        return False
    
    def _generate_and_send_status_report(self, current_time: float):
        """
        Generate and send comprehensive status report.
        
        Args:
            current_time: Current timestamp
        """
        try:
            status_data = self.status_collector.collect_comprehensive_status()
            
            status_data['report_metadata'] = {
                'report_id': f"{self.engine.engine_name}_{self.report_counter}",
                'report_time': datetime.now(timezone.utc).isoformat(),
                'report_interval': self.reporting_interval,
                'reporter_uptime': current_time - (self.last_report_time or current_time)
            }
            
            self.status_collector.send_to_performance_monitor(status_data)
            
            self._log_status_summary(status_data)
            
            self.last_report_time = current_time
            self.report_counter += 1
            self._update_status_cache(status_data)
            
        except Exception as e:
            self.logger.error(f"Failed to generate status report: {e}")
            raise StatusReportingError(f"Status report generation failed: {e}")
    
    def _log_status_summary(self, status_data: Dict[str, Any]):
        """
        Log a concise status summary.
        
        Args:
            status_data: Status information to summarize
        """
        try:
            summary_parts = [
                f"Engine: {self.engine.engine_name}",
                f"Status: {'Running' if status_data.get('is_running') else 'Stopped'}",
                f"Jobs: {status_data.get('jobs_processed', 0)} processed",
                f"Errors: {status_data.get('jobs_failed', 0)}"
            ]
            
            metrics = status_data.get('performance_metrics', {})
            if 'jobs_per_minute' in metrics:
                summary_parts.append(
                    f"Rate: {metrics['jobs_per_minute']:.{DECIMAL_PRECISION_JOBS_PER_MINUTE}f}/min"
                )
            
            db_health = status_data.get('database_health', {})
            if db_health.get('primary_db_accessible'):
                summary_parts.append(
                    f"DB: OK ({db_health.get('response_time_ms', 0):.{DECIMAL_PRECISION_DB_RESPONSE_MS}f}ms)"
                )
            else:
                summary_parts.append("DB: ERROR")
            
            summary = " | ".join(summary_parts)
            self.logger.info(f"Status Report: {summary}")
            
        except Exception as e:
            self.logger.warning(f"Failed to log status summary: {e}")
    
    def _has_significant_status_change(self) -> bool:
        """
        Check if there have been significant status changes.
        
        Returns:
            True if significant changes detected
        """
        try:
            if self.last_status_hash is None:
                return True
            
            current_metrics = {
                'is_running': self.engine.is_running,
                'jobs_processed': self.engine.jobs_processed,
                'jobs_failed': self.engine.jobs_failed
            }
            
            current_hash = hash(json.dumps(current_metrics, sort_keys=True))
            
            if current_hash != self.last_status_hash:
                return True
            
            return False
            
        except Exception:
            return True
    
    def _update_status_cache(self, status_data: Dict[str, Any]):
        """
        Update status cache for change detection.
        
        Args:
            status_data: Current status data
        """
        try:
            key_metrics = {
                'is_running': status_data.get('is_running'),
                'jobs_processed': status_data.get('jobs_processed'),
                'jobs_failed': status_data.get('jobs_failed')
            }
            
            self.last_status_hash = hash(json.dumps(key_metrics, sort_keys=True))
            
            self.status_collector.update_performance_history({
                'timestamp': time.time(),
                'jobs_processed': status_data.get('jobs_processed', 0),
                'jobs_failed': status_data.get('jobs_failed', 0),
                'is_running': status_data.get('is_running', False)
            })
            
        except Exception as e:
            self.logger.warning(f"Failed to update status cache: {e}")
    
    def force_status_report(self) -> Dict[str, Any]:
        """
        Force an immediate status report regardless of timing.
        
        Returns:
            Status data that was reported
        """
        try:
            current_time = time.time()
            status_data = self.status_collector.collect_comprehensive_status()
            
            self.status_collector.send_to_performance_monitor(status_data)
            self._log_status_summary(status_data)
            
            self.last_report_time = current_time
            self.report_counter += 1
            self._update_status_cache(status_data)
            
            self.logger.info("Forced status report completed")
            return status_data
            
        except Exception as e:
            self.logger.error(f"Forced status report failed: {e}")
            raise StatusReportingError(f"Forced status report failed: {e}")
    
    def get_reporter_status(self) -> Dict[str, Any]:
        """
        Get status of the status reporter itself.
        
        Returns:
            Dictionary with reporter status information
        """
        return {
            'engine_name': self.engine.engine_name,
            'reports_sent': self.report_counter,
            'last_report_time': self.last_report_time,
            'reporting_interval': self.reporting_interval,
            'status_collector_status': self.status_collector.get_collector_status(),
            'health_monitor_status': self.health_monitor.get_monitor_status()
        }