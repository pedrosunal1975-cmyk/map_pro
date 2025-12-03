"""
Signal Handling Package.

Provides comprehensive signal handling functionality for graceful
shutdown and system event management. This refactored package
addresses architectural issues by:

1. Introducing abstractions (interfaces) - addressing low abstraction ratio
2. Reducing coupling through dependency inversion
3. Splitting large complex modules into focused components
4. Eliminating magic numbers through constants
5. Removing emoji usage (replaced with ASCII)
6. Reducing complexity through Strategy pattern

Package Structure:
    - signal_constants: Centralized constants and magic number replacements
    - signal_handler_interface: Abstractions for dependency inversion
    - signal_state_manager: State management separated from handling logic
    - signal_handler_strategies: Strategy pattern for async/sync handling
    - signal_handler: Main orchestration component
    - shutdown_coordinator: Coordinated shutdown sequences

Original Location: /map_pro/signal_handlers.py (single file, 302 lines)
New Location: /map_pro/core/signals/ (package with 6 modules)

CRITICAL PATH MIGRATION:
    The original signal_handlers.py was at MapPro project root (/map_pro/).
    This refactored package is now under /map_pro/core/signals/ to better
    organize the codebase and follow the existing core/ structure pattern.

IMPORT CHANGES REQUIRED:
    Old: from signal_handlers import SignalHandler, ShutdownCoordinator
    New: from core.signals import SignalHandler, ShutdownCoordinator

Example:
    >>> from core.signals import SignalHandler, ShutdownCoordinator
    >>> 
    >>> handler = SignalHandler(system_coordinator, logger)
    >>> handler.register_handlers()
    >>> 
    >>> coordinator = ShutdownCoordinator(system_coordinator, logger)
    >>> await coordinator.perform_graceful_shutdown()
"""

from .signal_constants import (
    ExitCodes,
    SignalNames,
    ShutdownMessages,
    ShutdownTimings
)

from .signal_handler_interface import (
    ISignalHandler,
    IShutdownCoordinator,
    ISystemCoordinator
)

from .signal_state_manager import (
    SignalState,
    ExitCodeCalculator,
    SignalStateManager
)

from .signal_handler_strategies import (
    SignalHandlerStrategy,
    AsyncSignalHandlerStrategy,
    SyncSignalHandlerStrategy,
    SignalProcessor
)

from .signal_handler import SignalHandler

from .shutdown_coordinator import (
    ShutdownCoordinator,
    ShutdownStep,
    ShutdownSequence
)


# Public API - maintain backward compatibility
__all__ = [
    # Main classes (backward compatible)
    'SignalHandler',
    'ShutdownCoordinator',
    
    # Constants
    'ExitCodes',
    'SignalNames',
    'ShutdownMessages',
    'ShutdownTimings',
    
    # Interfaces (for testing and extension)
    'ISignalHandler',
    'IShutdownCoordinator',
    'ISystemCoordinator',
    
    # State management (for advanced usage)
    'SignalStateManager',
    'SignalState',
    'ExitCodeCalculator',
    
    # Strategies (for customization)
    'SignalHandlerStrategy',
    'AsyncSignalHandlerStrategy',
    'SyncSignalHandlerStrategy',
    'SignalProcessor',
    
    # Shutdown components (for advanced usage)
    'ShutdownStep',
    'ShutdownSequence'
]


# Version information
__version__ = '2.0.0'
__author__ = 'MapPro Development Team'