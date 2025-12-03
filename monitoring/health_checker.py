"""
Map Pro System Health Checker
=============================

Comprehensive system health monitoring coordinator.
Integrates database, resource, and logging health checks.

Save location: tools/monitoring/health_checker.py
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from .database_health import DatabaseHealthChecker
from .resource_health import ResourceHealthChecker

logger = get_logger(__name__, 'monitoring')


class SystemHealthChecker:
    """
    System-wide health monitoring coordinator.
    
    Responsibilities:
    - Coordinate all health checks
    - Aggregate health status
    - Track health trends
    - Manage health thresholds
    
    Does NOT handle:
    - Specific health check implementations (specialized checkers handle this)
    - Health issue remediation (components handle their own recovery)
    """
    
    def __init__(self):
        self.last_full_check = None
        self.health_history = []
        self.max_history_items = 100
        
        # Initialize specialized health checkers
        self.db_health_checker = DatabaseHealthChecker()
        self.resource_health_checker = ResourceHealthChecker()
        
        # Health thresholds
        self.thresholds = {
            'memory_usage_percent': 85.0,
            'disk_usage_percent': 90.0,
            'cpu_usage_percent': 80.0,
            'database_response_time_ms': 1000.0,
            'log_file_size_mb': 100.0
        }
        
        logger.info("System health checker initialized")
    
    async def perform_health_check(self, startup_mode: bool = False) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.
        
        Args:
            startup_mode: If True, uses relaxed criteria appropriate for system startup.
                         Only critical issues (>95% CPU, >90% memory, >95% disk) are flagged.
                         If False, uses standard production thresholds.
        
        Returns:
            Complete health status dictionary
        """
        logger.debug(f"Starting {'startup' if startup_mode else 'comprehensive'} health check")
        
        health_status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_healthy': True,
            'issues': [],
            'warnings': [],
            'details': {},
            'startup_mode': startup_mode
        }
        
        try:
            # Check database health
            db_health = await self.db_health_checker.check_all_databases()
            health_status['details']['databases'] = db_health
            if not db_health.get('overall_healthy', False):
                health_status['overall_healthy'] = False
                health_status['issues'].extend(db_health.get('issues', []))
            
            # Check file system health
            fs_health = self.resource_health_checker.check_filesystem_health(startup_mode=startup_mode)
            health_status['details']['filesystem'] = fs_health
            if not fs_health.get('overall_healthy', False):
                health_status['overall_healthy'] = False
                health_status['issues'].extend(fs_health.get('issues', []))
            
            # Check system resources with startup awareness
            resource_health = self.resource_health_checker.check_all_resources(startup_mode=startup_mode)
            health_status['details']['resources'] = resource_health
            if not resource_health.get('overall_healthy', False):
                health_status['overall_healthy'] = False
                health_status['issues'].extend(resource_health.get('issues', []))
            
            # Check log system health
            log_health = await self._check_logging_health()
            health_status['details']['logging'] = log_health
            if not log_health.get('overall_healthy', False):
                health_status['warnings'].extend(log_health.get('warnings', []))
            
            # Store in history
            self._update_health_history(health_status)
            self.last_full_check = datetime.now(timezone.utc)
            
            logger.debug("Health check completed")
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_healthy': False,
                'issues': [f"Health check system failure: {e}"],
                'warnings': [],
                'details': {},
                'startup_mode': startup_mode
            }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health status summary."""
        if not self.health_history:
            return {
                'status': 'no_checks_performed',
                'last_check': None,
                'overall_healthy': None
            }
        
        latest_check = self.health_history[-1]
        
        return {
            'status': 'healthy' if latest_check['overall_healthy'] else 'unhealthy',
            'last_check': latest_check['timestamp'],
            'overall_healthy': latest_check['overall_healthy'],
            'active_issues': len(latest_check.get('issues', [])),
            'active_warnings': len(latest_check.get('warnings', [])),
            'check_history_count': len(self.health_history)
        }
    
    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze health trends over specified time period."""
        if not self.health_history:
            return {'status': 'no_data'}
        
        # Filter history by time period
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_checks = [
            check for check in self.health_history
            if datetime.fromisoformat(check['timestamp']) > cutoff_time
        ]
        
        if not recent_checks:
            return {'status': 'no_recent_data'}
        
        # Calculate trends
        total_checks = len(recent_checks)
        healthy_checks = sum(1 for check in recent_checks if check['overall_healthy'])
        unhealthy_checks = total_checks - healthy_checks
        
        # Identify recurring issues
        issue_counts = {}
        for check in recent_checks:
            for issue in check.get('issues', []):
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        return {
            'period_hours': hours,
            'total_checks': total_checks,
            'healthy_percentage': (healthy_checks / total_checks) * 100 if total_checks > 0 else 0,
            'unhealthy_checks': unhealthy_checks,
            'recurring_issues': {
                issue: count for issue, count in issue_counts.items()
                if count > 1
            },
            'trend': 'improving' if recent_checks[-1]['overall_healthy'] else 'degrading'
        }
    
    async def _check_logging_health(self) -> Dict[str, Any]:
        """Check logging system health."""
        log_health = {
            'overall_healthy': True,
            'issues': [],
            'warnings': [],
            'log_files': {}
        }
        
        try:
            log_directory = map_pro_paths.logs_root
            
            if not log_directory.exists():
                log_health['warnings'].append("Log directory does not exist")
                return log_health
            
            # Check log files
            log_files = list(log_directory.glob('*.log'))
            
            for log_file in log_files:
                file_size_mb = log_file.stat().st_size / (1024**2)
                log_health['log_files'][log_file.name] = {
                    'size_mb': round(file_size_mb, 2),
                    'readable': log_file.is_file()
                }
                
                if file_size_mb > self.thresholds['log_file_size_mb']:
                    log_health['warnings'].append(f"Large log file: {log_file.name} ({file_size_mb:.1f}MB)")
            
            return log_health
            
        except Exception as e:
            logger.error(f"Logging health check failed: {e}")
            log_health['overall_healthy'] = False
            log_health['issues'].append(f"Logging check error: {e}")
            return log_health
    
    def _update_health_history(self, health_status: Dict[str, Any]):
        """Update health check history."""
        self.health_history.append(health_status.copy())
        
        # Maintain history size limit
        if len(self.health_history) > self.max_history_items:
            self.health_history.pop(0)
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update health check thresholds."""
        for key, value in new_thresholds.items():
            if key in self.thresholds:
                old_value = self.thresholds[key]
                self.thresholds[key] = value
                logger.info(f"Updated threshold {key}: {old_value} -> {value}")
            else:
                logger.warning(f"Unknown threshold key: {key}")
    
    def get_current_thresholds(self) -> Dict[str, float]:
        """Get current health check thresholds."""
        return self.thresholds.copy()