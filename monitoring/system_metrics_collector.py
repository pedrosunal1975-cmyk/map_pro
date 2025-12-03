"""
Map Pro System Metrics Collector
=================================

Collects system resource metrics (CPU, memory, disk).

Save location: tools/monitoring/system_metrics_collector.py
"""

import psutil
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from .resource_health import ResourceHealthChecker
from .monitoring_constants import (
    BYTES_PER_GB,
    ROUND_DECIMAL_PLACES
)

logger = get_logger(__name__, 'monitoring')


class SystemMetricsCollector:
    """
    Collects system resource metrics.
    
    Responsibilities:
    - Collect CPU usage metrics
    - Collect memory usage metrics
    - Collect disk usage metrics
    - Optionally collect process-specific metrics
    """
    
    def __init__(self) -> None:
        """Initialize system metrics collector."""
        self.resource_checker = ResourceHealthChecker()
    
    async def collect(
        self,
        enable_detailed: bool = True
    ) -> Dict[str, Any]:
        """
        Collect system resource metrics.
        
        Args:
            enable_detailed: Whether to include detailed metrics
            
        Returns:
            Dictionary with system metrics
        """
        try:
            resource_health = await self.resource_checker.check_system_resources()
            
            system_metrics = {
                'cpu': self._collect_cpu_metrics(
                    resource_health=resource_health,
                    enable_detailed=enable_detailed
                ),
                'memory': self._collect_memory_metrics(
                    resource_health=resource_health
                ),
                'disk': self._collect_disk_metrics(
                    resource_health=resource_health
                )
            }
            
            if enable_detailed:
                system_metrics['process'] = self._collect_process_metrics()
            
            return system_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {'error': str(e)}
    
    def _collect_cpu_metrics(
        self,
        resource_health: Dict[str, Any],
        enable_detailed: bool
    ) -> Dict[str, Any]:
        """
        Collect CPU metrics.
        
        Args:
            resource_health: Resource health data
            enable_detailed: Whether to include per-CPU metrics
            
        Returns:
            Dictionary with CPU metrics
        """
        cpu_metrics = {
            'percent': resource_health['cpu']['usage_percent'],
            'count': psutil.cpu_count()
        }
        
        if enable_detailed:
            cpu_metrics['per_cpu'] = psutil.cpu_percent(percpu=True)
        else:
            cpu_metrics['per_cpu'] = None
        
        return cpu_metrics
    
    def _collect_memory_metrics(
        self,
        resource_health: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collect memory metrics.
        
        Args:
            resource_health: Resource health data
            
        Returns:
            Dictionary with memory metrics
        """
        memory = psutil.virtual_memory()
        
        return {
            'percent': resource_health['memory']['usage_percent'],
            'total_gb': round(memory.total / BYTES_PER_GB, ROUND_DECIMAL_PLACES),
            'available_gb': round(
                memory.available / BYTES_PER_GB,
                ROUND_DECIMAL_PLACES
            ),
            'used_gb': round(memory.used / BYTES_PER_GB, ROUND_DECIMAL_PLACES)
        }
    
    def _collect_disk_metrics(
        self,
        resource_health: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collect disk metrics.
        
        Args:
            resource_health: Resource health data
            
        Returns:
            Dictionary with disk metrics
        """
        disk = psutil.disk_usage('/')
        
        return {
            'percent': resource_health['disk']['usage_percent'],
            'total_gb': round(disk.total / BYTES_PER_GB, ROUND_DECIMAL_PLACES),
            'free_gb': round(disk.free / BYTES_PER_GB, ROUND_DECIMAL_PLACES),
            'used_gb': round(disk.used / BYTES_PER_GB, ROUND_DECIMAL_PLACES)
        }
    
    def _collect_process_metrics(self) -> Dict[str, Any]:
        """
        Collect process-specific metrics.
        
        Returns:
            Dictionary with process metrics
        """
        try:
            process = psutil.Process()
            
            return {
                'memory_mb': round(
                    process.memory_info().rss / (1024 ** 2),
                    ROUND_DECIMAL_PLACES
                ),
                'cpu_percent': process.cpu_percent(),
                'threads': process.num_threads(),
                'open_files': len(process.open_files())
            }
        except Exception as e:
            logger.error(f"Failed to collect process metrics: {e}")
            return {'error': str(e)}