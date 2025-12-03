"""
Map Pro Component Manager
=========================

Coordinates component lifecycle and dependencies across all Map Pro system components.
Integrates ComponentRegistry, DependencyResolver, and ComponentLifecycle.

Save location: core/component_manager.py
"""

from typing import Dict, List, Any
from datetime import datetime, timezone

from .system_logger import get_logger
from .component_registry import ComponentRegistry, ComponentState
from .dependency_resolver import DependencyResolver
from .component_lifecycle import ComponentLifecycle

logger = get_logger(__name__, 'core')


class ComponentManager:
    """
    Central coordinator for all Map Pro components.
    
    Responsibilities:
    - Coordinate component registration and lifecycle
    - Manage component dependencies and ordering
    - Monitor component health and coordinate recovery
    - Provide comprehensive component status
    
    Does NOT handle:
    - Component implementation details (components manage themselves)
    - Engine-specific logic (engines coordinate their own behavior)
    - Database operations (database_coordinator handles this)
    """
    
    def __init__(self):
        self.registry = ComponentRegistry()
        self.dependency_resolver = DependencyResolver()
        self.lifecycle = ComponentLifecycle(self.registry)
        self.is_initialized = False
        
        logger.info("Component manager initialized")
    
    def register_component(self, name: str, component_instance: Any, 
                          dependencies: List[str], critical: bool = False) -> bool:
        """Register a component with the manager."""
        result = self.registry.register(name, component_instance, dependencies, critical)
        
        if result:
            # Recalculate ordering after registration
            components = self.registry.get_all_components()
            self.dependency_resolver.calculate_startup_order(components)
            self.dependency_resolver.calculate_shutdown_order()
        
        return result
    
    def unregister_component(self, name: str) -> bool:
        """Unregister a component from the manager."""
        result = self.registry.unregister(name)
        
        if result:
            # Recalculate ordering after unregistration
            components = self.registry.get_all_components()
            self.dependency_resolver.calculate_startup_order(components)
            self.dependency_resolver.calculate_shutdown_order()
        
        return result
    
    async def initialize_components(self) -> bool:
        """Initialize all registered components in dependency order."""
        logger.info("Initializing components")
        
        try:
            startup_order = self.dependency_resolver.get_startup_order()
            
            for component_name in startup_order:
                if not await self.lifecycle.initialize_component(component_name):
                    logger.error(f"Failed to initialize component: {component_name}")
                    return False
            
            self.is_initialized = True
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            return False
    
    async def start_components(self) -> bool:
        """Start all initialized components in dependency order."""
        if not self.is_initialized:
            logger.error("Cannot start components - not initialized")
            return False
        
        logger.info("Starting components")
        
        try:
            startup_order = self.dependency_resolver.get_startup_order()
            
            for component_name in startup_order:
                if not await self.lifecycle.start_component(component_name):
                    logger.error(f"Failed to start component: {component_name}")
                    return False
            
            logger.info("All components started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Component startup failed: {e}")
            return False
    
    async def stop_components(self) -> bool:
        """Stop all running components in reverse dependency order."""
        logger.info("Stopping components")
        
        success = True
        shutdown_order = self.dependency_resolver.get_shutdown_order()
        
        for component_name in shutdown_order:
            if not await self.lifecycle.stop_component(component_name):
                logger.error(f"Failed to stop component: {component_name}")
                success = False
                # Continue stopping other components
        
        if success:
            logger.info("All components stopped successfully")
        else:
            logger.warning("Some components failed to stop properly")
        
        return success
    
    async def restart_component(self, name: str) -> bool:
        """Restart a specific component."""
        return await self.lifecycle.restart_component(name)
    
    def check_component_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health status of all components."""
        health_status = {}
        components = self.registry.get_all_components()
        
        for name, component_info in components.items():
            try:
                component_health = {
                    'name': name,
                    'state': component_info.state.value,
                    'healthy': component_info.state == ComponentState.RUNNING,
                    'error_count': component_info.error_count,
                    'last_error': component_info.last_error,
                    'last_health_check': component_info.last_health_check.isoformat() if component_info.last_health_check else None
                }
                
                # Check if component has health check method
                if hasattr(component_info.component_instance, 'check_health'):
                    try:
                        component_specific_health = component_info.component_instance.check_health()
                        component_health.update(component_specific_health)
                        component_info.last_health_check = datetime.now(timezone.utc)
                    except Exception as e:
                        logger.warning(f"Component {name} health check failed: {e}")
                        component_health['healthy'] = False
                        component_health['health_check_error'] = str(e)
                
                health_status[name] = component_health
                
            except Exception as e:
                logger.error(f"Failed to check health for component {name}: {e}")
                health_status[name] = {
                    'name': name,
                    'healthy': False,
                    'error': str(e)
                }
        
        return health_status
    
    def get_component_status(self) -> Dict[str, Any]:
        """Get comprehensive status information for all components."""
        components = self.registry.get_all_components()
        
        return {
            'total_components': len(components),
            'startup_order': self.dependency_resolver.get_startup_order(),
            'shutdown_order': self.dependency_resolver.get_shutdown_order(),
            'components': self.registry.get_component_status()['components']
        }