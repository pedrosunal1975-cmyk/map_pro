# File: /map_pro/core/startup_validation_runner.py

"""
Startup Validation Runner
==========================

Executes startup validation workflow.
Coordinates running all startup checks in proper order.

SINGLE RESPONSIBILITY: Execute startup validation workflow.
"""

from typing import Dict, Any

from core.system_logger import get_logger

from .directory_validator import DirectoryValidator
from .partition_separation_validator import PartitionSeparationValidator
from .file_size_validator import FileSizeValidator
from .config_validator import ConfigValidator
from .database_connectivity_validator import DatabaseConnectivityValidator
from .permissions_validator import PermissionsValidator

logger = get_logger(__name__, 'core')


class StartupValidationRunner:
    """
    Runs startup validation checks workflow.
    
    SINGLE RESPONSIBILITY: Execute complete startup validation sequence.
    
    Responsibilities:
    - Execute startup checks in proper order
    - Aggregate results
    - Log workflow progress
    
    Does NOT:
    - Implement validation logic (validators do this)
    - Determine overall status (system_validator does this)
    - Generate alerts (alert_manager does this)
    """
    
    def __init__(
        self,
        directory_validator: DirectoryValidator,
        partition_validator: PartitionSeparationValidator,
        file_size_validator: FileSizeValidator,
        config_validator: ConfigValidator,
        db_validator: DatabaseConnectivityValidator,
        permissions_validator: PermissionsValidator
    ):
        """
        Initialize startup validation runner.
        
        Args:
            directory_validator: Directory structure validator
            partition_validator: Partition separation validator
            file_size_validator: File size compliance validator
            config_validator: Configuration validator
            db_validator: Database connectivity validator
            permissions_validator: Permissions validator
        """
        self.directory_validator = directory_validator
        self.partition_validator = partition_validator
        self.file_size_validator = file_size_validator
        self.config_validator = config_validator
        self.db_validator = db_validator
        self.permissions_validator = permissions_validator
        
        self.logger = logger
    
    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all startup validation checks.
        
        Returns:
            Dictionary with all startup check results
        """
        self.logger.debug("Running all startup validation checks")
        
        checks = {
            'directory_structure': self._run_directory_check(),
            'data_program_separation': self._run_partition_check(),
            'file_size_compliance': self._run_file_size_check(),
            'configuration_files': self._run_config_check(),
            'database_connectivity': self._run_database_check(),
            'permissions': self._run_permissions_check()
        }
        
        self.logger.debug("Startup validation checks completed")
        return checks
    
    def _run_directory_check(self) -> Dict[str, Any]:
        """Run directory structure validation."""
        return self.directory_validator.validate_directory_structure()
    
    def _run_partition_check(self) -> Dict[str, Any]:
        """Run partition separation validation."""
        return self.partition_validator.validate_data_program_separation()
    
    def _run_file_size_check(self) -> Dict[str, Any]:
        """Run file size compliance validation."""
        return self.file_size_validator.validate_file_size_compliance()
    
    def _run_config_check(self) -> Dict[str, Any]:
        """Run configuration files validation."""
        return self.config_validator.validate_configuration_files()
    
    def _run_database_check(self) -> Dict[str, Any]:
        """Run database connectivity validation."""
        return self.db_validator.validate_database_connectivity()
    
    def _run_permissions_check(self) -> Dict[str, Any]:
        """Run permissions validation."""
        return self.permissions_validator.validate_permissions()


__all__ = ['StartupValidationRunner']