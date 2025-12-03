"""
Signal Handler - Main Implementation.

Provides the main SignalHandler class that orchestrates signal
handling using strategies and state management.

Original Location: /map_pro/signal_handlers.py (SignalHandler class)
New Location: /map_pro/core/signals/signal_handler.py

Migration Note: This is the refactored SignalHandler class from the original
signal_handlers.py at project root. The class now delegates to strategies and
state managers instead of handling everything internally. Complexity reduced
from 16 to <10 through separation of concerns.

IMPORTANT PATH CHANGE:
    Old import: from signal_handlers import SignalHandler
    New import: from core.signals import SignalHandler
"""

import asyncio
from typing import Optional, Set
from logging import Logger

from .signal_handler_interface import ISignalHandler
from .signal_state_manager import SignalStateManager
from .signal_handler_strategies import (
    SignalHandlerStrategy,
    AsyncSignalHandlerStrategy,
    SyncSignalHandlerStrategy,
    SignalProcessor
)


class SignalHandler(ISignalHandler):
    """
    Manages OS signal handling for graceful shutdown.
    
    Orchestrates signal handling using strategy pattern for async
    and sync contexts. Coordinates with system for clean shutdown.
    
    This refactored version reduces complexity from 16 to <10 and
    improves maintainability through separation of concerns.
    
    Attributes:
        coordinator: System coordinator instance
        logger: Logger instance
    
    Example:
        >>> handler = SignalHandler(system_coordinator, logger)
        >>> handler.register_handlers()
        >>> 
        >>> # Later, check if shutdown was requested
        >>> if handler.is_shutdown_requested():
        ...     print("Shutting down gracefully")
    """
    
    def __init__(self, coordinator: any, logger: Logger) -> None:
        """
        Initialize signal handler.
        
        Args:
            coordinator: System coordinator for shutdown coordination
            logger: Logger instance for logging signal events
        """
        self._coordinator = coordinator
        self._logger = logger
        self._state_manager = SignalStateManager()
        self._processor = SignalProcessor(
            self._state_manager,
            coordinator,
            logger
        )
        self._strategy: Optional[SignalHandlerStrategy] = None
    
    def register_handlers(self) -> None:
        """
        Register signal handlers for graceful shutdown.
        
        Automatically detects execution context (async vs sync) and
        uses appropriate strategy for signal handling.
        
        Sets up handlers for:
        - SIGINT (Ctrl+C)
        - SIGTERM (termination signal)
        """
        self._strategy = self._create_strategy()
        self._strategy.register_signal_handlers(
            self._create_signal_callback()
        )
    
    def restore_handlers(self) -> None:
        """
        Restore original signal handlers.
        
        Should be called during cleanup to restore default behavior.
        """
        if self._strategy:
            self._strategy.restore_signal_handlers()
            self._strategy = None
    
    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested.
        
        Returns:
            True if shutdown was requested, False otherwise
        """
        return self._state_manager.is_shutdown_requested()
    
    def get_signals_received(self) -> Set[int]:
        """
        Get set of signals that have been received.
        
        Returns:
            Set of signal numbers
        """
        return self._state_manager.get_signals_received()
    
    def get_exit_code(self) -> int:
        """
        Get appropriate exit code based on signals received.
        
        Returns:
            Exit code appropriate for the signals received
        """
        return self._state_manager.calculate_exit_code()
    
    def _create_strategy(self) -> SignalHandlerStrategy:
        """
        Create appropriate signal handling strategy.
        
        Returns:
            Async or sync strategy based on execution context
        """
        try:
            loop = asyncio.get_running_loop()
            return AsyncSignalHandlerStrategy(loop, self._logger)
        except RuntimeError:
            return SyncSignalHandlerStrategy(self._logger)
    
    def _create_signal_callback(self):
        """
        Create signal callback based on strategy type.
        
        Returns:
            Async or sync signal callback function
        """
        if isinstance(self._strategy, AsyncSignalHandlerStrategy):
            return self._processor.process_signal_async
        else:
            return self._processor.process_signal_sync


__all__ = ['SignalHandler']