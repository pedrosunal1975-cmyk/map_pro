"""
Map Pro Extraction Validators
=============================

Validates extraction operations before and after execution.
Ensures archive integrity and extraction success.

Architecture: Pre/post extraction validation with safety checks.

Components:
- ExtractionValidator: Main validation coordinator
- PreExtractionValidator: Pre-extraction checks
- PostExtractionValidator: Post-extraction checks
- PathSecurityValidator: Security and path traversal checks
- ValidationResult: Container for validation results
"""

from pathlib import Path
from typing import Dict, Any, List

from core.system_logger import get_logger

# Import refactored components
from .validation_config import ValidationConfig
from .path_security_validator import PathSecurityValidator
from .filesystem_utils import FilesystemUtils
from .pre_extraction_validator import PreExtractionValidator
from .post_extraction_validator import PostExtractionValidator

logger = get_logger(__name__, 'engine')


class ExtractionValidator:
    """
    Main extraction validator coordinator.
    
    Coordinates pre-extraction and post-extraction validation
    using specialized validator classes.
    
    Responsibilities:
    - Coordinate validation workflow
    - Delegate to specialized validators
    - Provide unified validation interface
    """
    
    def __init__(
        self,
        max_extraction_size_mb: float = None,
        min_free_space_mb: float = None,
        config: ValidationConfig = None
    ):
        """
        Initialize extraction validator.
        
        Args:
            max_extraction_size_mb: Maximum allowed extraction size (for backward compatibility)
            min_free_space_mb: Minimum required free disk space (for backward compatibility)
            config: Validation configuration object (preferred)
        """
        self.logger = get_logger(__name__, 'engine')
        
        # Use config or create from parameters (backward compatible)
        if config:
            self.config = config
        else:
            self.config = ValidationConfig(
                max_extraction_size_mb=max_extraction_size_mb,
                min_free_space_mb=min_free_space_mb
            )
        
        # Store for backward compatibility
        self.max_extraction_size_mb = self.config.max_extraction_size_mb
        self.min_free_space_mb = self.config.min_free_space_mb
        
        # Initialize specialized validators
        self.pre_validator = PreExtractionValidator(self.config)
        self.post_validator = PostExtractionValidator()
    
    def validate_pre_extraction(
        self,
        archive_path: Path,
        destination: Path
    ) -> Dict[str, Any]:
        """
        Validate conditions before extraction.
        
        Args:
            archive_path: Path to archive file
            destination: Destination directory
            
        Returns:
            Dictionary with validation results
        """
        return self.pre_validator.validate(archive_path, destination)
    
    def validate_post_extraction(self, extraction_path: Path) -> Dict[str, Any]:
        """
        Validate extraction results.
        
        Args:
            extraction_path: Path where files were extracted
            
        Returns:
            Dictionary with validation results
        """
        return self.post_validator.validate(extraction_path)


class ValidationResult:
    """
    Container for validation results.
    
    Provides a consistent interface for validation outcomes.
    """
    
    def __init__(
        self,
        valid: bool,
        errors: List[str] = None,
        warnings: List[str] = None
    ):
        """
        Initialize validation result.
        
        Args:
            valid: Whether validation passed
            errors: List of error messages
            warnings: List of warning messages
        """
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """
        Create ValidationResult from dictionary.
        
        Args:
            data: Dictionary with validation data
            
        Returns:
            ValidationResult instance
        """
        return cls(
            valid=data.get('valid', False),
            errors=data.get('errors', []),
            warnings=data.get('warnings', [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'valid': self.valid,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def add_error(self, error: str) -> None:
        """
        Add an error message.
        
        Args:
            error: Error message to add
        """
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str) -> None:
        """
        Add a warning message.
        
        Args:
            warning: Warning message to add
        """
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult') -> None:
        """
        Merge another validation result into this one.
        
        Args:
            other: Another ValidationResult to merge
        """
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False
    
    def __bool__(self) -> bool:
        """
        Allow boolean evaluation.
        
        Returns:
            Validation status
        """
        return self.valid
    
    def __str__(self) -> str:
        """
        String representation.
        
        Returns:
            Human-readable string
        """
        status = "VALID" if self.valid else "INVALID"
        parts = [f"Validation: {status}"]
        
        if self.errors:
            parts.append(f"Errors: {', '.join(self.errors)}")
        
        if self.warnings:
            parts.append(f"Warnings: {', '.join(self.warnings)}")
        
        return " | ".join(parts)
    
    def __repr__(self) -> str:
        """
        Developer representation.
        
        Returns:
            Detailed representation
        """
        return (
            f"ValidationResult(valid={self.valid}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)})"
        )


# Export all classes for backward compatibility
__all__ = [
    'ExtractionValidator',
    'PreExtractionValidator',
    'PostExtractionValidator',
    'PathSecurityValidator',
    'ValidationResult',
    'ValidationConfig',
    'FilesystemUtils'
]