"""
Map Pro Metrics Exporter
=========================

Exports metrics in various formats (JSON, Prometheus, human-readable).

Save location: tools/monitoring/metrics_exporter.py
"""

import json
import time
from typing import Dict, Any

from core.system_logger import get_logger
from .monitoring_constants import (
    REPORT_SEPARATOR_CHAR,
    REPORT_SEPARATOR_LENGTH
)

logger = get_logger(__name__, 'monitoring')


class MetricsExporter:
    """
    Exports metrics in multiple formats.
    
    Responsibilities:
    - Export metrics as JSON
    - Export metrics in Prometheus format
    - Generate human-readable reports
    """
    
    def to_json(self, metrics: Dict[str, Any]) -> str:
        """
        Export metrics in JSON format.
        
        Args:
            metrics: Metrics to export
            
        Returns:
            JSON string of metrics
        """
        if not metrics:
            return "{}"
        
        return json.dumps(metrics, indent=2)
    
    def to_prometheus(self, metrics: Dict[str, Any]) -> str:
        """
        Export metrics in Prometheus format.
        
        Args:
            metrics: Metrics to export
            
        Returns:
            Prometheus-formatted metrics string
        """
        if not metrics:
            return ""
        
        lines = []
        timestamp = int(time.time() * 1000)
        
        # System metrics
        if 'system' in metrics:
            lines.extend(
                self._export_system_metrics_prometheus(
                    metrics['system'],
                    timestamp
                )
            )
        
        # Queue metrics
        if 'queues' in metrics and 'overall' in metrics['queues']:
            lines.extend(
                self._export_queue_metrics_prometheus(
                    metrics['queues']['overall'],
                    timestamp
                )
            )
        
        # Database metrics
        if 'databases' in metrics:
            lines.extend(
                self._export_database_metrics_prometheus(
                    metrics['databases'],
                    timestamp
                )
            )
        
        return '\n'.join(lines)
    
    def _export_system_metrics_prometheus(
        self,
        sys_metrics: Dict[str, Any],
        timestamp: int
    ) -> list:
        """
        Export system metrics in Prometheus format.
        
        Args:
            sys_metrics: System metrics
            timestamp: Unix timestamp in milliseconds
            
        Returns:
            List of Prometheus metric lines
        """
        lines = []
        
        lines.append("# TYPE mappro_cpu_percent gauge")
        lines.append(f"mappro_cpu_percent {sys_metrics['cpu']['percent']} {timestamp}")
        
        lines.append("# TYPE mappro_memory_percent gauge")
        lines.append(f"mappro_memory_percent {sys_metrics['memory']['percent']} {timestamp}")
        
        lines.append("# TYPE mappro_disk_percent gauge")
        lines.append(f"mappro_disk_percent {sys_metrics['disk']['percent']} {timestamp}")
        
        return lines
    
    def _export_queue_metrics_prometheus(
        self,
        queue_metrics: Dict[str, Any],
        timestamp: int
    ) -> list:
        """
        Export queue metrics in Prometheus format.
        
        Args:
            queue_metrics: Queue metrics
            timestamp: Unix timestamp in milliseconds
            
        Returns:
            List of Prometheus metric lines
        """
        lines = []
        
        lines.append("# TYPE mappro_total_jobs gauge")
        lines.append(f"mappro_total_jobs {queue_metrics.get('total_jobs', 0)} {timestamp}")
        
        lines.append("# TYPE mappro_active_jobs gauge")
        lines.append(f"mappro_active_jobs {queue_metrics.get('active_jobs', 0)} {timestamp}")
        
        return lines
    
    def _export_database_metrics_prometheus(
        self,
        db_metrics: Dict[str, Any],
        timestamp: int
    ) -> list:
        """
        Export database metrics in Prometheus format.
        
        Args:
            db_metrics: Database metrics
            timestamp: Unix timestamp in milliseconds
            
        Returns:
            List of Prometheus metric lines
        """
        lines = []
        
        lines.append("# TYPE mappro_databases_healthy gauge")
        healthy_value = 1 if db_metrics.get('overall_healthy') else 0
        lines.append(f"mappro_databases_healthy {healthy_value} {timestamp}")
        
        return lines
    
    def to_human_readable(self, metrics: Dict[str, Any]) -> str:
        """
        Generate human-readable metrics report.
        
        Args:
            metrics: Metrics to format
            
        Returns:
            Formatted report string
        """
        if not metrics:
            return "No metrics available"
        
        separator = REPORT_SEPARATOR_CHAR * REPORT_SEPARATOR_LENGTH
        
        report_lines = [
            separator,
            "MAP PRO SYSTEM METRICS REPORT",
            f"Generated: {metrics.get('timestamp', 'Unknown')}",
            separator,
            "",
            self._format_system_section(metrics.get('system', {})),
            "",
            self._format_queue_section(metrics.get('queues', {})),
            "",
            self._format_database_section(metrics.get('databases', {})),
            "",
            separator
        ]
        
        return '\n'.join(report_lines)
    
    def _format_system_section(self, system_metrics: Dict[str, Any]) -> str:
        """
        Format system metrics section.
        
        Args:
            system_metrics: System metrics
            
        Returns:
            Formatted system section
        """
        if not system_metrics or 'error' in system_metrics:
            return "SYSTEM RESOURCES:\n  Error collecting metrics"
        
        cpu_percent = system_metrics.get('cpu', {}).get('percent', 0)
        memory = system_metrics.get('memory', {})
        disk = system_metrics.get('disk', {})
        
        return (
            "SYSTEM RESOURCES:\n"
            f"  CPU:    {cpu_percent}%\n"
            f"  Memory: {memory.get('percent', 0)}% ({memory.get('used_gb', 0)}GB used)\n"
            f"  Disk:   {disk.get('percent', 0)}% ({disk.get('used_gb', 0)}GB used)"
        )
    
    def _format_queue_section(self, queue_metrics: Dict[str, Any]) -> str:
        """
        Format queue metrics section.
        
        Args:
            queue_metrics: Queue metrics
            
        Returns:
            Formatted queue section
        """
        if not queue_metrics or 'error' in queue_metrics:
            return "JOB QUEUES:\n  Error collecting metrics"
        
        overall = queue_metrics.get('overall', {})
        health_indicators = queue_metrics.get('health_indicators', {})
        
        return (
            "JOB QUEUES:\n"
            f"  Total Jobs:  {overall.get('total_jobs', 0)}\n"
            f"  Active Jobs: {overall.get('active_jobs', 0)}\n"
            f"  Processing Rate: {health_indicators.get('processing_rate', 0)} jobs/min"
        )
    
    def _format_database_section(self, db_metrics: Dict[str, Any]) -> str:
        """
        Format database metrics section.
        
        Args:
            db_metrics: Database metrics
            
        Returns:
            Formatted database section
        """
        if not db_metrics or 'error' in db_metrics:
            return "DATABASES:\n  Error collecting metrics"
        
        overall_healthy = db_metrics.get('overall_healthy', False)
        databases = db_metrics.get('databases', {})
        
        lines = [
            "DATABASES:",
            f"  Overall Healthy: {'Yes' if overall_healthy else 'No'}"
        ]
        
        for db_name, db_status in databases.items():
            status_str = "Healthy" if db_status.get('healthy') else "Unhealthy"
            response_time = db_status.get('response_time_ms', 0)
            lines.append(f"  {db_name.upper()}: {status_str} ({response_time}ms)")
        
        return '\n'.join(lines)