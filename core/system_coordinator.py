# File: /map_pro/core/system_coordinator.py

"""
Map Pro System Coordinator
==========================

Central coordinator for the entire Map Pro system lifecycle.
Orchestrates initialization, operation, and shutdown of all components.

Architecture: Top-level system orchestrator - delegates to specialized managers.

This coordinator delegates to:
- SystemInitializationManager: System initialization workflow
- SystemEngineManager: Engine lifecycle and monitoring
- SystemRuntimeManager: Runtime operations and health monitoring
"""

from typing import Dict, Any
from datetime import datetime, timezone

from .system_logger import get_logger
from .database_coordinator import db_coordinator
from .system_validator import SystemValidator
from .component_manager import ComponentManager
from tools.monitoring.health_checker import SystemHealthChecker

from .system_initialization_manager import SystemInitializationManager
from .system_engine_manager import SystemEngineManager
from .system_runtime_manager import SystemRuntimeManager

logger = get_logger(__name__, 'core')


class SystemCoordinator:
    """
    Central coordinator for the entire Map Pro system.
    
    Responsibilities:
    - System initialization coordination
    - Component lifecycle management
    - System health monitoring and status reporting
    - Runtime operation coordination
    - Graceful shutdown
    
    Delegates to specialized managers:
    - SystemInitializationManager: Handles initialization sequence
    - SystemEngineManager: Manages engine operations
    - SystemRuntimeManager: Manages runtime and shutdown
    """
    
    def __init__(self):
        """Initialize system coordinator and sub-managers."""
        # State tracking
        self.is_initialized = False
        
        # Core managers
        self.component_manager = ComponentManager()
        self.health_checker = SystemHealthChecker()
        self.system_validator = SystemValidator()
        
        # Specialized managers
        self.initialization_manager = SystemInitializationManager(
            self.component_manager,
            self.system_validator
        )
        
        self.engine_manager = SystemEngineManager(
            self.component_manager
        )
        
        self.runtime_manager = SystemRuntimeManager(
            self.component_manager,
            self.health_checker
        )
        
        logger.info("System coordinator created")
    
    async def initialize_system(self) -> bool:
        """
        Initialize the entire Map Pro system.
        
        Delegates to SystemInitializationManager for complete
        initialization workflow.
        
        Returns:
            True if initialization successful, False otherwise
        """
        success = await self.initialization_manager.initialize_system()
        
        if success:
            self.is_initialized = True
        
        return success
    
    async def start_system(self) -> bool:
        """
        Start the Map Pro system and all components.
        
        Returns:
            True if startup successful, False otherwise
        """
        if not self.is_initialized:
            logger.error("Cannot start system - not initialized")
            return False
        
        # Start system via runtime manager
        if not await self.runtime_manager.start_system():
            logger.error("Failed to start system")
            return False
        
        # Start engine processing threads
        logger.info("Starting engine processing threads")
        try:
            await self.engine_manager.start_engines()
        except Exception as e:
            logger.error(f"Failed to start engines: {e}")
            await self.runtime_manager.shutdown_system()
            return False
        
        logger.info("Map Pro system started successfully")
        return True
    
    async def run_main_loop(self) -> None:
        """
        Main system operation loop.
        
        Delegates to SystemRuntimeManager for runtime operations.
        """
        await self.runtime_manager.run_main_loop()
    
    async def shutdown_system(self) -> bool:
        """
        Gracefully shutdown the entire Map Pro system.
        
        Delegates to SystemRuntimeManager for shutdown coordination.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        success = await self.runtime_manager.shutdown_system()
        
        if success:
            self.is_initialized = False
        
        return success
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status information.
        
        Returns:
            Dictionary with complete system status
        """
        return {
            'system_coordinator': {
                'is_initialized': self.is_initialized,
                'is_running': self.runtime_manager.is_running,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            'initialization': self.initialization_manager.get_initialization_status(),
            'runtime': self.runtime_manager.get_runtime_status(),
            'components': self.component_manager.get_component_status(),
            'engines': self.engine_manager.get_engine_status(),
            'health': self.health_checker.get_health_summary(),
            'database': self._get_database_status()
        }
    
    def _get_database_status(self) -> Dict[str, Any]:
        """
        Get database coordinator status.
        
        Returns:
            Database status dictionary
        """
        if db_coordinator._is_initialized:
            return db_coordinator.check_health()
        else:
            return {'status': 'not_initialized'}
    
    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get status of all registered engines.
        
        Convenience method for debugging and monitoring.
        
        Returns:
            Dictionary with engine status information
        """
        return self.engine_manager.get_engine_status()


# Global system coordinator instance
system_coordinator = SystemCoordinator()


__all__ = ['SystemCoordinator', 'system_coordinator']