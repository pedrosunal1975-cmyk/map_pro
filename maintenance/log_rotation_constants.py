# File: /map_pro/tools/maintenance/log_rotation_constants.py

"""
Log Rotation Constants
=======================

Constants for log rotation operations.
Eliminates magic numbers and centralizes configuration values.
"""

# File size conversion constants
BYTES_PER_KILOBYTE = 1024
BYTES_PER_MEGABYTE = 1024 * 1024

# Default configuration values
DEFAULT_RETENTION_DAYS = 30
DEFAULT_COMPRESS_LOGS = True

# Environment variable names
ENV_LOG_RETENTION_DAYS = 'MAP_PRO_LOG_RETENTION_DAYS'
ENV_COMPRESS_LOGS = 'MAP_PRO_COMPRESS_LOGS'

# Log file patterns
LOG_EXTENSION = '.log'
COMPRESSED_EXTENSION = '.gz'
LOG_SEPARATOR = '.log.'

# True/False string values for environment parsing
TRUE_VALUES = frozenset(['true', '1', 'yes', 'on'])
FALSE_VALUES = frozenset(['false', '0', 'no', 'off'])


__all__ = [
    'BYTES_PER_KILOBYTE',
    'BYTES_PER_MEGABYTE',
    'DEFAULT_RETENTION_DAYS',
    'DEFAULT_COMPRESS_LOGS',
    'ENV_LOG_RETENTION_DAYS',
    'ENV_COMPRESS_LOGS',
    'LOG_EXTENSION',
    'COMPRESSED_EXTENSION',
    'LOG_SEPARATOR',
    'TRUE_VALUES',
    'FALSE_VALUES',
]