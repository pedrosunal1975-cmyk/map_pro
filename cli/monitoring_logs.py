"""
Logs Handler for Monitoring Commands.

Handles system log viewing and filtering.

Location: tools/cli/monitoring_logs.py
"""

from typing import Optional

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

from .monitoring_constants import MonitoringIcons, MonitoringDefaults


logger = get_logger(__name__, 'maintenance')


class LogsHandler:
    """
    Handles log viewing operations.
    
    Features:
    - Recent log display
    - Component filtering
    - Log level filtering
    - Tail support
    - Follow mode (planned)
    
    Example:
        >>> handler = LogsHandler()
        >>> handler.show(component='parser', level='ERROR', tail=100)
    """
    
    def __init__(self):
        """Initialize logs handler."""
        self.logger = logger
    
    def show(
        self,
        component: Optional[str] = None,
        level: Optional[str] = None,
        tail: int = MonitoringDefaults.LOG_TAIL,
        follow: bool = False
    ) -> int:
        """
        Show recent system logs.
        
        Args:
            component: Filter by component
            level: Filter by log level
            tail: Number of recent lines
            follow: Follow log output (not yet implemented)
            
        Returns:
            0 for success, 1 for failure
        """
        try:
            self._print_header(component, level, tail, follow)
            
            if follow:
                print("Following logs (Ctrl+C to stop)...")
                print("Log following not yet implemented in this version")
                return 1
            else:
                return self._display_recent_logs(component, level, tail)
        
        except Exception as e:
            print(f"{MonitoringIcons.ERROR} Failed to get logs: {e}")
            self.logger.error(f"Log display failed: {e}", exc_info=True)
            return 1
    
    def _print_header(
        self,
        component: Optional[str],
        level: Optional[str],
        tail: int,
        follow: bool
    ) -> None:
        """
        Print log display header.
        
        Args:
            component: Component filter
            level: Level filter
            tail: Tail count
            follow: Follow mode
        """
        filters = []
        if component:
            filters.append(f"component: {component}")
        if level:
            filters.append(f"level: {level}")
        
        filter_text = f" ({', '.join(filters)})" if filters else ""
        print(f"\n{MonitoringIcons.LOGS} Recent Logs{filter_text} (tail: {tail}):")
    
    def _display_recent_logs(
        self,
        component: Optional[str],
        level: Optional[str],
        tail: int
    ) -> int:
        """
        Display recent logs.
        
        Args:
            component: Component filter
            level: Level filter
            tail: Number of lines
            
        Returns:
            0 for success
        """
        try:
            from core.system_logger import map_pro_logger
            
            logs = map_pro_logger.get_recent_logs(
                component=component,
                level=level,
                limit=tail
            )
            
            if not logs:
                print("  No logs found")
                return 0
            
            for log_entry in logs:
                self._display_single_log(log_entry)
            
            return 0
        
        except (ImportError, AttributeError):
            print("  Log viewer not available")
            print("  Try checking log files directly:")
            print(f"    {map_pro_paths.logs_system}/system.log")
            print(f"    {map_pro_paths.logs_engines}/*/")
            return 0
    
    def _display_single_log(self, log_entry: dict) -> None:
        """
        Display a single log entry.
        
        Args:
            log_entry: Log entry dictionary
        """
        timestamp = log_entry.get('timestamp', 'Unknown')
        log_level = log_entry.get('level', 'INFO')
        log_component = log_entry.get('component', 'System')
        message = log_entry.get('message', '')
        
        level_icon = {
            'DEBUG': MonitoringIcons.DEBUG,
            'INFO': MonitoringIcons.INFO,
            'WARNING': MonitoringIcons.WARNING,
            'ERROR': MonitoringIcons.ERROR,
            'CRITICAL': MonitoringIcons.CRITICAL
        }.get(log_level, '[LOG]')
        
        print(f"  {level_icon} [{timestamp}] {log_component}: {message}")


__all__ = ['LogsHandler']