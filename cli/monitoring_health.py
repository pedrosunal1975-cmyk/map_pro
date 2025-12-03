"""
Health Check Handler for Monitoring Commands.

Handles comprehensive system health checks with component-specific diagnostics.

Location: tools/cli/monitoring_health.py
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
import psutil

from .monitoring_constants import MonitoringIcons, ResourceThresholds


logger = get_logger(__name__, 'maintenance')


class HealthCheckHandler:
    """
    Handles system health check operations.
    
    Performs comprehensive health checks including:
    - Database connectivity
    - Resource usage
    - Component status
    - System integrity
    
    Example:
        >>> handler = HealthCheckHandler()
        >>> exit_code = handler.run(component='database', verbose=True)
    """
    
    def __init__(self):
        """Initialize health check handler."""
        self.logger = logger
        self.health_checker = None
    
    def run(self, component: Optional[str] = None, verbose: bool = False) -> int:
        """
        Run comprehensive health check.
        
        Args:
            component: Specific component to check
            verbose: Show detailed output
            
        Returns:
            0 if healthy, 1 if issues found
        """
        try:
            print(f"{MonitoringIcons.VALIDATION} Running system health check...")
            
            # Get health result
            health_result = self._get_health_result(component)
            
            # Display results
            return self._display_results(health_result, verbose)
        
        except Exception as e:
            print(f"{MonitoringIcons.ERROR} Health check failed: {e}")
            self.logger.error(f"Health check failed: {e}", exc_info=True)
            return 1
    
    def _get_health_result(self, component: Optional[str]) -> Dict[str, Any]:
        """
        Get health check result.
        
        Args:
            component: Component to check
            
        Returns:
            Health result dictionary
        """
        health_checker = self._get_health_checker()
        
        if component:
            print(f"Focusing on component: {component}")
            if health_checker:
                return health_checker.check_component_health(component)
            else:
                return self._basic_health_check(component)
        else:
            if health_checker:
                return health_checker.perform_health_check()
            else:
                return self._basic_health_check()
    
    def _get_health_checker(self):
        """Lazy initialization of health checker."""
        if self.health_checker is None:
            try:
                from tools.monitoring.health_checker import SystemHealthChecker
                self.health_checker = SystemHealthChecker()
            except ImportError:
                self.logger.warning(
                    "SystemHealthChecker not available, using basic health checks"
                )
                self.health_checker = None
        return self.health_checker
    
    def _basic_health_check(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Basic health check when SystemHealthChecker is not available.
        
        Args:
            component: Component to check
            
        Returns:
            Health result dictionary
        """
        try:
            issues = []
            
            # Check database connections
            db_issues = self._check_database_connections()
            issues.extend(db_issues)
            
            # Check basic system resources
            resource_issues = self._check_basic_resources()
            issues.extend(resource_issues)
            
            return self._build_health_result(issues)
        
        except Exception as e:
            return self._build_error_health_result(e)
    
    def _check_database_connections(self) -> list:
        """
        Check database connections.
        
        Returns:
            List of database issues
        """
        db_issues = []
        databases = ['core', 'parsed', 'library', 'mapped']
        
        for db_name in databases:
            try:
                with db_coordinator.get_connection(db_name) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
            except Exception as e:
                db_issues.append(f"Database {db_name}: {str(e)}")
        
        return db_issues
    
    def _check_basic_resources(self) -> list:
        """
        Check basic system resources.
        
        Returns:
            List of resource issues
        """
        resource_issues = []
        
        try:
            # Memory check
            memory = psutil.virtual_memory()
            if memory.percent > ResourceThresholds.MEMORY_CRITICAL:
                resource_issues.append(f"High memory usage: {memory.percent:.1f}%")
            
            # Disk check
            disk = psutil.disk_usage('/')
            if disk.percent > ResourceThresholds.DISK_CRITICAL:
                resource_issues.append(f"High disk usage: {disk.percent:.1f}%")
        
        except ImportError:
            resource_issues.append("psutil not available for resource monitoring")
        
        return resource_issues
    
    def _build_health_result(self, issues: list) -> Dict[str, Any]:
        """Build health result dictionary from issues list."""
        return {
            'overall_health': 'healthy' if not issues else 'warning',
            'components': {
                'basic_check': {
                    'status': 'healthy' if not issues else 'warning',
                    'issues': issues
                }
            },
            'critical_issues': [i for i in issues if 'critical' in i.lower()],
            'warnings': [i for i in issues if 'critical' not in i.lower()]
        }
    
    def _build_error_health_result(self, error: Exception) -> Dict[str, Any]:
        """Build error health result dictionary."""
        return {
            'overall_health': 'error',
            'components': {
                'basic_check': {
                    'status': 'error',
                    'issues': [str(error)]
                }
            },
            'critical_issues': [str(error)],
            'warnings': []
        }
    
    def _display_results(self, health_result: Dict[str, Any], verbose: bool) -> int:
        """
        Display health check results.
        
        Args:
            health_result: Health check results
            verbose: Show detailed output
            
        Returns:
            0 if healthy, 1 if issues found
        """
        overall_health = health_result.get('overall_health', 'unknown')
        
        # Display overall health
        self._display_overall_health(overall_health)
        
        # Display component status
        self._display_component_status(health_result, verbose)
        
        # Display critical issues
        self._display_critical_issues(health_result)
        
        # Display warnings if verbose
        if verbose:
            self._display_warnings(health_result)
        
        return 0 if overall_health == 'healthy' else 1
    
    def _display_overall_health(self, overall_health: str) -> None:
        """Display overall health status."""
        health_icon = self._get_health_icon(overall_health)
        print(f"\n{health_icon} Overall Health: {overall_health.upper()}")
    
    def _get_health_icon(self, health_status: str) -> str:
        """Get icon for health status."""
        if health_status == 'healthy':
            return MonitoringIcons.HEALTHY
        elif health_status == 'warning':
            return MonitoringIcons.WARNING
        else:
            return MonitoringIcons.ERROR
    
    def _display_component_status(
        self,
        health_result: Dict[str, Any],
        verbose: bool
    ) -> None:
        """Display component status."""
        components = health_result.get('components', {})
        for comp_name, comp_status in components.items():
            status = comp_status.get('status', 'unknown')
            status_icon = self._get_health_icon(status)
            
            print(f"  {status_icon} {comp_name}: {status}")
            
            if verbose or status != 'healthy':
                issues = comp_status.get('issues', [])
                for issue in issues:
                    print(f"    - {issue}")
    
    def _display_critical_issues(self, health_result: Dict[str, Any]) -> None:
        """Display critical issues."""
        critical_issues = health_result.get('critical_issues', [])
        if critical_issues:
            print(f"\n{MonitoringIcons.CRITICAL} Critical Issues ({len(critical_issues)}):")
            for issue in critical_issues:
                print(f"  - {issue}")
    
    def _display_warnings(self, health_result: Dict[str, Any]) -> None:
        """Display warnings."""
        warnings = health_result.get('warnings', [])
        if warnings:
            print(f"\n{MonitoringIcons.WARNING} Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")


__all__ = ['HealthCheckHandler']