# File: /map_pro/tools/maintenance/log_rotation_config.py

"""
Log Rotation Configuration
===========================

Manages configuration for log rotation operations.
Loads settings from environment variables with sensible defaults.
"""

import os

from .log_rotation_constants import (
    DEFAULT_RETENTION_DAYS,
    DEFAULT_COMPRESS_LOGS,
    ENV_LOG_RETENTION_DAYS,
    ENV_COMPRESS_LOGS,
    TRUE_VALUES
)


class LogRotationConfig:
    """
    Configuration manager for log rotation.
    
    Responsibilities:
    - Load configuration from environment
    - Provide validated configuration values
    - Parse environment variables correctly
    """
    
    def __init__(self):
        """Initialize log rotation configuration from environment."""
        self.retention_days = self._load_retention_days()
        self.compress_logs = self._load_compress_logs()
    
    def _load_retention_days(self) -> int:
        """
        Load retention days from environment.
        
        Returns:
            Number of days to retain logs
        """
        retention_str = os.getenv(ENV_LOG_RETENTION_DAYS, str(DEFAULT_RETENTION_DAYS))
        
        try:
            return int(retention_str)
        except ValueError:
            return DEFAULT_RETENTION_DAYS
    
    def _load_compress_logs(self) -> bool:
        """
        Load compression setting from environment.
        
        Returns:
            True if logs should be compressed
        """
        compress_str = os.getenv(ENV_COMPRESS_LOGS, str(DEFAULT_COMPRESS_LOGS).lower())
        
        return compress_str.lower() in TRUE_VALUES


__all__ = ['LogRotationConfig']