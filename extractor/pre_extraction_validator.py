"""
Pre-Extraction Validator
========================

File: engines/extractor/pre_extraction_validator.py

Validates conditions before extraction.
Imported by extraction_validators.py
"""

from pathlib import Path
from typing import Dict, Any, List

from core.system_logger import get_logger

from .validation_config import ValidationConfig
from .filesystem_utils import FilesystemUtils


class PreExtractionValidator:
    """
    Validates conditions before extraction.
    
    Responsibilities:
    - Archive existence and readability checks
    - Archive size validation
    - Disk space validation
    - Destination directory checks
    - Write permission validation
    """
    
    def __init__(self, config: ValidationConfig):
        """
        Initialize pre-extraction validator.
        
        Args:
            config: Validation configuration
        """
        self.config = config
        self.fs = FilesystemUtils()
        self.logger = get_logger(__name__, 'engine')
    
    def validate(
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
        errors = []
        warnings = []
        
        # Check archive
        archive_errors = self._validate_archive(archive_path)
        errors.extend(archive_errors)
        
        if errors:
            # Stop early if archive is invalid
            return self._build_result(False, errors, warnings)
        
        # Get archive size for further checks
        archive_size_mb = self.fs.get_file_size_mb(archive_path)
        
        # Validate archive size
        size_errors = self._validate_archive_size(archive_size_mb)
        errors.extend(size_errors)
        
        # Validate destination
        dest_errors = self._validate_destination(destination)
        errors.extend(dest_errors)
        
        # Validate disk space
        space_errors, space_warnings = self._validate_disk_space(
            destination,
            archive_size_mb
        )
        errors.extend(space_errors)
        warnings.extend(space_warnings)
        
        # Build result
        is_valid = len(errors) == 0
        
        if not is_valid:
            self.logger.warning(
                f"Pre-extraction validation failed: {', '.join(errors)}"
            )
        
        return self._build_result(is_valid, errors, warnings)
    
    def _validate_archive(self, archive_path: Path) -> List[str]:
        """
        Validate archive file.
        
        Args:
            archive_path: Path to archive
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not archive_path.exists():
            errors.append(f"Archive file not found: {archive_path}")
            return errors
        
        if not archive_path.is_file():
            errors.append(f"Archive path is not a file: {archive_path}")
        
        if not self.fs.is_readable(archive_path):
            errors.append(f"Archive file is not readable: {archive_path}")
        
        return errors
    
    def _validate_archive_size(self, archive_size_mb: float) -> List[str]:
        """
        Validate archive size is within limits.
        
        Args:
            archive_size_mb: Archive size in MB
            
        Returns:
            List of error messages
        """
        errors = []
        
        if archive_size_mb > self.config.max_extraction_size_mb:
            errors.append(
                f"Archive too large: {archive_size_mb:.2f}MB "
                f"(max: {self.config.max_extraction_size_mb:.2f}MB)"
            )
        
        return errors
    
    def _validate_destination(self, destination: Path) -> List[str]:
        """
        Validate destination directory.
        
        Args:
            destination: Destination directory path
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check if destination exists and is not a directory
        if destination.exists() and not destination.is_dir():
            errors.append(
                f"Destination exists but is not a directory: {destination}"
            )
            return errors
        
        # Check write permissions
        if destination.exists():
            if not self.fs.is_writable(destination):
                errors.append(
                    f"No write permission for destination: {destination}"
                )
        else:
            parent = destination.parent
            if not parent.exists() or not self.fs.is_writable(parent):
                errors.append(
                    f"Cannot create destination directory: {destination}"
                )
        
        return errors
    
    def _validate_disk_space(
        self,
        destination: Path,
        archive_size_mb: float
    ) -> tuple[List[str], List[str]]:
        """
        Validate disk space availability.
        
        Args:
            destination: Destination directory
            archive_size_mb: Archive size in MB
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        free_space_mb = self.fs.get_free_space_mb(destination)
        
        # Check minimum free space requirement
        if free_space_mb < self.config.min_free_space_mb:
            errors.append(
                f"Insufficient disk space: {free_space_mb:.2f}MB free "
                f"(min required: {self.config.min_free_space_mb:.2f}MB)"
            )
        
        # Check estimated extraction space
        estimated_extraction_mb = self.config.estimate_extraction_size_mb(
            archive_size_mb
        )
        
        if estimated_extraction_mb > free_space_mb:
            warnings.append(
                f"May not have enough space. Archive: {archive_size_mb:.2f}MB, "
                f"Free: {free_space_mb:.2f}MB"
            )
        
        return errors, warnings
    
    def _build_result(
        self,
        valid: bool,
        errors: List[str],
        warnings: List[str]
    ) -> Dict[str, Any]:
        """
        Build validation result dictionary.
        
        Args:
            valid: Whether validation passed
            errors: List of errors
            warnings: List of warnings
            
        Returns:
            Validation result dictionary
        """
        return {
            'valid': valid,
            'errors': errors,
            'warnings': warnings
        }