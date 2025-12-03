"""
Map Pro Error Tracker
=====================

Tracks error history and patterns for engines.
Specialized component for error data management and analysis.

Architecture: Specialized component focused on error tracking and pattern analysis.
"""

import time
from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque

from core.system_logger import get_logger

if TYPE_CHECKING:
    from .engine_base import BaseEngine

logger = get_logger(__name__, 'engine')


class ErrorTracker:
    """
    Tracks error history and patterns for engines.
    
    Responsibilities:
    - Error history storage and management
    - Error pattern analysis
    - Error rate calculations
    - Error statistics generation
    
    Does NOT handle:
    - Error recovery logic (recovery_manager handles this)
    - Alert generation (error_handler handles this)
    - Error handling decisions (error_handler handles this)
    """
    
    def __init__(self, engine: 'BaseEngine'):
        """
        Initialize error tracker for specific engine.
        
        Args:
            engine: The engine instance this tracker belongs to
        """
        self.engine = engine
        self.logger = get_logger(f"engines.{engine.engine_name}.error_tracker", 'engine')
        
        # Error tracking data structures
        self.error_history = deque(maxlen=1000)  # Last 1000 errors
        self.error_counts = defaultdict(int)  # Count by error type
        self.consecutive_errors = 0
        self.last_error_time = None
        
        # Error rate monitoring configuration
        self.error_rate_window = 300  # 5 minutes
        self.database_error_threshold = 5  # High error rate threshold
        
        self.logger.debug(f"Error tracker initialized for {engine.engine_name}")
    
    def record_error(self, error_info: Dict[str, Any]):
        """
        Record error in history and update counters.
        
        Args:
            error_info: Error information to record
        """
        try:
            # Add to history
            self.error_history.append(error_info)
            
            # Update counters
            error_key = f"{error_info['error_type']}:{error_info['error_class']}"
            self.error_counts[error_key] += 1
            
            # Update consecutive error tracking
            self.consecutive_errors += 1
            self.last_error_time = time.time()
            
            self.logger.debug(f"Recorded error: {error_key} (consecutive: {self.consecutive_errors})")
            
        except Exception as e:
            self.logger.error(f"Failed to record error: {e}")
    
    def reset_counters(self):
        """Reset error counters after successful operation."""
        try:
            self.consecutive_errors = 0
            self.last_error_time = None
            self.logger.debug("Error counters reset")
        except Exception as e:
            self.logger.error(f"Failed to reset error counters: {e}")
    
    def get_consecutive_errors(self) -> int:
        """
        Get current consecutive error count.
        
        Returns:
            Number of consecutive errors
        """
        return self.consecutive_errors
    
    def count_recent_errors_of_type(self, error_type: str, minutes: int = 5) -> int:
        """
        Count recent errors of specific type.
        
        Args:
            error_type: Type of error to count
            minutes: Time window in minutes
            
        Returns:
            Number of recent errors of this type
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            recent_count = 0
            for error_info in reversed(self.error_history):
                error_time = datetime.fromisoformat(error_info['timestamp'])
                if error_time < cutoff_time:
                    break
                if error_info['error_type'] == error_type:
                    recent_count += 1
            
            return recent_count
            
        except Exception as e:
            self.logger.warning(f"Failed to count recent errors: {e}")
            return 0
    
    def is_database_error_rate_high(self, database_name: str) -> bool:
        """
        Check if database error rate is unusually high.
        
        Args:
            database_name: Name of database to check
            
        Returns:
            True if error rate is high
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.error_rate_window)
            
            db_errors = 0
            for error_info in reversed(self.error_history):
                error_time = datetime.fromisoformat(error_info['timestamp'])
                if error_time < cutoff_time:
                    break
                if (error_info['error_type'] == 'database' and 
                    error_info.get('database') == database_name):
                    db_errors += 1
            
            return db_errors >= self.database_error_threshold
            
        except Exception as e:
            self.logger.warning(f"Failed to check database error rate: {e}")
            return False
    
    def calculate_recent_error_rate(self, minutes: int = 5) -> float:
        """
        Calculate recent error rate (errors per minute).
        
        Args:
            minutes: Time window in minutes
            
        Returns:
            Error rate in errors per minute
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            recent_errors = 0
            for error_info in reversed(self.error_history):
                error_time = datetime.fromisoformat(error_info['timestamp'])
                if error_time < cutoff_time:
                    break
                recent_errors += 1
            
            return recent_errors / float(minutes)
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate error rate: {e}")
            return 0.0
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        try:
            return {
                'engine_name': self.engine.engine_name,
                'total_errors': len(self.error_history),
                'consecutive_errors': self.consecutive_errors,
                'last_error_time': self.last_error_time,
                'error_counts_by_type': dict(self.error_counts),
                'recent_error_rate': self.calculate_recent_error_rate(),
                'error_history_size': len(self.error_history),
                'error_rate_window': self.error_rate_window
            }
        except Exception as e:
            self.logger.error(f"Failed to get error statistics: {e}")
            return {'error': str(e)}
    
    def get_error_patterns(self) -> Dict[str, Any]:
        """
        Analyze error patterns and trends.
        
        Returns:
            Dictionary with error pattern analysis
        """
        try:
            patterns = {
                'most_common_errors': [],
                'error_trend': 'stable',
                'peak_error_times': [],
                'database_error_distribution': {}
            }
            
            # Most common error types
            sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
            patterns['most_common_errors'] = sorted_errors[:5]
            
            # Database error distribution
            db_errors = defaultdict(int)
            for error_info in self.error_history:
                if error_info['error_type'] == 'database':
                    db_name = error_info.get('database', 'unknown')
                    db_errors[db_name] += 1
            patterns['database_error_distribution'] = dict(db_errors)
            
            # Error trend analysis (simplified)
            recent_rate = self.calculate_recent_error_rate(5)  # Last 5 minutes
            older_rate = self.calculate_recent_error_rate(15) - recent_rate  # 5-15 minutes ago
            
            if recent_rate > older_rate * 1.5:
                patterns['error_trend'] = 'increasing'
            elif recent_rate < older_rate * 0.5:
                patterns['error_trend'] = 'decreasing'
            else:
                patterns['error_trend'] = 'stable'
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to analyze error patterns: {e}")
            return {'error': str(e)}
    
    def get_tracker_status(self) -> Dict[str, Any]:
        """
        Get status of the error tracker itself.
        
        Returns:
            Dictionary with tracker status information
        """
        return {
            'error_history_size': len(self.error_history),
            'max_history_size': self.error_history.maxlen,
            'consecutive_errors': self.consecutive_errors,
            'unique_error_types': len(self.error_counts),
            'tracking_window_minutes': self.error_rate_window / 60
        }