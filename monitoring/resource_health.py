"""
Map Pro Resource Health Checker
===============================

Monitors system resource usage (CPU, memory, disk) for health monitoring.

Save location: tools/monitoring/resource_health.py
"""

import psutil
import shutil
from typing import Dict, Any
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'monitoring')


class ResourceHealthChecker:
    """
    Monitor system resource health.
    
    Responsibilities:
    - CPU usage monitoring
    - Memory usage monitoring
    - Disk space monitoring
    - System load monitoring
    
    Does NOT handle:
    - Database performance (database_health handles this)
    - Alert generation (alert_generator handles this)
    """
    
    def __init__(self):
        self.logger = logger
        
        # Standard health thresholds (production)
        self.cpu_warning_threshold = 80.0  # %
        self.cpu_critical_threshold = 95.0  # %
        self.memory_warning_threshold = 80.0  # %
        self.memory_critical_threshold = 90.0  # %
        self.disk_warning_threshold = 85.0  # %
        self.disk_critical_threshold = 95.0  # %
        
        self.logger.info("Resource health checker initialized")
    
    def check_all_resources(self, startup_mode: bool = False) -> Dict[str, Any]:
        """
        Check all system resources.
        
        Args:
            startup_mode: If True, only flags critical resource issues (>95% CPU, >90% memory, >95% disk).
                         If False, uses standard warning thresholds (>80% CPU, >80% memory, >85% disk).
        
        Returns:
            Complete resource health status
        """
        try:
            return {
                'cpu': self.check_cpu(startup_mode=startup_mode),
                'memory': self.check_memory(startup_mode=startup_mode),
                'disk': self.check_disk(startup_mode=startup_mode),
                'load': self.check_system_load(),
                'overall_healthy': self._determine_overall_health(startup_mode=startup_mode),
                'timestamp': psutil.time.time()
            }
        
        except Exception as e:
            self.logger.error(f"Failed to check system resources: {e}")
            return {
                'error': str(e),
                'overall_healthy': False
            }
    
    def check_cpu(self, startup_mode: bool = False) -> Dict[str, Any]:
        """
        Check CPU usage.
        
        Args:
            startup_mode: If True, only critical threshold (>95%) marks as unhealthy
        """
        try:
            # Get CPU percentages
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            
            # Determine health status based on mode
            if startup_mode:
                # Startup mode: Only critical threshold matters for health
                if cpu_percent >= self.cpu_critical_threshold:
                    status = 'critical'
                    healthy = False
                elif cpu_percent >= self.cpu_warning_threshold:
                    status = 'warning'
                    healthy = True  # Warning is OK during startup
                else:
                    status = 'healthy'
                    healthy = True
            else:
                # Production mode: Standard behavior
                if cpu_percent >= self.cpu_critical_threshold:
                    status = 'critical'
                    healthy = False
                elif cpu_percent >= self.cpu_warning_threshold:
                    status = 'warning'
                    healthy = False
                else:
                    status = 'healthy'
                    healthy = True
            
            return {
                'healthy': healthy,
                'status': status,
                'usage_percent': cpu_percent,
                'cpu_count_physical': cpu_count,
                'cpu_count_logical': cpu_count_logical,
                'load_1min': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None,
                'load_5min': psutil.getloadavg()[1] if hasattr(psutil, 'getloadavg') else None,
                'load_15min': psutil.getloadavg()[2] if hasattr(psutil, 'getloadavg') else None
            }
        
        except Exception as e:
            self.logger.error(f"Failed to check CPU: {e}")
            return {
                'healthy': False,
                'status': 'error',
                'error': str(e)
            }
    
    def check_memory(self, startup_mode: bool = False) -> Dict[str, Any]:
        """
        Check memory usage.
        
        Args:
            startup_mode: If True, only critical threshold (>90%) marks as unhealthy
        """
        try:
            # Get memory statistics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Determine health status based on mode
            if startup_mode:
                # Startup mode: Only critical threshold matters for health
                if memory.percent >= self.memory_critical_threshold:
                    status = 'critical'
                    healthy = False
                elif memory.percent >= self.memory_warning_threshold:
                    status = 'warning'
                    healthy = True  # Warning is OK during startup
                else:
                    status = 'healthy'
                    healthy = True
            else:
                # Production mode: Standard behavior
                if memory.percent >= self.memory_critical_threshold:
                    status = 'critical'
                    healthy = False
                elif memory.percent >= self.memory_warning_threshold:
                    status = 'warning'
                    healthy = False
                else:
                    status = 'healthy'
                    healthy = True
            
            return {
                'healthy': healthy,
                'status': status,
                'usage_percent': memory.percent,
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'used_gb': memory.used / (1024**3),
                'free_gb': memory.free / (1024**3),
                'swap_usage_percent': swap.percent,
                'swap_total_gb': swap.total / (1024**3),
                'swap_used_gb': swap.used / (1024**3)
            }
        
        except Exception as e:
            self.logger.error(f"Failed to check memory: {e}")
            return {
                'healthy': False,
                'status': 'error',
                'error': str(e)
            }
    
    def check_disk(self, startup_mode: bool = False) -> Dict[str, Any]:
        """
        Check disk space for Map Pro directories.
        
        Args:
            startup_mode: If True, only critical threshold (>95%) marks as unhealthy
        """
        try:
            disk_status = {}
            overall_healthy = True
            worst_status = 'healthy'
            
            # Check key directories
            key_paths = {
                'program_root': map_pro_paths.program_root,
                'data_root': map_pro_paths.data_root,
                'logs_root': map_pro_paths.logs_root
            }
            
            for path_name, path in key_paths.items():
                try:
                    if path.exists():
                        usage = shutil.disk_usage(path)
                        total_gb = usage.total / (1024**3)
                        free_gb = usage.free / (1024**3)
                        used_gb = (usage.total - usage.free) / (1024**3)
                        used_percent = (used_gb / total_gb) * 100
                        
                        # Determine status based on mode
                        if startup_mode:
                            # Startup mode: Only critical threshold matters for health
                            if used_percent >= self.disk_critical_threshold:
                                status = 'critical'
                                healthy = False
                                worst_status = 'critical'
                                overall_healthy = False
                            elif used_percent >= self.disk_warning_threshold:
                                status = 'warning'
                                healthy = True  # Warning is OK during startup
                                if worst_status != 'critical':
                                    worst_status = 'warning'
                            else:
                                status = 'healthy'
                                healthy = True
                        else:
                            # Production mode: Standard behavior
                            if used_percent >= self.disk_critical_threshold:
                                status = 'critical'
                                healthy = False
                                worst_status = 'critical'
                                overall_healthy = False
                            elif used_percent >= self.disk_warning_threshold:
                                status = 'warning'
                                healthy = False
                                if worst_status != 'critical':
                                    worst_status = 'warning'
                                overall_healthy = False
                            else:
                                status = 'healthy'
                                healthy = True
                        
                        disk_status[path_name] = {
                            'healthy': healthy,
                            'status': status,
                            'path': str(path),
                            'usage_percent': used_percent,
                            'total_gb': total_gb,
                            'used_gb': used_gb,
                            'free_gb': free_gb
                        }
                    else:
                        disk_status[path_name] = {
                            'healthy': False,
                            'status': 'error',
                            'error': f"Path does not exist: {path}"
                        }
                        overall_healthy = False
                        worst_status = 'critical'
                
                except Exception as e:
                    disk_status[path_name] = {
                        'healthy': False,
                        'status': 'error',
                        'error': str(e)
                    }
                    overall_healthy = False
                    worst_status = 'critical'
            
            return {
                'healthy': overall_healthy,
                'status': worst_status,
                'paths': disk_status
            }
        
        except Exception as e:
            self.logger.error(f"Failed to check disk space: {e}")
            return {
                'healthy': False,
                'status': 'error',
                'error': str(e)
            }
    
    def check_system_load(self) -> Dict[str, Any]:
        """Check system load and process information."""
        try:
            # Get process information
            process_count = len(psutil.pids())
            
            # Get boot time
            boot_time = psutil.boot_time()
            
            # Get network I/O if available
            try:
                net_io = psutil.net_io_counters()
                network_stats = {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            except Exception as e:
                network_stats = None
            
            # Get disk I/O if available
            try:
                disk_io = psutil.disk_io_counters()
                disk_stats = {
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count,
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes
                }
            except Exception as e:
                disk_stats = None
            
            return {
                'healthy': True,
                'status': 'healthy',
                'process_count': process_count,
                'boot_time': boot_time,
                'uptime_seconds': psutil.time.time() - boot_time,
                'network_io': network_stats,
                'disk_io': disk_stats
            }
        
        except Exception as e:
            self.logger.error(f"Failed to check system load: {e}")
            return {
                'healthy': False,
                'status': 'error',
                'error': str(e)
            }
            
    def check_filesystem_health(self, startup_mode: bool = False) -> Dict[str, Any]:
        """
        Check filesystem health metrics.
        
        Args:
            startup_mode: If True, only critical threshold (>95%) marks as unhealthy
        """
        try:
            import psutil
            disk_usage = psutil.disk_usage('/')
            
            # Determine health based on mode
            if startup_mode:
                # Startup mode: Only critical threshold
                is_healthy = disk_usage.percent < self.disk_critical_threshold
            else:
                # Production mode: Warning threshold
                is_healthy = disk_usage.percent < self.disk_warning_threshold
            
            return {
                'overall_healthy': is_healthy,
                'healthy': is_healthy,
                'disk_percent_used': disk_usage.percent,
                'disk_free_gb': disk_usage.free / (1024**3),
                'disk_total_gb': disk_usage.total / (1024**3),
                'issues': [] if is_healthy else [f"Root filesystem usage at {disk_usage.percent:.1f}%"]
            }
        except Exception as e:
            return {
                'overall_healthy': False,
                'healthy': False,
                'error': str(e),
                'issues': [f"Filesystem check error: {e}"]
            }

    def _determine_overall_health(self, startup_mode: bool = False) -> bool:
        """
        Determine overall resource health.
        
        Args:
            startup_mode: If True, uses relaxed criteria
        """
        try:
            cpu_health = self.check_cpu(startup_mode=startup_mode)
            memory_health = self.check_memory(startup_mode=startup_mode)
            disk_health = self.check_disk(startup_mode=startup_mode)
            
            return (cpu_health.get('healthy', False) and 
                   memory_health.get('healthy', False) and 
                   disk_health.get('healthy', False))
        
        except Exception:
            return False