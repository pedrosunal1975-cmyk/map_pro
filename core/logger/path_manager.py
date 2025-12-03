# File: /map_pro/core/logger/path_manager.py
"""
Log Path Manager
================

Manages log directory creation and path determination.

Responsibility: File system operations for logging infrastructure.
"""

from pathlib import Path
from typing import Optional

from ..data_paths import map_pro_paths
from .exceptions import LogPathError
from .constants import (
    ENGINE_NAMES,
    SYSTEM_LOG_FILE,
    CORE_LOG_FILE,
    MARKET_LOG_FILE,
    INTEGRATION_LOG_FILE
)


class LogPathManager:
    """
    Manages log directory creation and path determination.
    
    Ensures all necessary log directories exist and provides
    appropriate log file paths based on component type.
    """
    
    def __init__(self):
        """Initialize path manager with centralized paths."""
        self.paths = map_pro_paths
    
    def ensure_log_directories(self) -> None:
        """
        Create all necessary log directories.
        
        Creates the main log directories and engine-specific subdirectories.
        
        Raises:
            LogPathError: If directory creation fails
        """
        log_directories = [
            self.paths.logs_engines,
            self.paths.logs_integrations,
            self.paths.logs_system,
            self.paths.logs_alerts
        ]
        
        # Add engine-specific log directories
        for engine_name in ENGINE_NAMES:
            log_directories.append(self.paths.get_engine_log_path(engine_name))
        
        # Create all directories
        for directory in log_directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise LogPathError(
                    f"Failed to create log directory {directory}: {e}"
                ) from e
            except Exception as e:
                raise LogPathError(
                    f"Unexpected error creating log directory {directory}: {e}"
                ) from e
    
    def get_log_file_path(
        self, 
        name: str, 
        component_type: Optional[str] = None
    ) -> Optional[Path]:
        """
        Determine appropriate log file path based on component type.
        
        Args:
            name: Logger name (typically module __name__)
            component_type: Type of component ('engine', 'integration', 'core', 'market')
            
        Returns:
            Path to log file or None if not file-based
            
        Examples:
            get_log_file_path('engines.parser', 'engine')
            # Returns: /logs/engines/parser/parser.log
            
            get_log_file_path('core.database', 'core')
            # Returns: /logs/system/core_operations.log
        """
        if component_type == 'engine':
            return self._get_engine_log_path(name)
        
        elif component_type == 'integration':
            return self.paths.logs_integrations / INTEGRATION_LOG_FILE
        
        elif component_type == 'core':
            return self.paths.logs_system / CORE_LOG_FILE
        
        elif component_type == 'market':
            return self.paths.logs_system / MARKET_LOG_FILE
        
        else:
            return self.paths.logs_system / SYSTEM_LOG_FILE
    
    def _get_engine_log_path(self, name: str) -> Optional[Path]:
        """
        Get log path for engine components.
        
        Args:
            name: Module name containing engine identifier
            
        Returns:
            Path to engine log file or None if not an engine
        """
        engine_name = self._extract_engine_name(name)
        if engine_name:
            return self.paths.get_engine_log_path(engine_name) / f"{engine_name}.log"
        return None
    
    def _extract_engine_name(self, name: str) -> Optional[str]:
        """
        Extract engine name from module name.
        
        Searches for known engine names within the module path.
        
        Args:
            name: Module name (e.g., 'engines.parser.coordinator')
            
        Returns:
            Engine name if found, None otherwise
            
        Examples:
            _extract_engine_name('engines.parser.coordinator') -> 'parser'
            _extract_engine_name('core.system_manager') -> None
        """
        name_lower = name.lower()
        for engine_name in ENGINE_NAMES:
            if engine_name in name_lower:
                return engine_name
        return None
    
    def get_alert_log_path(self) -> Path:
        """
        Get path for alert log file.
        
        Returns:
            Path to alert log file
        """
        from .constants import ALERT_LOG_FILE
        return self.paths.logs_alerts / ALERT_LOG_FILE
    
    def validate_log_path(self, path: Path) -> bool:
        """
        Validate that a log path is writable.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is writable, False otherwise
        """
        try:
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Test write access by creating a temporary file
            test_file = path.parent / f".write_test_{path.name}"
            try:
                test_file.touch()
                test_file.unlink()
                return True
            except OSError:
                return False
                
        except Exception:
            return False