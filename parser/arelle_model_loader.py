# engines/parser/arelle_model_loader.py
"""
Arelle Model Loader
===================

Handles loading and validation of XBRL models.
Provides clean interface for model operations with statistics tracking.

Responsibilities:
- Load XBRL models from files
- Track loading statistics
- Validate loaded models
- Error handling for load operations

Design Pattern: Loader Pattern
Benefits: Separation of concerns, statistics tracking, testability
"""

import logging
import time
from pathlib import Path
from typing import Optional, Union, Dict, Any
from contextlib import contextmanager

from .arelle_exceptions import ArelleModelLoadError


class ArelleModelLoader:
    """
    Loads and validates XBRL models using Arelle.
    
    Tracks statistics and handles errors during loading.
    """
    
    def __init__(self, model_manager, logger: logging.Logger):
        """
        Initialize model loader.
        
        Args:
            model_manager: Arelle ModelManager instance
            logger: Logger instance
        """
        self.model_manager = model_manager
        self.logger = logger
        
        # Statistics tracking
        self.stats = {
            'models_loaded': 0,
            'load_failures': 0,
            'total_load_time': 0.0
        }
    
    def load_model(self, file_path: Union[Path, str]):
        """
        Load XBRL model from file.
        
        Args:
            file_path: Path to XBRL file (Path object or string)
            
        Returns:
            ModelXbrl instance or None if loading failed
            
        Raises:
            ArelleModelLoadError: If controller not initialized
        """
        if not self.model_manager:
            error_msg = "Model manager not initialized. Initialize controller first."
            self.logger.error(error_msg)
            raise ArelleModelLoadError(error_msg)
        
        # Convert to Path if string
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        
        if not file_path.exists():
            error_msg = f"XBRL file not found: {file_path}"
            self.logger.error(error_msg)
            self.stats['load_failures'] += 1
            return None
        
        try:
            start_time = time.time()
            
            # Use modelManager.load() as per Arelle best practices
            model_xbrl = self.model_manager.load(str(file_path))
            
            load_time = time.time() - start_time
            self.stats['total_load_time'] += load_time
            
            if model_xbrl:
                self.stats['models_loaded'] += 1
                self.logger.debug(
                    f"Loaded XBRL model: {file_path.name} "
                    f"({load_time:.2f}s, {self.stats['models_loaded']} total)"
                )
                return model_xbrl
            else:
                error_msg = f"ModelManager.load() returned None for: {file_path}"
                self.logger.error(error_msg)
                self.stats['load_failures'] += 1
                return None
        
        except FileNotFoundError as e:
            error_msg = f"File not found during load: {file_path}"
            self.logger.error(error_msg)
            self.stats['load_failures'] += 1
            return None
        
        except PermissionError as e:
            error_msg = f"Permission denied reading file: {file_path}"
            self.logger.error(error_msg)
            self.stats['load_failures'] += 1
            return None
        
        except (AttributeError, TypeError) as e:
            error_msg = f"Arelle API error loading model from {file_path}: {e}"
            self.logger.error(error_msg)
            self.stats['load_failures'] += 1
            return None
        
        except Exception as e:
            error_msg = f"Unexpected error loading XBRL model from {file_path}: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.stats['load_failures'] += 1
            return None
    
    @contextmanager
    def load_context(self, file_path: Union[Path, str], cleanup_callback):
        """
        Context manager for loading and cleaning up XBRL model.
        
        Usage:
            with loader.load_context(file_path, cleanup_func) as model_xbrl:
                if model_xbrl:
                    # Use model_xbrl
                    pass
            # Automatically cleaned up
        
        Args:
            file_path: Path to XBRL file (Path object or string)
            cleanup_callback: Function to call for cleanup
            
        Yields:
            ModelXbrl instance or None if loading failed
        """
        model_xbrl = None
        try:
            model_xbrl = self.load_model(file_path)
            yield model_xbrl
        finally:
            if model_xbrl and cleanup_callback:
                cleanup_callback(model_xbrl)
    
    def validate_model(self, model_xbrl) -> Dict[str, Any]:
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
        validation = {
            'valid': False,
            'facts_count': 0,
            'contexts_count': 0,
            'units_count': 0,
            'errors': [],
            'warnings': []
        }
        
        if not model_xbrl:
            validation['errors'].append("Model is None")
            return validation
        
        try:
            # Check for basic structure with proper attribute checking
            if hasattr(model_xbrl, 'facts'):
                try:
                    validation['facts_count'] = len(model_xbrl.facts)
                except TypeError as e:
                    validation['warnings'].append(f"Cannot determine facts count: {e}")
            
            if hasattr(model_xbrl, 'contexts'):
                try:
                    validation['contexts_count'] = len(model_xbrl.contexts)
                except TypeError as e:
                    validation['warnings'].append(
                        f"Cannot determine contexts count: {e}"
                    )
            
            if hasattr(model_xbrl, 'units'):
                try:
                    validation['units_count'] = len(model_xbrl.units)
                except TypeError as e:
                    validation['warnings'].append(f"Cannot determine units count: {e}")
            
            # Check for Arelle-reported errors
            if hasattr(model_xbrl, 'errors') and model_xbrl.errors:
                try:
                    validation['errors'].extend([str(err) for err in model_xbrl.errors])
                except (TypeError, AttributeError) as e:
                    validation['warnings'].append(f"Cannot read model errors: {e}")
            
            # Basic validation logic
            if validation['facts_count'] > 0:
                validation['valid'] = True
            else:
                validation['warnings'].append("No facts found in model")
            
            if validation['contexts_count'] == 0:
                validation['warnings'].append("No contexts found in model")
        
        except AttributeError as e:
            validation['errors'].append(f"Model structure error: {str(e)}")
        
        except Exception as e:
            validation['errors'].append(f"Validation error: {str(e)}")
            self.logger.error(f"Unexpected validation error: {e}", exc_info=True)
        
        return validation
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get loader statistics.
        
        Returns:
            Dictionary containing loading statistics
        """
        stats = self.stats.copy()
        
        if stats['models_loaded'] > 0:
            stats['average_load_time'] = (
                stats['total_load_time'] / stats['models_loaded']
            )
        else:
            stats['average_load_time'] = 0.0
        
        return stats


__all__ = ['ArelleModelLoader']