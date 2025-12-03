"""
Map Pro Error Handler
====================

Handles error processing and recovery for engines.
Provides specialized error handling patterns for different types of engine errors.

Architecture: Specialized component focused on error handling coordination.
"""

import time
import traceback
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque

from core.system_logger import get_logger
from shared.exceptions.custom_exceptions import EngineError, DatabaseError, CriticalEngineError
from .error_tracker import ErrorTracker
from .recovery_manager import RecoveryManager
from .engine_error_classifier import (
    engine_error_classifier,
    EngineErrorType,
    classify_engine_error,
    is_system_error,
    is_data_error
)

if TYPE_CHECKING:
    from .engine_base import BaseEngine

logger = get_logger(__name__, 'engine')


class ErrorHandler:
    """
    Main error handling coordinator for engines.
    
    Responsibilities:
    - Error classification and routing
    - Recovery strategy coordination
    - Alert triggering
    - Error handler lifecycle management
    
    Does NOT handle:
    - Error tracking details (error_tracker handles this)
    - Recovery strategy implementation (recovery_manager handles this)
    - Alert delivery (alert_manager handles this)
    """
    
    def __init__(self, engine: 'BaseEngine'):
        """
        Initialize error handler for specific engine.
        
        Args:
            engine: The engine instance this handler belongs to
        """
        self.engine = engine
        self.logger = get_logger(f"engines.{engine.engine_name}.error_handler", 'engine')
        
        # Initialize components
        self.error_tracker = ErrorTracker(engine)
        self.recovery_manager = RecoveryManager(engine)
        
        # Error handling thresholds
        self.critical_error_threshold = 5  # 5 consecutive errors trigger critical handling
        
        self.logger.debug(f"Error handler initialized for {engine.engine_name}")
    
    def handle_initialization_error(self, error: Exception):
        """
        Handle errors during engine initialization.
        
        Args:
            error: The initialization error that occurred
        """
        try:
            error_info = self._create_error_info('initialization', error)
            self.error_tracker.record_error(error_info)
            
            self.logger.error(
                f"Engine {self.engine.engine_name} initialization failed: {error}",
                extra={'error_type': 'initialization', 'traceback': traceback.format_exc()}
            )
            
            # Get recovery suggestion
            retry_delay = self.recovery_manager.get_recovery_delay('initialization')
            if retry_delay:
                self.logger.info(f"Suggested retry delay: {retry_delay} seconds")
            else:
                self.logger.error("Maximum initialization retry attempts reached")
                self._trigger_critical_alert('initialization', error)
                
        except Exception as e:
            self.logger.error(f"Error in initialization error handler: {e}")
    
    def handle_startup_error(self, error: Exception):
        """
        Handle errors during engine startup.
        
        Args:
            error: The startup error that occurred
        """
        try:
            error_info = self._create_error_info('startup', error)
            self.error_tracker.record_error(error_info)
            
            self.logger.error(
                f"Engine {self.engine.engine_name} startup failed: {error}",
                extra={'error_type': 'startup', 'traceback': traceback.format_exc()}
            )
            
            # Check if we should attempt recovery
            if self.recovery_manager.should_attempt_recovery('startup'):
                retry_delay = self.recovery_manager.get_recovery_delay('initialization')
                if retry_delay:
                    self.logger.warning(f"Startup error recovery: retry in {retry_delay} seconds")
                else:
                    self._trigger_critical_alert('startup', error)
            else:
                self._trigger_critical_alert('startup', error)
                
        except Exception as e:
            self.logger.error(f"Error in startup error handler: {e}")
    
    def handle_database_error(self, error: Exception, database_name: str):
        """
        Handle database-related errors.
        
        Args:
            error: The database error that occurred
            database_name: Name of the database that had the error
        """
        try:
            error_info = self._create_error_info('database', error, {'database': database_name})
            self.error_tracker.record_error(error_info)
            
            self.logger.error(
                f"Database error in {self.engine.engine_name} ({database_name}): {error}",
                extra={'error_type': 'database', 'database': database_name, 'traceback': traceback.format_exc()}
            )
            
            # Check error rate for this database
            if self.error_tracker.is_database_error_rate_high(database_name):
                self.logger.error(f"High error rate detected for database {database_name}")
                self._trigger_database_alert(database_name, error)
            
            # Suggest recovery delay
            retry_delay = self.recovery_manager.get_recovery_delay('database')
            if retry_delay:
                self.logger.info(f"Database error recovery delay: {retry_delay} seconds")
                
        except Exception as e:
            self.logger.error(f"Error in database error handler: {e}")
    
    def handle_processing_error(self, error: Exception):
        """
        Handle errors during job processing.
        
        Args:
            error: The processing error that occurred
        """
        try:
            error_info = self._create_error_info('processing', error)
            self.error_tracker.record_error(error_info)
            
            self.logger.warning(
                f"Processing error in {self.engine.engine_name}: {error}",
                extra={'error_type': 'processing', 'traceback': traceback.format_exc()}
            )
            
            # Check if we're in an error spiral
            consecutive_errors = self.error_tracker.get_consecutive_errors()
            if consecutive_errors >= self.critical_error_threshold:
                self.logger.error(f"Critical error threshold reached: {consecutive_errors} consecutive errors")
                self._trigger_critical_alert('processing', error)
            else:
                # Normal processing error handling
                retry_delay = self.recovery_manager.get_recovery_delay('processing')
                if retry_delay:
                    self.logger.info(f"Processing error recovery delay: {retry_delay} seconds")
                    
        except Exception as e:
            self.logger.error(f"Error in processing error handler: {e}")
    
    def handle_engine_processing_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle engine processing errors with system vs data classification.
        
        This method classifies errors into:
        - System errors: Infrastructure issues requiring engineering attention
        - Data errors: Data quality issues expected in real-world data
        
        Args:
            error: The processing error that occurred
            context: Optional context information (document_id, filing_id, etc.)
            
        Returns:
            Dictionary with error classification and handling recommendations
        """
        try:
            # Classify the error
            error_report = engine_error_classifier.create_error_report(
                error,
                error_message=str(error),
                context=context
            )
            
            # Log appropriately based on classification
            log_level = error_report['log_level']
            error_type = error_report['error_type']
            
            if log_level == 'error':
                self.logger.error(
                    f"SYSTEM ERROR in {self.engine.engine_name}: {error}",
                    extra={
                        'error_type': error_type,
                        'classification': 'system_error',
                        'context': context,
                        'traceback': traceback.format_exc()
                    }
                )
            elif log_level == 'warning':
                self.logger.warning(
                    f"DATA QUALITY ISSUE in {self.engine.engine_name}: {error}",
                    extra={
                        'error_type': error_type,
                        'classification': 'data_error',
                        'context': context
                    }
                )
            
            # Record error with classification
            error_info = self._create_error_info('processing', error, context)
            error_info['engine_error_type'] = error_type
            error_info['is_system_error'] = error_report['is_system_error']
            error_info['is_data_error'] = error_report['is_data_error']
            self.error_tracker.record_error(error_info)
            
            # Handle based on error type
            if error_report['is_system_error']:
                # System errors might indicate a critical issue
                consecutive_errors = self.error_tracker.get_consecutive_errors()
                if consecutive_errors >= self.critical_error_threshold:
                    self._trigger_critical_alert('system_error', error)
            
            # Return full error report for caller to use
            return error_report
            
        except Exception as e:
            self.logger.error(f"Error in engine processing error handler: {e}")
            # Return a basic error report on failure
            return {
                'error_class': error.__class__.__name__,
                'error_message': str(error),
                'error_type': 'unknown',
                'is_system_error': False,
                'is_data_error': False,
                'log_level': 'error',
                'status_label': 'failed',
                'should_retry': False
            }
    
    def handle_critical_error(self, error: Exception):
        """
        Handle critical errors that may require engine shutdown.
        
        Args:
            error: The critical error that occurred
        """
        try:
            error_info = self._create_error_info('critical', error)
            self.error_tracker.record_error(error_info)
            
            self.logger.critical(
                f"CRITICAL ERROR in {self.engine.engine_name}: {error}",
                extra={'error_type': 'critical', 'traceback': traceback.format_exc()}
            )
            
            # Always trigger alert for critical errors
            self._trigger_critical_alert('critical', error)
            
            # Check if engine should be stopped
            if self.recovery_manager.should_stop_engine_on_critical_error():
                self.logger.critical(f"Stopping engine {self.engine.engine_name} due to critical error")
                # Note: We don't actually stop the engine here to avoid circular calls
                # The engine's main loop should check error conditions and stop itself
            
        except Exception as e:
            self.logger.error(f"Error in critical error handler: {e}")
    
    def _create_error_info(self, error_type: str, error: Exception, 
                          additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create standardized error information dictionary.
        
        Args:
            error_type: Type of error (initialization, database, processing, etc.)
            error: The error that occurred
            additional_context: Additional context information
            
        Returns:
            Dictionary with error information
        """
        error_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'engine_name': self.engine.engine_name,
            'error_type': error_type,
            'error_class': error.__class__.__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        if additional_context:
            error_info.update(additional_context)
        
        return error_info
    
    def _trigger_critical_alert(self, error_type: str, error: Exception):
        """
        Trigger critical alert for serious errors.
        
        Args:
            error_type: Type of error
            error: The error that occurred
        """
        try:
            from core.alert_manager import create_alert
            
            consecutive_errors = self.error_tracker.get_consecutive_errors()
            alert_message = (
                f"Critical error in engine {self.engine.engine_name} "
                f"({error_type}): {str(error)}"
            )
            
            create_alert(
                f"engine_critical_{self.engine.engine_name}",
                alert_message,
                'critical',
                {'error_type': error_type, 'consecutive_errors': consecutive_errors}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create critical alert: {e}")
    
    def _trigger_database_alert(self, database_name: str, error: Exception):
        """
        Trigger alert for database-specific issues.
        
        Args:
            database_name: Name of problematic database
            error: The database error that occurred
        """
        try:
            from core.alert_manager import create_alert
            
            alert_message = (
                f"Database issues in engine {self.engine.engine_name} "
                f"(database: {database_name}): {str(error)}"
            )
            
            create_alert(
                f"engine_database_{self.engine.engine_name}_{database_name}",
                alert_message,
                'warning',
                {'database': database_name, 'error_type': 'database'}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create database alert: {e}")
    
    def reset_error_counters(self):
        """Reset error counters after successful operation."""
        try:
            self.error_tracker.reset_counters()
            self.logger.debug("Error counters reset after successful operation")
        except Exception as e:
            self.logger.error(f"Failed to reset error counters: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        try:
            stats = self.error_tracker.get_error_statistics()
            stats['recovery_status'] = self.recovery_manager.get_recovery_status()
            return stats
        except Exception as e:
            self.logger.error(f"Failed to get error statistics: {e}")
            return {'error': str(e)}