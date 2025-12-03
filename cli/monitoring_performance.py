"""
Performance Metrics Handler for Monitoring Commands.

Handles performance metrics collection and display.

Location: tools/cli/monitoring_performance.py
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger
import psutil

from .monitoring_constants import MonitoringIcons


logger = get_logger(__name__, 'maintenance')


class PerformanceHandler:
    """
    Handles performance metrics operations.
    
    Features:
    - System-wide performance metrics
    - Component-specific metrics
    - Engine performance tracking
    - Configurable time periods
    
    Example:
        >>> handler = PerformanceHandler()
        >>> handler.show(component='parser', period='24h')
    """
    
    def __init__(self):
        """Initialize performance handler."""
        self.logger = logger
    
    def show(self, component: Optional[str] = None, period: str = '1h') -> int:
        """
        Show performance metrics.
        
        Args:
            component: Specific component to show
            period: Time period ('1h', '24h', '7d')
            
        Returns:
            0 for success, 1 for failure
        """
        try:
            print(f"\n{MonitoringIcons.PERF} Performance Metrics ({period}):")
            
            try:
                from core.performance_metrics_collector import performance_collector
                self._display_with_collector(performance_collector, component, period)
            except ImportError:
                self._display_basic_metrics()
            
            return 0
        
        except Exception as e:
            print(f"{MonitoringIcons.ERROR} Failed to get performance metrics: {e}")
            self.logger.error(f"Performance metrics failed: {e}", exc_info=True)
            return 1
    
    def _display_with_collector(
        self,
        performance_collector,
        component: Optional[str],
        period: str
    ) -> None:
        """
        Display performance metrics using collector.
        
        Args:
            performance_collector: Performance collector instance
            component: Component to display
            period: Time period
        """
        if component:
            metrics = performance_collector.get_component_metrics(component, period)
            print(f"\n  {component.upper()} Metrics:")
            self._display_metrics(metrics)
        else:
            # System-wide metrics
            system_metrics = performance_collector.get_system_metrics(period)
            print(f"\n  System Metrics:")
            self._display_metrics(system_metrics)
            
            # Engine metrics
            self._display_all_engine_metrics(performance_collector, period)
    
    def _display_all_engine_metrics(self, performance_collector, period: str) -> None:
        """
        Display metrics for all engines.
        
        Args:
            performance_collector: Performance collector instance
            period: Time period
        """
        engines = ['searcher', 'downloader', 'extractor', 'parser', 'librarian', 'mapper']
        for engine in engines:
            try:
                engine_metrics = performance_collector.get_engine_metrics(engine, period)
                if engine_metrics:
                    print(f"\n  {engine.upper()} Engine:")
                    self._display_metrics(engine_metrics)
            except Exception:
                continue
    
    def _display_basic_metrics(self) -> None:
        """Display basic performance metrics."""
        print("  Performance metrics collector not available")
        print("  Basic system metrics:")
        try:
            print(f"    CPU Usage: {psutil.cpu_percent():.1f}%")
            print(f"    Memory Usage: {psutil.virtual_memory().percent:.1f}%")
            print(f"    Disk Usage: {psutil.disk_usage('/').percent:.1f}%")
        except ImportError:
            print("    System metrics not available")
    
    def _display_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Display performance metrics in formatted way.
        
        Args:
            metrics: Metrics dictionary
        """
        if not metrics:
            print("    No metrics available")
            return
        
        for key, value in metrics.items():
            formatted_key = key.replace('_', ' ').title()
            
            if isinstance(value, float):
                if 'percent' in key.lower():
                    print(f"    {formatted_key}: {value:.1f}%")
                elif 'rate' in key.lower():
                    print(f"    {formatted_key}: {value:.2f}")
                else:
                    print(f"    {formatted_key}: {value:.2f}")
            elif isinstance(value, int):
                print(f"    {formatted_key}: {value:,}")
            else:
                print(f"    {formatted_key}: {value}")


__all__ = ['PerformanceHandler']