"""
Signal Constants Module.

Centralized constants for signal handling operations.
Eliminates magic numbers and provides standard signal definitions.

Original Location: /map_pro/signal_handlers.py (part of original file)
New Location: /map_pro/core/signals/signal_constants.py

Migration Note: This module was extracted from signal_handlers.py which was
originally at project root. It is now part of the signals package under core/.
"""

import signal
from typing import Dict


class ExitCodes:
    """Standard exit codes for process termination."""
    
    SUCCESS = 0
    SIGINT = 130  # Standard exit code for SIGINT (Ctrl+C)
    SIGTERM = 143  # Standard exit code for SIGTERM
    FORCED_EXIT = 1  # Forced exit after repeated signal


class SignalNames:
    """Human-readable names for OS signals."""
    
    MAPPING: Dict[int, str] = {
        signal.SIGINT: 'SIGINT',
        signal.SIGTERM: 'SIGTERM'
    }
    
    @classmethod
    def get_name(cls, signum: int) -> str:
        """
        Get human-readable name for signal number.
        
        Args:
            signum: Signal number
            
        Returns:
            Signal name or generic description
        """
        return cls.MAPPING.get(signum, f"Signal {signum}")


class ShutdownMessages:
    """Standard messages for shutdown events."""
    
    GRACEFUL_SHUTDOWN = "[STOP] {signal_name} received - shutting down gracefully..."
    FORCE_EXIT_HINT = "   (Press Ctrl+C again to force immediate exit)"
    FORCED_EXIT = "[WARNING] {signal_name} received again - forcing exit"
    SHUTDOWN_IN_PROGRESS = "Shutdown already in progress"
    SHUTDOWN_REQUESTED = "{signal_name} received - initiating graceful shutdown"


class ShutdownTimings:
    """Timing constants for shutdown operations."""
    
    CLEANUP_WAIT_SECONDS = 0.5
    

__all__ = [
    'ExitCodes',
    'SignalNames',
    'ShutdownMessages',
    'ShutdownTimings'
]