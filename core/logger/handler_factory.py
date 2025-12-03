# File: /map_pro/core/logger/handler_factory.py
"""
Log Handler Factory
===================

Creates and configures logging handlers.

Responsibility: Handler creation with proper formatting and rotation.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any

from .constants import (
    BYTES_PER_MB,
    CONSOLE_FORMAT,
    FILE_FORMAT,
    ALERT_FORMAT_TEMPLATE
)


class LogHandlerFactory:
    """
    Creates and configures logging handlers.
    
    Provides factory methods for creating standardized handlers
    with consistent formatting and rotation policies.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize handler factory.
        
        Args:
            config: Logging configuration dictionary
        """
        self.config = config
    
    def create_console_handler(self) -> logging.StreamHandler:
        """
        Create standardized console handler.
        
        Returns:
            Configured console handler with appropriate formatter
            
        Notes:
            - Uses console_log_level from config
            - Applies standard console format
            - Outputs to stderr
        """
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.get_log_level(self.config["console_log_level"]))
        
        console_formatter = logging.Formatter(
            CONSOLE_FORMAT,
            datefmt=self.config["date_format"]
        )
        console_handler.setFormatter(console_formatter)
        
        return console_handler
    
    def create_file_handler(self, log_file_path: Path) -> Optional[logging.Handler]:
        """
        Create rotating file handler.
        
        Args:
            log_file_path: Path to log file
            
        Returns:
            Configured file handler or None if creation fails
            
        Notes:
            - Implements automatic log rotation
            - Uses file_log_level from config
            - Applies detailed file format with function/line info
            - Handles creation failures gracefully
        """
        try:
            # Calculate max bytes from MB config
            max_bytes = self.config["max_file_size_mb"] * BYTES_PER_MB
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=self.config["backup_count"],
                encoding='utf-8'
            )
            file_handler.setLevel(self.get_log_level(self.config["file_log_level"]))
            
            # Detailed formatter for file logs
            file_formatter = logging.Formatter(
                FILE_FORMAT,
                datefmt=self.config["date_format"]
            )
            file_handler.setFormatter(file_formatter)
            
            return file_handler
            
        except OSError as e:
            print(f"Warning: Could not create file handler for {log_file_path}: {e}")
            return None
        except IOError as e:
            print(f"Warning: IO error creating file handler for {log_file_path}: {e}")
            return None
        except Exception as e:
            print(f"Warning: Unexpected error creating file handler for {log_file_path}: {e}")
            return None
    
    def create_alert_handler(
        self, 
        log_file_path: Path, 
        alert_type: str, 
        component: str
    ) -> Optional[logging.Handler]:
        """
        Create alert handler with custom formatting.
        
        Args:
            log_file_path: Path to alert log file
            alert_type: Type of alert (included in log format)
            component: Component generating alert (included in log format)
            
        Returns:
            Configured alert handler or None if creation fails
            
        Notes:
            - Uses WARNING level by default
            - Includes alert type and component in format
            - Implements log rotation
        """
        try:
            # Calculate max bytes from MB config
            max_bytes = self.config["max_file_size_mb"] * BYTES_PER_MB
            
            alert_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=self.config["backup_count"],
                encoding='utf-8'
            )
            alert_handler.setLevel(logging.WARNING)
            
            # Format with alert type and component
            alert_format = ALERT_FORMAT_TEMPLATE.format(
                alert_type=alert_type,
                component=component
            )
            alert_formatter = logging.Formatter(
                alert_format,
                datefmt=self.config["date_format"]
            )
            alert_handler.setFormatter(alert_formatter)
            
            return alert_handler
            
        except (OSError, IOError) as e:
            print(f"Warning: Could not create alert handler: {e}")
            return None
        except Exception as e:
            print(f"Warning: Unexpected error creating alert handler: {e}")
            return None
    
    def get_log_level(self, level_name: str) -> int:
        """
        Convert log level name to logging constant.
        
        Args:
            level_name: Log level name (e.g., 'DEBUG', 'INFO')
            
        Returns:
            Logging level constant (e.g., logging.DEBUG)
            
        Notes:
            - Case-insensitive
            - Falls back to INFO for invalid levels
            
        Examples:
            get_log_level('DEBUG') -> 10
            get_log_level('info') -> 20
            get_log_level('INVALID') -> 20 (INFO)
        """
        try:
            return getattr(logging, level_name.upper())
        except AttributeError:
            print(f"Warning: Invalid log level '{level_name}', using INFO")
            return logging.INFO
    
    def create_custom_handler(
        self,
        log_file_path: Path,
        level: str,
        format_string: str,
        max_bytes: Optional[int] = None,
        backup_count: Optional[int] = None
    ) -> Optional[logging.Handler]:
        """
        Create handler with custom configuration.
        
        Args:
            log_file_path: Path to log file
            level: Log level name
            format_string: Custom format string
            max_bytes: Optional override for max file size
            backup_count: Optional override for backup count
            
        Returns:
            Configured handler or None if creation fails
        """
        try:
            # Use provided values or fall back to config
            if max_bytes is None:
                max_bytes = self.config["max_file_size_mb"] * BYTES_PER_MB
            if backup_count is None:
                backup_count = self.config["backup_count"]
            
            handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            handler.setLevel(self.get_log_level(level))
            
            formatter = logging.Formatter(
                format_string,
                datefmt=self.config["date_format"]
            )
            handler.setFormatter(formatter)
            
            return handler
            
        except Exception as e:
            print(f"Warning: Could not create custom handler: {e}")
            return None