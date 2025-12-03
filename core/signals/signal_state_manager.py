"""
Signal State Manager.

Manages state tracking for signal handling including shutdown
requests and received signals. Provides thread-safe state access.

Original Location: /map_pro/signal_handlers.py (SignalHandler class attributes)
New Location: /map_pro/core/signals/signal_state_manager.py

Migration Note: This module extracts state management logic from the original
SignalHandler class in signal_handlers.py (project root). State tracking is
now separated from signal handling logic for better Single Responsibility.
"""

import signal
from typing import Set, Optional
from threading import Lock

from .signal_constants import ExitCodes, SignalNames


class SignalState:
    """
    Tracks signal handling state.
    
    Maintains thread-safe state about shutdown requests and
    received signals. Separated from handler logic for clarity.
    
    Attributes:
        shutdown_requested: Whether shutdown has been requested
        signals_received: Set of signal numbers that were received
    """
    
    def __init__(self) -> None:
        """Initialize signal state tracking."""
        self._shutdown_requested = False
        self._signals_received: Set[int] = set()
        self._lock = Lock()
    
    def mark_shutdown_requested(self) -> None:
        """Mark that shutdown has been requested."""
        with self._lock:
            self._shutdown_requested = True
    
    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested.
        
        Returns:
            True if shutdown requested, False otherwise
        """
        with self._lock:
            return self._shutdown_requested
    
    def record_signal(self, signum: int) -> bool:
        """
        Record that a signal was received.
        
        Args:
            signum: Signal number received
            
        Returns:
            True if this is a repeat signal, False if first occurrence
        """
        with self._lock:
            is_repeat = signum in self._signals_received
            self._signals_received.add(signum)
            return is_repeat
    
    def get_signals_received(self) -> Set[int]:
        """
        Get set of signals received.
        
        Returns:
            Set of signal numbers (copy for thread safety)
        """
        with self._lock:
            return self._signals_received.copy()
    
    def reset(self) -> None:
        """Reset all state to initial values."""
        with self._lock:
            self._shutdown_requested = False
            self._signals_received.clear()


class ExitCodeCalculator:
    """
    Calculates appropriate exit codes based on signals.
    
    Determines the correct exit code to use based on which
    signals were received during shutdown.
    """
    
    @staticmethod
    def calculate_exit_code(signals_received: Set[int]) -> int:
        """
        Calculate exit code based on signals received.
        
        Args:
            signals_received: Set of signal numbers that were received
            
        Returns:
            Appropriate exit code for the signals
        """
        if signal.SIGINT in signals_received:
            return ExitCodes.SIGINT
        
        if signal.SIGTERM in signals_received:
            return ExitCodes.SIGTERM
        
        return ExitCodes.SUCCESS


class SignalStateManager:
    """
    High-level manager for signal state operations.
    
    Provides a facade over state tracking and exit code
    calculation for cleaner signal handler implementation.
    """
    
    def __init__(self) -> None:
        """Initialize signal state manager."""
        self._state = SignalState()
        self._exit_code_calculator = ExitCodeCalculator()
    
    def request_shutdown(self) -> None:
        """Mark that shutdown has been requested."""
        self._state.mark_shutdown_requested()
    
    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested.
        
        Returns:
            True if shutdown requested, False otherwise
        """
        return self._state.is_shutdown_requested()
    
    def record_signal_received(self, signum: int) -> bool:
        """
        Record that a signal was received.
        
        Args:
            signum: Signal number received
            
        Returns:
            True if this is a repeat signal, False if first
        """
        return self._state.record_signal(signum)
    
    def get_signals_received(self) -> Set[int]:
        """
        Get set of all signals received.
        
        Returns:
            Set of signal numbers
        """
        return self._state.get_signals_received()
    
    def calculate_exit_code(self) -> int:
        """
        Calculate appropriate exit code.
        
        Returns:
            Exit code based on signals received
        """
        signals = self._state.get_signals_received()
        return self._exit_code_calculator.calculate_exit_code(signals)
    
    def reset_state(self) -> None:
        """Reset all state to initial values."""
        self._state.reset()


__all__ = [
    'SignalState',
    'ExitCodeCalculator',
    'SignalStateManager'
]