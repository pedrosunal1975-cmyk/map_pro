# engines/downloader/download_validation_coordinator.py
"""
Download Validation Coordinator
================================

Coordinates pre and post-download validation workflows.
Provides clear validation pipeline with logging and error handling.

Responsibilities:
- Pre-download validation orchestration
- Post-download validation orchestration
- Validation result interpretation
- Failed download cleanup

Design Pattern: Facade Pattern
Benefits: Simplifies validation workflow, centralized error handling
"""

from pathlib import Path
from typing import Optional, Tuple

from .download_validator import DownloadValidator, ValidationResult
from .download_result import DownloadResult


class DownloadValidationCoordinator:
    """
    Coordinates validation steps for download operations.
    
    Provides a clean interface for validation workflows and handles
    cleanup of failed downloads.
    """
    
    def __init__(self, validator: DownloadValidator, logger):
        """
        Initialize validation coordinator.
        
        Args:
            validator: Download validator instance
            logger: Logger instance for tracking validation steps
        """
        self.validator = validator
        self.logger = logger
    
    def validate_pre_download(
        self,
        url: str,
        save_path: Path
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute pre-download validation checks.
        
        Args:
            url: URL to be downloaded
            save_path: Target save path for download
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passed
            - error_message: None if valid, error description if invalid
        """
        self.logger.debug(f"Running pre-download validation for: {url}")
        
        validation_result = self.validator.validate_pre_download(url, save_path)
        
        if validation_result.valid:
            self.logger.debug("Pre-download validation passed")
            return True, None
        
        error_message = self._format_validation_error(
            validation_result,
            stage="pre-download"
        )
        self.logger.warning(error_message)
        return False, error_message
    
    def validate_post_download(
        self,
        save_path: Path
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute post-download validation checks.
        
        Args:
            save_path: Path where file was saved
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passed
            - error_message: None if valid, error description if invalid
        """
        self.logger.debug(f"Running post-download validation for: {save_path}")
        
        validation_result = self.validator.validate_post_download(save_path)
        
        if validation_result.valid:
            self.logger.debug("Post-download validation passed")
            return True, None
        
        error_message = self._format_validation_error(
            validation_result,
            stage="post-download"
        )
        self.logger.warning(error_message)
        return False, error_message
    
    def cleanup_failed_download(self, file_path: Path) -> None:
        """
        Clean up failed download file.
        
        Args:
            file_path: Path to file that should be removed
        """
        try:
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Cleaned up failed download: {file_path}")
            else:
                self.logger.debug(f"No cleanup needed, file does not exist: {file_path}")
        except OSError as e:
            self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during cleanup of {file_path}: {e}")
    
    def _format_validation_error(
        self,
        validation_result: ValidationResult,
        stage: str
    ) -> str:
        """
        Format validation error message.
        
        Args:
            validation_result: Validation result object
            stage: Validation stage identifier (e.g., "pre-download", "post-download")
            
        Returns:
            Formatted error message string
        """
        failed_checks = ', '.join(validation_result.checks_failed)
        return f"{stage.capitalize()} validation failed: {failed_checks}"