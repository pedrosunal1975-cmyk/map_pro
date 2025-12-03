# File: /map_pro/core/permissions_validator.py

"""
Permissions Validator
=====================

Validates file system permissions.

Responsibility: File system permissions validation only.
"""

from typing import Dict, Any, List
from pathlib import Path

from core.data_paths import map_pro_paths
from core.system_logger import get_logger

from .validation_constants import (
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_ERROR,
    KEY_STATUS,
    KEY_DETAILS,
    KEY_ERROR,
    KEY_PERMISSION_ISSUES,
    DETAIL_PATHS_TESTED,
    DETAIL_PERMISSION_ERRORS,
    PERMISSION_TEST_FILE
)

logger = get_logger(__name__, 'core')


class PermissionsValidator:
    """
    Validates file system permissions.
    
    Responsibility: File system write permission validation.
    """
    
    def __init__(self):
        """Initialize permissions validator."""
        logger.debug("Permissions validator initialized")
    
    def validate_permissions(self) -> Dict[str, Any]:
        """
        Validate file system permissions.
        
        Returns:
            Validation result dictionary with status and details
        """
        result = self._create_base_result()
        
        try:
            critical_write_paths = self._get_critical_write_paths()
            
            for path in critical_write_paths:
                self._test_write_permission(path, result)
            
            result[KEY_DETAILS] = {
                DETAIL_PATHS_TESTED: len(critical_write_paths),
                DETAIL_PERMISSION_ERRORS: len(result[KEY_PERMISSION_ISSUES])
            }
            
        except Exception as e:
            result[KEY_STATUS] = STATUS_ERROR
            result[KEY_ERROR] = str(e)
            logger.error(f"Permissions validation error: {e}")
        
        return result
    
    # ========================================================================
    # PRIVATE VALIDATION METHODS
    # ========================================================================
    
    def _create_base_result(self) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            KEY_STATUS: STATUS_PASS,
            KEY_PERMISSION_ISSUES: [],
            KEY_DETAILS: {}
        }
    
    def _get_critical_write_paths(self) -> List[Path]:
        """Get list of critical paths requiring write permissions."""
        return [
            map_pro_paths.data_temp,
            map_pro_paths.logs_system,
            map_pro_paths.outputs_root
        ]
    
    def _test_write_permission(self, path: Path, result: Dict[str, Any]) -> None:
        """
        Test write permission for a specific path.
        
        Args:
            path: Path to test
            result: Result dictionary to update
        """
        test_file = path / PERMISSION_TEST_FILE
        
        try:
            test_file.touch()
            test_file.unlink()
        except PermissionError as e:
            self._record_permission_error(path, e, result)
        except FileNotFoundError as e:
            self._record_permission_error(path, e, result)
        except Exception as e:
            logger.warning(f"Unexpected error testing {path}: {e}")
            self._record_permission_error(path, e, result)
    
    def _record_permission_error(
        self,
        path: Path,
        error: Exception,
        result: Dict[str, Any]
    ) -> None:
        """
        Record a permission error in the result.
        
        Args:
            path: Path with permission issue
            error: Exception that occurred
            result: Result dictionary to update
        """
        result[KEY_PERMISSION_ISSUES].append({
            'path': str(path),
            'error': str(error)
        })
        result[KEY_STATUS] = STATUS_FAIL