"""
Constants for Monitoring Commands.

Centralized constants used across all monitoring modules.

Location: tools/cli/monitoring_constants.py
"""


class MonitoringIcons:
    """Display icons for monitoring output."""
    
    # Status icons
    RUNNING = "[OK]"
    STOPPED = "[FAIL]"
    UNKNOWN = "[?]"
    
    # Health icons
    HEALTHY = "[OK]"
    WARNING = "[WARN]"
    ERROR = "[ERR]"
    
    # Severity icons
    ALERT = "[ALERT]"
    CRITICAL = "[CRIT]"
    INFO = "[INFO]"
    DEBUG = "[DBG]"
    VALIDATION = "[CHECK]"
    
    # Additional status
    PROC = "[PROC]"
    NET = "[NET]"
    RES = "[RES]"
    PERF = "[PERF]"
    STATUS = "[STATUS]"
    LOGS = "[LOGS]"
    CLEANUP = "[CLEANUP]"


class ResourceThresholds:
    """Thresholds for resource usage monitoring."""
    
    # CPU thresholds (percentage)
    CPU_WARNING = 70
    CPU_CRITICAL = 90
    
    # Memory thresholds (percentage)
    MEMORY_WARNING = 70
    MEMORY_CRITICAL = 90
    
    # Disk thresholds (percentage)
    DISK_WARNING = 80
    DISK_CRITICAL = 95


class MonitoringDefaults:
    """Default values for monitoring operations."""
    
    # Limits
    ALERT_LIMIT = 50
    LOG_TAIL = 50
    
    # Display
    SEPARATOR_LENGTH = 60
    
    # Time periods
    DEFAULT_PERIOD = '1h'


__all__ = [
    'MonitoringIcons',
    'ResourceThresholds',
    'MonitoringDefaults'
]