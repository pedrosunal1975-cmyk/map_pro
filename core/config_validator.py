# File: /map_pro/core/config_validator.py

"""
Configuration Validator
========================

Validates configuration files existence and validity.

Responsibility: Configuration file validation only.

Note: Map Pro uses Python-based configuration (.py files), not JSON configs.
This validator checks for critical Python config modules.
"""

import ast
from typing import Dict, Any, List
from pathlib import Path

from core.data_paths import map_pro_paths
from core.system_logger import get_logger

from .validation_constants import (
    STATUS_PASS,
    STATUS_WARNING,
    STATUS_FAIL,
    STATUS_ERROR,
    KEY_STATUS,
    KEY_DETAILS,
    KEY_ERROR,
    KEY_MISSING_FILES,
    KEY_INVALID_FILES,
    DETAIL_CONFIGS_CHECKED,
    DETAIL_MISSING_COUNT,
    DETAIL_INVALID_COUNT
)

logger = get_logger(__name__, 'core')


class ConfigValidator:
    """
    Validates configuration files.
    
    Responsibility: Configuration file existence and validity validation.
    """
    
    def __init__(self):
        """Initialize configuration validator."""
        logger.debug("Configuration validator initialized")
    
    def validate_configuration_files(self) -> Dict[str, Any]:
        """
        Validate that required configuration files exist and are valid.
        
        Returns:
            Validation result dictionary with status and details
        """
        result = self._create_base_result()
        
        try:
            required_configs = self._get_required_config_files()
            
            for config_file in required_configs:
                self._validate_config_file(config_file, result)
            
            result[KEY_DETAILS] = {
                DETAIL_CONFIGS_CHECKED: len(required_configs),
                DETAIL_MISSING_COUNT: len(result[KEY_MISSING_FILES]),
                DETAIL_INVALID_COUNT: len(result[KEY_INVALID_FILES])
            }
            
            # Add detailed warning message if there are issues
            if result[KEY_MISSING_FILES] or result[KEY_INVALID_FILES]:
                result['warning_message'] = self._format_config_issues_message(result)
            
        except Exception as e:
            result[KEY_STATUS] = STATUS_ERROR
            result[KEY_ERROR] = str(e)
            logger.error(f"Configuration validation error: {e}")
        
        return result
    
    # ========================================================================
    # PRIVATE VALIDATION METHODS
    # ========================================================================
    
    def _create_base_result(self) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            KEY_STATUS: STATUS_PASS,
            KEY_MISSING_FILES: [],
            KEY_INVALID_FILES: [],
            KEY_DETAILS: {}
        }
    
    def _get_required_config_files(self) -> List[Path]:
        """
        Get list of required Python configuration files.
        
        Map Pro uses Python-based configuration, so we check for critical .py config modules.
        Returns:
            List of Path objects to Python config files
        """
        program_root = map_pro_paths.program_root
        
        return [
            program_root / 'application_config.py',     # Main application configuration
            program_root / 'core' / 'data_paths.py',    # Data paths configuration
        ]
    
    def _validate_config_file(self, config_file: Path, result: Dict[str, Any]) -> None:
        """
        Validate a single configuration file.
        
        Args:
            config_file: Path to configuration file
            result: Result dictionary to update
        """
        if not config_file.exists():
            result[KEY_MISSING_FILES].append(str(config_file))
            result[KEY_STATUS] = STATUS_WARNING
        else:
            self._validate_json_syntax(config_file, result)
    
    def _validate_json_syntax(self, config_file: Path, result: Dict[str, Any]) -> None:
        """
        Validate Python syntax of configuration file.
        
        Args:
            config_file: Path to configuration file
            result: Result dictionary to update
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
                # Parse Python syntax
                ast.parse(source_code)
        except SyntaxError as e:
            result[KEY_INVALID_FILES].append(str(config_file))
            result[KEY_STATUS] = STATUS_FAIL
            logger.warning(f"Invalid Python syntax in {config_file}: {e}")
        except IOError as e:
            result[KEY_INVALID_FILES].append(str(config_file))
            result[KEY_STATUS] = STATUS_FAIL
            logger.warning(f"Cannot read {config_file}: {e}")
    
    def _format_config_issues_message(self, result: Dict[str, Any]) -> str:
        """
        Format configuration issues into a human-readable warning message.
        
        Args:
            result: Validation result dictionary
            
        Returns:
            Formatted warning message with specific config file details
        """
        messages = []
        
        missing_files = result.get(KEY_MISSING_FILES, [])
        invalid_files = result.get(KEY_INVALID_FILES, [])
        
        if missing_files:
            # Show only filenames for brevity, not full paths
            missing_names = [Path(f).name for f in missing_files]
            messages.append(f"missing: {', '.join(missing_names)}")
        
        if invalid_files:
            # Show only filenames for brevity
            invalid_names = [Path(f).name for f in invalid_files]
            messages.append(f"invalid: {', '.join(invalid_names)}")
        
        if messages:
            return f"Config issues - {'; '.join(messages)}"
        
        return ""