"""
Map Pro Performance Monitor
===========================

Central coordination for performance monitoring across all Map Pro components.
Provides oversight without implementing specific monitoring operations.

Architecture: Core oversight/coordination only - delegates collection and alerting to specialized components.
"""

import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque

from .data_paths import map_pro_paths
from .system_logger import get_logger
from .performance_metrics_collector import MetricsCollector
from .alert_manager import alert_manager

logger = get_logger(__name__, 'core')


class PerformanceMonitor:
    """
    Central coordinator for performance monitoring across all Map Pro components.
    
    Responsibilities:
    - Orchestrating performance monitoring across system
    - Coordinating metrics collection and alert generation
    - Managing monitoring lifecycle and configuration
    
    Does NOT handle:
    - Detailed metrics collection (metrics_collector handles this)
    - Alert generation logic (alert_manager handles this)
    - Engine-specific performance optimization
    """
    
    def __init__(self):
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.monitoring_interval = 60  # seconds
        self.is_monitoring = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        self.metrics_collector = MetricsCollector()
        
        logger.info("Performance monitor initializing")
    
    def start_monitoring(self):
        """Start background performance monitoring."""
        if self.is_monitoring:
            logger.warning("Performance monitoring already started")
            return
        
        self.is_monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background performance monitoring."""
        self.is_monitoring = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.is_monitoring:
            try:
                self._collect_and_store_metrics()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_and_store_metrics(self):
        """Collect metrics and store in history."""
        try:
            # Use metrics collector to gather all metrics
            all_metrics = self.metrics_collector.collect_all_metrics()
            
            # Store with timestamp
            timestamp = datetime.now(timezone.utc)
            
            with self._lock:
                for category, metrics in all_metrics.items():
                    self.metrics_history[category].append({
                        'timestamp': timestamp,
                        'metrics': metrics
                    })
            
            # Send to alert manager for threshold checking
            alert_manager.check_performance_thresholds(all_metrics)
            
        except Exception as e:
            logger.error(f"Failed to collect and store metrics: {e}")
    
    def record_engine_metric(self, engine_name: str, metric_name: str, value: float, 
                           metadata: Optional[Dict[str, Any]] = None):
        """
        Record a metric from an engine.
        
        Args:
            engine_name: Name of reporting engine
            metric_name: Name of the metric
            value: Metric value
            metadata: Optional additional metadata
        """
        try:
            with self._lock:
                self.metrics_history[f"engine_{engine_name}"].append({
                    'timestamp': datetime.now(timezone.utc),
                    'metric_name': metric_name,
                    'value': value,
                    'metadata': metadata or {}
                })
            
            logger.debug(f"Recorded metric {metric_name}={value} from {engine_name}")
            
        except Exception as e:
            logger.error(f"Failed to record metric from {engine_name}: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        try:
            with self._lock:
                latest_metrics = {}
                
                for category, history in self.metrics_history.items():
                    if history:
                        latest_metrics[category] = history[-1]
            
            return {
                'monitoring_active': self.is_monitoring,
                'latest_metrics': latest_metrics,
                'metrics_history_size': {k: len(v) for k, v in self.metrics_history.items()}
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {'error': str(e)}
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate performance report for specified time period.
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Performance report dictionary
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            with self._lock:
                report = {
                    'report_period_hours': hours,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'categories': {}
                }
                
                for category, history in self.metrics_history.items():
                    filtered_metrics = [
                        entry for entry in history 
                        if entry['timestamp'] >= cutoff_time
                    ]
                    
                    if filtered_metrics:
                        report['categories'][category] = {
                            'data_points': len(filtered_metrics),
                            'first_timestamp': filtered_metrics[0]['timestamp'].isoformat(),
                            'last_timestamp': filtered_metrics[-1]['timestamp'].isoformat()
                        }
                    else:
                        report['categories'][category] = {
                            'data_points': 0
                        }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {'error': str(e)}


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def record_metric(engine_name: str, metric_name: str, value: float, 
                 metadata: Optional[Dict[str, Any]] = None):
    """Convenience function to record engine metrics."""
    performance_monitor.record_engine_metric(engine_name, metric_name, value, metadata)


def get_performance_summary() -> Dict[str, Any]:
    """Convenience function to get performance summary."""
    return performance_monitor.get_performance_summary()