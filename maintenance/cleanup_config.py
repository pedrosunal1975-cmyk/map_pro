# File: /map_pro/tools/maintenance/cleanup_config.py

"""
Cleanup Configuration
=====================

Manages cleanup configuration from environment variables.

Responsibilities:
- Load and parse environment variables
- Provide default values
- Validate configuration
- Centralize configuration access

Related Files:
- cleanup_scheduler.py: Main scheduler
- cleanup_executor.py: Execution logic
"""

import os
from typing import Any


class EnvironmentKeys:
    """Environment variable keys for cleanup configuration."""
    TEMP_RETENTION_DAYS = 'MAP_PRO_TEMP_RETENTION_DAYS'
    DOWNLOAD_RETENTION_DAYS = 'MAP_PRO_DOWNLOAD_RETENTION_DAYS'
    FAILED_JOB_RETENTION_DAYS = 'MAP_PRO_FAILED_JOB_RETENTION_DAYS'
    OLD_JOB_RETENTION_DAYS = 'MAP_PRO_OLD_JOB_RETENTION_DAYS'
    MAX_TEMP_SIZE_GB = 'MAP_PRO_MAX_TEMP_SIZE_GB'
    MAX_LOG_SIZE_GB = 'MAP_PRO_MAX_LOG_SIZE_GB'
    CLEANUP_TEMP_FILES = 'MAP_PRO_CLEANUP_TEMP_FILES'
    CLEANUP_DOWNLOADS = 'MAP_PRO_CLEANUP_DOWNLOADS'
    CLEANUP_DATABASE = 'MAP_PRO_CLEANUP_DATABASE'
    CLEANUP_LOGS = 'MAP_PRO_CLEANUP_LOGS'
    CLEANUP_CONNECTIONS = 'MAP_PRO_CLEANUP_CONNECTIONS'


class ConfigDefaults:
    """Default values for cleanup configuration."""
    TEMP_RETENTION_DAYS = 7
    DOWNLOAD_RETENTION_DAYS = 14
    FAILED_JOB_RETENTION_DAYS = 30
    OLD_JOB_RETENTION_DAYS = 90
    MAX_TEMP_SIZE_GB = 10.0
    MAX_LOG_SIZE_GB = 5.0
    CLEANUP_TEMP_FILES = True
    CLEANUP_DOWNLOADS = True
    CLEANUP_DATABASE = True
    CLEANUP_LOGS = False
    CLEANUP_CONNECTIONS = True


class RecommendationThresholds:
    """Thresholds for cleanup recommendations."""
    OLD_JOBS_THRESHOLD = 1000
    FAILED_JOBS_THRESHOLD = 100


class CleanupConfig:
    """
    Manages cleanup configuration from environment variables.
    
    This class loads configuration from environment variables with
    fallback to sensible defaults.
    """
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Retention periods in days
        self.temp_retention_days = self._get_int_env(
            EnvironmentKeys.TEMP_RETENTION_DAYS,
            ConfigDefaults.TEMP_RETENTION_DAYS
        )
        
        self.download_retention_days = self._get_int_env(
            EnvironmentKeys.DOWNLOAD_RETENTION_DAYS,
            ConfigDefaults.DOWNLOAD_RETENTION_DAYS
        )
        
        self.failed_job_retention_days = self._get_int_env(
            EnvironmentKeys.FAILED_JOB_RETENTION_DAYS,
            ConfigDefaults.FAILED_JOB_RETENTION_DAYS
        )
        
        self.old_job_retention_days = self._get_int_env(
            EnvironmentKeys.OLD_JOB_RETENTION_DAYS,
            ConfigDefaults.OLD_JOB_RETENTION_DAYS
        )
        
        # Size thresholds in GB
        self.max_temp_size_gb = self._get_float_env(
            EnvironmentKeys.MAX_TEMP_SIZE_GB,
            ConfigDefaults.MAX_TEMP_SIZE_GB
        )
        
        self.max_log_size_gb = self._get_float_env(
            EnvironmentKeys.MAX_LOG_SIZE_GB,
            ConfigDefaults.MAX_LOG_SIZE_GB
        )
        
        # Cleanup enable/disable flags
        self.cleanup_temp_files = self._get_bool_env(
            EnvironmentKeys.CLEANUP_TEMP_FILES,
            ConfigDefaults.CLEANUP_TEMP_FILES
        )
        
        self.cleanup_downloads = self._get_bool_env(
            EnvironmentKeys.CLEANUP_DOWNLOADS,
            ConfigDefaults.CLEANUP_DOWNLOADS
        )
        
        self.cleanup_database = self._get_bool_env(
            EnvironmentKeys.CLEANUP_DATABASE,
            ConfigDefaults.CLEANUP_DATABASE
        )
        
        self.cleanup_logs = self._get_bool_env(
            EnvironmentKeys.CLEANUP_LOGS,
            ConfigDefaults.CLEANUP_LOGS
        )
        
        self.cleanup_connections = self._get_bool_env(
            EnvironmentKeys.CLEANUP_CONNECTIONS,
            ConfigDefaults.CLEANUP_CONNECTIONS
        )
        
        # Recommendation thresholds
        self.old_jobs_threshold = RecommendationThresholds.OLD_JOBS_THRESHOLD
        self.failed_jobs_threshold = RecommendationThresholds.FAILED_JOBS_THRESHOLD
    
    def _get_int_env(self, key: str, default: int) -> int:
        """
        Get integer value from environment variable.
        
        Args:
            key: Environment variable key
            default: Default value if key not found or invalid
            
        Returns:
            Integer value from environment or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            return default
    
    def _get_float_env(self, key: str, default: float) -> float:
        """
        Get float value from environment variable.
        
        Args:
            key: Environment variable key
            default: Default value if key not found or invalid
            
        Returns:
            Float value from environment or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        try:
            return float(value)
        except ValueError:
            return default
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """
        Get boolean value from environment variable.
        
        Accepts 'true', 'yes', '1' as True (case-insensitive).
        All other values are considered False.
        
        Args:
            key: Environment variable key
            default: Default value if key not found
            
        Returns:
            Boolean value from environment or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        
        return value.lower() in ('true', 'yes', '1')
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary with all configuration values
        """
        return {
            'temp_retention_days': self.temp_retention_days,
            'download_retention_days': self.download_retention_days,
            'failed_job_retention_days': self.failed_job_retention_days,
            'old_job_retention_days': self.old_job_retention_days,
            'max_temp_size_gb': self.max_temp_size_gb,
            'max_log_size_gb': self.max_log_size_gb,
            'cleanup_temp_files': self.cleanup_temp_files,
            'cleanup_downloads': self.cleanup_downloads,
            'cleanup_database': self.cleanup_database,
            'cleanup_logs': self.cleanup_logs,
            'cleanup_connections': self.cleanup_connections,
            'old_jobs_threshold': self.old_jobs_threshold,
            'failed_jobs_threshold': self.failed_jobs_threshold
        }


__all__ = [
    'CleanupConfig',
    'EnvironmentKeys',
    'ConfigDefaults',
    'RecommendationThresholds'
]