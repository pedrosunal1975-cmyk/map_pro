# File: /map_pro/core/logger/exceptions.py
"""
Logging System Exceptions
==========================

Custom exceptions for the logging system.
Provides specific error types for better error handling.
"""


class LoggingConfigError(Exception):
    """
    Raised when logging configuration encounters an error.
    
    This includes:
    - Invalid configuration values
    - Directory creation failures
    - File access issues
    - Invalid log levels
    """
    pass


class LogPathError(LoggingConfigError):
    """
    Raised when log path operations fail.
    
    This includes:
    - Directory creation failures
    - Permission issues
    - Path validation failures
    """
    pass