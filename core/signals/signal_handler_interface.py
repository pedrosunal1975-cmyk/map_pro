"""
Signal Handler Interface.

Defines abstractions for signal handling to improve testability
and reduce coupling. Provides clear contracts for implementations.

Original Location: N/A (new file created during refactoring)
New Location: /map_pro/core/signals/signal_handler_interface.py

Migration Note: This is a new file created to introduce abstractions
and implement Dependency Inversion Principle. The original signal_handlers.py
at project root did not have these interfaces.
"""

from abc import ABC, abstractmethod
from typing import Set


class ISignalHandler(ABC):
    """
    Interface for signal handling implementations.
    
    Defines the contract that all signal handlers must implement,
    enabling dependency inversion and easier testing.
    """
    
    @abstractmethod
    def register_handlers(self) -> None:
        """
        Register signal handlers for the process.
        
        Should set up handlers for relevant OS signals like
        SIGINT and SIGTERM.
        """
        pass
    
    @abstractmethod
    def restore_handlers(self) -> None:
        """
        Restore original signal handlers.
        
        Should be called during cleanup to restore default
        signal handling behavior.
        """
        pass
    
    @abstractmethod
    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested.
        
        Returns:
            True if shutdown was requested, False otherwise
        """
        pass
    
    @abstractmethod
    def get_signals_received(self) -> Set[int]:
        """
        Get set of signals that have been received.
        
        Returns:
            Set of signal numbers received
        """
        pass
    
    @abstractmethod
    def get_exit_code(self) -> int:
        """
        Get appropriate exit code based on signals received.
        
        Returns:
            Exit code appropriate for the termination signal
        """
        pass


class IShutdownCoordinator(ABC):
    """
    Interface for coordinating system shutdown.
    
    Defines how system components should be shut down
    in a coordinated manner.
    """
    
    @abstractmethod
    async def perform_graceful_shutdown(self) -> None:
        """
        Perform coordinated graceful shutdown.
        
        Should orchestrate shutdown across all system components,
        ensuring clean resource release and state persistence.
        """
        pass
    
    @abstractmethod
    def is_shutdown_in_progress(self) -> bool:
        """
        Check if shutdown is currently in progress.
        
        Returns:
            True if shutdown is in progress, False otherwise
        """
        pass


class ISystemCoordinator(ABC):
    """
    Interface for system coordination operations.
    
    Abstracts the system coordinator to reduce coupling
    and improve testability of signal handlers.
    """
    
    @abstractmethod
    async def request_shutdown(self) -> None:
        """
        Request system shutdown.
        
        Initiates graceful shutdown of system components.
        """
        pass
    
    @abstractmethod
    async def shutdown_system(self) -> None:
        """
        Perform system shutdown.
        
        Executes the actual shutdown procedures for all
        system components.
        """
        pass


__all__ = [
    'ISignalHandler',
    'IShutdownCoordinator',
    'ISystemCoordinator'
]