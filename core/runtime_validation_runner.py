# File: /map_pro/core/runtime_validation_runner.py

"""
Runtime Validation Runner
==========================

Executes runtime validation workflow.
Coordinates running lighter checks during system operation.

SINGLE RESPONSIBILITY: Execute runtime validation workflow.
"""

from typing import Dict, Any

from core.system_logger import get_logger

from .partition_separation_validator import PartitionSeparationValidator
from .database_connectivity_validator import DatabaseConnectivityValidator

logger = get_logger(__name__, 'core')


class RuntimeValidationRunner:
    """
    Runs runtime validation checks workflow.
    
    SINGLE RESPONSIBILITY: Execute lightweight runtime validation sequence.
    
    Responsibilities:
    - Execute runtime checks (lighter than startup)
    - Aggregate results
    - Log workflow progress
    
    Does NOT:
    - Implement validation logic (validators do this)
    - Determine overall status (system_validator does this)
    - Generate alerts (alert_manager does this)
    """
    
    def __init__(
        self,
        partition_validator: PartitionSeparationValidator,
        db_validator: DatabaseConnectivityValidator
    ):
        """
        Initialize runtime validation runner.
        
        Args:
            partition_validator: Partition separation validator
            db_validator: Database connectivity validator
        """
        self.partition_validator = partition_validator
        self.db_validator = db_validator
        
        self.logger = logger
    
    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all runtime validation checks.
        
        Returns:
            Dictionary with runtime check results
        """
        self.logger.debug("Running runtime validation checks")
        
        checks = {
            'data_program_separation': self._run_partition_check(),
            'database_connectivity': self._run_database_check()
        }
        
        self.logger.debug("Runtime validation checks completed")
        return checks
    
    def _run_partition_check(self) -> Dict[str, Any]:
        """Run partition separation validation."""
        return self.partition_validator.validate_data_program_separation()
    
    def _run_database_check(self) -> Dict[str, Any]:
        """Run database connectivity validation."""
        return self.db_validator.validate_database_connectivity()


__all__ = ['RuntimeValidationRunner']