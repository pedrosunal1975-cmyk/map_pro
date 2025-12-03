# File: /map_pro/core/partition_separation_validator.py

"""
Partition Separation Validator
===============================

Validates data/program partition separation.

Responsibility: Partition separation validation only.
"""

from typing import Dict, Any

from core.system_logger import get_logger
from shared.validators.partition_validator import PartitionValidator

from .validation_constants import (
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_ERROR,
    KEY_STATUS,
    KEY_DETAILS,
    KEY_ERROR,
    KEY_VIOLATIONS,
    DETAIL_DATA_IN_PROGRAM,
    DETAIL_PROGRAMS_IN_DATA,
    DETAIL_SEPARATION_COMPLIANT
)

logger = get_logger(__name__, 'core')


class PartitionSeparationValidator:
    """
    Validates data/program partition separation.
    
    Responsibility: Data/program separation validation using existing validator.
    """
    
    def __init__(self):
        """Initialize partition separation validator."""
        self.partition_validator = PartitionValidator()
        logger.debug("Partition separation validator initialized")
    
    def validate_data_program_separation(self) -> Dict[str, Any]:
        """
        Validate data/program partition separation.
        
        Returns:
            Validation result dictionary with status and details
        """
        result = self._create_base_result()
        
        try:
            violations = self.partition_validator.validate_partitions()
            
            if violations['data_in_program'] or violations['programs_in_data']:
                result[KEY_STATUS] = STATUS_FAIL
                result[KEY_VIOLATIONS] = violations
                
                result[KEY_DETAILS] = {
                    DETAIL_DATA_IN_PROGRAM: len(violations['data_in_program']),
                    DETAIL_PROGRAMS_IN_DATA: len(violations['programs_in_data'])
                }
            else:
                result[KEY_DETAILS] = {
                    DETAIL_SEPARATION_COMPLIANT: True
                }
                
        except Exception as e:
            result[KEY_STATUS] = STATUS_ERROR
            result[KEY_ERROR] = str(e)
            logger.error(f"Partition separation validation error: {e}")
        
        return result
    
    def check_compliance(self) -> bool:
        """
        Quick check if partition separation is compliant.
        
        Returns:
            True if compliant, False otherwise
        """
        try:
            return self.partition_validator.check_compliance()
        except Exception as e:
            logger.error(f"Compliance check error: {e}")
            return False
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _create_base_result(self) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            KEY_STATUS: STATUS_PASS,
            KEY_VIOLATIONS: {},
            KEY_DETAILS: {}
        }