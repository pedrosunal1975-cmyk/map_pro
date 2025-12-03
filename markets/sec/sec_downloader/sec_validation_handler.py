# File: /map_pro/markets/sec/sec_downloader/sec_validation_handler.py

"""
SEC Validation Handler
======================

Handles SEC-specific validation requirements before download.
Validates URLs, file paths, and SEC identifier formats.
"""

from pathlib import Path
from typing import NamedTuple

from core.system_logger import get_logger
from .sec_download_validator import SECDownloadValidator

logger = get_logger(__name__, 'market')


class ValidationResult(NamedTuple):
    """Result of SEC validation check."""
    is_valid: bool
    error_message: str = ""


class SECValidationHandler:
    """
    Handles SEC-specific validation.
    
    Responsibilities:
    - Validate ZIP URLs
    - Validate save paths
    - Validate CIK and accession number formats
    - Aggregate validation results
    """
    
    def __init__(self, user_agent: str):
        """
        Initialize validation handler.
        
        Args:
            user_agent: SEC user-agent string
        """
        self.validator = SECDownloadValidator(user_agent=user_agent)
        self.logger = logger
    
    def validate_pre_download(
        self,
        zip_url: str,
        save_path: Path,
        cik: str,
        accession_number: str
    ) -> ValidationResult:
        """
        Validate SEC-specific requirements before download.
        
        Args:
            zip_url: ZIP file URL to validate
            save_path: Destination path for file
            cik: CIK identifier
            accession_number: Accession number
            
        Returns:
            ValidationResult with validation status and error message if failed
        """
        validation_result = self.validator.validate_sec_pre_download(
            zip_url,
            save_path,
            cik,
            accession_number
        )
        
        if not validation_result.valid:
            error_msg = self._format_validation_error(validation_result.checks_failed)
            self.logger.warning(error_msg)
            return ValidationResult(is_valid=False, error_message=error_msg)
        
        return ValidationResult(is_valid=True)
    
    def _format_validation_error(self, checks_failed: list) -> str:
        """
        Format validation error message from failed checks.
        
        Args:
            checks_failed: List of failed validation check names
            
        Returns:
            Formatted error message
        """
        return f"SEC validation failed: {', '.join(checks_failed)}"