"""
Shutdown Coordinator.

Coordinates graceful shutdown across application components.
Provides high-level orchestration of shutdown sequences.

Original Location: /map_pro/signal_handlers.py (ShutdownCoordinator class)
New Location: /map_pro/core/signals/shutdown_coordinator.py

Migration Note: This is the refactored ShutdownCoordinator class from the
original signal_handlers.py at project root. Enhanced with ShutdownStep and
ShutdownSequence classes for better shutdown orchestration.

IMPORTANT PATH CHANGE:
    Old import: from signal_handlers import ShutdownCoordinator
    New import: from core.signals import ShutdownCoordinator
"""

import asyncio
from logging import Logger

from .signal_handler_interface import IShutdownCoordinator
from .signal_constants import ShutdownMessages, ShutdownTimings


class ShutdownStep:
    """
    Represents a single step in the shutdown sequence.
    
    Encapsulates the logic and metadata for one shutdown operation.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        async_func,
        is_critical: bool = True
    ) -> None:
        """
        Initialize shutdown step.
        
        Args:
            name: Step identifier
            description: Human-readable description
            async_func: Async function to execute
            is_critical: Whether failure should stop shutdown
        """
        self.name = name
        self.description = description
        self.async_func = async_func
        self.is_critical = is_critical


class ShutdownSequence:
    """
    Manages the sequence of shutdown operations.
    
    Provides ordered execution of shutdown steps with
    error handling and logging.
    """
    
    def __init__(self, logger: Logger) -> None:
        """
        Initialize shutdown sequence.
        
        Args:
            logger: Logger instance
        """
        self._logger = logger
        self._steps = []
    
    def add_step(self, step: ShutdownStep) -> None:
        """
        Add a step to the shutdown sequence.
        
        Args:
            step: Shutdown step to add
        """
        self._steps.append(step)
    
    async def execute(self) -> bool:
        """
        Execute all shutdown steps in sequence.
        
        Returns:
            True if all critical steps succeeded, False otherwise
        """
        success = True
        
        for step in self._steps:
            try:
                self._logger.info(f"Executing shutdown step: {step.description}")
                await step.async_func()
                self._logger.debug(f"Completed shutdown step: {step.name}")
                
            except Exception as e:
                self._logger.error(
                    f"Error in shutdown step '{step.name}': {e}",
                    exc_info=True
                )
                
                if step.is_critical:
                    success = False
                    self._logger.error(
                        f"Critical shutdown step failed: {step.name}"
                    )
        
        return success


class ShutdownCoordinator(IShutdownCoordinator):
    """
    Coordinates graceful shutdown across application components.
    
    Provides high-level shutdown coordination that works with
    signal handlers and system coordinator. Manages shutdown
    sequence and ensures clean resource release.
    
    Example:
        >>> coordinator = ShutdownCoordinator(system_coordinator, logger)
        >>> await coordinator.perform_graceful_shutdown()
    """
    
    def __init__(self, coordinator: any, logger: Logger) -> None:
        """
        Initialize shutdown coordinator.
        
        Args:
            coordinator: System coordinator instance
            logger: Logger instance
        """
        self._coordinator = coordinator
        self._logger = logger
        self._shutdown_in_progress = False
    
    async def perform_graceful_shutdown(self) -> None:
        """
        Perform coordinated graceful shutdown.
        
        Executes shutdown sequence:
        1. Mark shutdown in progress
        2. Stop accepting new work
        3. Complete pending operations
        4. Shutdown system components
        5. Release resources
        6. Wait for cleanup
        """
        if self._shutdown_in_progress:
            self._logger.warning(ShutdownMessages.SHUTDOWN_IN_PROGRESS)
            return
        
        self._shutdown_in_progress = True
        self._logger.info("Beginning graceful shutdown sequence")
        
        try:
            sequence = self._build_shutdown_sequence()
            success = await sequence.execute()
            
            if success:
                self._logger.info("Graceful shutdown completed successfully")
            else:
                self._logger.warning(
                    "Graceful shutdown completed with errors"
                )
        
        except Exception as e:
            self._logger.error(
                f"Unexpected error during graceful shutdown: {e}",
                exc_info=True
            )
        
        finally:
            self._shutdown_in_progress = False
    
    def is_shutdown_in_progress(self) -> bool:
        """
        Check if shutdown is currently in progress.
        
        Returns:
            True if shutdown in progress, False otherwise
        """
        return self._shutdown_in_progress
    
    def _build_shutdown_sequence(self) -> ShutdownSequence:
        """
        Build the shutdown sequence.
        
        Returns:
            Configured shutdown sequence
        """
        sequence = ShutdownSequence(self._logger)
        
        # Step 1: Request system shutdown
        sequence.add_step(ShutdownStep(
            name="system_shutdown",
            description="Requesting system shutdown",
            async_func=self._shutdown_system,
            is_critical=True
        ))
        
        # Step 2: Wait for cleanup
        sequence.add_step(ShutdownStep(
            name="cleanup_wait",
            description="Waiting for cleanup to complete",
            async_func=self._wait_for_cleanup,
            is_critical=False
        ))
        
        return sequence
    
    async def _shutdown_system(self) -> None:
        """Shutdown system coordinator."""
        await self._coordinator.shutdown_system()
    
    async def _wait_for_cleanup(self) -> None:
        """Wait briefly for cleanup operations."""
        await asyncio.sleep(ShutdownTimings.CLEANUP_WAIT_SECONDS)


__all__ = ['ShutdownCoordinator', 'ShutdownStep', 'ShutdownSequence']