#!/usr/bin/env python3
"""
Map Pro Main Entry Point.

Minimal entry point that delegates to application_runner for actual execution.
This module only handles:
- Python path setup
- Async runtime initialization
- Dependency injection setup
- Exit code propagation

All application logic is in application_runner.py.
All signal handling is in core/signals package (refactored from signal_handlers.py).

SIGNAL HANDLING NOTE:
    The original signal_handlers.py at project root has been refactored into
    the core.signals package. The signal handling setup is now done in
    application_runner.py which imports from core.signals.
    
    Old: /map_pro/signal_handlers.py (single file, plural name)
    New: /map_pro/core/signals/ (package with multiple modules, singular name)

DEPENDENCY INJECTION:
    Uses a factory function pattern for dependency injection to decouple
    the entry point from concrete implementations. This improves:
    - Testability (can inject mock applications)
    - Flexibility (easy to swap implementations)
    - Maintainability (explicit dependency management)

Usage:
    python main.py [options]
    
Options:
    --daemon        Run in daemon mode (background process)
    --config PATH   Use custom configuration file
    --debug         Enable debug mode
    --validate      Validate system configuration and exit
    --health        Perform health check and exit
    --status        Show system status and exit
    --interactive   Run in interactive mode (prompt for workflow parameters)
    
Examples:
    # Interactive mode (prompts for input)
    python main.py --interactive
    
    # Daemon mode (background processing)
    python main.py --daemon
    
    # System validation
    python main.py --validate

Original Location: /map_pro/main.py
Current Location: /map_pro/main.py

History:
    - Original main.py contained all logic including signal handling
    - Refactored: signal_handlers.py extracted to project root
    - Refactored: application_runner.py extracted to project root
    - Refactored: signal_handlers.py moved to core/signals/ package
    - Refactored: Added dependency injection pattern to reduce coupling
"""

import sys
import asyncio
from pathlib import Path
from typing import Protocol

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


class ApplicationProtocol(Protocol):
    """Protocol defining the interface for application instances."""
    
    async def run(self) -> int:
        """
        Run the application.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        ...


def create_application() -> ApplicationProtocol:
    """
    Factory function to create the application instance.
    
    This is the dependency injection point. By using a factory function,
    we decouple main.py from the concrete MapProApplication implementation.
    
    For testing, this function can be mocked or replaced to inject
    different application implementations.
    
    Returns:
        ApplicationProtocol: An application instance
    """
    from application_runner import MapProApplication
    return MapProApplication()


async def run_application(app: ApplicationProtocol) -> int:
    """
    Execute the application asynchronously.
    
    Args:
        app: The application instance to run
        
    Returns:
        Exit code from the application
    """
    return await app.run()


def main_sync() -> int:
    """
    Synchronous wrapper for the async main function.
    
    This is the actual entry point that sets up the async runtime
    and delegates to the application runner.
    
    The application runner handles:
    - Signal handler setup (from core.signals)
    - Mode selection and execution
    - Exit code management
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Create application via dependency injection
        app = create_application()
        
        # Run application in async context
        return asyncio.run(run_application(app))
    
    except KeyboardInterrupt:
        print("\nShutdown requested")
        return 0
    
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main_sync()
    sys.exit(exit_code)