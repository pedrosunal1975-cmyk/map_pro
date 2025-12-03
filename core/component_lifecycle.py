"""
Map Pro Component Lifecycle
===========================

Handles component lifecycle operations: initialize, start, stop, restart.
Manages individual component state transitions.

Save location: core/component_lifecycle.py
"""

import asyncio
from datetime import datetime, timezone
from .system_logger import get_logger
from .component_registry import ComponentState
from shared.exceptions.custom_exceptions import ComponentError

logger = get_logger(__name__, 'core')


class ComponentLifecycle:
    """
    Manages component lifecycle operations.
    
    Responsibilities:
    - Component initialization
    - Component startup
    - Component shutdown
    - Component restart
    - State transition management
    
    Does NOT handle:
    - Component registration (ComponentRegistry handles this)
    - Dependency ordering (DependencyResolver handles this)
    - Health monitoring (ComponentManager handles this)
    """
    
    def __init__(self, registry):
        self.registry = registry
        logger.debug("Component lifecycle manager initialized")
    
    async def initialize_component(self, name: str) -> bool:
        """
        Initialize a specific component.
        
        Args:
            name: Component name
            
        Returns:
            True if initialization successful, False otherwise
        """
        component_info = self.registry.get_component(name)
        if not component_info:
            logger.error(f"Cannot initialize unknown component: {name}")
            return False
        
        try:
            self.registry.update_component_state(name, ComponentState.INITIALIZING)
            
            # Check if component has initialize method
            if hasattr(component_info.component_instance, 'initialize'):
                result = component_info.component_instance.initialize()
                
                # Handle async initialize methods
                if asyncio.iscoroutine(result):
                    result = await result
                
                if not result:
                    raise ComponentError(f"Component {name} initialize() returned False")
            
            self.registry.update_component_state(name, ComponentState.INITIALIZED)
            component_info.initialization_time = datetime.now(timezone.utc)
            
            logger.info(f"Component {name} initialized successfully")
            return True
            
        except Exception as e:
            self.registry.record_error(name, str(e))
            logger.error(f"Failed to initialize component {name}: {e}")
            return False
    
    async def start_component(self, name: str) -> bool:
        """
        Start a specific component.
        
        Args:
            name: Component name
            
        Returns:
            True if start successful, False otherwise
        """
        component_info = self.registry.get_component(name)
        if not component_info:
            logger.error(f"Cannot start unknown component: {name}")
            return False
        
        # Skip if already running
        if component_info.state == ComponentState.RUNNING:
            return True
        
        try:
            self.registry.update_component_state(name, ComponentState.STARTING)
            
            # Check if component has start method
            if hasattr(component_info.component_instance, 'start'):
                result = component_info.component_instance.start()
                
                # Handle async start methods
                if asyncio.iscoroutine(result):
                    result = await result
                
                if not result:
                    raise ComponentError(f"Component {name} start() returned False")
            
            self.registry.update_component_state(name, ComponentState.RUNNING)
            component_info.startup_time = datetime.now(timezone.utc)
            
            logger.info(f"Component {name} started successfully")
            return True
            
        except Exception as e:
            self.registry.record_error(name, str(e))
            logger.error(f"Failed to start component {name}: {e}")
            return False
    
    async def stop_component(self, name: str) -> bool:
        """
        Stop a specific component.
        
        Args:
            name: Component name
            
        Returns:
            True if stop successful, False otherwise
        """
        component_info = self.registry.get_component(name)
        if not component_info:
            return True
        
        # Skip if already stopped
        if component_info.state in [ComponentState.STOPPED, ComponentState.FAILED]:
            return True
        
        try:
            self.registry.update_component_state(name, ComponentState.STOPPING)
            
            # Check if component has stop method
            if hasattr(component_info.component_instance, 'stop'):
                result = component_info.component_instance.stop()
                
                # Handle async stop methods
                if asyncio.iscoroutine(result):
                    result = await result
                
                # Don't fail shutdown if stop() returns False
                if not result:
                    logger.warning(f"Component {name} stop() returned False")
            
            self.registry.update_component_state(name, ComponentState.STOPPED)
            
            logger.info(f"Component {name} stopped successfully")
            return True
            
        except Exception as e:
            self.registry.record_error(name, str(e))
            logger.error(f"Failed to stop component {name}: {e}")
            return False
    
    async def restart_component(self, name: str) -> bool:
        """
        Restart a specific component.
        
        Args:
            name: Component name
            
        Returns:
            True if restart successful, False otherwise
        """
        if not self.registry.component_exists(name):
            logger.error(f"Cannot restart unknown component: {name}")
            return False
        
        logger.info(f"Restarting component: {name}")
        
        try:
            # Stop component
            if not await self.stop_component(name):
                logger.warning(f"Component {name} did not stop cleanly")
            
            # Start component
            if not await self.start_component(name):
                logger.error(f"Component {name} failed to restart")
                return False
            
            logger.info(f"Component {name} restarted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart component {name}: {e}")
            return False