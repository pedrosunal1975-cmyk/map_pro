"""
Map Pro Alert Manager - Refactored
==================================

Central alert coordination for all Map Pro system alerts.
Delegates specialized responsibilities to focused components.

File: /map_pro/core/alert_manager.py

Architecture: Orchestrator pattern - coordinates specialized components
"""

from typing import Dict, Any

from .system_logger import get_logger
from .alert_components import (
    Alert,
    AlertConfigurationLoader,
    DatabaseAlertChecker,
    QueueAlertChecker,
    ProcessingAlertChecker,
    AlertHistory,
    AlertProcessor
)

logger = get_logger(__name__, 'core')


class AlertManager:
    """
    Central coordinator for all system alerts across Map Pro.
    
    Single Responsibility: Coordinate alert checking workflow.
    
    Delegates specialized tasks to focused components:
    - Configuration loading → AlertConfigurationLoader
    - Database checks → DatabaseAlertChecker
    - Queue checks → QueueAlertChecker
    - Processing checks → ProcessingAlertChecker
    - Alert processing → AlertProcessor
    - History management → AlertHistory
    
    Does NOT handle:
    - Metrics collection (performance_monitor handles this)
    - Specific alert delivery mechanisms (engines handle notifications)
    - Direct threshold checking (checker components handle this)
    """
    
    def __init__(self):
        """Initialize alert manager with specialized components."""
        # Load configuration
        config_loader = AlertConfigurationLoader()
        self.thresholds = config_loader.load_thresholds()
        
        # Initialize checkers with thresholds
        self.database_checker = DatabaseAlertChecker(self.thresholds)
        self.queue_checker = QueueAlertChecker(self.thresholds)
        self.processing_checker = ProcessingAlertChecker(self.thresholds)
        
        # Initialize history and processor
        self.history = AlertHistory(max_history=1000)
        self.processor = AlertProcessor(self.history)
        
        logger.info("Alert manager initialized")
    
    def check_performance_thresholds(self, metrics: Dict[str, Dict[str, Any]]) -> None:
        """
        Check performance metrics against thresholds and generate alerts.
        
        Coordinates checking across all metric categories and processes
        any alerts generated.
        
        Args:
            metrics: Dictionary of metrics organized by category:
                - 'database': Database performance metrics
                - 'queue': Queue metrics
                - 'processing': Processing metrics
        """
        try:
            # Collect alerts from all checkers
            alerts = []
            
            if 'database' in metrics:
                alerts.extend(self.database_checker.check(metrics['database']))
            
            if 'queue' in metrics:
                alerts.extend(self.queue_checker.check(metrics['queue']))
            
            if 'processing' in metrics:
                alerts.extend(self.processing_checker.check(metrics['processing']))
            
            # Process all alerts
            for alert in alerts:
                self.processor.process(alert)
                
        except Exception as e:
            logger.error(f"Failed to check performance thresholds: {e}")
    
    def create_system_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = 'warning',
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Create a system alert manually.
        
        Args:
            alert_type: Type of alert (e.g., 'partition_violation', 'configuration_error')
            message: Alert message
            severity: 'warning' or 'critical'
            metadata: Additional alert metadata
        """
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata or {}
        )
        
        self.processor.process(alert)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get summary of recent alerts.
        
        Returns:
            Dictionary with alert statistics and recent alert info
        """
        try:
            return self.history.get_summary()
        except Exception as e:
            logger.error(f"Failed to get alert summary: {e}")
            return {'error': str(e)}
    
    @property
    def alert_history(self) -> list:
        """
        Get alert history list (backward compatibility).
        
        Returns:
            List of all alerts in history
        """
        return self.history.alerts
    
    @property
    def alert_thresholds(self) -> Dict[str, Any]:
        """
        Get alert thresholds as dictionary (backward compatibility).
        
        Returns:
            Dictionary of threshold values
        """
        return {
            'job_processing_time_warning': self.thresholds.job_processing_time_warning,
            'job_processing_time_critical': self.thresholds.job_processing_time_critical,
            'queue_size_warning': self.thresholds.queue_size_warning,
            'queue_size_critical': self.thresholds.queue_size_critical,
            'success_rate_warning': self.thresholds.success_rate_warning,
            'success_rate_critical': self.thresholds.success_rate_critical,
            'database_response_warning': self.thresholds.database_response_warning,
            'database_response_critical': self.thresholds.database_response_critical,
            'retry_rate_warning': self.thresholds.retry_rate_warning,
            'retry_rate_critical': self.thresholds.retry_rate_critical,
            'queue_age_warning': self.thresholds.queue_age_warning,
            'queue_age_critical': self.thresholds.queue_age_critical,
            'engine_failure_rate_warning': self.thresholds.engine_failure_rate_warning,
            'engine_failure_rate_critical': self.thresholds.engine_failure_rate_critical
        }


# =============================================================================
# GLOBAL INSTANCE & CONVENIENCE FUNCTIONS
# =============================================================================

# Global alert manager instance
alert_manager = AlertManager()


def create_alert(
    alert_type: str,
    message: str,
    severity: str = 'warning',
    metadata: Dict[str, Any] = None
) -> None:
    """
    Convenience function to create system alerts.
    
    Args:
        alert_type: Type of alert
        message: Alert message
        severity: Alert severity ('warning' or 'critical')
        metadata: Additional metadata
    """
    alert_manager.create_system_alert(alert_type, message, severity, metadata)


__all__ = ['AlertManager', 'alert_manager', 'create_alert']