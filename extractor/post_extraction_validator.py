"""
Post-Extraction Validator
=========================

File: engines/extractor/post_extraction_validator.py

Validates extraction results after extraction.
Imported by extraction_validators.py
"""

from pathlib import Path
from typing import Dict, Any, List

from core.system_logger import get_logger

from .path_security_validator import PathSecurityValidator
from .filesystem_utils import FilesystemUtils


class PostExtractionValidator:
    """
    Validates extraction results after extraction.
    
    Responsibilities:
    - Extraction directory existence check
    - File count validation
    - Directory readability check
    - Security validation via PathSecurityValidator
    """
    
    def __init__(self):
        """Initialize post-extraction validator."""
        self.logger = get_logger(__name__, 'engine')
        self.security_validator = PathSecurityValidator()
        self.fs = FilesystemUtils()
    
    def validate(self, extraction_path: Path) -> Dict[str, Any]:
        """
        Validate extraction results.
        
        Args:
            extraction_path: Path where files were extracted
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        # Check extraction directory
        dir_errors = self._validate_extraction_directory(extraction_path)
        errors.extend(dir_errors)
        
        if errors:
            # Stop early if directory is invalid
            return self._build_result(False, errors, warnings)
        
        # Check extracted files
        file_warnings = self._validate_extracted_files(extraction_path)
        warnings.extend(file_warnings)
        
        # Check for security issues
        security_warnings = self._validate_security(extraction_path)
        warnings.extend(security_warnings)
        
        # Build result
        is_valid = len(errors) == 0
        
        if not is_valid:
            self.logger.warning(
                f"Post-extraction validation failed: {', '.join(errors)}"
            )
        
        return self._build_result(is_valid, errors, warnings)
    
    def _validate_extraction_directory(
        self,
        extraction_path: Path
    ) -> List[str]:
        """
        Validate extraction directory exists and is readable.
        
        Args:
            extraction_path: Extraction directory path
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not extraction_path.exists():
            errors.append(
                f"Extraction directory not found: {extraction_path}"
            )
            return errors
        
        if not extraction_path.is_dir():
            errors.append(
                f"Extraction path is not a directory: {extraction_path}"
            )
        
        if not self.fs.is_readable(extraction_path):
            errors.append(
                f"Extraction directory is not readable: {extraction_path}"
            )
        
        return errors
    
    def _validate_extracted_files(
        self,
        extraction_path: Path
    ) -> List[str]:
        """
        Validate extracted files exist.
        
        Args:
            extraction_path: Extraction directory path
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        try:
            file_count = self.fs.count_files(extraction_path)
            
            if file_count == 0:
                warnings.append("No files found in extraction directory")
            
        except Exception as e:
            warnings.append(f"Failed to scan extraction directory: {e}")
        
        return warnings
    
    def _validate_security(self, extraction_path: Path) -> List[str]:
        """
        Validate security of extracted paths.
        
        Args:
            extraction_path: Extraction directory path
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        suspicious_paths = self.security_validator.check_for_suspicious_paths(
            extraction_path
        )
        
        if suspicious_paths:
            warnings.append(
                f"Found {len(suspicious_paths)} suspicious file paths"
            )
        
        return warnings
    
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