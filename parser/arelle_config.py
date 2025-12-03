# engines/parser/arelle_config.py
"""
Arelle Controller Configuration
================================

Configuration constants for Arelle controller.
Centralizes all magic numbers and default settings.

Design Pattern: Configuration Object
Benefits: Single source of truth, easy testing, clear defaults
"""

from dataclasses import dataclass


# Module-level constants
DEFAULT_LOG_LEVEL = "WARNING"
TEMP_DIR_PREFIX = 'map_pro_arelle_'
LOG_FORMAT = '[%(asctime)s] %(message)s'
UNKNOWN_VERSION = 'unknown'


@dataclass(frozen=True)
class ArelleConfig:
    """
    Configuration for Arelle controller.
    
    Attributes:
        log_level: Logging level for Arelle messages
        temp_dir_prefix: Prefix for temporary directories
        log_format: Format string for Arelle logs
    """
    log_level: str = DEFAULT_LOG_LEVEL
    temp_dir_prefix: str = TEMP_DIR_PREFIX
    log_format: str = LOG_FORMAT
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if configuration is valid
        """
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        return self.log_level.upper() in valid_levels


# Default configuration instance
DEFAULT_CONFIG = ArelleConfig()


__all__ = [
    'ArelleConfig',
    'DEFAULT_CONFIG',
    'DEFAULT_LOG_LEVEL',
    'TEMP_DIR_PREFIX',
    'LOG_FORMAT',
    'UNKNOWN_VERSION'
]