# engines/parser/arelle_resource_manager.py
"""
Arelle Resource Manager
========================

Manages lifecycle of Arelle resources (temp directories, controllers, models).
Handles initialization, cleanup, and resource tracking.

Responsibilities:
- Temporary directory management
- Controller initialization and shutdown
- Model cleanup
- Resource state tracking

Design Pattern: Resource Manager
Benefits: Centralized resource handling, proper cleanup, state tracking
"""

import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional

from .arelle_config import ArelleConfig, DEFAULT_CONFIG
from .arelle_imports import ARELLE_AVAILABLE
from .arelle_exceptions import ArelleInitializationError


class ArelleResourceManager:
    """
    Manages Arelle controller and temporary resources.
    
    Handles initialization, configuration, and cleanup of Arelle components.
    """
    
    def __init__(self, config: ArelleConfig, logger: logging.Logger):
        """
        Initialize resource manager.
        
        Args:
            config: Arelle configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.controller = None
        self.model_manager = None
        self.temp_dir: Optional[Path] = None
        self.is_initialized = False
    
    def initialize_controller(self):
        """
        Initialize Arelle controller and model manager.
        
        Returns:
            Tuple of (controller, model_manager)
            
        Raises:
            ArelleInitializationError: If initialization fails
        """
        if not ARELLE_AVAILABLE:
            error_msg = "Cannot initialize Arelle: library not available"
            self.logger.error(error_msg)
            raise ArelleInitializationError(error_msg)
        
        try:
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix=self.config.temp_dir_prefix))
            self.logger.debug(f"Created Arelle temp directory: {self.temp_dir}")
            
            # Initialize Arelle controller
            from arelle import Cntlr, ModelManager
            
            self.controller = Cntlr.Cntlr(
                logFileName=None,
                logFormat=self.config.log_format
            )
            
            # Configure logging
            self._configure_logging()
            
            # Initialize model manager
            self.model_manager = ModelManager.initialize(self.controller)
            
            if not self.model_manager:
                raise ArelleInitializationError("ModelManager.initialize() returned None")
            
            self.is_initialized = True
            self.logger.debug("Arelle resources initialized")
            
            return self.controller, self.model_manager
            
        except (OSError, IOError) as e:
            error_msg = f"Failed to create temporary directory: {e}"
            self.logger.error(error_msg)
            self.cleanup_temp_dir()
            raise ArelleInitializationError(error_msg) from e
        
        except AttributeError as e:
            error_msg = f"Arelle API error during initialization: {e}"
            self.logger.error(error_msg)
            self.cleanup_temp_dir()
            raise ArelleInitializationError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Unexpected error initializing Arelle: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.cleanup_temp_dir()
            raise ArelleInitializationError(error_msg) from e
    
    def _configure_logging(self) -> None:
        """Configure Arelle logging level."""
        try:
            if hasattr(self.controller, 'logger') and self.controller.logger:
                log_level_obj = getattr(
                    logging,
                    self.config.log_level.upper(),
                    logging.WARNING
                )
                self.controller.logger.setLevel(log_level_obj)
                self.logger.debug(f"Set Arelle log level to {self.config.log_level}")
        except (AttributeError, ValueError) as e:
            self.logger.warning(f"Could not set Arelle log level: {e}")
    
    def shutdown_controller(self) -> None:
        """
        Shutdown controller and cleanup resources.
        
        Safe to call multiple times.
        """
        if not self.is_initialized:
            self.logger.debug("Resources already shutdown or never initialized")
            return
        
        # Close model manager
        self._close_model_manager()
        
        # Close controller
        self._close_controller()
        
        # Clean up temp directory
        self.cleanup_temp_dir()
        
        # Reset state
        self.controller = None
        self.model_manager = None
        self.is_initialized = False
        
        self.logger.debug("Arelle resources shutdown complete")
    
    def _close_model_manager(self) -> None:
        """Close model manager with error handling."""
        try:
            if self.model_manager and hasattr(self.model_manager, 'close'):
                self.model_manager.close()
                self.logger.debug("Model manager closed")
        except AttributeError as e:
            self.logger.warning(f"Model manager has no close method: {e}")
        except RuntimeError as e:
            self.logger.warning(f"RuntimeError closing model manager: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error closing model manager: {e}",
                exc_info=True
            )
    
    def _close_controller(self) -> None:
        """Close controller with error handling."""
        try:
            if self.controller and hasattr(self.controller, 'close'):
                self.controller.close()
                self.logger.debug("Arelle controller closed")
        except AttributeError as e:
            self.logger.warning(f"Controller has no close method: {e}")
        except RuntimeError as e:
            self.logger.warning(f"RuntimeError closing controller: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error closing controller: {e}",
                exc_info=True
            )
    
    def cleanup_temp_dir(self) -> None:
        """
        Clean up temporary directory.
        
        Safe to call multiple times.
        """
        if not self.temp_dir:
            return
        
        if not self.temp_dir.exists():
            self.logger.debug(f"Temp directory already removed: {self.temp_dir}")
            self.temp_dir = None
            return
        
        try:
            shutil.rmtree(self.temp_dir)
            self.logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
        
        except PermissionError as e:
            self.logger.warning(
                f"Permission denied cleaning up temp directory {self.temp_dir}: {e}"
            )
        
        except OSError as e:
            self.logger.warning(
                f"OS error cleaning up temp directory {self.temp_dir}: {e}"
            )
        
        except Exception as e:
            self.logger.error(
                f"Unexpected error cleaning up temp directory {self.temp_dir}: {e}",
                exc_info=True
            )
        
        finally:
            self.temp_dir = None
    
    def cleanup_model(self, model_xbrl) -> None:
        """
        Clean up XBRL model to free memory.
        
        Args:
            model_xbrl: Model to clean up
        """
        if not model_xbrl:
            self.logger.debug("No model to clean up (model is None)")
            return
        
        try:
            if hasattr(model_xbrl, 'close'):
                model_xbrl.close()
                self.logger.debug("XBRL model closed successfully")
            else:
                self.logger.warning("Model has no close() method")
        
        except AttributeError as e:
            self.logger.warning(f"Model cleanup AttributeError: {e}")
        
        except RuntimeError as e:
            self.logger.warning(f"Model cleanup RuntimeError: {e}")
        
        except Exception as e:
            self.logger.error(
                f"Unexpected error closing XBRL model: {e}",
                exc_info=True
            )


__all__ = ['ArelleResourceManager']