# File: /map_pro/core/validation_checks.py

"""
Map Pro Validation Checks
=========================

Implements validation coordination for Map Pro system components.
Pure coordination - delegates all validation logic to specialized validators.

Architecture: Follows Single Responsibility Principle strictly.
Sole responsibility: Coordinate validation checks and aggregate results.

This module has been further enhanced to:
- validation_checks.py (this file) - Pure coordination only
- startup_validation_runner.py - Startup checks workflow
- runtime_validation_runner.py - Runtime checks workflow
- validation_result_aggregator.py - Result aggregation

Improvements Made:
- Separated validation types into focused classes (already done)
- Extracted check running workflows (NEW)
- Extracted result aggregation (NEW)
- Pure facade pattern - zero validation logic
- Enhanced testability
- Maintained 100% backward compatibility

Responsibilities:
- Provide public API for validation
- Coordinate validator instantiation
- Delegate to validation runners

Does NOT handle:
- Individual validation logic (validators handle this)
- Check execution workflows (runners handle this)
- Result aggregation (aggregator handles this)
- Alert generation (alert_manager handles this)
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger

from .directory_validator import DirectoryValidator
from .partition_separation_validator import PartitionSeparationValidator
from .file_size_validator import FileSizeValidator
from .config_validator import ConfigValidator
from .database_connectivity_validator import DatabaseConnectivityValidator
from .permissions_validator import PermissionsValidator
from .engine_readiness_validator import EngineReadinessValidator

from .startup_validation_runner import StartupValidationRunner
from .runtime_validation_runner import RuntimeValidationRunner

logger = get_logger(__name__, 'core')


class ValidationChecks:
    """
    Coordinates validation checks for Map Pro system.
    
    SINGLE RESPONSIBILITY: Provide validation API and coordinate validators.
    
    This class is now a pure facade:
    - Instantiates validators once
    - Delegates to specialized runners
    - Provides clean public API
    - Zero validation or workflow logic
    
    Does NOT implement:
    - Individual validation logic (validators handle this)
    - Check execution workflows (runners handle this)  
    - Result aggregation (runners handle this)
    - Alert generation (alert_manager handles this)
    """
    
    def __init__(
        self,
        directory_validator: Optional[DirectoryValidator] = None,
        partition_validator: Optional[PartitionSeparationValidator] = None,
        file_size_validator: Optional[FileSizeValidator] = None,
        config_validator: Optional[ConfigValidator] = None,
        db_validator: Optional[DatabaseConnectivityValidator] = None,
        permissions_validator: Optional[PermissionsValidator] = None,
        engine_readiness_validator: Optional[EngineReadinessValidator] = None,
        startup_runner: Optional[StartupValidationRunner] = None,
        runtime_runner: Optional[RuntimeValidationRunner] = None
    ):
        """
        Initialize validation checks with optional dependencies.
        
        Args:
            directory_validator: Directory validator (created if None)
            partition_validator: Partition validator (created if None)
            file_size_validator: File size validator (created if None)
            config_validator: Config validator (created if None)
            db_validator: Database validator (created if None)
            permissions_validator: Permissions validator (created if None)
            engine_readiness_validator: Engine readiness validator (created if None)
            startup_runner: Startup validation runner (created if None)
            runtime_runner: Runtime validation runner (created if None)
        """
        # Initialize validators
        self.directory_validator = directory_validator or DirectoryValidator()
        self.partition_validator = partition_validator or PartitionSeparationValidator()
        self.file_size_validator = file_size_validator or FileSizeValidator()
        self.config_validator = config_validator or ConfigValidator()
        self.db_validator = db_validator or DatabaseConnectivityValidator()
        self.permissions_validator = permissions_validator or PermissionsValidator()
        
        # Engine readiness validator with dependencies
        self.engine_readiness_validator = engine_readiness_validator or EngineReadinessValidator(
            self.db_validator,
            self.partition_validator,
            self.directory_validator
        )
        
        # Initialize validation runners
        self.startup_runner = startup_runner or StartupValidationRunner(
            self.directory_validator,
            self.partition_validator,
            self.file_size_validator,
            self.config_validator,
            self.db_validator,
            self.permissions_validator
        )
        
        self.runtime_runner = runtime_runner or RuntimeValidationRunner(
            self.partition_validator,
            self.db_validator
        )
        
        logger.info("Validation checks component initialized")
    
    def run_all_startup_checks(self) -> Dict[str, Any]:
        """
        Run all startup validation checks.
        
        Delegates to StartupValidationRunner.
        
        Returns:
            Dictionary with all startup check results
        """
        return self.startup_runner.run_all_checks()
    
    def run_runtime_checks(self) -> Dict[str, Any]:
        """
        Run lighter validation checks for runtime.
        
        Delegates to RuntimeValidationRunner.
        
        Returns:
            Dictionary with runtime check results
        """
        return self.runtime_runner.run_all_checks()
    
    # ========================================================================
    # INDIVIDUAL VALIDATION CHECK API
    # ========================================================================
    # These provide direct access to individual validators for specific needs
    
    def validate_directory_structure(self) -> Dict[str, Any]:
        """
        Validate that required directory structure exists.
        
        Returns:
            Validation result from DirectoryValidator
        """
        return self.directory_validator.validate_directory_structure()
    
    def validate_data_program_separation(self) -> Dict[str, Any]:
        """
        Validate data/program partition separation.
        
        Returns:
            Validation result from PartitionSeparationValidator
        """
        return self.partition_validator.validate_data_program_separation()
    
    def validate_file_size_compliance(self) -> Dict[str, Any]:
        """
        Validate file size compliance.
        
        Returns:
            Validation result from FileSizeValidator
        """
        return self.file_size_validator.validate_file_size_compliance()
    
    def validate_configuration_files(self) -> Dict[str, Any]:
        """
        Validate configuration files existence and validity.
        
        Returns:
            Validation result from ConfigValidator
        """
        return self.config_validator.validate_configuration_files()
    
    def validate_database_connectivity(self) -> Dict[str, Any]:
        """
        Validate database connectivity and health.
        
        Returns:
            Validation result from DatabaseConnectivityValidator
        """
        return self.db_validator.validate_database_connectivity()
    
    def validate_permissions(self) -> Dict[str, Any]:
        """
        Validate file system permissions.
        
        Returns:
            Validation result from PermissionsValidator
        """
        return self.permissions_validator.validate_permissions()
    
    def check_engine_readiness(self, engine_name: str) -> Dict[str, Any]:
        """
        Validate that system is ready for specific engine to start.
        
        Args:
            engine_name: Name of engine requesting validation
            
        Returns:
            Engine readiness validation results
        """
        return self.engine_readiness_validator.check_engine_readiness(engine_name)


__all__ = ['ValidationChecks']