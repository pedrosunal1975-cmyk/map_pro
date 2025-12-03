# File: engines/base/health_monitor.py
"""
Map Pro Health Monitor
=====================

Handles health monitoring and checks for engines.
Specialized component for engine health assessment and issue detection.

Architecture: Specialized component focused on health monitoring logic.
"""

import time
from typing import Dict, Any, List, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from core.system_logger import get_logger

if TYPE_CHECKING:
    from .engine_base import BaseEngine

logger = get_logger(__name__, 'engine')


class HealthMonitor:
    """
    Handles health monitoring for engines.

    Responsibilities:
    - Comprehensive health checks
    - Issue detection and reporting
    - Health check timing management
    - Stall detection

    Does NOT handle:
    - Status data collection (status_collector handles this)
    - Report generation (status_reporter handles this)
    - Performance metrics (status_collector handles this)
    """

    def __init__(self, engine: 'BaseEngine'):
        """
        Initialize health monitor for specific engine.

        Args:
            engine: The engine instance this monitor belongs to
        """
        self.engine = engine
        self.logger = get_logger(f"engines.{engine.engine_name}.health_monitor", 'engine')

        self.health_check_interval = 300
        self.last_health_check = None
        self.stall_threshold_minutes = 15

        self.consecutive_failed_checks = 0
        self.max_failed_checks = 3

        self.logger.debug(f"Health monitor initialized for {engine.engine_name}")

    def should_perform_health_check(self, current_time: float) -> bool:
        """
        Determine if health check should be performed.

        Args:
            current_time: Current timestamp

        Returns:
            True if health check should be performed
        """
        if self.last_health_check is None:
            return True

        return (current_time - self.last_health_check) >= self.health_check_interval

    def perform_health_check(self, current_time: float):
        """
        Perform comprehensive health check.

        Args:
            current_time: Current timestamp
        """
        try:
            health_issues = self._identify_health_issues()

            if health_issues:
                self.consecutive_failed_checks += 1
                self._handle_health_issues(health_issues)
            else:
                self.consecutive_failed_checks = 0
                self.logger.debug("Health check passed")

            self.last_health_check = current_time

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.consecutive_failed_checks += 1

    def _identify_health_issues(self) -> List[str]:
        """
        Identify current health issues with the engine.

        Returns:
            List of health issue descriptions
        """
        issues = []

        try:
            if not self.engine.is_running:
                issues.append("Engine not running")

            if not self._check_database_connectivity():
                issues.append("Database not accessible")

            if self._is_processing_stalled():
                issues.append("Processing appears stalled")

            thread_issues = self._check_thread_health()
            issues.extend(thread_issues)

            resource_issues = self._check_resource_health()
            issues.extend(resource_issues)

        except Exception as e:
            issues.append(f"Health check error: {str(e)}")

        return issues

    def _check_database_connectivity(self) -> bool:
        """
        Check if database is accessible.

        Returns:
            True if database is accessible
        """
        try:
            with self.engine.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.warning(f"Database connectivity check failed: {e}")
            return False

    def _is_processing_stalled(self) -> bool:
        """
        Check if processing appears to be stalled.

        Returns:
            True if processing appears stalled
        """
        try:
            if not self.engine.last_activity:
                return False

            time_since_activity = datetime.now(timezone.utc) - self.engine.last_activity
            return time_since_activity > timedelta(minutes=self.stall_threshold_minutes)

        except Exception as e:
            self.logger.debug(f"Unable to check stall status: {e}")
            return False

    def _check_thread_health(self) -> List[str]:
        """
        Check for thread-related health issues.

        Returns:
            List of thread health issues
        """
        issues = []

        try:
            if hasattr(self.engine, '_main_thread') and self.engine._main_thread:
                if not self.engine._main_thread.is_alive() and self.engine.is_running:
                    issues.append("Main thread died but engine marked as running")

            import threading
            thread_count = threading.active_count()
            if thread_count > 50:
                issues.append(f"High thread count: {thread_count}")

        except Exception as e:
            issues.append(f"Thread health check error: {str(e)}")

        return issues

    def _check_resource_health(self) -> List[str]:
        """
        Check for resource-related health issues.

        Returns:
            List of resource health issues
        """
        issues = []

        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())

            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            if memory_mb > 1000:
                issues.append(f"High memory usage: {memory_mb:.1f}MB")

            cpu_percent = process.cpu_percent()
            if cpu_percent > 80:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")

            try:
                open_files = len(process.open_files())
                if open_files > 500:
                    issues.append(f"Many open files: {open_files}")
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                self.logger.debug(f"Cannot check open files: {e}")

        except ImportError:
            self.logger.debug("psutil not available, skipping resource checks")
        except Exception as e:
            issues.append(f"Resource health check error: {str(e)}")

        return issues

    def _handle_health_issues(self, health_issues: List[str]):
        """
        Handle identified health issues.

        Args:
            health_issues: List of health issue descriptions
        """
        for issue in health_issues:
            self.logger.warning(f"Health issue detected: {issue}")

        if self.consecutive_failed_checks >= self.max_failed_checks:
            self.logger.error(
                f"Engine {self.engine.engine_name} has failed {self.consecutive_failed_checks} "
                f"consecutive health checks. Issues: {', '.join(health_issues)}"
            )

            self._trigger_health_alerts(health_issues)
        else:
            self.logger.warning(
                f"Health check found issues (attempt {self.consecutive_failed_checks}): "
                f"{', '.join(health_issues)}"
            )

    def _trigger_health_alerts(self, health_issues: List[str]):
        """
        Trigger health alerts for serious issues.

        Args:
            health_issues: List of health issue descriptions
        """
        try:
            from core.alert_manager import create_alert

            alert_message = (
                f"Engine {self.engine.engine_name} has failed multiple health checks. "
                f"Issues: {', '.join(health_issues)}"
            )

            create_alert(
                f"engine_health_{self.engine.engine_name}",
                alert_message,
                'critical'
            )

        except Exception as e:
            self.logger.error(f"Failed to create health alert: {e}")

    def get_monitor_status(self) -> Dict[str, Any]:
        """
        Get status of the health monitor itself.

        Returns:
            Dictionary with monitor status information
        """
        return {
            'health_check_interval': self.health_check_interval,
            'last_health_check': self.last_health_check,
            'consecutive_failed_checks': self.consecutive_failed_checks,
            'max_failed_checks': self.max_failed_checks,
            'stall_threshold_minutes': self.stall_threshold_minutes
        }

    def force_health_check(self) -> Dict[str, Any]:
        """
        Force an immediate health check regardless of timing.

        Returns:
            Health check results
        """
        try:
            current_time = time.time()
            health_issues = self._identify_health_issues()

            result = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'engine_name': self.engine.engine_name,
                'health_status': 'healthy' if not health_issues else 'unhealthy',
                'issues_found': health_issues,
                'consecutive_failed_checks': self.consecutive_failed_checks
            }

            if health_issues:
                self._handle_health_issues(health_issues)
            else:
                self.consecutive_failed_checks = 0

            self.last_health_check = current_time
            self.logger.info("Forced health check completed")

            return result

        except Exception as e:
            self.logger.error(f"Forced health check failed: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'engine_name': self.engine.engine_name,
                'health_status': 'error',
                'error': str(e)
            }