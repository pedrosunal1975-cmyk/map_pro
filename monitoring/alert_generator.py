"""
Map Pro Alert Generator
=======================

Generates and sends alerts based on system metrics and thresholds.
Integrates with core.alert_manager for alert coordination.

Save location: tools/monitoring/alert_generator.py
"""

import os
import smtplib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.system_logger import get_logger
from core.alert_manager import alert_manager, create_alert

logger = get_logger(__name__, 'monitoring')


class AlertGenerator:
    """
    Generate and distribute system alerts.
    
    Responsibilities:
    - Monitor alert_manager for new alerts
    - Format alert messages
    - Send notifications via email/Slack
    - Track alert delivery status
    
    Does NOT handle:
    - Alert creation (alert_manager handles this)
    - Metric collection (performance_monitor handles this)
    - Alert threshold configuration (alert_manager handles this)
    """
    
    def __init__(self):
        self.logger = logger
        
        # Load notification configuration from environment
        self.email_enabled = os.getenv('MAP_PRO_ALERT_EMAIL_ENABLED', 'false').lower() == 'true'
        self.slack_enabled = os.getenv('MAP_PRO_ALERT_SLACK_ENABLED', 'false').lower() == 'true'
        
        # Email configuration
        self.smtp_host = os.getenv('MAP_PRO_SMTP_HOST', 'localhost')
        self.smtp_port = int(os.getenv('MAP_PRO_SMTP_PORT', '587'))
        self.smtp_user = os.getenv('MAP_PRO_SMTP_USER', '')
        self.smtp_password = os.getenv('MAP_PRO_SMTP_PASSWORD', '')
        self.alert_email_from = os.getenv('MAP_PRO_ALERT_EMAIL_FROM', 'mappro@example.com')
        self.alert_email_to = os.getenv('MAP_PRO_ALERT_EMAIL_TO', '').split(',')
        
        # Slack configuration
        self.slack_webhook_url = os.getenv('MAP_PRO_SLACK_WEBHOOK_URL', '')
        
        # Alert delivery tracking
        self.delivery_history = []
        self.max_delivery_history = 100
        
        # Alert level filtering
        self.min_email_severity = os.getenv('MAP_PRO_MIN_EMAIL_SEVERITY', 'warning')  # warning or critical
        self.min_slack_severity = os.getenv('MAP_PRO_MIN_SLACK_SEVERITY', 'critical')  # warning or critical
        
        self.logger.info("Alert generator initialized")
        if self.email_enabled:
            self.logger.info(f"Email alerts enabled to: {self.alert_email_to}")
        if self.slack_enabled:
            self.logger.info("Slack alerts enabled")
    
    def process_pending_alerts(self) -> Dict[str, Any]:
        """
        Process all pending alerts from alert_manager.
        
        Returns:
            Dictionary with processing results
        """
        try:
            # Get recent alerts from alert_manager
            alert_summary = alert_manager.get_alert_summary()
            
            if alert_summary.get('recent_alerts', 0) == 0:
                return {
                    'success': True,
                    'alerts_processed': 0,
                    'alerts_sent': 0,
                    'errors': []
                }
            
            # Process alerts
            processed_count = 0
            sent_count = 0
            errors = []
            
            # Get recent critical and warning alerts
            recent_alerts = alert_manager.alert_history[-10:]  # Process last 10 alerts
            
            for alert in recent_alerts:
                try:
                    processed_count += 1
                    
                    # Send alert based on severity
                    if self._should_send_alert(alert):
                        success = self._send_alert(alert)
                        if success:
                            sent_count += 1
                        else:
                            errors.append(f"Failed to send alert: {alert.get('alert_id')}")
                
                except Exception as e:
                    errors.append(f"Error processing alert: {e}")
                    self.logger.error(f"Error processing alert: {e}")
            
            return {
                'success': len(errors) == 0,
                'alerts_processed': processed_count,
                'alerts_sent': sent_count,
                'errors': errors
            }
        
        except Exception as e:
            self.logger.error(f"Failed to process pending alerts: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_test_alert(self, alert_type: str = 'email') -> bool:
        """
        Send a test alert to verify configuration.
        
        Args:
            alert_type: Type of alert to test ('email' or 'slack')
        
        Returns:
            True if test alert sent successfully
        """
        test_alert = {
            'type': 'test_alert',
            'severity': 'info',
            'message': 'Test alert from Map Pro monitoring system',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'alert_id': 'test_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'metadata': {
                'test': True,
                'component': 'alert_generator'
            }
        }
        
        try:
            if alert_type == 'email':
                return self._send_email_alert(test_alert)
            elif alert_type == 'slack':
                return self._send_slack_alert(test_alert)
            else:
                self.logger.error(f"Unknown alert type: {alert_type}")
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to send test alert: {e}")
            return False
    
    def _should_send_alert(self, alert: Dict[str, Any]) -> bool:
        """Determine if alert should be sent based on severity."""
        severity = alert.get('severity', 'warning')
        
        # Check if alert meets minimum severity thresholds
        if self.email_enabled:
            if severity == 'critical' or (severity == 'warning' and self.min_email_severity == 'warning'):
                return True
        
        if self.slack_enabled:
            if severity == 'critical' or (severity == 'warning' and self.min_slack_severity == 'warning'):
                return True
        
        return False
    
    def _send_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Send alert through configured channels.
        
        Args:
            alert: Alert dictionary
        
        Returns:
            True if alert sent successfully through at least one channel
        """
        success = False
        
        try:
            # Send email if enabled
            if self.email_enabled:
                email_sent = self._send_email_alert(alert)
                if email_sent:
                    success = True
                    self.logger.info(f"Email alert sent: {alert.get('alert_id')}")
            
            # Send Slack if enabled
            if self.slack_enabled:
                slack_sent = self._send_slack_alert(alert)
                if slack_sent:
                    success = True
                    self.logger.info(f"Slack alert sent: {alert.get('alert_id')}")
            
            # Track delivery
            self._track_delivery(alert, success)
            
            return success
        
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            return False
    
    def _send_email_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via email."""
        if not self.email_enabled or not self.alert_email_to:
            return False
        
        try:
            # Format email
            subject = self._format_email_subject(alert)
            body = self._format_email_body(alert)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.alert_email_from
            msg['To'] = ', '.join(self.alert_email_to)
            
            # Add plain text and HTML versions
            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(self._format_email_html(alert), 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _send_slack_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via Slack webhook."""
        if not self.slack_enabled or not self.slack_webhook_url:
            return False
        
        try:
            import requests
            
            # Format Slack message
            slack_message = self._format_slack_message(alert)
            
            # Send to Slack
            response = requests.post(
                self.slack_webhook_url,
                json=slack_message,
                timeout=10
            )
            
            return response.status_code == 200
        
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def _format_email_subject(self, alert: Dict[str, Any]) -> str:
        """Format email subject line."""
        severity = alert.get('severity', 'info').upper()
        alert_type = alert.get('type', 'alert')
        
        emoji = '🚨' if severity == 'CRITICAL' else '[WARNING]' if severity == 'WARNING' else '[INFO]️'
        
        return f"{emoji} Map Pro {severity}: {alert_type}"
    
    def _format_email_body(self, alert: Dict[str, Any]) -> str:
        """Format plain text email body."""
        severity = alert.get('severity', 'info').upper()
        message = alert.get('message', 'No message provided')
        timestamp = alert.get('timestamp', 'Unknown')
        alert_id = alert.get('alert_id', 'Unknown')
        metadata = alert.get('metadata', {})
        
        body = f"""
Map Pro System Alert
{'=' * 50}

Severity: {severity}
Time: {timestamp}
Alert ID: {alert_id}

Message:
{message}

"""
        
        if metadata:
            body += "\nAdditional Information:\n"
            for key, value in metadata.items():
                body += f"  {key}: {value}\n"
        
        body += f"\n{'=' * 50}\n"
        body += "This is an automated alert from Map Pro monitoring system.\n"
        
        return body
    
    def _format_email_html(self, alert: Dict[str, Any]) -> str:
        """Format HTML email body."""
        severity = alert.get('severity', 'info').upper()
        message = alert.get('message', 'No message provided')
        timestamp = alert.get('timestamp', 'Unknown')
        alert_id = alert.get('alert_id', 'Unknown')
        
        severity_color = {
            'CRITICAL': '#dc3545',
            'WARNING': '#ffc107',
            'INFO': '#17a2b8'
        }.get(severity, '#6c757d')
        
        html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {severity_color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 5px 5px; }}
        .message {{ background-color: white; padding: 15px; border-left: 4px solid {severity_color}; margin: 15px 0; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 0.9em; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Map Pro System Alert - {severity}</h2>
        </div>
        <div class="content">
            <p><strong>Time:</strong> {timestamp}</p>
            <p><strong>Alert ID:</strong> {alert_id}</p>
            <div class="message">
                <strong>Message:</strong><br/>
                {message}
            </div>
        </div>
        <div class="footer">
            <p>This is an automated alert from Map Pro monitoring system.</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _format_slack_message(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Format Slack message payload."""
        severity = alert.get('severity', 'info')
        message = alert.get('message', 'No message provided')
        timestamp = alert.get('timestamp', 'Unknown')
        
        color = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'good'
        }.get(severity, '#808080')
        
        emoji = {
            'critical': ':rotating_light:',
            'warning': ':warning:',
            'info': ':information_source:'
        }.get(severity, ':bell:')
        
        return {
            'text': f"{emoji} Map Pro Alert - {severity.upper()}",
            'attachments': [
                {
                    'color': color,
                    'fields': [
                        {
                            'title': 'Message',
                            'value': message,
                            'short': False
                        },
                        {
                            'title': 'Time',
                            'value': timestamp,
                            'short': True
                        },
                        {
                            'title': 'Severity',
                            'value': severity.upper(),
                            'short': True
                        }
                    ],
                    'footer': 'Map Pro Monitoring',
                    'ts': int(datetime.now(timezone.utc).timestamp())
                }
            ]
        }
    
    def _track_delivery(self, alert: Dict[str, Any], success: bool):
        """Track alert delivery status."""
        delivery_record = {
            'alert_id': alert.get('alert_id'),
            'severity': alert.get('severity'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': success,
            'channels': []
        }
        
        if self.email_enabled:
            delivery_record['channels'].append('email')
        if self.slack_enabled:
            delivery_record['channels'].append('slack')
        
        self.delivery_history.append(delivery_record)
        
        # Maintain history size limit
        if len(self.delivery_history) > self.max_delivery_history:
            self.delivery_history.pop(0)
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get alert delivery statistics."""
        if not self.delivery_history:
            return {
                'total_alerts': 0,
                'successful_deliveries': 0,
                'failed_deliveries': 0,
                'success_rate': 0.0
            }
        
        total = len(self.delivery_history)
        successful = sum(1 for d in self.delivery_history if d['success'])
        failed = total - successful
        
        return {
            'total_alerts': total,
            'successful_deliveries': successful,
            'failed_deliveries': failed,
            'success_rate': (successful / total) * 100 if total > 0 else 0.0,
            'last_delivery': self.delivery_history[-1]['timestamp'] if self.delivery_history else None
        }


__all__ = ['AlertGenerator']