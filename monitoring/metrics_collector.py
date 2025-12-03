"""
Map Pro Metrics Collector
==========================

Collects system, queue, database, and engine metrics.

Save location: tools/monitoring/metrics_collector.py
"""

from typing import Dict, Any
from datetime import datetime, timezone

from core.system_logger import get_logger
from .system_metrics_collector import SystemMetricsCollector
from .queue_metrics_collector import QueueMetricsCollector
from .database_metrics_collector import DatabaseMetricsCollector
from .engine_metrics_collector import EngineMetricsCollector

logger = get_logger(__name__, 'monitoring')


class MetricsCollector:
    """
    Coordinates collection of all system metrics.
    
    Responsibilities:
    - Delegate to specialized metric collectors
    - Aggregate collected metrics
    - Handle collection errors gracefully
    """
    
    def __init__(
        self,
        db_coordinator,
        job_orchestrator
    ) -> None:
        """
        Initialize metrics collector.
        
        Args:
            db_coordinator: Database coordinator instance
            job_orchestrator: Job orchestrator instance
        """
        self.system_collector = SystemMetricsCollector()
        self.queue_collector = QueueMetricsCollector(
            db_coordinator=db_coordinator,
            job_orchestrator=job_orchestrator
        )
        self.database_collector = DatabaseMetricsCollector(
            db_coordinator=db_coordinator
        )
        self.engine_collector = EngineMetricsCollector(
            db_coordinator=db_coordinator
        )
    
    async def collect_all_metrics(
        self,
        enable_detailed: bool = True
    ) -> Dict[str, Any]:
        """
        Collect all system metrics.
        
        Args:
            enable_detailed: Whether to collect detailed metrics
            
        Returns:
            Dictionary with all metrics organized by category
        """
        metrics = {
            'system': await self.system_collector.collect(
                enable_detailed=enable_detailed
            ),
            'queues': await self.queue_collector.collect(),
            'databases': await self.database_collector.collect(
                enable_detailed=enable_detailed
            ),
            'engines': await self.engine_collector.collect()
        }
        
        return metrics