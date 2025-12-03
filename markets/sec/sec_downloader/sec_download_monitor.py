"""
SEC Download Monitor
===================

Monitors SEC-specific download metrics and performance.
Tracks rate limit compliance, ZIP identification success, and SEC-specific errors.

Save location: markets/sec/sec_downloader/sec_download_monitor.py
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


@dataclass
class SECDownloadMetrics:
    """Metrics for SEC download operations."""
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    
    # ZIP identification
    index_based_success: int = 0
    pattern_based_success: int = 0
    fallback_used: int = 0
    zip_identification_failures: int = 0
    
    # Rate limiting
    rate_limit_waits: int = 0
    total_wait_time: float = 0.0
    
    # SEC-specific errors
    user_agent_errors: int = 0
    rate_limit_exceeded_errors: int = 0
    forbidden_errors: int = 0
    not_found_errors: int = 0
    
    # Timing
    total_download_time: float = 0.0
    average_download_time: float = 0.0
    
    # Data volume
    total_bytes_downloaded: int = 0
    average_file_size_mb: float = 0.0
    
    def calculate_rates(self):
        """Calculate derived metrics."""
        if self.total_downloads > 0:
            self.average_download_time = self.total_download_time / self.total_downloads
            self.average_file_size_mb = (self.total_bytes_downloaded / self.total_downloads) / (1024 * 1024)
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_downloads == 0:
            return 0.0
        return (self.successful_downloads / self.total_downloads) * 100
    
    def get_zip_identification_rate(self) -> float:
        """Calculate ZIP identification success rate."""
        total_attempts = (
            self.index_based_success + 
            self.pattern_based_success + 
            self.fallback_used + 
            self.zip_identification_failures
        )
        if total_attempts == 0:
            return 0.0
        successes = self.index_based_success + self.pattern_based_success + self.fallback_used
        return (successes / total_attempts) * 100


class SECDownloadMonitor:
    """
    Monitors SEC download operations and collects metrics.
    
    Tracks:
    - Download success/failure rates
    - ZIP identification strategy effectiveness
    - Rate limit compliance
    - SEC-specific error patterns
    - Performance metrics
    """
    
    def __init__(self, metrics_window_minutes: int = 60):
        """
        Initialize monitor.
        
        Args:
            metrics_window_minutes: Time window for recent metrics
        """
        self.metrics_window = timedelta(minutes=metrics_window_minutes)
        
        # Overall metrics
        self.overall_metrics = SECDownloadMetrics()
        
        # Recent events for windowed metrics
        self.recent_events = deque(maxlen=1000)
        
        # Error tracking
        self.error_details = defaultdict(list)
        
        # Performance tracking
        self.download_times = deque(maxlen=100)
        self.file_sizes = deque(maxlen=100)
        
        logger.info("SEC download monitor initialized")
    
    def record_download_start(self, filing_id: str, url: str):
        """
        Record download start.
        
        Args:
            filing_id: Filing identifier
            url: Download URL
        """
        event = {
            'type': 'download_start',
            'filing_id': filing_id,
            'url': url,
            'timestamp': datetime.now(timezone.utc)
        }
        self.recent_events.append(event)
        
        logger.debug(f"Download started: {filing_id}")
    
    def record_download_success(
        self,
        filing_id: str,
        file_size_bytes: int,
        duration_seconds: float,
        strategy_used: Optional[str] = None
    ):
        """
        Record successful download.
        
        Args:
            filing_id: Filing identifier
            file_size_bytes: Downloaded file size
            duration_seconds: Download duration
            strategy_used: ZIP identification strategy used
        """
        self.overall_metrics.total_downloads += 1
        self.overall_metrics.successful_downloads += 1
        self.overall_metrics.total_bytes_downloaded += file_size_bytes
        self.overall_metrics.total_download_time += duration_seconds
        
        # Track strategy
        if strategy_used:
            if strategy_used == 'index_based':
                self.overall_metrics.index_based_success += 1
            elif strategy_used == 'pattern_based':
                self.overall_metrics.pattern_based_success += 1
            elif strategy_used == 'fallback':
                self.overall_metrics.fallback_used += 1
        
        # Track performance
        self.download_times.append(duration_seconds)
        self.file_sizes.append(file_size_bytes)
        
        # Record event
        event = {
            'type': 'download_success',
            'filing_id': filing_id,
            'file_size_bytes': file_size_bytes,
            'duration_seconds': duration_seconds,
            'strategy_used': strategy_used,
            'timestamp': datetime.now(timezone.utc)
        }
        self.recent_events.append(event)
        
        logger.info(
            f"Download success: {filing_id} - "
            f"{file_size_bytes / (1024 * 1024):.2f}MB in {duration_seconds:.1f}s"
        )
    
    def record_download_failure(
        self,
        filing_id: str,
        error_message: str,
        error_type: Optional[str] = None
    ):
        """
        Record failed download.
        
        Args:
            filing_id: Filing identifier
            error_message: Error description
            error_type: Type of error
        """
        self.overall_metrics.total_downloads += 1
        self.overall_metrics.failed_downloads += 1
        
        # Track SEC-specific errors
        if error_type:
            if 'user-agent' in error_type.lower():
                self.overall_metrics.user_agent_errors += 1
            elif 'rate limit' in error_type.lower() or '429' in error_type:
                self.overall_metrics.rate_limit_exceeded_errors += 1
            elif '403' in error_type:
                self.overall_metrics.forbidden_errors += 1
            elif '404' in error_type:
                self.overall_metrics.not_found_errors += 1
        
        # Store error details
        self.error_details[error_type or 'unknown'].append({
            'filing_id': filing_id,
            'error_message': error_message,
            'timestamp': datetime.now(timezone.utc)
        })
        
        # Record event
        event = {
            'type': 'download_failure',
            'filing_id': filing_id,
            'error_message': error_message,
            'error_type': error_type,
            'timestamp': datetime.now(timezone.utc)
        }
        self.recent_events.append(event)
        
        logger.warning(f"Download failure: {filing_id} - {error_message}")
    
    def record_zip_identification_failure(self, filing_id: str, reason: str):
        """
        Record ZIP identification failure.
        
        Args:
            filing_id: Filing identifier
            reason: Failure reason
        """
        self.overall_metrics.zip_identification_failures += 1
        
        event = {
            'type': 'zip_identification_failure',
            'filing_id': filing_id,
            'reason': reason,
            'timestamp': datetime.now(timezone.utc)
        }
        self.recent_events.append(event)
        
        logger.warning(f"ZIP identification failed: {filing_id} - {reason}")
    
    def record_rate_limit_wait(self, wait_time: float):
        """
        Record rate limit wait.
        
        Args:
            wait_time: Time waited in seconds
        """
        self.overall_metrics.rate_limit_waits += 1
        self.overall_metrics.total_wait_time += wait_time
        
        if wait_time > 0.1:  # Log significant waits
            logger.debug(f"Rate limit wait: {wait_time:.3f}s")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics.
        
        Returns:
            Dictionary with all metrics
        """
        # Calculate derived metrics
        self.overall_metrics.calculate_rates()
        
        return {
            'overall': {
                'total_downloads': self.overall_metrics.total_downloads,
                'successful_downloads': self.overall_metrics.successful_downloads,
                'failed_downloads': self.overall_metrics.failed_downloads,
                'success_rate': round(self.overall_metrics.get_success_rate(), 2),
                'total_bytes_downloaded': self.overall_metrics.total_bytes_downloaded,
                'total_mb_downloaded': round(
                    self.overall_metrics.total_bytes_downloaded / (1024 * 1024), 2
                ),
                'average_file_size_mb': round(self.overall_metrics.average_file_size_mb, 2),
                'average_download_time': round(self.overall_metrics.average_download_time, 2)
            },
            'zip_identification': {
                'index_based_success': self.overall_metrics.index_based_success,
                'pattern_based_success': self.overall_metrics.pattern_based_success,
                'fallback_used': self.overall_metrics.fallback_used,
                'failures': self.overall_metrics.zip_identification_failures,
                'success_rate': round(self.overall_metrics.get_zip_identification_rate(), 2)
            },
            'rate_limiting': {
                'total_waits': self.overall_metrics.rate_limit_waits,
                'total_wait_time': round(self.overall_metrics.total_wait_time, 2),
                'average_wait': round(
                    self.overall_metrics.total_wait_time / self.overall_metrics.rate_limit_waits
                    if self.overall_metrics.rate_limit_waits > 0 else 0, 3
                )
            },
            'errors': {
                'user_agent_errors': self.overall_metrics.user_agent_errors,
                'rate_limit_exceeded': self.overall_metrics.rate_limit_exceeded_errors,
                'forbidden_403': self.overall_metrics.forbidden_errors,
                'not_found_404': self.overall_metrics.not_found_errors,
                'error_types': list(self.error_details.keys())
            },
            'recent_performance': self._get_recent_performance()
        }
    
    def _get_recent_performance(self) -> Dict[str, Any]:
        """Get recent performance metrics."""
        if not self.download_times:
            return {
                'recent_downloads': 0,
                'average_time': 0,
                'average_size_mb': 0
            }
        
        return {
            'recent_downloads': len(self.download_times),
            'average_time': round(sum(self.download_times) / len(self.download_times), 2),
            'min_time': round(min(self.download_times), 2),
            'max_time': round(max(self.download_times), 2),
            'average_size_mb': round(
                sum(self.file_sizes) / len(self.file_sizes) / (1024 * 1024), 2
            )
        }
    
    def get_recent_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events.
        
        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        events = list(self.recent_events)
        
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        
        # Sort by timestamp descending (most recent first)
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return events[:limit]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get error summary.
        
        Returns:
            Summary of errors by type
        """
        summary = {}
        
        for error_type, errors in self.error_details.items():
            summary[error_type] = {
                'count': len(errors),
                'recent_errors': errors[-5:] if len(errors) > 5 else errors
            }
        
        return summary
    
    def get_strategy_effectiveness(self) -> Dict[str, Any]:
        """
        Get ZIP identification strategy effectiveness.
        
        Returns:
            Strategy usage statistics
        """
        total = (
            self.overall_metrics.index_based_success +
            self.overall_metrics.pattern_based_success +
            self.overall_metrics.fallback_used
        )
        
        if total == 0:
            return {
                'total_identifications': 0,
                'strategies': {}
            }
        
        return {
            'total_identifications': total,
            'strategies': {
                'index_based': {
                    'count': self.overall_metrics.index_based_success,
                    'percentage': round(
                        (self.overall_metrics.index_based_success / total) * 100, 1
                    )
                },
                'pattern_based': {
                    'count': self.overall_metrics.pattern_based_success,
                    'percentage': round(
                        (self.overall_metrics.pattern_based_success / total) * 100, 1
                    )
                },
                'fallback': {
                    'count': self.overall_metrics.fallback_used,
                    'percentage': round(
                        (self.overall_metrics.fallback_used / total) * 100, 1
                    )
                }
            }
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.overall_metrics = SECDownloadMetrics()
        self.recent_events.clear()
        self.error_details.clear()
        self.download_times.clear()
        self.file_sizes.clear()
        
        logger.info("SEC download metrics reset")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status assessment.
        
        Returns:
            Health status with recommendations
        """
        metrics = self.overall_metrics
        success_rate = metrics.get_success_rate()
        zip_id_rate = metrics.get_zip_identification_rate()
        
        # Assess health
        health = 'healthy'
        issues = []
        recommendations = []
        
        # Check success rate
        if success_rate < 80:
            health = 'critical'
            issues.append(f'Low success rate: {success_rate:.1f}%')
            recommendations.append('Review error logs and network connectivity')
        elif success_rate < 90:
            health = 'warning'
            issues.append(f'Below target success rate: {success_rate:.1f}%')
        
        # Check ZIP identification
        if zip_id_rate < 90:
            if health == 'healthy':
                health = 'warning'
            issues.append(f'Low ZIP identification rate: {zip_id_rate:.1f}%')
            recommendations.append('Check index.json availability and pattern matching')
        
        # Check for frequent errors
        if metrics.user_agent_errors > 5:
            if health == 'healthy':
                health = 'warning'
            issues.append(f'Multiple user-agent errors: {metrics.user_agent_errors}')
            recommendations.append('Verify MAP_PRO_SEC_USER_AGENT configuration')
        
        if metrics.rate_limit_exceeded_errors > 0:
            issues.append(f'Rate limit exceeded {metrics.rate_limit_exceeded_errors} times')
            recommendations.append('Review rate limiting configuration and usage patterns')
        
        return {
            'status': health,
            'success_rate': round(success_rate, 1),
            'zip_identification_rate': round(zip_id_rate, 1),
            'total_downloads': metrics.total_downloads,
            'issues': issues,
            'recommendations': recommendations
        }


# Global monitor instance
_sec_download_monitor: Optional[SECDownloadMonitor] = None


def get_sec_download_monitor() -> SECDownloadMonitor:
    """
    Get global SEC download monitor instance.
    
    Returns:
        SECDownloadMonitor instance
    """
    global _sec_download_monitor
    
    if _sec_download_monitor is None:
        _sec_download_monitor = SECDownloadMonitor()
        logger.info("Created global SEC download monitor")
    
    return _sec_download_monitor


def reset_sec_download_monitor():
    """Reset global monitor (useful for testing)."""
    global _sec_download_monitor
    _sec_download_monitor = None
    logger.debug("Global SEC download monitor reset")