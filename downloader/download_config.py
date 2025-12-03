# engines/downloader/download_config.py
"""
Download Coordinator Configuration Module
==========================================

Centralizes all configuration constants for the download coordinator.
Eliminates magic numbers and provides single source of truth for settings.

Design Pattern: Configuration Object
Benefits: Easy testing, clear documentation, environment-specific overrides
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ProtocolConfig:
    """Configuration for protocol handlers."""
    
    DEFAULT_TIMEOUT_SECONDS: int = 30
    DEFAULT_CHUNK_SIZE_BYTES: int = 8192
    SUPPORTED_PROTOCOLS: List[str] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.SUPPORTED_PROTOCOLS is None:
            object.__setattr__(self, 'SUPPORTED_PROTOCOLS', ['http', 'https', 'ftp'])


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration for download validation."""
    
    MAX_FILE_SIZE_MB: float = 500.0
    MIN_FREE_SPACE_MB: float = 1000.0
    VERIFY_CHECKSUMS: bool = True


@dataclass(frozen=True)
class DownloadConfig:
    """Master configuration for download coordinator."""
    
    protocol: ProtocolConfig = None
    validation: ValidationConfig = None
    
    def __post_init__(self):
        """Initialize nested configurations with defaults."""
        if self.protocol is None:
            object.__setattr__(self, 'protocol', ProtocolConfig())
        if self.validation is None:
            object.__setattr__(self, 'validation', ValidationConfig())


# Default configuration instance
DEFAULT_DOWNLOAD_CONFIG = DownloadConfig()