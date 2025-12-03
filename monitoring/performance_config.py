"""
Performance Configuration
========================

File: tools/monitoring/performance_config.py

Configuration for performance analysis operations.
"""

import os
from dataclasses import dataclass


@dataclass
class PerformanceConfig:
    """
    Configuration for performance analysis.
    
    Centralizes all performance thresholds and settings.
    """
    
    # Analysis window
    analysis_window_hours: int = None
    
    # Thresholds
    slow_job_threshold_seconds: float = None
    bottleneck_queue_threshold: int = None
    critical_failure_rate: float = 0.20  # 20%
    high_failure_rate: float = 0.10      # 10%
    engine_failure_threshold: float = 0.15  # 15%
    
    # History
    max_history_size: int = 100
    
    # Trend detection
    trend_increase_threshold: float = 1.2  # 20% increase
    trend_decrease_threshold: float = 0.8  # 20% decrease
    min_history_for_trends: int = 2
    trend_comparison_size: int = 5  # Last 5 analyses
    
    def __post_init__(self):
        """Initialize configuration from environment variables."""
        if self.analysis_window_hours is None:
            self.analysis_window_hours = int(
                os.getenv('MAP_PRO_ANALYSIS_WINDOW_HOURS', '24')
            )
        
        if self.slow_job_threshold_seconds is None:
            self.slow_job_threshold_seconds = float(
                os.getenv('MAP_PRO_SLOW_JOB_THRESHOLD', '300.0')
            )
        
        if self.bottleneck_queue_threshold is None:
            self.bottleneck_queue_threshold = int(
                os.getenv('MAP_PRO_BOTTLENECK_QUEUE_THRESHOLD', '50')
            )
        
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration values."""
        if self.analysis_window_hours <= 0:
            raise ValueError("analysis_window_hours must be positive")
        
        if self.slow_job_threshold_seconds <= 0:
            raise ValueError("slow_job_threshold_seconds must be positive")
        
        if self.bottleneck_queue_threshold < 0:
            raise ValueError("bottleneck_queue_threshold must be non-negative")
        
        if not (0 <= self.critical_failure_rate <= 1):
            raise ValueError("critical_failure_rate must be between 0 and 1")