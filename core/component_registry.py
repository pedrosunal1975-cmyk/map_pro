"""
Map Pro Component Registry
==========================

Manages component registration and dependency tracking.
Handles component information storage and retrieval.

Save location: core/component_registry.py
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from .system_logger import get_logger

logger = get_logger(__name__, 'core')


class ComponentState(Enum):
    """Component lifecycle states."""
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ComponentInfo:
    """Information about a registered component."""
    name: str
    component_instance: Any
    dependencies: List[str]
    state: ComponentState
    initialization_time: Optional[datetime] = None
    startup_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None


class ComponentRegistry:
    """
    Registry for all Map Pro components.
    
    Responsibilities:
    - Component registration with dependency tracking
    - Component information storage and retrieval
    - Dependency validation
    
    Does NOT handle:
    - Component lifecycle operations (ComponentLifecycle handles this)
    - Startup/shutdown ordering (DependencyResolver handles this)
    - Component health monitoring (ComponentManager handles this)
    """
    
    def __init__(self):
        self.components: Dict[str, ComponentInfo] = {}
        logger.info("Component registry initialized")
    
    def register(self, name: str, component_instance: Any, 
                dependencies: List[str], critical: bool = False) -> bool:
        """
        Register a component with the registry.
        
        Args:
            name: Unique component name
            component_instance: The component object
            dependencies: List of component names this depends on
            critical: Whether component is critical for system operation
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            if name in self.components:
                logger.warning(f"Component {name} already registered, updating")
            
            # Validate dependencies exist or will be registered
            for dep in dependencies:
                if dep not in self.components:
                    logger.info(f"Component {name} depends on {dep} (not yet registered)")
            
            component_info = ComponentInfo(
                name=name,
                component_instance=component_instance,
                dependencies=dependencies,
                state=ComponentState.REGISTERED
            )
            
            self.components[name] = component_info
            
            logger.info(f"Registered component: {name} with dependencies: {dependencies}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register component {name}: {e}")
            return False
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a component from the registry.
        
        Args:
            name: Component name to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            if name not in self.components:
                logger.warning(f"Component {name} not registered")
                return False
            
            del self.components[name]
            logger.info(f"Unregistered component: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister component {name}: {e}")
            return False
    
    def get_component(self, name: str) -> Optional[ComponentInfo]:
        """
        Get component information by name.
        
        Args:
            name: Component name
            
        Returns:
            ComponentInfo if found, None otherwise
        """
        return self.components.get(name)
    
    def get_all_components(self) -> Dict[str, ComponentInfo]:
        """
        Get all registered components.
        
        Returns:
            Dictionary of all components
        """
        return self.components.copy()
    
    def component_exists(self, name: str) -> bool:
        """
        Check if component is registered.
        
        Args:
            name: Component name
            
        Returns:
            True if component exists, False otherwise
        """
        return name in self.components
    
    def update_component_state(self, name: str, state: ComponentState) -> bool:
        """
        Update component state.
        
        Args:
            name: Component name
            state: New component state
            
        Returns:
            True if update successful, False otherwise
        """
        if name not in self.components:
            logger.error(f"Cannot update state for unknown component: {name}")
            return False
        
        self.components[name].state = state
        return True
    
    def record_error(self, name: str, error: str):
        """
        Record an error for a component.
        
        Args:
            name: Component name
            error: Error message
        """
        if name in self.components:
            self.components[name].error_count += 1
            self.components[name].last_error = error
            self.components[name].state = ComponentState.FAILED
    
    def get_component_status(self) -> Dict[str, Any]:
        """
        Get status information for all components.
        
        Returns:
            Dictionary with component status
        """
        return {
            'total_components': len(self.components),
            'components': {
                name: {
                    'state': info.state.value,
                    'dependencies': info.dependencies,
                    'initialization_time': info.initialization_time.isoformat() if info.initialization_time else None,
                    'startup_time': info.startup_time.isoformat() if info.startup_time else None,
                    'error_count': info.error_count,
                    'last_error': info.last_error
                }
                for name, info in self.components.items()
            }
        }