"""
Status Display Handler for Monitoring Commands.

Handles system status display with real-time monitoring support.

Location: tools/cli/monitoring_status.py
"""

import time
from typing import Optional

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
import psutil

from .monitoring_constants import MonitoringIcons, MonitoringDefaults


logger = get_logger(__name__, 'maintenance')


class StatusHandler:
    """
    Handles system status display operations.
    
    Features:
    - Real-time system status
    - Component status monitoring
    - Database connectivity status
    - Resource usage overview
    - Auto-refresh capability
    
    Example:
        >>> handler = StatusHandler()
        >>> handler.show(refresh_interval=5)
    """
    
    def __init__(self):
        """Initialize status handler."""
        self.logger = logger
    
    def show(self, refresh_interval: Optional[int] = None) -> int:
        """
        Show system status overview.
        
        Args:
            refresh_interval: Auto-refresh interval in seconds (None for single display)
            
        Returns:
            0 for success, 1 for failure
        """
        try:
            if refresh_interval:
                self._show_refreshing_status(refresh_interval)
            else:
                print(f"\n{MonitoringIcons.STATUS} Map Pro System Status:")
                self._display_status()
            
            return 0
        
        except Exception as e:
            print(f"{MonitoringIcons.ERROR} Failed to get system status: {e}")
            self.logger.error(f"Status display failed: {e}", exc_info=True)
            return 1
    
    def _show_refreshing_status(self, refresh_interval: int) -> None:
        """
        Show status with auto-refresh.
        
        Args:
            refresh_interval: Refresh interval in seconds
        """
        separator = "=" * MonitoringDefaults.SEPARATOR_LENGTH
        print(f"System status (refreshing every {refresh_interval}s, Ctrl+C to stop):")
        
        try:
            while True:
                print(f"\n{separator}")
                print(f"Status at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(separator)
                self._display_status()
                
                time.sleep(refresh_interval)
        
        except KeyboardInterrupt:
            print("\nStopped monitoring.")
    
    def _display_status(self) -> None:
        """Display current system status."""
        try:
            self._display_system_uptime()
            self._display_engine_status()
            self._display_database_status()
            self._display_resource_usage()
        except Exception as e:
            print(f"  Error getting status details: {e}")
            self.logger.error(f"Status display error: {e}", exc_info=True)
    
    def _display_system_uptime(self) -> None:
        """Display system uptime."""
        try:
            from core.performance_monitor import performance_monitor
            uptime = performance_monitor.get_system_uptime()
            print(f"  Uptime: {uptime}")
        except ImportError:
            print("  Uptime: Not available")
    
    def _display_engine_status(self) -> None:
        """Display engine status."""
        engines = ['searcher', 'downloader', 'extractor', 'parser', 'librarian', 'mapper']
        print(f"\n  Engines:")
        
        try:
            from core.component_manager import component_manager
            
            for engine in engines:
                self._display_single_engine_status(engine, component_manager)
        except ImportError:
            for engine in engines:
                print(f"    {MonitoringIcons.UNKNOWN} {engine.title()}: Status unavailable")
    
    def _display_single_engine_status(self, engine: str, component_manager) -> None:
        """
        Display status of a single engine.
        
        Args:
            engine: Engine name
            component_manager: Component manager instance
        """
        try:
            status = component_manager.get_component_status(f'{engine}_engine')
            running = status.get('status') == 'running'
            icon = MonitoringIcons.RUNNING if running else MonitoringIcons.STOPPED
            print(f"    {icon} {engine.title()}: {'Running' if running else 'Stopped'}")
        except Exception as e:
            self.logger.warning(f"Failed to get component status for {engine}_engine: {e}")
            print(f"    {MonitoringIcons.UNKNOWN} {engine.title()}: Unknown")
    
    def _display_database_status(self) -> None:
        """Display database status."""
        print(f"\n  Databases:")
        for db_name in ['core', 'parsed', 'library', 'mapped']:
            try:
                with db_coordinator.get_connection(db_name) as conn:
                    print(f"    {MonitoringIcons.HEALTHY} {db_name.title()}: Connected")
            except Exception as e:
                self.logger.error(f"Database connection failed for {db_name}: {e}")
                print(f"    {MonitoringIcons.ERROR} {db_name.title()}: Disconnected")
    
    def _display_resource_usage(self) -> None:
        """Display resource usage."""
        try:
            from core.performance_monitor import performance_monitor
            resources = performance_monitor.get_resource_usage()
            print(f"\n  Resources:")
            print(f"    CPU: {resources.get('cpu_percent', 0):.1f}%")
            print(f"    Memory: {resources.get('memory_percent', 0):.1f}%")
            print(f"    Disk: {resources.get('disk_percent', 0):.1f}%")
        except ImportError:
            self._display_basic_resource_usage()
    
    def _display_basic_resource_usage(self) -> None:
        """Display basic resource usage using psutil."""
        try:
            print(f"\n  Resources:")
            print(f"    CPU: {psutil.cpu_percent():.1f}%")
            print(f"    Memory: {psutil.virtual_memory().percent:.1f}%")
            print(f"    Disk: {psutil.disk_usage('/').percent:.1f}%")
        except ImportError:
            print(f"\n  Resources: Not available")


__all__ = ['StatusHandler']