# File: /map_pro/tools/maintenance/cleanup_scheduler_constants.py

"""
Cleanup Scheduler Constants
============================

Constants for cleanup scheduling operations.
Eliminates magic numbers and centralizes configuration values.
"""

# Cleanup naming constants
CLEANUP_NAME_PREFIX = 'cleanup'
TARGETED_CLEANUP_PREFIX = 'targeted_cleanup'

# History management constants
MAX_HISTORY_ENTRIES = 50
HISTORY_LOG_FILENAME = 'cleanup_history.json'

# Priority levels
PRIORITY_HIGH = 'high'
PRIORITY_MEDIUM = 'medium'
PRIORITY_LOW = 'low'


__all__ = [
    'CLEANUP_NAME_PREFIX',
    'TARGETED_CLEANUP_PREFIX',
    'MAX_HISTORY_ENTRIES',
    'HISTORY_LOG_FILENAME',
    'PRIORITY_HIGH',
    'PRIORITY_MEDIUM',
    'PRIORITY_LOW',
]