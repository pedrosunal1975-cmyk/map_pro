# File: /map_pro/core/logger/logger_registry.py
"""
Logger Registry
===============

Manages logger instances and their lifecycle.

Responsibility: Logger creation, caching, and retrieval.
"""

import logging
from typing import Optional, Dict, Any

from .handler_factory import LogHandlerFactory
from .path_manager import LogPathManager


class LoggerRegistry:
    """
    Manages logger instances and their lifecycle.
    
    Provides centralized logger creation and caching to ensure
    consistent logger configuration across the system.
    """
    
    def __init__(
        self,
        handler_factory: LogHandlerFactory,
        path_manager: LogPathManager,
        config: Dict[str, Any]
    ):
        """
        Initialize logger registry.
        
        Args:
            handler_factory: Factory for creating handlers
            path_manager: Manager for log paths
            config: Logging configuration
        """
        self.handler_factory = handler_factory
        self.path_manager = path_manager
        self.config = config
        self._loggers: Dict[str, logging.Logger] = {}
    
    def get_logger(
        self, 
        name: str, 
        component_type: Optional[str] = None
    ) -> logging.Logger:
        """
        Get or create a logger for specified component.
        
        Args:
            name: Logger name (usually __name__)
            component_type: Type of component ('engine', 'market', 'core', etc.)
            
        Returns:
            Configured logger instance
            
        Notes:
            - Caches loggers to avoid duplicate creation
            - Adds appropriate handlers based on component type
            - Prevents duplicate handlers on existing loggers
        """
        logger_key = self._get_logger_key(name, component_type)
        
        if logger_key not in self._loggers:
            self._loggers[logger_key] = self._create_logger(name, component_type)
        
        return self._loggers[logger_key]
    
    def _get_logger_key(self, name: str, component_type: Optional[str]) -> str:
        """
        Generate cache key for logger.
        
        Args:
            name: Logger name
            component_type: Type of component
            
        Returns:
            Cache key for logger
        """
        if component_type:
            return f"{component_type}.{name}"
        return name
    
    def _create_logger(
        self, 
        name: str, 
        component_type: Optional[str] = None
    ) -> logging.Logger:
        """
        Create new logger with appropriate handlers.
        
        Args:
            name: Logger name
            component_type: Type of component
            
        Returns:
            Configured logger with handlers
            
        Notes:
            - Sets logger level from config
            - Adds console handler for all loggers
            - Adds file handler based on component type
            - Prevents duplicate handlers
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.handler_factory.get_log_level(self.config["log_level"]))
        
        # Prevent propagation to parent loggers to avoid duplicate console output
        logger.propagate = False

        # Prevent duplicate handlers if logger already exists
        if logger.handlers:
            return logger
        
        # Add console handler for all loggers
        console_handler = self.handler_factory.create_console_handler()
        logger.addHandler(console_handler)
        
        # Add file handler based on component type
        self._add_file_handler(logger, name, component_type)
        
        return logger
    
    def _add_file_handler(
        self,
        logger: logging.Logger,
        name: str,
        component_type: Optional[str]
    ) -> None:
        """
        Add file handler to logger based on component type.
        
        Args:
            logger: Logger to add handler to
            name: Logger name
            component_type: Type of component
        """
        log_file_path = self.path_manager.get_log_file_path(name, component_type)
        
        if log_file_path:
            file_handler = self.handler_factory.create_file_handler(log_file_path)
            if file_handler:
                logger.addHandler(file_handler)
    
    def get_logger_count(self) -> int:
        """
        Get count of registered loggers.
        
        Returns:
            Number of loggers in registry
        """
        return len(self._loggers)
    
    def get_registered_loggers(self) -> Dict[str, logging.Logger]:
        """
        Get all registered loggers.
        
        Returns:
            Dictionary of logger names to logger instances
        """
        return self._loggers.copy()
    
    def clear_registry(self) -> None:
        """
        Clear the logger registry.
        
        Notes:
            - Does not remove handlers from existing loggers
            - Use with caution - mainly for testing
        """
        self._loggers.clear()
    
    def get_logger_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered logger.
        
        Args:
            name: Logger name or key
            
        Returns:
            Dictionary with logger information or None if not found
        """
        # Try exact match first
        if name in self._loggers:
            logger = self._loggers[name]
            return self._build_logger_info(logger)
        
        # Try partial match
        for key, logger in self._loggers.items():
            if name in key:
                return self._build_logger_info(logger)
        
        return None
    
    def _build_logger_info(self, logger: logging.Logger) -> Dict[str, Any]:
        """
        Build information dictionary for logger.
        
        Args:
            logger: Logger to get info for
            
        Returns:
            Dictionary with logger details
        """
        return {
            'name': logger.name,
            'level': logging.getLevelName(logger.level),
            'handler_count': len(logger.handlers),
            'handlers': [
                {
                    'type': type(handler).__name__,
                    'level': logging.getLevelName(handler.level)
                }
                for handler in logger.handlers
            ]
        }
    
    def reconfigure_logger(
        self,
        name: str,
        new_level: Optional[str] = None,
        component_type: Optional[str] = None
    ) -> bool:
        """
        Reconfigure an existing logger.
        
        Args:
            name: Logger name
            new_level: New log level (optional)
            component_type: New component type (optional)
            
        Returns:
            True if reconfigured, False if logger not found
        """
        logger_key = self._get_logger_key(name, component_type)
        
        if logger_key not in self._loggers:
            return False
        
        logger = self._loggers[logger_key]
        
        if new_level:
            logger.setLevel(self.handler_factory.get_log_level(new_level))
        
        return True