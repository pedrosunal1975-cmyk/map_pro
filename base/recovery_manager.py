"""
Map Pro Recovery Manager
=======================

Handles error recovery strategies and decisions for engines.
Specialized component for recovery logic and timing management.

Architecture: Specialized component focused on recovery strategy implementation.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta, timezone

from core.system_logger import get_logger

if TYPE_CHECKING:
    from .engine_base import BaseEngine
    from .error_tracker import ErrorTracker

logger = get_logger(__name__, 'engine')


class RecoveryManager:
    """
    Handles error recovery strategies and decisions for engines.
    
    Responsibilities:
    - Recovery strategy implementation
    - Recovery timing and delays
    - Recovery decision logic
    - Recovery attempt tracking
    
    Does NOT handle:
    - Error tracking (error_tracker handles this)
    - Error classification (error_handler handles this)
    - Alert generation (error_handler handles this)
    """
    
    def __init__(self, engine: 'BaseEngine'):
        """
        Initialize recovery manager for specific engine.
        
        Args:
            engine: The engine instance this manager belongs to
        """
        self.engine = engine
        self.logger = get_logger(f"engines.{engine.engine_name}.recovery_manager", 'engine')
        
        # Recovery configuration
        self.max_error_rate = 10  # Max 10 errors per 5-minute window
        self.critical_error_multiplier = 2  # Critical threshold is 2x normal
        
        # Recovery delay strategies (progressive delays in seconds)
        self.recovery_delays = {
            'initialization': [1, 5, 15, 30, 60],
            'database': [2, 10, 30, 60, 120],
            'processing': [5, 15, 45, 120, 300],
            'critical': [60, 300, 900, 1800]  # 1min, 5min, 15min, 30min
        }
        
        # Recovery attempt tracking
        self.recovery_attempts = {}
        self.last_recovery_reset = datetime.now(timezone.utc)
        
        self.logger.debug(f"Recovery manager initialized for {engine.engine_name}")
    
    def get_recovery_delay(self, error_type: str) -> Optional[float]:
        """
        Get suggested recovery delay for error type.
        
        Args:
            error_type: Type of error
            
        Returns:
            Delay in seconds, or None if max attempts reached
        """
        try:
            delays = self.recovery_delays.get(error_type, [1, 5, 15])
            
            # Get recent error count for this type
            recent_errors = self._get_recent_error_count(error_type)
            
            if recent_errors < len(delays):
                delay = delays[recent_errors]
                self._record_recovery_attempt(error_type)
                return delay
            else:
                self.logger.warning(f"Maximum recovery attempts reached for {error_type}")
                return None  # Max attempts reached
                
        except Exception as e:
            self.logger.error(f"Failed to get recovery delay: {e}")
            return 30  # Default delay
    
    def should_attempt_recovery(self, error_type: str) -> bool:
        """
        Determine if recovery should be attempted for error type.
        
        Args:
            error_type: Type of error
            
        Returns:
            True if recovery should be attempted
        """
        try:
            # Get error tracker from engine
            error_tracker = getattr(self.engine, 'error_handler', None)
            if error_tracker and hasattr(error_tracker, 'error_tracker'):
                tracker = error_tracker.error_tracker
                
                # Don't attempt recovery if too many consecutive errors
                consecutive_errors = tracker.get_consecutive_errors()
                if consecutive_errors >= self._get_critical_threshold():
                    return False
                
                # Check overall error rate
                recent_errors = tracker.count_recent_errors_of_type(error_type)
                if recent_errors >= self.max_error_rate:
                    return False
            
            # Check recovery attempts for this error type
            attempts = self.recovery_attempts.get(error_type, 0)
            max_attempts = len(self.recovery_delays.get(error_type, [1, 5, 15]))
            
            if attempts >= max_attempts:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to determine recovery feasibility: {e}")
            return False  # Safe default
    
    def should_stop_engine_on_critical_error(self) -> bool:
        """
        Determine if engine should be stopped due to critical error patterns.
        
        Returns:
            True if engine should be stopped
        """
        try:
            # Get error tracker from engine
            error_tracker = getattr(self.engine, 'error_handler', None)
            if error_tracker and hasattr(error_tracker, 'error_tracker'):
                tracker = error_tracker.error_tracker
                
                # Stop if too many consecutive errors
                consecutive_errors = tracker.get_consecutive_errors()
                critical_threshold = self._get_critical_threshold()
                
                if consecutive_errors >= critical_threshold * 2:
                    return True
                
                # Stop if critical error rate is too high
                critical_errors = tracker.count_recent_errors_of_type('critical')
                if critical_errors >= 3:  # 3 critical errors in 5 minutes
                    return True
                
                # Stop if overall error rate is extremely high
                total_error_rate = tracker.calculate_recent_error_rate()
                if total_error_rate >= self.max_error_rate * 2:  # 2x normal rate
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to determine engine stop condition: {e}")
            return False
    
    def reset_recovery_attempts(self, error_type: Optional[str] = None):
        """
        Reset recovery attempts for specific error type or all types.
        
        Args:
            error_type: Specific error type to reset, or None for all types
        """
        try:
            if error_type:
                self.recovery_attempts[error_type] = 0
                self.logger.debug(f"Reset recovery attempts for {error_type}")
            else:
                self.recovery_attempts.clear()
                self.last_recovery_reset = datetime.now(timezone.utc)
                self.logger.debug("Reset all recovery attempts")
                
        except Exception as e:
            self.logger.error(f"Failed to reset recovery attempts: {e}")
    
    def _get_recent_error_count(self, error_type: str) -> int:
        """
        Get recent error count for specific type.
        
        Args:
            error_type: Type of error to count
            
        Returns:
            Number of recent errors of this type
        """
        try:
            # Get error tracker from engine
            error_tracker = getattr(self.engine, 'error_handler', None)
            if error_tracker and hasattr(error_tracker, 'error_tracker'):
                tracker = error_tracker.error_tracker
                return tracker.count_recent_errors_of_type(error_type)
            
            return 0
            
        except Exception:
            return 0
    
    def _get_critical_threshold(self) -> int:
        """
        Get critical error threshold based on engine type.
        
        Returns:
            Critical error threshold
        """
        # Base threshold
        base_threshold = 5
        
        # Adjust based on engine type
        engine_adjustments = {
            'parser': 3,      # Parser errors are more serious
            'mapper': 3,      # Mapper errors are more serious
            'searcher': 7,    # Searcher can tolerate more errors
            'downloader': 6,  # Downloader can tolerate some errors
            'extractor': 5,   # Standard threshold
            'librarian': 8    # Librarian can tolerate more errors
        }
        
        return engine_adjustments.get(self.engine.engine_name, base_threshold)
    
    def _record_recovery_attempt(self, error_type: str):
        """
        Record a recovery attempt for error type.
        
        Args:
            error_type: Type of error being recovered from
        """
        try:
            self.recovery_attempts[error_type] = self.recovery_attempts.get(error_type, 0) + 1
            self.logger.debug(f"Recorded recovery attempt for {error_type} (total: {self.recovery_attempts[error_type]})")
        except Exception as e:
            self.logger.error(f"Failed to record recovery attempt: {e}")
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """
        Get current recovery status and statistics.
        
        Returns:
            Dictionary with recovery status information
        """
        try:
            return {
                'engine_name': self.engine.engine_name,
                'recovery_attempts': dict(self.recovery_attempts),
                'critical_threshold': self._get_critical_threshold(),
                'max_error_rate': self.max_error_rate,
                'last_recovery_reset': self.last_recovery_reset.isoformat(),
                'recovery_strategies': {
                    error_type: len(delays) 
                    for error_type, delays in self.recovery_delays.items()
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get recovery status: {e}")
            return {'error': str(e)}
    
    def update_recovery_strategy(self, error_type: str, delays: list):
        """
        Update recovery strategy for specific error type.
        
        Args:
            error_type: Error type to update
            delays: List of delay values in seconds
        """
        try:
            self.recovery_delays[error_type] = delays
            self.logger.info(f"Updated recovery strategy for {error_type}: {delays}")
        except Exception as e:
            self.logger.error(f"Failed to update recovery strategy: {e}")
    
    def get_next_recovery_delay(self, error_type: str) -> Optional[float]:
        """
        Get next recovery delay without recording an attempt.
        
        Args:
            error_type: Type of error
            
        Returns:
            Next delay in seconds, or None if max attempts would be reached
        """
        try:
            delays = self.recovery_delays.get(error_type, [1, 5, 15])
            recent_errors = self._get_recent_error_count(error_type)
            
            if recent_errors < len(delays):
                return delays[recent_errors]
            else:
                return None  # Max attempts would be reached
                
        except Exception as e:
            self.logger.error(f"Failed to get next recovery delay: {e}")
            return None