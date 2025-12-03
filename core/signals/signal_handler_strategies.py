"""
Signal Handler Strategies.

Implements different strategies for handling signals in async
and sync contexts. Uses Strategy pattern to reduce complexity.

Original Location: /map_pro/signal_handlers.py (methods within SignalHandler class)
New Location: /map_pro/core/signals/signal_handler_strategies.py

Migration Note: This module extracts signal handling methods from the original
SignalHandler class in signal_handlers.py (project root). The Strategy pattern
replaces the original if/else logic to reduce complexity from 16 to <10.
"""

import signal
import asyncio
import sys
from abc import ABC, abstractmethod
from typing import Callable, Optional
from logging import Logger

from .signal_constants import ExitCodes, SignalNames, ShutdownMessages
from .signal_state_manager import SignalStateManager


class SignalHandlerStrategy(ABC):
    """
    Abstract base class for signal handling strategies.
    
    Defines how signals should be handled in different
    execution contexts (async vs sync).
    """
    
    @abstractmethod
    def register_signal_handlers(
        self,
        handler: Callable[[int], None]
    ) -> None:
        """
        Register signal handlers.
        
        Args:
            handler: Callback function for signal handling
        """
        pass
    
    @abstractmethod
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        pass


class AsyncSignalHandlerStrategy(SignalHandlerStrategy):
    """
    Signal handling strategy for asyncio event loops.
    
    Uses asyncio-compatible signal handling mechanisms
    for integration with async applications.
    """
    
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        logger: Logger
    ) -> None:
        """
        Initialize async signal handler strategy.
        
        Args:
            loop: Asyncio event loop
            logger: Logger instance
        """
        self._loop = loop
        self._logger = logger
        self._registered_signals = []
    
    def register_signal_handlers(
        self,
        handler: Callable[[int], None]
    ) -> None:
        """
        Register async-compatible signal handlers.
        
        Args:
            handler: Async callback function for signals
        """
        for signum in [signal.SIGINT, signal.SIGTERM]:
            self._loop.add_signal_handler(
                signum,
                lambda s=signum: asyncio.create_task(handler(s))
            )
            self._registered_signals.append(signum)
        
        self._logger.info(
            "Async signal handlers registered (SIGINT, SIGTERM)"
        )
    
    def restore_signal_handlers(self) -> None:
        """Remove asyncio signal handlers."""
        for signum in self._registered_signals:
            try:
                self._loop.remove_signal_handler(signum)
            except Exception as e:
                self._logger.debug(
                    f"Could not remove handler for signal {signum}: {e}"
                )
        
        self._registered_signals.clear()
        self._logger.debug("Async signal handlers removed")


class SyncSignalHandlerStrategy(SignalHandlerStrategy):
    """
    Signal handling strategy for synchronous execution.
    
    Uses standard signal module for registration when
    no asyncio event loop is available.
    """
    
    def __init__(self, logger: Logger) -> None:
        """
        Initialize sync signal handler strategy.
        
        Args:
            logger: Logger instance
        """
        self._logger = logger
        self._original_handlers = {}
    
    def register_signal_handlers(
        self,
        handler: Callable[[int], None]
    ) -> None:
        """
        Register synchronous signal handlers.
        
        Args:
            handler: Callback function for signals
        """
        for signum in [signal.SIGINT, signal.SIGTERM]:
            self._original_handlers[signum] = signal.signal(
                signum,
                lambda s, f, signum=signum: handler(signum)
            )
        
        self._logger.info(
            "Sync signal handlers registered (SIGINT, SIGTERM)"
        )
    
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for signum, handler in self._original_handlers.items():
            try:
                signal.signal(signum, handler)
            except Exception as e:
                self._logger.debug(
                    f"Could not restore handler for signal {signum}: {e}"
                )
        
        self._original_handlers.clear()
        self._logger.debug("Original signal handlers restored")


class SignalProcessor:
    """
    Processes received signals and coordinates shutdown.
    
    Handles the logic of what to do when a signal is received,
    including repeat signal detection and shutdown coordination.
    """
    
    def __init__(
        self,
        state_manager: SignalStateManager,
        coordinator: any,
        logger: Logger
    ) -> None:
        """
        Initialize signal processor.
        
        Args:
            state_manager: Signal state manager
            coordinator: System coordinator for shutdown
            logger: Logger instance
        """
        self._state_manager = state_manager
        self._coordinator = coordinator
        self._logger = logger
    
    async def process_signal_async(self, signum: int) -> None:
        """
        Process a received signal asynchronously.
        
        Args:
            signum: Signal number received
        """
        signal_name = SignalNames.get_name(signum)
        is_repeat = self._state_manager.record_signal_received(signum)
        
        if is_repeat or self._state_manager.is_shutdown_requested():
            self._handle_forced_exit(signum, signal_name)
            return
        
        self._initiate_graceful_shutdown(signum, signal_name)
        await self._request_system_shutdown()
    
    def process_signal_sync(self, signum: int) -> None:
        """
        Process a received signal synchronously.
        
        Args:
            signum: Signal number received
        """
        signal_name = SignalNames.get_name(signum)
        is_repeat = self._state_manager.record_signal_received(signum)
        
        if is_repeat or self._state_manager.is_shutdown_requested():
            self._handle_forced_exit(signum, signal_name)
            return
        
        self._initiate_graceful_shutdown(signum, signal_name)
    
    def _handle_forced_exit(self, signum: int, signal_name: str) -> None:
        """
        Handle forced exit on repeated signal.
        
        Args:
            signum: Signal number
            signal_name: Human-readable signal name
        """
        message = ShutdownMessages.FORCED_EXIT.format(
            signal_name=signal_name
        )
        self._logger.warning(f"{signal_name} received again - forcing immediate exit")
        print(f"\n{message}")
        
        exit_code = ExitCodes.SIGINT if signum == signal.SIGINT else ExitCodes.SIGTERM
        sys.exit(exit_code)
    
    def _initiate_graceful_shutdown(self, signum: int, signal_name: str) -> None:
        """
        Initiate graceful shutdown process.
        
        Args:
            signum: Signal number
            signal_name: Human-readable signal name
        """
        self._state_manager.request_shutdown()
        
        self._logger.info(
            ShutdownMessages.SHUTDOWN_REQUESTED.format(
                signal_name=signal_name
            )
        )
        
        print(f"\n{ShutdownMessages.GRACEFUL_SHUTDOWN.format(signal_name=signal_name)}")
        print(ShutdownMessages.FORCE_EXIT_HINT)
    
    async def _request_system_shutdown(self) -> None:
        """Request shutdown from system coordinator."""
        try:
            if hasattr(self._coordinator, 'request_shutdown'):
                await self._coordinator.request_shutdown()
            elif hasattr(self._coordinator, '_is_running'):
                self._coordinator._is_running = False
        except Exception as e:
            self._logger.error(
                f"Error during shutdown request: {e}",
                exc_info=True
            )


__all__ = [
    'SignalHandlerStrategy',
    'AsyncSignalHandlerStrategy',
    'SyncSignalHandlerStrategy',
    'SignalProcessor'
]