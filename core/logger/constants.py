# File: /map_pro/core/logger/constants.py
"""
Logging System Constants
=========================

Centralized constants for the logging system.
Eliminates magic strings and numbers throughout the codebase.
"""

from typing import Dict, List, Any


# Engine names for log path determination
ENGINE_NAMES: List[str] = [
    'searcher',
    'downloader',
    'extractor',
    'parser',
    'librarian',
    'mapper'
]

# Valid log level names
VALID_LOG_LEVELS: List[str] = [
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL'
]

# Default logging configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "log_level": "INFO",
    "file_log_level": "DEBUG",
    "console_log_level": "INFO",
    "max_file_size_mb": 10,
    "backup_count": 5,
    "date_format": "%Y-%m-%d %H:%M:%S"
}

# Configuration file name
CONFIG_FILE_NAME: str = "logging_config.json"

# Log file names
SYSTEM_LOG_FILE: str = "system.log"
CORE_LOG_FILE: str = "core_operations.log"
MARKET_LOG_FILE: str = "market_operations.log"
INTEGRATION_LOG_FILE: str = "integration_operations.log"
ALERT_LOG_FILE: str = "critical_errors.log"

# Conversion constants
BYTES_PER_MB: int = 1024 * 1024

# Formatter templates
CONSOLE_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
FILE_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
ALERT_FORMAT_TEMPLATE: str = '%(asctime)s - ALERT - {alert_type} - {component} - %(message)s'