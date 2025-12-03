# File: /map_pro/core/file_size_validator.py

"""
File Size Validator
===================

Validates file size compliance.

Responsibility: File size validation only.
"""

from typing import Dict, Any

from core.system_logger import get_logger
from tools.monitoring.file_size_checker import FileSizeChecker

from .validation_constants import (
    STATUS_PASS,
    STATUS_WARNING,
    STATUS_ERROR,
    KEY_STATUS,
    KEY_DETAILS,
    KEY_ERROR,
    KEY_VIOLATIONS,
    DETAIL_FILES_EXCEEDING_LIMIT,
    DETAIL_LARGEST_FILE_LINES,
    DETAIL_ALL_FILES_COMPLIANT
)

logger = get_logger(__name__, 'core')


class FileSizeValidator:
    """
    Validates file size compliance.
    
    Responsibility: File size validation using existing checker.
    """
    
    def __init__(self):
        """Initialize file size validator."""
        self.file_size_checker = FileSizeChecker()
        logger.debug("File size validator initialized")
    
    def validate_file_size_compliance(self) -> Dict[str, Any]:
        """
        Validate file size compliance.
        
        Returns:
            Validation result dictionary with status and details
        """
        result = self._create_base_result()
        
        try:
            violations = self.file_size_checker.scan_project()
            
            if violations:
                result[KEY_STATUS] = STATUS_WARNING  # Non-critical but should be addressed
                result[KEY_VIOLATIONS] = violations
                
                result[KEY_DETAILS] = {
                    DETAIL_FILES_EXCEEDING_LIMIT: len(violations),
                    DETAIL_LARGEST_FILE_LINES: self._get_largest_file_lines(violations)
                }
                
                # Add detailed warning message for better visibility
                result['warning_message'] = self._format_violation_message(violations)
            else:
                result[KEY_DETAILS] = {
                    DETAIL_ALL_FILES_COMPLIANT: True
                }
                
        except Exception as e:
            result[KEY_STATUS] = STATUS_ERROR
            result[KEY_ERROR] = str(e)
            logger.error(f"File size validation error: {e}")
        
        return result
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _create_base_result(self) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            KEY_STATUS: STATUS_PASS,
            KEY_VIOLATIONS: [],
            KEY_DETAILS: {}
        }
    
    def _get_largest_file_lines(self, violations: list) -> int:
        """
        Get largest file line count from violations.
        
        Args:
            violations: List of violation tuples
            
        Returns:
            Maximum line count, or 0 if no violations
        """
        if not violations:
            return 0
        return max(v[1] for v in violations)
    
    def _format_violation_message(self, violations: list) -> str:
        """
        Format violations into a human-readable warning message.
        
        Args:
            violations: List of violation tuples (file_path, line_count, limit)
            
        Returns:
            Formatted warning message with specific file details
        """
        if not violations:
            return ""
        
        # Limit to first 3 violations to keep message concise
        display_violations = violations[:3]
        violation_details = []
        
        for violation in display_violations:
            # violation is expected to be a tuple: (file_path, line_count, limit)
            if len(violation) >= 3:
                file_path, line_count, limit = violation[0], violation[1], violation[2]
                violation_details.append(f"{file_path} ({line_count} lines exceeds {limit} limit)")
            elif len(violation) >= 2:
                # Fallback if limit not provided
                file_path, line_count = violation[0], violation[1]
                violation_details.append(f"{file_path} ({line_count} lines)")
        
        message = f"{len(violations)} file(s) exceed size limits: {', '.join(violation_details)}"
        
        if len(violations) > 3:
            message += f" ... and {len(violations) - 3} more"
        
        return message