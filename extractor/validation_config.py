"""
Validation Configuration
=======================

File: engines/extractor/validation_config.py

Centralized configuration for extraction validation.
Imported by extraction_validators.py
"""

from dataclasses import dataclass


@dataclass
class ValidationConfig:
    """
    Configuration for extraction validation.
    
    Centralizes all validation thresholds and constants.
    """
    
    # Size limits
    max_extraction_size_mb: float = 5000.0  # 5 GB
    min_free_space_mb: float = 1000.0       # 1 GB
    
    # Extraction estimation
    extraction_size_multiplier: int = 2     # Assume 2x archive size
    
    # Conversion constants
    bytes_per_mb: int = 1024 * 1024
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_extraction_size_mb is None:
            self.max_extraction_size_mb = 5000.0
        
        if self.min_free_space_mb is None:
            self.min_free_space_mb = 1000.0
        
        if self.max_extraction_size_mb <= 0:
            raise ValueError("max_extraction_size_mb must be positive")
        
        if self.min_free_space_mb < 0:
            raise ValueError("min_free_space_mb must be non-negative")
    
    def estimate_extraction_size_mb(self, archive_size_mb: float) -> float:
        """
        Estimate extraction size from archive size.
        
        Args:
            archive_size_mb: Archive size in MB
            
        Returns:
            Estimated extraction size in MB
        """
        return archive_size_mb * self.extraction_size_multiplier