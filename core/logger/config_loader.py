# File: /map_pro/core/logger/config_loader.py
"""
Log Configuration Loader
=========================

Loads and validates logging configuration from JSON file.

Responsibility: Configuration file operations and validation.
"""

import json
from pathlib import Path
from typing import Dict, Any

from .exceptions import LoggingConfigError
from .constants import (
    DEFAULT_CONFIG,
    VALID_LOG_LEVELS,
    CONFIG_FILE_NAME
)


class LogConfigLoader:
    """
    Loads and validates logging configuration from file.
    
    Provides robust configuration loading with validation and
    fallback to defaults if configuration file is missing or invalid.
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize config loader.
        
        Args:
            config_path: Path to configuration directory
        """
        self.config_file = config_path / CONFIG_FILE_NAME
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load logging configuration from file.
        
        Returns:
            Configuration dictionary (defaults if file doesn't exist)
            
        Notes:
            - Returns default config if file doesn't exist
            - Merges loaded config with defaults
            - Validates all configuration values
            - Falls back to defaults on any error
        """
        if not self.config_file.exists():
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # Merge with defaults to ensure all required keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(loaded_config)
            
            # Validate merged configuration
            self._validate_config(config)
            
            return config
            
        except json.JSONDecodeError as e:
            # Log warning but continue with defaults
            print(f"Warning: Invalid JSON in {self.config_file}: {e}")
            print("Using default logging configuration.")
            return DEFAULT_CONFIG.copy()
        
        except IOError as e:
            print(f"Warning: Could not read {self.config_file}: {e}")
            print("Using default logging configuration.")
            return DEFAULT_CONFIG.copy()
        
        except LoggingConfigError as e:
            print(f"Warning: Configuration validation failed: {e}")
            print("Using default logging configuration.")
            return DEFAULT_CONFIG.copy()
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration values.
        
        Args:
            config: Configuration to validate
            
        Raises:
            LoggingConfigError: If config contains invalid values
        """
        # Validate log levels
        self._validate_log_levels(config)
        
        # Validate numeric values
        self._validate_numeric_values(config)
        
        # Validate date format
        self._validate_date_format(config)
    
    def _validate_log_levels(self, config: Dict[str, Any]) -> None:
        """
        Validate all log level settings.
        
        Args:
            config: Configuration to validate
            
        Raises:
            LoggingConfigError: If any log level is invalid
        """
        log_level_keys = ['log_level', 'file_log_level', 'console_log_level']
        
        for key in log_level_keys:
            if key in config:
                level = str(config[key]).upper()
                if level not in VALID_LOG_LEVELS:
                    raise LoggingConfigError(
                        f"Invalid log level '{config[key]}' for {key}. "
                        f"Must be one of: {', '.join(VALID_LOG_LEVELS)}"
                    )
    
    def _validate_numeric_values(self, config: Dict[str, Any]) -> None:
        """
        Validate numeric configuration values.
        
        Args:
            config: Configuration to validate
            
        Raises:
            LoggingConfigError: If numeric values are invalid
        """
        # Validate max file size
        if 'max_file_size_mb' in config:
            size = config['max_file_size_mb']
            if not isinstance(size, (int, float)) or size <= 0:
                raise LoggingConfigError(
                    f"max_file_size_mb must be positive number, got: {size}"
                )
        
        # Validate backup count
        if 'backup_count' in config:
            count = config['backup_count']
            if not isinstance(count, int) or count < 0:
                raise LoggingConfigError(
                    f"backup_count must be non-negative integer, got: {count}"
                )
    
    def _validate_date_format(self, config: Dict[str, Any]) -> None:
        """
        Validate date format string.
        
        Args:
            config: Configuration to validate
            
        Raises:
            LoggingConfigError: If date format is invalid
        """
        if 'date_format' in config:
            date_format = config['date_format']
            if not isinstance(date_format, str) or not date_format:
                raise LoggingConfigError(
                    f"date_format must be non-empty string, got: {date_format}"
                )
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            
        Raises:
            LoggingConfigError: If save fails
        """
        try:
            # Validate before saving
            self._validate_config(config)
            
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
                
        except (IOError, OSError) as e:
            raise LoggingConfigError(
                f"Failed to save configuration to {self.config_file}: {e}"
            ) from e