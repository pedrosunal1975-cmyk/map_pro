"""
Resource Usage Handler for Monitoring Commands.

Handles system resource monitoring and display.

Location: tools/cli/monitoring_resources.py
"""

from typing import Dict, Any

from core.system_logger import get_logger
import psutil

from .monitoring_constants import MonitoringIcons, ResourceThresholds


logger = get_logger(__name__, 'maintenance')


class ResourcesHandler:
    """
    Handles resource usage monitoring operations.
    
    Features:
    - CPU usage monitoring
    - Memory usage tracking
    - Disk space monitoring
    - Network statistics (detailed mode)
    - Process counting (detailed mode)
    
    Example:
        >>> handler = ResourcesHandler()
        >>> handler.show(detailed=True)
    """
    
    def __init__(self):
        """Initialize resources handler."""
        self.logger = logger
    
    def show(self, detailed: bool = False) -> int:
        """
        Show resource usage.
        
        Args:
            detailed: Show detailed breakdown
            
        Returns:
            0 for success, 1 for failure
        """
        try:
            print(f"\n{MonitoringIcons.RES} System Resource Usage:")
            
            try:
                from core.performance_monitor import performance_monitor
                self._display_monitored_resources(performance_monitor, detailed)
            except ImportError:
                self._display_psutil_resources(detailed)
            
            return 0
        
        except Exception as e:
            print(f"{MonitoringIcons.ERROR} Failed to get resource usage: {e}")
            self.logger.error(f"Resource display failed: {e}", exc_info=True)
            return 1
    
    def _display_monitored_resources(self, performance_monitor, detailed: bool) -> None:
        """
        Display resources using performance monitor.
        
        Args:
            performance_monitor: Performance monitor instance
            detailed: Show detailed breakdown
        """
        resources = (performance_monitor.get_detailed_resource_usage() if detailed 
                    else performance_monitor.get_resource_usage())
        
        self._display_cpu_usage(resources, detailed)
        self._display_memory_usage(resources, detailed)
        self._display_disk_usage(resources, detailed)
        
        if detailed:
            self._display_network_usage(resources)
            self._display_process_count(resources)
    
    def _display_psutil_resources(self, detailed: bool) -> None:
        """
        Display resources using psutil.
        
        Args:
            detailed: Show detailed breakdown
        """
        print("  Using basic system resource monitoring:")
        try:
            # CPU
            cpu_percent = psutil.cpu_percent()
            cpu_icon = self._get_resource_icon(
                cpu_percent,
                ResourceThresholds.CPU_WARNING,
                ResourceThresholds.CPU_CRITICAL
            )
            print(f"  {cpu_icon} CPU Usage: {cpu_percent:.1f}%")
            
            # Memory
            memory = psutil.virtual_memory()
            memory_icon = self._get_resource_icon(
                memory.percent,
                ResourceThresholds.MEMORY_WARNING,
                ResourceThresholds.MEMORY_CRITICAL
            )
            print(f"  {memory_icon} Memory: {memory.percent:.1f}% "
                  f"({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)")
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_icon = self._get_resource_icon(
                disk.percent,
                ResourceThresholds.DISK_WARNING,
                ResourceThresholds.DISK_CRITICAL
            )
            print(f"  {disk_icon} Disk: {disk.percent:.1f}% "
                  f"({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)")
            
            if detailed:
                print(f"  {MonitoringIcons.PROC} CPU Cores: {psutil.cpu_count()}")
                print(f"  {MonitoringIcons.PROC} Active Processes: {len(psutil.pids())}")
        
        except ImportError:
            print("  Resource monitoring not available (psutil not installed)")
    
    def _get_resource_icon(
        self,
        percent: float,
        warning_threshold: int,
        critical_threshold: int
    ) -> str:
        """
        Get icon based on resource usage percentage.
        
        Args:
            percent: Usage percentage
            warning_threshold: Warning threshold
            critical_threshold: Critical threshold
            
        Returns:
            Appropriate icon string
        """
        if percent < warning_threshold:
            return MonitoringIcons.RUNNING
        elif percent < critical_threshold:
            return MonitoringIcons.WARNING
        else:
            return MonitoringIcons.STOPPED
    
    def _display_cpu_usage(self, resources: Dict[str, Any], detailed: bool) -> None:
        """Display CPU usage."""
        cpu_percent = resources.get('cpu_percent', 0)
        cpu_icon = self._get_resource_icon(
            cpu_percent,
            ResourceThresholds.CPU_WARNING,
            ResourceThresholds.CPU_CRITICAL
        )
        print(f"  {cpu_icon} CPU Usage: {cpu_percent:.1f}%")
        
        if detailed:
            cpu_cores = resources.get('cpu_cores', 1)
            cpu_freq = resources.get('cpu_freq_mhz', 0)
            print(f"    Cores: {cpu_cores}, Frequency: {cpu_freq:.0f}MHz")
    
    def _display_memory_usage(self, resources: Dict[str, Any], detailed: bool) -> None:
        """Display memory usage."""
        memory_percent = resources.get('memory_percent', 0)
        memory_used_gb = resources.get('memory_used_gb', 0)
        memory_total_gb = resources.get('memory_total_gb', 0)
        memory_icon = self._get_resource_icon(
            memory_percent,
            ResourceThresholds.MEMORY_WARNING,
            ResourceThresholds.MEMORY_CRITICAL
        )
        
        print(f"  {memory_icon} Memory: {memory_percent:.1f}% "
              f"({memory_used_gb:.1f}GB / {memory_total_gb:.1f}GB)")
    
    def _display_disk_usage(self, resources: Dict[str, Any], detailed: bool) -> None:
        """Display disk usage."""
        disk_percent = resources.get('disk_percent', 0)
        disk_used_gb = resources.get('disk_used_gb', 0)
        disk_total_gb = resources.get('disk_total_gb', 0)
        disk_icon = self._get_resource_icon(
            disk_percent,
            ResourceThresholds.DISK_WARNING,
            ResourceThresholds.DISK_CRITICAL
        )
        
        print(f"  {disk_icon} Disk: {disk_percent:.1f}% "
              f"({disk_used_gb:.1f}GB / {disk_total_gb:.1f}GB)")
    
    def _display_network_usage(self, resources: Dict[str, Any]) -> None:
        """Display network usage."""
        network = resources.get('network', {})
        if network:
            print(f"  {MonitoringIcons.NET} Network:")
            print(f"    Bytes Sent: {network.get('bytes_sent', 0):,}")
            print(f"    Bytes Received: {network.get('bytes_recv', 0):,}")
    
    def _display_process_count(self, resources: Dict[str, Any]) -> None:
        """Display process count."""
        process_count = resources.get('process_count', 0)
        print(f"  {MonitoringIcons.PROC} Active Processes: {process_count}")


__all__ = ['ResourcesHandler']