# File: /map_pro/core/system_logger.py
"""
Map Pro Central Logging Authority
=================================

Provides unified logging infrastructure for all Map Pro components.
Uses data_paths.py for all log file locations - no hardcoded paths.

Architecture: Core oversight/coordination only - no implementation logic.
All engines, markets, and components must use this for consistent logging.

Improvements Made:
- Split into focused modules under core/logger/ directory
- Fixed SRP violation: Each class in separate module
- Enhanced error handling: Specific exceptions, no silent failures
- Improved validation: Config validation, level validation
- Better encapsulation: State management methods
- Enhanced testability: Each component independently testable
- Better organization: Grouped related functionality
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, List, Any

from .data_paths import map_pro_paths
from .logger.exceptions import LoggingConfigError
from .logger.path_manager import LogPathManager
from .logger.config_loader import LogConfigLoader
from .logger.handler_factory import LogHandlerFactory
from .logger.logger_registry import LoggerRegistry
from .logger.constants import ENGINE_NAMES


class MapProLogger:
    """
    Central logging coordinator for Map Pro system.
    
    Provides engine-specific loggers with consistent formatting and rotation.
    All logging configuration is managed centrally for system-wide consistency.
    
    Responsibility: Coordinate logging components and provide public API.
    """
    
    def __init__(self):
        """Initialize logging system."""
        # Initialize components
        self.path_manager = LogPathManager()
        self.config_loader = LogConfigLoader(map_pro_paths.config_system)
        
        # Load configuration
        self.config = self.config_loader.load_config()
        
        # Initialize factories and registries
        self.handler_factory = LogHandlerFactory(self.config)
        self.logger_registry = LoggerRegistry(
            self.handler_factory,
            self.path_manager,
            self.config
        )
        
        # State tracking
        self._alert_logger: Optional[logging.Logger] = None
        self._original_console_level: Optional[str] = None
        
        # Ensure directories exist
        self.path_manager.ensure_log_directories()
    
    def get_logger(self, name: str, component_type: Optional[str] = None) -> logging.Logger:
        """
        Get or create a logger for specified component.
        
        Args:
            name: Logger name (usually __name__)
            component_type: Type of component ('engine', 'market', 'core', 'integration', etc.)
            
        Returns:
            Configured logger instance with appropriate handlers
        """
        return self.logger_registry.get_logger(name, component_type)
    
    def log_system_event(self, event_type: str, message: str, level: str = "INFO") -> None:
        """
        Log system-wide events to dedicated system log.
        
        Args:
            event_type: Type of event (e.g., "STARTUP", "SHUTDOWN")
            message: Event message
            level: Log level (default: "INFO")
        """
        system_logger = self.get_logger("map_pro.system", "core")
        log_level = self.handler_factory.get_log_level(level)
        
        formatted_message = f"[{event_type}] {message}"
        system_logger.log(log_level, formatted_message)
    
    def log_alert(self, alert_type: str, message: str, component: str) -> None:
        """
        Log critical alerts to dedicated alerts log.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            component: Component generating alert
        """
        if self._alert_logger is None:
            self._alert_logger = self._create_alert_logger(alert_type, component)
        
        self._alert_logger.error(message)
    
    def _create_alert_logger(self, alert_type: str, component: str) -> logging.Logger:
        """
        Create dedicated alert logger.
        
        Args:
            alert_type: Type of alert
            component: Component generating alert
            
        Returns:
            Configured alert logger
        """
        alert_log_path = map_pro_paths.logs_alerts / "critical_errors.log"
        
        alert_logger = logging.getLogger("map_pro.alerts")
        alert_logger.setLevel(logging.WARNING)
        
        alert_handler = self.handler_factory.create_alert_handler(
            alert_log_path,
            alert_type,
            component
        )
        
        if alert_handler:
            alert_logger.addHandler(alert_handler)
        
        return alert_logger
    
    def get_log_status(self) -> Dict[str, Any]:
        """
        Get current logging system status for monitoring.
        
        Returns:
            Dictionary with logging system status
        """
        return {
            "active_loggers": self.logger_registry.get_logger_count(),
            "log_level": self.config["log_level"],
            "log_directories_exist": all([
                map_pro_paths.logs_engines.exists(),
                map_pro_paths.logs_integrations.exists(),
                map_pro_paths.logs_system.exists(),
                map_pro_paths.logs_alerts.exists()
            ]),
            "config_loaded": bool(self.config)
        }
    
    def set_console_log_level(
        self, 
        level: str, 
        logger_patterns: Optional[List[str]] = None
    ) -> None:
        """
        Dynamically change console log level for specific loggers.
        
        Args:
            level: New log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
            logger_patterns: List of logger name patterns to modify
        """
        if logger_patterns is None:
            logger_patterns = self._get_engine_logger_patterns()
        
        log_level = self.handler_factory.get_log_level(level)
        
        # Store original level if suppressing
        if level.upper() == 'CRITICAL' and self._original_console_level is None:
            self._original_console_level = self.config.get("console_log_level", "INFO")
        
        # Update matching loggers
        matching_loggers = self._get_matching_loggers(logger_patterns)
        for logger in matching_loggers:
            self._set_logger_console_level(logger, log_level)
    
    def suppress_console_logging(self, logger_patterns: Optional[List[str]] = None) -> None:
        """
        Temporarily suppress console logging by setting level to CRITICAL.
        
        Args:
            logger_patterns: List of logger name patterns to suppress
        """
        self.set_console_log_level('CRITICAL', logger_patterns)
    
    def restore_console_logging(self, logger_patterns: Optional[List[str]] = None) -> None:
        """
        Restore console logging to original level.
        
        Args:
            logger_patterns: List of logger name patterns to restore
        """
        original_level = self._original_console_level or 'INFO'
        self.set_console_log_level(original_level, logger_patterns)
        self._original_console_level = None
    
    def _get_engine_logger_patterns(self) -> List[str]:
        """
        Get list of engine logger name patterns.
        
        Returns:
            List of logger patterns
        """
        patterns = []
        for engine_name in ENGINE_NAMES:
            patterns.extend([
                f'engines.{engine_name}.status_reporter',
                f'engines.{engine_name}'
            ])
        return patterns
    
    def _get_matching_loggers(self, patterns: List[str]) -> List[logging.Logger]:
        """
        Get all loggers matching the given patterns.
        
        Args:
            patterns: List of patterns to match
            
        Returns:
            List of matching logger instances
        """
        matching_loggers = []
        
        for logger_name in logging.Logger.manager.loggerDict:
            if any(pattern in logger_name for pattern in patterns):
                logger_instance = logging.getLogger(logger_name)
                matching_loggers.append(logger_instance)
        
        return matching_loggers
    
    def _set_logger_console_level(self, logger: logging.Logger, level: int) -> None:
        """
        Set console handler level for a specific logger.
        
        Args:
            logger: Logger to modify
            level: New log level
        """
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                if not hasattr(handler, '_original_level'):
                    handler._original_level = handler.level
                handler.setLevel(level)


@contextmanager
def suppress_engine_console_logs():
    """
    Context manager to suppress engine console logs during interactive input.
    
    Yields control while logs are suppressed, then restores original levels.
    
    Usage:
        with suppress_engine_console_logs():
            user_input = input("Enter value: ")
    """
    # Get engine logger patterns
    patterns = []
    for engine_name in ENGINE_NAMES:
        patterns.extend([
            f'engines.{engine_name}.status_reporter',
            f'engines.{engine_name}'
        ])
    
    # Find matching loggers and store original state
    loggers_to_restore = []
    
    try:
        # Suppress all matching loggers
        for logger_name in logging.Logger.manager.loggerDict:
            if any(pattern in logger_name for pattern in patterns):
                logger_instance = logging.getLogger(logger_name)
                
                # Store original logger level
                original_logger_level = logger_instance.level
                logger_instance.setLevel(logging.CRITICAL)
                
                # Store original handler levels
                handler_levels = []
                for handler in logger_instance.handlers:
                    if isinstance(handler, logging.StreamHandler):
                        handler_levels.append(handler.level)
                        handler.setLevel(logging.CRITICAL)
                
                loggers_to_restore.append(
                    (logger_instance, original_logger_level, handler_levels)
                )
        
        yield
        
    finally:
        # Restore all loggers to original state
        for logger_instance, original_logger_level, handler_levels in loggers_to_restore:
            logger_instance.setLevel(original_logger_level)
            
            handler_idx = 0
            for handler in logger_instance.handlers:
                if isinstance(handler, logging.StreamHandler):
                    if handler_idx < len(handler_levels):
                        handler.setLevel(handler_levels[handler_idx])
                    handler_idx += 1


# Global logger instance for system-wide use
map_pro_logger = MapProLogger()


def get_logger(name: str, component_type: Optional[str] = None) -> logging.Logger:
    """
    Convenience function to get a logger from the central logging system.
    
    Args:
        name: Logger name (usually __name__)
        component_type: Type of component
    
    Usage Examples:
        logger = get_logger(__name__, 'engine')        # For engine components
        logger = get_logger(__name__, 'market')        # For market components
        logger = get_logger(__name__, 'core')          # For core components
        logger = get_logger(__name__, 'integration')   # For integration components
        logger = get_logger(__name__)                  # For general components
    """
    return map_pro_logger.get_logger(name, component_type)


def log_system_event(event_type: str, message: str, level: str = "INFO") -> None:
    """
    Log system-wide events.
    
    Args:
        event_type: Type of event
        message: Event message
        level: Log level (default: "INFO")
    
    Usage:
        log_system_event("STARTUP", "Map Pro system initialized")
        log_system_event("SHUTDOWN", "Map Pro system stopping", "WARNING")
    """
    map_pro_logger.log_system_event(event_type, message, level)


def log_alert(alert_type: str, message: str, component: str) -> None:
    """
    Log critical alerts that require immediate attention.
    
    Args:
        alert_type: Type of alert
        message: Alert message
        component: Component generating alert
    
    Usage:
        log_alert("PARTITION_VIOLATION", "Data file found in program partition", "core.validator")
        log_alert("DATABASE_ERROR", "PostgreSQL connection failed", "core.database")
    """
    map_pro_logger.log_alert(alert_type, message, component)


__all__ = [
    'MapProLogger',
    'map_pro_logger',
    'get_logger',
    'log_system_event',
    'log_alert',
    'suppress_engine_console_logs',
    'LoggingConfigError'
]