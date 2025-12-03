"""
Path Security Validator
======================

File: engines/extractor/path_security_validator.py

Validates path security and prevents path traversal attacks.
Imported by extraction_validators.py
"""

from pathlib import Path
from typing import List

from core.system_logger import get_logger


class PathSecurityValidator:
    """
    Validates path security and prevents path traversal attacks.
    
    Responsibilities:
    - Check for path traversal attempts
    - Validate paths stay within extraction directory
    - Detect suspicious file paths
    """
    
    def __init__(self):
        """Initialize path security validator."""
        self.logger = get_logger(__name__, 'engine')
    
    def check_for_suspicious_paths(
        self,
        extraction_path: Path
    ) -> List[Path]:
        """
        Check for suspicious file paths (path traversal attempts).
        
        Args:
            extraction_path: Extraction directory
            
        Returns:
            List of suspicious paths
        """
        suspicious = []
        
        try:
            extraction_resolved = extraction_path.resolve()
            
            for file_path in extraction_path.rglob('*'):
                if self._is_path_suspicious(file_path, extraction_resolved):
                    suspicious.append(file_path)
                    self.logger.warning(f"Suspicious path detected: {file_path}")
        
        except Exception as e:
            self.logger.warning(f"Failed to check for suspicious paths: {e}")
        
        return suspicious
    
    def _is_path_suspicious(
        self,
        file_path: Path,
        extraction_resolved: Path
    ) -> bool:
        """
        Check if a single path is suspicious.
        
        Args:
            file_path: Path to check
            extraction_resolved: Resolved extraction directory path
            
        Returns:
            True if path is suspicious
        """
        try:
            # Check if path escapes extraction directory
            file_path.resolve().relative_to(extraction_resolved)
            return False
        except ValueError:
            # Path is outside extraction directory
            return True
    
    def validate_path_safety(
        self,
        file_path: Path,
        base_path: Path
    ) -> bool:
        """
        Validate a single path is safe relative to base path.
        
        Args:
            file_path: Path to validate
            base_path: Base path that file should be within
            
        Returns:
            True if path is safe
        """
        try:
            file_path.resolve().relative_to(base_path.resolve())
            return True
        except ValueError:
            return False