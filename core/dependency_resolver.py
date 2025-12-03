"""
Map Pro Dependency Resolver
===========================

Resolves component dependencies and calculates startup/shutdown order.
Uses topological sorting to determine correct component ordering.

Save location: core/dependency_resolver.py
"""

from typing import List, Dict
from .system_logger import get_logger
from shared.exceptions.custom_exceptions import ComponentError

logger = get_logger(__name__, 'core')


class DependencyResolver:
    """
    Resolves component dependencies and ordering.
    
    Responsibilities:
    - Dependency resolution via topological sort
    - Startup order calculation
    - Shutdown order calculation (reverse of startup)
    - Circular dependency detection
    
    Does NOT handle:
    - Component registration (ComponentRegistry handles this)
    - Component lifecycle operations (ComponentLifecycle handles this)
    """
    
    def __init__(self):
        self.startup_order: List[str] = []
        self.shutdown_order: List[str] = []
        logger.debug("Dependency resolver initialized")
    
    def calculate_startup_order(self, components: Dict) -> List[str]:
        """
        Calculate component startup order based on dependencies.
        
        Args:
            components: Dictionary of ComponentInfo objects
            
        Returns:
            List of component names in startup order
            
        Raises:
            ComponentError: If circular dependencies detected
        """
        try:
            self.startup_order = self._topological_sort(components)
            logger.debug(f"Calculated startup order: {self.startup_order}")
            return self.startup_order
        except Exception as e:
            logger.error(f"Failed to calculate startup order: {e}")
            # Fallback to simple order if sort fails
            self.startup_order = list(components.keys())
            return self.startup_order
    
    def calculate_shutdown_order(self) -> List[str]:
        """
        Calculate component shutdown order (reverse of startup).
        
        Returns:
            List of component names in shutdown order
        """
        self.shutdown_order = list(reversed(self.startup_order))
        logger.debug(f"Calculated shutdown order: {self.shutdown_order}")
        return self.shutdown_order
    
    def get_startup_order(self) -> List[str]:
        """Get current startup order."""
        return self.startup_order.copy()
    
    def get_shutdown_order(self) -> List[str]:
        """Get current shutdown order."""
        return self.shutdown_order.copy()
    
    def _topological_sort(self, components: Dict) -> List[str]:
        """
        Perform topological sort to determine component startup order.
        Uses Kahn's algorithm for topological sorting.
        
        Args:
            components: Dictionary of ComponentInfo objects
            
        Returns:
            List of component names in startup order
            
        Raises:
            ComponentError: If circular dependencies detected
        """
        # Calculate in-degrees
        in_degree = {name: 0 for name in components}
        
        for component_info in components.values():
            for dep in component_info.dependencies:
                if dep in in_degree:  # Only count registered dependencies
                    in_degree[component_info.name] += 1
        
        # Initialize queue with nodes that have no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # Update in-degrees of dependent components
            for component_info in components.values():
                if current in component_info.dependencies:
                    in_degree[component_info.name] -= 1
                    if in_degree[component_info.name] == 0:
                        queue.append(component_info.name)
        
        # Check for circular dependencies
        if len(result) != len(components):
            remaining = [name for name in components if name not in result]
            raise ComponentError(f"Circular dependencies detected among components: {remaining}")
        
        return result