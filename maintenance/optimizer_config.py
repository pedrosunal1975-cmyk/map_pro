"""
Optimizer Configuration
======================

File: tools/maintenance/optimizer_config.py

Configuration for system optimizer operations.
"""

import os
from dataclasses import dataclass


@dataclass
class OptimizerConfig:
    """
    Configuration for system optimizer.
    
    Centralizes all optimizer thresholds and settings.
    """
    
    # General settings
    auto_optimize: bool = None
    optimization_interval_hours: int = None
    max_history_size: int = 50
    
    # Resource thresholds
    max_memory_usage_percent: float = None
    max_disk_usage_percent: float = None
    
    # Memory optimization
    low_memory_threshold: float = 50.0
    min_pool_size: int = 5
    max_pool_size: int = 30
    min_cache_size_mb: int = 256
    max_cache_size_mb: int = 2000
    
    # Database optimization
    high_pool_utilization: float = 90.0
    pool_size_increment: int = 5
    max_db_pool_size: int = 50
    
    # Disk optimization
    large_directory_threshold_gb: float = 5.0
    
    # Queue optimization
    high_queue_threshold: int = 100
    old_job_threshold_seconds: int = 3600  # 1 hour
    max_concurrent_jobs: int = 20
    concurrent_jobs_increment: int = 2
    
    # Performance optimization
    high_failure_rate: float = 0.15  # 15%
    slow_processing_threshold_seconds: int = 600  # 10 minutes
    max_retry_attempts: int = 5
    retry_increment: int = 1
    max_timeout_minutes: int = 120
    timeout_increment_minutes: int = 15
    
    def __post_init__(self):
        """Initialize configuration from environment variables."""
        if self.auto_optimize is None:
            self.auto_optimize = (
                os.getenv('MAP_PRO_AUTO_OPTIMIZE', 'false').lower() == 'true'
            )
        
        if self.optimization_interval_hours is None:
            self.optimization_interval_hours = int(
                os.getenv('MAP_PRO_OPTIMIZATION_INTERVAL', '24')
            )
        
        if self.max_memory_usage_percent is None:
            self.max_memory_usage_percent = float(
                os.getenv('MAP_PRO_MAX_MEMORY_USAGE', '80.0')
            )
        
        if self.max_disk_usage_percent is None:
            self.max_disk_usage_percent = float(
                os.getenv('MAP_PRO_MAX_DISK_USAGE', '85.0')
            )
        
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration values."""
        if self.optimization_interval_hours <= 0:
            raise ValueError("optimization_interval_hours must be positive")
        
        if not (0 <= self.max_memory_usage_percent <= 100):
            raise ValueError("max_memory_usage_percent must be between 0 and 100")
        
        if not (0 <= self.max_disk_usage_percent <= 100):
            raise ValueError("max_disk_usage_percent must be between 0 and 100")