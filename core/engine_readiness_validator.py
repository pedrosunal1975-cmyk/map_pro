# File: /map_pro/core/engine_readiness_validator.py

"""
Engine Readiness Validator
===========================

Validates system readiness for specific engines.

Responsibility: Engine-specific readiness validation only.
"""

from typing import Dict, Any, List
from pathlib import Path

from core.data_paths import map_pro_paths
from core.system_logger import get_logger

from .validation_constants import (
    KEY_ENGINE_NAME,
    KEY_READY,
    KEY_BLOCKING_ISSUES,
    KEY_WARNINGS,
    KEY_BLOCKING,
    ENGINE_PARSER,
    ENGINE_LIBRARIAN,
    ENGINE_MAPPER,
    TAXONOMY_LIBRARIES_SUBDIR,
    TAXONOMY_DOWNLOADS_SUBDIR,
    MSG_COORDINATOR_NOT_INITIALIZED,
    MSG_PARTITION_VIOLATION,
    MSG_REQUIRED_PATH_MISSING,
    MSG_VALIDATION_ERROR,
    MSG_NO_TAXONOMY_LIBRARIES,
    MSG_NO_TAXONOMY_DOWNLOADS,
    MSG_NO_PARSED_FACTS,
    MSG_ENGINE_CHECK_FAILED
)

logger = get_logger(__name__, 'core')


class EngineReadinessValidator:
    """
    Validates system readiness for specific engines.
    
    Responsibility: Engine-specific validation and readiness checks.
    """
    
    def __init__(self, db_validator, partition_validator, directory_validator):
        """
        Initialize engine readiness validator.
        
        Args:
            db_validator: Database connectivity validator
            partition_validator: Partition separation validator
            directory_validator: Directory structure validator
        """
        self.db_validator = db_validator
        self.partition_validator = partition_validator
        self.directory_validator = directory_validator
        logger.debug("Engine readiness validator initialized")
    
    def check_engine_readiness(self, engine_name: str) -> Dict[str, Any]:
        """
        Validate that system is ready for specific engine to start.
        
        Args:
            engine_name: Name of engine requesting validation
            
        Returns:
            Engine readiness validation results
        """
        result = self._create_base_result(engine_name)
        
        try:
            # Check database connectivity
            self._check_database_readiness(result)
            
            # Check data/program separation
            self._check_partition_compliance(result)
            
            # Check required directories
            self._check_required_directories(engine_name, result)
            
            # Engine-specific checks
            self._check_engine_specific_requirements(engine_name, result)
            
        except Exception as e:
            result[KEY_READY] = False
            result[KEY_BLOCKING_ISSUES].append(
                MSG_VALIDATION_ERROR.format(error=str(e))
            )
            logger.error(f"Engine readiness validation error for {engine_name}: {e}")
        
        return result
    
    # ========================================================================
    # PRIVATE VALIDATION METHODS
    # ========================================================================
    
    def _create_base_result(self, engine_name: str) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            KEY_ENGINE_NAME: engine_name,
            KEY_READY: True,
            KEY_BLOCKING_ISSUES: [],
            KEY_WARNINGS: []
        }
    
    def _check_database_readiness(self, result: Dict[str, Any]) -> None:
        """Check if database is ready."""
        if not self.db_validator.is_database_healthy():
            result[KEY_READY] = False
            result[KEY_BLOCKING_ISSUES].append(MSG_COORDINATOR_NOT_INITIALIZED)
    
    def _check_partition_compliance(self, result: Dict[str, Any]) -> None:
        """Check if partition separation is compliant."""
        if not self.partition_validator.check_compliance():
            result[KEY_READY] = False
            result[KEY_BLOCKING_ISSUES].append(MSG_PARTITION_VIOLATION)
    
    def _check_required_directories(self, engine_name: str, result: Dict[str, Any]) -> None:
        """Check if required directories exist for engine."""
        missing_paths = self.directory_validator.check_engine_directories(engine_name)
        
        for path in missing_paths:
            result[KEY_READY] = False
            result[KEY_BLOCKING_ISSUES].append(
                MSG_REQUIRED_PATH_MISSING.format(path=path)
            )
    
    def _check_engine_specific_requirements(
        self,
        engine_name: str,
        result: Dict[str, Any]
    ) -> None:
        """Check engine-specific requirements."""
        try:
            if engine_name == ENGINE_PARSER:
                self._check_parser_requirements(result)
            elif engine_name == ENGINE_LIBRARIAN:
                self._check_librarian_requirements(result)
            elif engine_name == ENGINE_MAPPER:
                self._check_mapper_requirements(result)
                
        except Exception as e:
            result[KEY_WARNINGS].append(
                MSG_ENGINE_CHECK_FAILED.format(error=str(e))
            )
    
    def _check_parser_requirements(self, result: Dict[str, Any]) -> None:
        """Check parser-specific requirements."""
        taxonomy_path = map_pro_paths.data_taxonomies / TAXONOMY_LIBRARIES_SUBDIR
        if not taxonomy_path.exists():
            result[KEY_WARNINGS].append(MSG_NO_TAXONOMY_LIBRARIES)
    
    def _check_librarian_requirements(self, result: Dict[str, Any]) -> None:
        """Check librarian-specific requirements."""
        downloads_path = map_pro_paths.data_taxonomies / TAXONOMY_DOWNLOADS_SUBDIR
        if not downloads_path.exists():
            result[KEY_WARNINGS].append(MSG_NO_TAXONOMY_DOWNLOADS)
    
    def _check_mapper_requirements(self, result: Dict[str, Any]) -> None:
        """Check mapper-specific requirements."""
        parsed_facts_path = map_pro_paths.data_parsed_facts
        if not any(parsed_facts_path.glob('*/*')):
            result[KEY_WARNINGS].append(MSG_NO_PARSED_FACTS)