# engines/parser/arelle_controller.py
"""
Map Pro Arelle Controller
=========================

Manages Arelle XBRL library lifecycle and provides clean interface for parsing.
Handles controller initialization, model loading, and resource cleanup.

Architecture: Universal Arelle management - works for all XBRL markets.
Based on grand_target's elegant Arelle-only approach.

Refactoring Notes:
- Split from 550+ lines into focused modules
- Configuration in arelle_config.py
- Exceptions in arelle_exceptions.py
- Import handling in arelle_imports.py
- Resource management in arelle_resource_manager.py
- Model loading in arelle_model_loader.py
- Main controller provides facade interface
- 100% backward compatible

Module Structure:
- arelle_config.py: Configuration and constants
- arelle_exceptions.py: Custom exception classes
- arelle_imports.py: Safe Arelle import handling
- arelle_resource_manager.py: Resource lifecycle management
- arelle_model_loader.py: Model loading and validation
- arelle_controller.py: Facade coordinating all components
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any
from contextlib import contextmanager

from core.system_logger import get_logger

# Import from split modules
from .arelle_config import ArelleConfig, DEFAULT_CONFIG
from .arelle_exceptions import (
    ArelleInitializationError,
    ArelleModelLoadError,
    ArelleValidationError
)
from .arelle_imports import (
    ARELLE_AVAILABLE,
    ARELLE_VERSION,
    ModelXbrl,
    get_arelle_info,
    check_arelle_available
)
from .arelle_resource_manager import ArelleResourceManager
from .arelle_model_loader import ArelleModelLoader


logger = get_logger(__name__, 'engine')


class ArelleController:
    """
    Manages Arelle XBRL parsing library.
    
    Responsibilities:
    - Initialize Arelle controller and model manager (via resource manager)
    - Load XBRL models from files (via model loader)
    - Manage temporary directories (via resource manager)
    - Clean up resources properly (via resource manager)
    - Provide facade interface for all Arelle operations
    
    Does NOT handle:
    - Fact extraction (fact_extractor handles this)
    - Context processing (context_processor handles this)
    - Output formatting (output_formatter handles this)
    
    Thread Safety: Not thread-safe. Create separate instances per thread.
    
    Design Pattern: Facade
    Benefits: Simple interface, delegated complexity, backward compatible
    """
    
    def __init__(
        self,
        log_level: str = None,
        config: Optional[ArelleConfig] = None
    ):
        """
        Initialize Arelle controller.
        
        Args:
            log_level: Logging level for Arelle messages (deprecated, use config)
            config: Arelle configuration object (recommended)
        """
        # Handle backward compatibility with log_level parameter
        if config is None:
            if log_level is not None:
                config = ArelleConfig(log_level=log_level)
            else:
                config = DEFAULT_CONFIG
        
        self.config = config
        self.logger = logger
        
        # Initialize component managers
        self.resource_manager = ArelleResourceManager(config, logger)
        self.model_loader: Optional[ArelleModelLoader] = None
        
        # Legacy attributes for backward compatibility
        self.controller = None
        self.model_manager = None
        self.temp_dir = None
        self.is_initialized = False
        self.log_level = config.log_level
        
        # Statistics (delegated to loader once initialized)
        self.stats = {
            'models_loaded': 0,
            'load_failures': 0,
            'total_load_time': 0.0
        }
    
    def initialize(self) -> bool:
        """
        Initialize Arelle controller and model manager.
        
        Returns:
            True if initialization successful, False otherwise
            
        Raises:
            ArelleInitializationError: If critical initialization fails
        """
        if self.is_initialized:
            self.logger.debug("Arelle controller already initialized")
            return True
        
        try:
            # Initialize resources via resource manager
            self.controller, self.model_manager = (
                self.resource_manager.initialize_controller()
            )
            
            # Initialize model loader
            self.model_loader = ArelleModelLoader(self.model_manager, self.logger)
            
            # Update legacy attributes for backward compatibility
            self.temp_dir = self.resource_manager.temp_dir
            self.is_initialized = True
            
            self.logger.info(
                f"Arelle controller initialized (version: {ARELLE_VERSION})"
            )
            return True
            
        except ArelleInitializationError:
            # Re-raise initialization errors
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error during initialization: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise ArelleInitializationError(error_msg) from e
    
    def load_xbrl_model(self, file_path: Union[Path, str]) -> Optional[ModelXbrl]:
        """
        Load XBRL model from file.
        
        Args:
            file_path: Path to XBRL file (Path object or string)
            
        Returns:
            ModelXbrl instance or None if loading failed
            
        Raises:
            ArelleModelLoadError: If controller not initialized
        """
        if not self.is_initialized or not self.model_loader:
            error_msg = "Arelle controller not initialized. Call initialize() first."
            self.logger.error(error_msg)
            raise ArelleModelLoadError(error_msg)
        
        model = self.model_loader.load_model(file_path)
        
        # Update legacy stats for backward compatibility
        self._sync_statistics()
        
        return model
    
    @contextmanager
    def load_xbrl_context(self, file_path: Union[Path, str]):
        """
        Context manager for loading and cleaning up XBRL model.
        
        Usage:
            with controller.load_xbrl_context(file_path) as model_xbrl:
                if model_xbrl:
                    # Use model_xbrl
                    pass
            # Automatically cleaned up
        
        Args:
            file_path: Path to XBRL file (Path object or string)
            
        Yields:
            ModelXbrl instance or None if loading failed
        """
        if not self.is_initialized or not self.model_loader:
            self.logger.error("Controller not initialized")
            yield None
            return
        
        with self.model_loader.load_context(
            file_path,
            self.resource_manager.cleanup_model
        ) as model_xbrl:
            yield model_xbrl
        
        # Update legacy stats
        self._sync_statistics()
    
    def cleanup_model(self, model_xbrl: ModelXbrl) -> None:
        """
        Clean up XBRL model to free memory.
        
        Args:
            model_xbrl: Model to clean up
        """
        self.resource_manager.cleanup_model(model_xbrl)
    
    def validate_model(self, model_xbrl: ModelXbrl) -> Dict[str, Any]:
        """
        Validate XBRL model and return diagnostic information.
        
        Args:
            model_xbrl: Model to validate
            
        Returns:
            Dictionary with validation results containing:
            - valid: bool indicating if model is valid
            - facts_count: number of facts in model
            - contexts_count: number of contexts
            - units_count: number of units
            - errors: list of error messages
            - warnings: list of warning messages
        """
        if not self.model_loader:
            return {
                'valid': False,
                'errors': ['Controller not initialized'],
                'warnings': [],
                'facts_count': 0,
                'contexts_count': 0,
                'units_count': 0
            }
        
        return self.model_loader.validate_model(model_xbrl)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get controller statistics.
        
        Returns:
            Dictionary containing:
            - models_loaded: total models successfully loaded
            - load_failures: total failed load attempts
            - total_load_time: cumulative time spent loading
            - average_load_time: average time per successful load
            - is_initialized: current initialization state
            - arelle_version: Arelle version string
        """
        if self.model_loader:
            stats = self.model_loader.get_statistics()
        else:
            stats = self.stats.copy()
            if stats['models_loaded'] > 0:
                stats['average_load_time'] = (
                    stats['total_load_time'] / stats['models_loaded']
                )
            else:
                stats['average_load_time'] = 0.0
        
        stats['is_initialized'] = self.is_initialized
        stats['arelle_version'] = ARELLE_VERSION
        
        return stats
    
    def shutdown(self) -> None:
        """
        Shutdown controller and cleanup resources.
        
        Safe to call multiple times. Logs warnings for cleanup failures
        but continues cleanup process.
        """
        if not self.is_initialized:
            self.logger.debug("Controller already shutdown or never initialized")
            return
        
        # Shutdown via resource manager
        self.resource_manager.shutdown_controller()
        
        # Update legacy attributes for backward compatibility
        self.controller = None
        self.model_manager = None
        self.temp_dir = None
        self.model_loader = None
        self.is_initialized = False
        
        self.logger.info("Arelle controller shutdown complete")
    
    def _sync_statistics(self) -> None:
        """Synchronize statistics from loader to legacy stats dict."""
        if self.model_loader:
            loader_stats = self.model_loader.get_statistics()
            self.stats.update({
                'models_loaded': loader_stats['models_loaded'],
                'load_failures': loader_stats['load_failures'],
                'total_load_time': loader_stats['total_load_time']
            })
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False


# Re-export for backward compatibility
__all__ = [
    'ArelleController',
    'get_arelle_info',
    'ARELLE_AVAILABLE',
    'ARELLE_VERSION',
    'ArelleInitializationError',
    'ArelleModelLoadError',
    'ArelleValidationError'
]