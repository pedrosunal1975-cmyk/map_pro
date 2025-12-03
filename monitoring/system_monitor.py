"""
Map Pro System Monitor - Main Coordinator
==========================================

Coordinates system monitoring and metrics collection.
Delegates specific monitoring concerns to specialized components.

Save location: tools/monitoring/system_monitor.py
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.job_orchestrator import job_orchestrator
from .metrics_collector import MetricsCollector
from .metrics_exporter import MetricsExporter
from .metrics_history import MetricsHistory
from .monitoring_constants import (
    DEFAULT_COLLECTION_INTERVAL,
    DEFAULT_METRICS_HISTORY_SIZE
)

logger = get_logger(__name__, 'monitoring')


class SystemMonitor:
    """
    Real-time system monitoring coordinator.
    
    Responsibilities:
    - Coordinate metrics collection across specialized collectors
    - Manage metrics history
    - Export metrics in various formats
    - Generate monitoring reports
    
    Does NOT handle:
    - Alert generation (alert_manager handles this)
    - Health remediation (components handle their own recovery)
    - Metrics persistence (uses in-memory buffer)
    """
    
    def __init__(
        self,
        metrics_history_size: int = DEFAULT_METRICS_HISTORY_SIZE
    ) -> None:
        """
        Initialize system monitor.
        
        Args:
            metrics_history_size: Maximum number of metrics snapshots to retain
        """
        self.metrics_history_size = metrics_history_size
        self.last_collection_time: Optional[datetime] = None
        
        # Initialize components
        self.collector = MetricsCollector(
            db_coordinator=db_coordinator,
            job_orchestrator=job_orchestrator
        )
        self.history = MetricsHistory(max_size=metrics_history_size)
        self.exporter = MetricsExporter()
        
        # Environment configuration
        self.collection_interval = int(
            os.getenv(
                'MAP_PRO_MONITORING_INTERVAL',
                str(DEFAULT_COLLECTION_INTERVAL)
            )
        )
        self.enable_detailed_metrics = (
            os.getenv('MAP_PRO_ENABLE_DETAILED_METRICS', 'true').lower() == 'true'
        )
        
        logger.info("System monitor initialized")
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect all system metrics.
        
        Returns:
            Dictionary with all current metrics including timestamp
        """
        collection_time = datetime.now(timezone.utc)
        
        metrics = await self.collector.collect_all_metrics(
            enable_detailed=self.enable_detailed_metrics
        )
        
        # Add timestamp to metrics
        metrics['timestamp'] = collection_time.isoformat()
        
        # Add to history
        self.history.add(metrics)
        self.last_collection_time = collection_time
        
        logger.debug(f"Metrics collected at {collection_time}")
        return metrics
    
    def get_metrics_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics.
        
        Args:
            limit: Optional limit on number of records to return
            
        Returns:
            List of historical metrics snapshots
        """
        return self.history.get(limit=limit)
    
    def export_metrics_json(
        self,
        metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Export metrics in JSON format.
        
        Args:
            metrics: Optional metrics to export, otherwise uses latest
            
        Returns:
            JSON string of metrics
        """
        if metrics is None:
            metrics = self.history.get_latest()
        
        return self.exporter.to_json(metrics)
    
    def export_metrics_prometheus(
        self,
        metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Export metrics in Prometheus format.
        
        Args:
            metrics: Optional metrics to export, otherwise uses latest
            
        Returns:
            Prometheus-formatted metrics string
        """
        if metrics is None:
            metrics = self.history.get_latest()
        
        return self.exporter.to_prometheus(metrics)
    
    async def generate_metrics_report(self) -> str:
        """
        Generate human-readable metrics report.
        
        Returns:
            Formatted report string
        """
        metrics = await self.collect_metrics()
        return self.exporter.to_human_readable(metrics)