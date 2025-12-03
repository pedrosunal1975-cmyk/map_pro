# File: /map_pro/core/directory_validator.py

"""
Directory Structure Validator
==============================

Validates directory structure and existence.

Responsibility: Directory validation only.
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
    KEY_MISSING_DIRECTORIES,
    DETAIL_DATA_DIRS_CHECKED,
    DETAIL_PROGRAM_DIRS_CHECKED,
    DETAIL_PROGRAM_MISSING
)

logger = get_logger(__name__, 'core')


class DirectoryValidator:
    """
    Validates directory structure exists and is correct.
    
    Responsibility: Directory existence and structure validation.
    """
    
    def __init__(self):
        """Initialize directory validator."""
        logger.debug("Directory validator initialized")
    
    def validate_directory_structure(self) -> Dict[str, Any]:
        """
        Validate that required directory structure exists.
        
        Returns:
            Validation result dictionary with status and details
        """
        result = self._create_base_result()
        
        try:
            # Validate critical data directories
            self._validate_data_directories(result)
            
            # Validate program directories
            self._validate_program_directories(result)
            
        except Exception as e:
            result[KEY_STATUS] = STATUS_ERROR
            result[KEY_ERROR] = str(e)
            logger.error(f"Directory validation error: {e}")
        
        return result
    
    def check_engine_directories(self, engine_name: str) -> List[Path]:
        """
        Get required directories for specific engine.
        
        Args:
            engine_name: Name of engine
            
        Returns:
            List of required paths that don't exist
        """
        required_paths = self._get_engine_required_paths(engine_name)
        missing_paths = []
        
        for path in required_paths:
            if not path.exists():
                missing_paths.append(path)
        
        return missing_paths
    
    # ========================================================================
    # PRIVATE VALIDATION METHODS
    # ========================================================================
    
    def _create_base_result(self) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            KEY_STATUS: STATUS_PASS,
            KEY_MISSING_DIRECTORIES: [],
            KEY_DETAILS: {}
        }
    
    def _validate_data_directories(self, result: Dict[str, Any]) -> None:
        """Validate critical data directories exist."""
        critical_directories = self._get_critical_data_directories()
        
        for directory in critical_directories:
            if not directory.exists():
                result[KEY_MISSING_DIRECTORIES].append(str(directory))
                result[KEY_STATUS] = STATUS_FAIL
        
        result[KEY_DETAILS][DETAIL_DATA_DIRS_CHECKED] = len(critical_directories)
    
    def _validate_program_directories(self, result: Dict[str, Any]) -> None:
        """Validate program directories exist."""
        program_directories = self._get_program_directories()
        program_missing = []
        
        for directory in program_directories:
            if not directory.exists():
                program_missing.append(str(directory))
                result[KEY_STATUS] = STATUS_FAIL
        
        result[KEY_DETAILS][DETAIL_PROGRAM_DIRS_CHECKED] = len(program_directories)
        result[KEY_DETAILS][DETAIL_PROGRAM_MISSING] = program_missing
    
    def _get_critical_data_directories(self) -> List[Path]:
        """Get list of critical data directories."""
        return [
            map_pro_paths.data_entities,
            map_pro_paths.data_parsed_facts,
            map_pro_paths.data_taxonomies,
            map_pro_paths.data_mapped_statements,
            map_pro_paths.config_system,
            map_pro_paths.logs_engines,
            map_pro_paths.postgresql_data
        ]
    
    def _get_program_directories(self) -> List[Path]:
        """Get list of program directories."""
        return [
            map_pro_paths.core,
            map_pro_paths.engines,
            map_pro_paths.markets,
            map_pro_paths.shared
        ]
    
    def _get_engine_required_paths(self, engine_name: str) -> List[Path]:
        """
        Get required paths for specific engine.
        
        Args:
            engine_name: Name of engine
            
        Returns:
            List of required paths
        """
        from .validation_constants import (
            ENGINE_SEARCHER,
            ENGINE_DOWNLOADER,
            ENGINE_EXTRACTOR,
            ENGINE_PARSER,
            ENGINE_LIBRARIAN,
            ENGINE_MAPPER
        )
        
        common_paths = [
            map_pro_paths.logs_engines,
            map_pro_paths.data_temp
        ]
        
        engine_specific_paths = {
            ENGINE_SEARCHER: [map_pro_paths.data_entities],
            ENGINE_DOWNLOADER: [map_pro_paths.data_entities],
            ENGINE_EXTRACTOR: [map_pro_paths.data_entities],
            ENGINE_PARSER: [map_pro_paths.data_parsed_facts, map_pro_paths.data_taxonomies],
            ENGINE_LIBRARIAN: [map_pro_paths.data_taxonomies],
            ENGINE_MAPPER: [map_pro_paths.data_mapped_statements]
        }
        
        return common_paths + engine_specific_paths.get(engine_name, [])