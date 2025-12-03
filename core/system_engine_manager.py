# File: /map_pro/core/system_engine_manager.py

"""
System Engine Manager
=====================

Manages engine lifecycle operations including starting, stopping, and monitoring.
...
"""

from typing import Dict, Any, List, Tuple, Optional

from .system_logger import get_logger
from .component_manager import ComponentManager

logger = get_logger(__name__, 'core')


class SystemEngineManager:
    """
    Manages engine operations and monitoring.
    ...
    """
    
    def __init__(self, component_manager: ComponentManager):
        """
        Initialize engine manager.
        
        Args:
            component_manager: Component lifecycle manager
        """
        self.component_manager = component_manager
        self._is_started = False  # [GREEN] FIX: Initialize state flag
        logger.debug("System engine manager created")
    
    async def start_engines(self) -> None:
        """
        Verify and start engine processing threads.
        
        Note: Engines are initially started by component_manager.start_components().
        This method verifies they're running and starts any stopped engines.
        """
        # [GREEN] CRITICAL FIX: Check if engines have already been started
        if self._is_started:
            logger.warning("Engine threads already verified/started. Skipping.")
            return

        logger.info("Verifying engine processing threads")
        
        try:
            # Find all registered engines
            engines = self._find_registered_engines()
            
            if not engines:
                logger.warning("No engines found - check engine registration")
                return
            
            logger.info(f"Found {len(engines)} engines")
            
            # Check and start engines as needed
            running_engines, stopped_engines = await self._check_and_start_engines(
                engines
            )
            
            # Log final status
            logger.info(
                f"Engine status: {len(running_engines)} running, "
                f"{len(stopped_engines)} stopped"
            )
            
            self._is_started = True  # [GREEN] FIX: Set status to started after success
            
        except Exception as e:
            logger.error(f"Failed to verify engine threads: {e}")
            raise
    
    def _find_registered_engines(self) -> List[Tuple[str, Any]]:
        """
        Find all registered engine components.
        
        Returns:
            List of (engine_name, engine_instance) tuples
        """
        engines = []
        
        for name, comp_info in self.component_manager.registry.components.items():
            component = comp_info.component_instance
            
            # Check if component is an engine (has job_processor)
            if self._is_engine(component):
                engines.append((name, component))
        
        return engines
    
    def _is_engine(self, component: Any) -> bool:
        """
        Check if component is an engine.
        
        Args:
            component: Component instance to check
            
        Returns:
            True if component is an engine
        """
        return (
            hasattr(component, 'start') and 
            hasattr(component, 'job_processor')
        )
    
    async def _check_and_start_engines(
        self,
        engines: List[Tuple[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """
        Check engine status and start stopped engines.
        
        Args:
            engines: List of (engine_name, engine_instance) tuples
            
        Returns:
            Tuple of (running_engines, stopped_engines) lists
        """
        running_engines = []
        stopped_engines = []
        
        for engine_name, engine_instance in engines:
            try:
                if self._is_engine_running(engine_instance):
                    running_engines.append(engine_name)
                    logger.debug(f"Engine {engine_name} is running")
                else:
                    stopped_engines.append(engine_name)
                    logger.warning(f"Engine {engine_name} is not running")
                    
                    # Attempt to start stopped engine
                    if await self._start_stopped_engine(engine_name, engine_instance):
                        running_engines.append(engine_name)
                        stopped_engines.remove(engine_name)
                        
            except Exception as e:
                logger.error(
                    f"Error checking/starting engine {engine_name}: {e}"
                )
        
        return running_engines, stopped_engines
    
    def _is_engine_running(self, engine_instance: Any) -> bool:
        """
        Check if engine is currently running.
        
        Args:
            engine_instance: Engine instance to check
            
        Returns:
            True if engine is running
        """
        return getattr(engine_instance, 'is_running', False)
    
    async def _start_stopped_engine(
        self,
        engine_name: str,
        engine_instance: Any
    ) -> bool:
        """
        Attempt to start a stopped engine.
        
        Args:
            engine_name: Name of engine
            engine_instance: Engine instance to start
            
        Returns:
            True if successfully started
        """
        logger.info(f"Attempting to start stopped engine: {engine_name}")
        
        try:
            # Ensure engine is initialized first
            if not self._ensure_engine_initialized(engine_name, engine_instance):
                return False
            
            # Start the engine
            if engine_instance.start():
                logger.info(f"Successfully started engine: {engine_name}")
                return True
            else:
                logger.error(f"Failed to start engine: {engine_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting engine {engine_name}: {e}")
            return False
    
    def _ensure_engine_initialized(
        self,
        engine_name: str,
        engine_instance: Any
    ) -> bool:
        """
        Ensure engine is initialized before starting.
        
        Args:
            engine_name: Name of engine
            engine_instance: Engine instance to check
            
        Returns:
            True if initialized or successfully initialized
        """
        if getattr(engine_instance, 'is_initialized', False):
            return True
        
        logger.debug(f"Initializing engine: {engine_name}")
        
        if engine_instance.initialize():
            logger.debug(f"Engine {engine_name} initialized")
            return True
        else:
            logger.error(f"Failed to initialize engine: {engine_name}")
            return False
    
    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get detailed status of all registered engines.
        
        Returns:
            Dictionary with engine status information
        """
        engine_status = {}
        
        try:
            for name, comp_info in self.component_manager.registry.components.items():
                component = comp_info.component_instance
                
                if self._is_engine(component):
                    engine_status[name] = self._build_engine_status(component)
                    
        except Exception as e:
            logger.error(f"Error getting engine status: {e}")
            engine_status['error'] = str(e)
        
        return engine_status
    
    def _build_engine_status(self, engine_instance: Any) -> Dict[str, Any]:
        """
        Build status dictionary for single engine.
        
        Args:
            engine_instance: Engine instance
            
        Returns:
            Status dictionary
        """
        return {
            'is_running': getattr(engine_instance, 'is_running', False),
            'is_initialized': getattr(engine_instance, 'is_initialized', False),
            'thread_alive': self._check_thread_alive(engine_instance),
            'jobs_processed': getattr(engine_instance, 'jobs_processed', 0),
            'jobs_failed': getattr(engine_instance, 'jobs_failed', 0),
            'last_activity': getattr(engine_instance, 'last_activity', None),
            'start_time': getattr(engine_instance, 'start_time', None),
            'supported_job_types': self._get_supported_job_types(engine_instance)
        }
    
    def _check_thread_alive(self, engine_instance: Any) -> bool:
        """
        Check if engine's main thread is alive.
        
        Args:
            engine_instance: Engine instance
            
        Returns:
            True if thread is alive
        """
        if not hasattr(engine_instance, '_main_thread'):
            return False
        
        thread = engine_instance._main_thread
        if thread is None:
            return False
        
        return thread.is_alive()
    
    def _get_supported_job_types(self, engine_instance: Any) -> List[str]:
        """
        Get list of job types supported by engine.
        
        Args:
            engine_instance: Engine instance
            
        Returns:
            List of supported job type strings
        """
        if not hasattr(engine_instance, 'get_supported_job_types'):
            return []
        
        try:
            return engine_instance.get_supported_job_types()
        except Exception as e:
            logger.error(f"Error getting supported job types: {e}")
            return []


__all__ = ['SystemEngineManager']