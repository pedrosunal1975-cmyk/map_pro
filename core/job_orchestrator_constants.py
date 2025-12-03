# File: /map_pro/core/job_orchestrator_constants.py

"""
Job Orchestrator Constants
===========================

Constants for job orchestration operations.
Centralizes configuration values and eliminates magic numbers.
"""

# Time-based constants
JOB_TIMEOUT_MINUTES = 60
QUEUE_STATS_LOOKBACK_HOURS = 24

# Database query constants
DEFAULT_FETCH_LIMIT = 1

# Default retry configuration
DEFAULT_MAX_RETRIES = 3


__all__ = [
    'JOB_TIMEOUT_MINUTES',
    'QUEUE_STATS_LOOKBACK_HOURS',
    'DEFAULT_FETCH_LIMIT',
    'DEFAULT_MAX_RETRIES',
]