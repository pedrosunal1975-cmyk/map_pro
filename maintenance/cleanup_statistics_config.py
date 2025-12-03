"""
Map Pro Cleanup Statistics Configuration
=========================================

Configuration constants for cleanup statistics collection.

Save location: tools/maintenance/cleanup_statistics_config.py
"""

from datetime import timedelta


class CleanupStatisticsConfig:
    """Configuration constants for cleanup statistics."""
    
    # Default size limits
    DEFAULT_MAX_TEMP_SIZE_GB = 10.0
    DEFAULT_MAX_LOG_SIZE_GB = 5.0
    
    # Byte conversion constants
    BYTES_PER_KB = 1024
    BYTES_PER_MB = 1024 * 1024
    BYTES_PER_GB = 1024 * 1024 * 1024
    
    # Age thresholds
    AGE_THRESHOLD_DAY = timedelta(days=1)
    AGE_THRESHOLD_WEEK = timedelta(days=7)
    AGE_THRESHOLD_MONTH = timedelta(days=30)
    
    # Database cleanup thresholds
    OLD_JOBS_RETENTION_DAYS = 90
    FAILED_JOBS_RETENTION_DAYS = 30
    
    # Analysis limits
    MAX_LARGEST_FILES_TO_TRACK = 10
    
    # File tracking
    WORKSPACE_DIRECTORY_IDENTIFIER = 'workspace'
    NO_EXTENSION_LABEL = 'no_extension'


__all__ = ['CleanupStatisticsConfig']