"""
Map Pro Alert System Components
===============================

Focused components for alert checking, processing, and storage.
Each component has a single, well-defined responsibility.

File: /map_pro/core/alert_components.py
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .data_paths import map_pro_paths
from .system_logger import get_logger, log_alert

logger = get_logger(__name__, 'core')


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Alert:
    """Structured alert data."""
    alert_type: str
    severity: str  # 'warning' or 'critical'
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    alert_id: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'timestamp': self.timestamp,
            'alert_id': self.alert_id,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'metadata': self.metadata
        }


@dataclass
class AlertThresholds:
    """Alert threshold configuration."""
    # Performance thresholds
    job_processing_time_warning: float = 300.0
    job_processing_time_critical: float = 600.0
    queue_size_warning: int = 50
    queue_size_critical: int = 100
    success_rate_warning: float = 0.90
    success_rate_critical: float = 0.80
    database_response_warning: float = 5.0
    database_response_critical: float = 10.0
    
    # System thresholds
    retry_rate_warning: float = 0.10
    retry_rate_critical: float = 0.25
    queue_age_warning: float = 1800.0
    queue_age_critical: float = 3600.0
    
    # Engine-specific thresholds
    engine_failure_rate_warning: float = 0.05
    engine_failure_rate_critical: float = 0.15


# =============================================================================
# CONFIGURATION LOADING
# =============================================================================

class AlertConfigurationLoader:
    """
    Single Responsibility: Load alert configuration from files.
    
    Handles reading configuration files, parsing JSON,
    and providing fallback defaults.
    """
    
    def load_thresholds(self) -> AlertThresholds:
        """
        Load alert thresholds from configuration file.
        
        Returns:
            AlertThresholds with loaded or default values
        """
        default_thresholds = AlertThresholds()
        
        try:
            config_file = self._find_config_file()
            
            if config_file and config_file.exists():
                return self._load_from_file(config_file, default_thresholds)
            else:
                logger.info("No alert threshold config file found, using defaults")
                return default_thresholds
                
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in alert config: {e}, using defaults")
            return default_thresholds
            
        except Exception as e:
            logger.warning(f"Failed to load alert thresholds: {e}, using defaults")
            return default_thresholds
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in standard locations."""
        # Try data partition config location first
        config_file = map_pro_paths.config_system / "system_settings.json"
        
        if config_file.exists():
            return config_file
        
        # Fallback to program root config
        fallback_config = Path(__file__).parent.parent / "config" / "system_settings.json"
        if fallback_config.exists():
            return fallback_config
        
        return None
    
    def _load_from_file(
        self,
        config_file: Path,
        defaults: AlertThresholds
    ) -> AlertThresholds:
        """Load thresholds from configuration file."""
        with open(config_file, 'r') as f:
            config = json.load(f)
            threshold_config = config.get('alert_thresholds', {})
            
            # Update defaults with loaded values
            for key, value in threshold_config.items():
                if hasattr(defaults, key):
                    setattr(defaults, key, value)
            
            logger.info(f"Loaded alert thresholds from {config_file}")
            return defaults


# =============================================================================
# ALERT CHECKING - DATABASE
# =============================================================================

class DatabaseAlertChecker:
    """
    Single Responsibility: Check database metrics for alert conditions.
    
    Evaluates database performance and health metrics against thresholds.
    """
    
    def __init__(self, thresholds: AlertThresholds):
        """
        Initialize checker with thresholds.
        
        Args:
            thresholds: Alert threshold configuration
        """
        self.thresholds = thresholds
    
    def check(self, db_metrics: Dict[str, Any]) -> List[Alert]:
        """
        Check database metrics for alert conditions.
        
        Args:
            db_metrics: Database metrics dictionary
            
        Returns:
            List of alerts generated
        """
        alerts = []
        
        # Check response time
        alerts.extend(self._check_response_time(db_metrics))
        
        # Check database health
        alerts.extend(self._check_health(db_metrics))
        
        return alerts
    
    def _check_response_time(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check database response time."""
        alerts = []
        response_time = metrics.get('response_time', 0)
        
        if response_time > self.thresholds.database_response_critical:
            alerts.append(Alert(
                alert_type='database_performance',
                severity='critical',
                message=f"Database response time {response_time:.2f}s exceeds critical threshold",
                metric_value=response_time,
                threshold=self.thresholds.database_response_critical
            ))
        elif response_time > self.thresholds.database_response_warning:
            alerts.append(Alert(
                alert_type='database_performance',
                severity='warning',
                message=f"Database response time {response_time:.2f}s exceeds warning threshold",
                metric_value=response_time,
                threshold=self.thresholds.database_response_warning
            ))
        
        return alerts
    
    def _check_health(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check database health status."""
        alerts = []
        
        if not metrics.get('databases_healthy', True):
            alerts.append(Alert(
                alert_type='database_health',
                severity='critical',
                message="One or more databases are unhealthy",
                metadata={'health_status': metrics.get('health_status', {})}
            ))
        
        return alerts


# =============================================================================
# ALERT CHECKING - QUEUE
# =============================================================================

class QueueAlertChecker:
    """
    Single Responsibility: Check queue metrics for alert conditions.
    
    Evaluates queue size and age metrics against thresholds.
    """
    
    def __init__(self, thresholds: AlertThresholds):
        """
        Initialize checker with thresholds.
        
        Args:
            thresholds: Alert threshold configuration
        """
        self.thresholds = thresholds
    
    def check(self, queue_metrics: Dict[str, Any]) -> List[Alert]:
        """
        Check queue metrics for alert conditions.
        
        Args:
            queue_metrics: Queue metrics dictionary
            
        Returns:
            List of alerts generated
        """
        alerts = []
        
        # Check queue size
        alerts.extend(self._check_queue_size(queue_metrics))
        
        # Check queue age
        alerts.extend(self._check_queue_age(queue_metrics))
        
        return alerts
    
    def _check_queue_size(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check active job count."""
        alerts = []
        active_jobs = metrics.get('active_jobs', 0)
        
        if active_jobs > self.thresholds.queue_size_critical:
            alerts.append(Alert(
                alert_type='queue_size',
                severity='critical',
                message=f"Active job count {active_jobs} exceeds critical threshold",
                metric_value=float(active_jobs),
                threshold=float(self.thresholds.queue_size_critical)
            ))
        elif active_jobs > self.thresholds.queue_size_warning:
            alerts.append(Alert(
                alert_type='queue_size',
                severity='warning',
                message=f"Active job count {active_jobs} exceeds warning threshold",
                metric_value=float(active_jobs),
                threshold=float(self.thresholds.queue_size_warning)
            ))
        
        return alerts
    
    def _check_queue_age(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check oldest queued job age."""
        alerts = []
        oldest_job_age = metrics.get('oldest_queued_job_age', 0)
        
        if oldest_job_age > self.thresholds.queue_age_critical:
            alerts.append(Alert(
                alert_type='queue_age',
                severity='critical',
                message=f"Oldest queued job age {oldest_job_age/60:.1f} minutes exceeds critical threshold",
                metric_value=oldest_job_age,
                threshold=self.thresholds.queue_age_critical
            ))
        elif oldest_job_age > self.thresholds.queue_age_warning:
            alerts.append(Alert(
                alert_type='queue_age',
                severity='warning',
                message=f"Oldest queued job age {oldest_job_age/60:.1f} minutes exceeds warning threshold",
                metric_value=oldest_job_age,
                threshold=self.thresholds.queue_age_warning
            ))
        
        return alerts


# =============================================================================
# ALERT CHECKING - PROCESSING
# =============================================================================

class ProcessingAlertChecker:
    """
    Single Responsibility: Check processing metrics for alert conditions.
    
    Evaluates success rates and retry rates against thresholds.
    """
    
    def __init__(self, thresholds: AlertThresholds):
        """
        Initialize checker with thresholds.
        
        Args:
            thresholds: Alert threshold configuration
        """
        self.thresholds = thresholds
    
    def check(self, processing_metrics: Dict[str, Any]) -> List[Alert]:
        """
        Check processing metrics for alert conditions.
        
        Args:
            processing_metrics: Processing metrics dictionary
            
        Returns:
            List of alerts generated
        """
        alerts = []
        
        # Check success rate
        alerts.extend(self._check_success_rate(processing_metrics))
        
        # Check retry rate
        alerts.extend(self._check_retry_rate(processing_metrics))
        
        return alerts
    
    def _check_success_rate(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check job success rate."""
        alerts = []
        success_rate = metrics.get('success_rate_24h', 1.0)
        
        if success_rate < self.thresholds.success_rate_critical:
            alerts.append(Alert(
                alert_type='success_rate',
                severity='critical',
                message=f"24h success rate {success_rate:.1%} below critical threshold",
                metric_value=success_rate,
                threshold=self.thresholds.success_rate_critical
            ))
        elif success_rate < self.thresholds.success_rate_warning:
            alerts.append(Alert(
                alert_type='success_rate',
                severity='warning',
                message=f"24h success rate {success_rate:.1%} below warning threshold",
                metric_value=success_rate,
                threshold=self.thresholds.success_rate_warning
            ))
        
        return alerts
    
    def _check_retry_rate(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check job retry rate."""
        alerts = []
        total_jobs = metrics.get('total_jobs_24h', 0)
        total_retries = metrics.get('total_retries_24h', 0)
        
        if total_jobs > 0:
            retry_rate = total_retries / total_jobs
            
            if retry_rate > self.thresholds.retry_rate_critical:
                alerts.append(Alert(
                    alert_type='retry_rate',
                    severity='critical',
                    message=f"24h retry rate {retry_rate:.1%} exceeds critical threshold",
                    metric_value=retry_rate,
                    threshold=self.thresholds.retry_rate_critical
                ))
            elif retry_rate > self.thresholds.retry_rate_warning:
                alerts.append(Alert(
                    alert_type='retry_rate',
                    severity='warning',
                    message=f"24h retry rate {retry_rate:.1%} exceeds warning threshold",
                    metric_value=retry_rate,
                    threshold=self.thresholds.retry_rate_warning
                ))
        
        return alerts


# =============================================================================
# ALERT HISTORY MANAGEMENT
# =============================================================================

class AlertHistory:
    """
    Single Responsibility: Manage alert history storage.
    
    Maintains a bounded history of alerts with automatic trimming.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize alert history.
        
        Args:
            max_history: Maximum number of alerts to retain
        """
        self.alerts: List[Dict[str, Any]] = []
        self.max_history = max_history
    
    def add(self, alert: Alert) -> None:
        """
        Add alert to history.
        
        Args:
            alert: Alert to add
        """
        # Generate unique ID
        alert.alert_id = f"alert_{len(self.alerts)}"
        
        # Add to history
        self.alerts.append(alert.to_dict())
        
        # Trim if needed
        if len(self.alerts) > self.max_history:
            self.alerts = self.alerts[-self.max_history:]
    
    def get_recent(self, count: int = 50) -> List[Dict[str, Any]]:
        """
        Get most recent alerts.
        
        Args:
            count: Number of alerts to retrieve
            
        Returns:
            List of recent alerts
        """
        return self.alerts[-count:]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of alert history.
        
        Returns:
            Summary dictionary with counts and statistics
        """
        recent_alerts = self.get_recent(50)
        
        critical_count = sum(
            1 for alert in recent_alerts 
            if alert['severity'] == 'critical'
        )
        warning_count = sum(
            1 for alert in recent_alerts 
            if alert['severity'] == 'warning'
        )
        
        return {
            'total_alerts': len(self.alerts),
            'recent_alerts': len(recent_alerts),
            'recent_critical': critical_count,
            'recent_warnings': warning_count,
            'last_alert_time': recent_alerts[-1]['timestamp'] if recent_alerts else None
        }


# =============================================================================
# ALERT PROCESSING
# =============================================================================

class AlertProcessor:
    """
    Single Responsibility: Process and log alerts.
    
    Handles alert logging based on severity and stores in history.
    """
    
    def __init__(self, history: AlertHistory):
        """
        Initialize processor with history storage.
        
        Args:
            history: AlertHistory instance for storage
        """
        self.history = history
    
    def process(self, alert: Alert) -> None:
        """
        Process alert by logging and storing.
        
        Args:
            alert: Alert to process
        """
        try:
            # Log based on severity
            if alert.severity == 'critical':
                logger.error(f"CRITICAL ALERT: {alert.message}")
                log_alert(alert.alert_type.upper(), alert.message, "alert_manager")
            else:
                logger.warning(f"WARNING ALERT: {alert.message}")
            
            # Store in history
            self.history.add(alert)
            
        except Exception as e:
            logger.error(f"Failed to process alert: {e}")


__all__ = [
    'Alert',
    'AlertThresholds',
    'AlertConfigurationLoader',
    'DatabaseAlertChecker',
    'QueueAlertChecker',
    'ProcessingAlertChecker',
    'AlertHistory',
    'AlertProcessor'
]