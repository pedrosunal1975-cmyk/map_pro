"""
Alerts Handler for Monitoring Commands.

Handles alert management and display.

Location: tools/cli/monitoring_alerts.py
"""

from typing import Dict, List, Optional

from core.system_logger import get_logger

from .monitoring_constants import MonitoringIcons, MonitoringDefaults


logger = get_logger(__name__, 'maintenance')


class AlertsHandler:
    """
    Handles alert management operations.
    
    Features:
    - Active alert display
    - Alert filtering by severity
    - Alert grouping
    - Limit controls
    
    Example:
        >>> handler = AlertsHandler()
        >>> handler.show(level='critical', limit=20)
    """
    
    def __init__(self):
        """Initialize alerts handler."""
        self.logger = logger
    
    def show(self, level_filter: Optional[str] = None, limit: int = MonitoringDefaults.ALERT_LIMIT) -> int:
        """
        Show active alerts.
        
        Args:
            level_filter: Filter by alert level ('info', 'warning', 'critical')
            limit: Maximum number of alerts to show
            
        Returns:
            0 if no critical alerts, 1 if critical alerts present
        """
        try:
            print(f"\n{MonitoringIcons.ALERT} Active Alerts (limit: {limit}):")
            
            try:
                from core.alert_manager import alert_manager
                alerts = alert_manager.get_active_alerts(
                    level_filter=level_filter,
                    limit=limit
                )
                
                if not alerts:
                    print("  No active alerts")
                    return 0
                
                return self._display_grouped_alerts(alerts)
            
            except ImportError:
                print("  Alert manager not available")
                return 0
        
        except Exception as e:
            print(f"{MonitoringIcons.ERROR} Failed to get alerts: {e}")
            self.logger.error(f"Alert display failed: {e}", exc_info=True)
            return 1
    
    def _display_grouped_alerts(self, alerts: list) -> int:
        """
        Display alerts grouped by severity.
        
        Args:
            alerts: List of alert dictionaries
            
        Returns:
            0 if no critical alerts, 1 if critical alerts present
        """
        by_severity = self._group_alerts_by_severity(alerts)
        
        severity_order = ['critical', 'warning', 'info']
        severity_icons = {
            'critical': MonitoringIcons.CRITICAL,
            'warning': MonitoringIcons.WARNING,
            'info': MonitoringIcons.INFO
        }
        
        for severity in severity_order:
            if severity in by_severity:
                alerts_for_severity = by_severity[severity]
                icon = severity_icons.get(severity, '[?]')
                
                print(f"\n  {icon} {severity.upper()} ({len(alerts_for_severity)}):")
                
                for alert in alerts_for_severity:
                    self._display_single_alert(alert)
        
        return 1 if 'critical' in by_severity else 0
    
    def _display_single_alert(self, alert: Dict) -> None:
        """
        Display a single alert.
        
        Args:
            alert: Alert dictionary
        """
        timestamp = alert.get('timestamp', 'Unknown')
        component = alert.get('component', 'Unknown')
        message = alert.get('message', 'No message')
        
        print(f"    [{timestamp}] {component}: {message}")
    
    def _group_alerts_by_severity(self, alerts: list) -> Dict[str, list]:
        """
        Group alerts by severity level.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Dictionary mapping severity to alert lists
        """
        by_severity = {}
        for alert in alerts:
            severity = alert.get('severity', 'unknown')
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(alert)
        return by_severity


__all__ = ['AlertsHandler']