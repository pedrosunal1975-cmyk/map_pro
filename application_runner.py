# application_runner.py
"""
MapPro Application Runner.

This module contains the main application logic for the MapPro system.
It handles command line argument processing, mode selection, and orchestration
of different operational modes (interactive, daemon, validation, etc.).

Responsibilities:
    - Command line argument parsing orchestration
    - System coordinator orchestration
    - Mode selection and execution
    - Exit code management
    - Signal handler integration

Does NOT Handle:
    - Signal handling implementation (core.signals package handles this)
    - Entry point logic (main.py handles this)
    - System component implementation (system_coordinator handles this)
    - Mode implementation details (execution_modes package handles this)

Original Location: /map_pro/application_runner.py (refactored from main.py)
Current Location: /map_pro/application_runner.py

IMPORT UPDATE:
    Old: from signal_handlers import SignalHandler
    New: from core.signals import SignalHandler
    
    Note: The module name changed from plural 'signal_handlers' to singular
    'signal_handler' as part of the package refactoring.

Improvements Made:
    - Enhanced error handling with specific exception types
    - Improved logging with contextual information
    - Added argument validation before mode execution
    - Better separation of concerns in mode selection
    - More descriptive error messages
    - Proper cleanup in finally block
    - No splitting (file is manageable and critical)

Example:
    >>> app = MapProApplication()
    >>> exit_code = await app.run()
"""

import sys
from typing import Optional

from core.system_coordinator import system_coordinator
from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from core.signals import SignalHandler

from application_config import ApplicationConstants, ApplicationState, ArgumentParser
from execution_modes import (
    ValidationMode,
    HealthCheckMode,
    StatusMode,
    InteractiveMode,
    DaemonMode
)


logger = get_logger(__name__, 'core')


class MapProApplication:
    """
    Main application controller for Map Pro system.
    
    Orchestrates the entire application lifecycle including:
    - Argument parsing and validation
    - Mode selection and execution
    - Signal handling setup
    - Exit code management
    - Error handling and logging
    
    Design Pattern: Application Controller / Facade
    Benefits: Single entry point, clear lifecycle, proper cleanup
    
    Example:
        >>> app = MapProApplication()
        >>> exit_code = await app.run()
        >>> sys.exit(exit_code)
    """
    
    def __init__(self):
        """
        Initialize application controller.
        
        Sets up initial state and prepares for execution.
        """
        self.state = ApplicationState()
        self.logger = logger
        self.signal_handler: Optional[SignalHandler] = None
    
    async def run(self) -> int:
        """
        Main application entry point.
        
        Orchestrates the complete application lifecycle:
        1. Setup signal handling
        2. Parse and validate arguments
        3. Log startup information
        4. Execute selected mode
        5. Handle shutdown and cleanup
        
        Returns:
            Exit code for the application (0 for success, non-zero for failure)
        """
        try:
            # Setup signal handling
            self._setup_signal_handling()
            
            # Parse arguments
            args = ArgumentParser.parse_arguments()
            
            # Validate arguments
            is_valid, error_message = ArgumentParser.validate_arguments(args)
            if not is_valid:
                self.logger.error(f"Invalid arguments: {error_message}")
                print(f"[FAIL] {error_message}")
                return ApplicationConstants.EXIT_FAILURE
            
            # Log startup
            self._log_startup(args)
            
            # Run in appropriate mode
            exit_code = await self._run_selected_mode(args)
            
            # Check for signal-based shutdown
            if self.signal_handler and self.signal_handler.is_shutdown_requested():
                signal_exit_code = self.signal_handler.get_exit_code()
                self.logger.info(
                    f"Signal-based shutdown requested, using exit code: {signal_exit_code}"
                )
                exit_code = signal_exit_code
            
            return exit_code
        
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            print("\n[INFO] Interrupted by user")
            return ApplicationConstants.EXIT_SIGINT
        
        except SystemExit as e:
            # Re-raise SystemExit (from argparse --help, etc.)
            raise
        
        except Exception as e:
            self.logger.error(f"Critical error in application: {e}", exc_info=True)
            print(f"[FAIL] Critical error: {e}")
            return ApplicationConstants.EXIT_FAILURE
        
        finally:
            # Restore signal handlers
            self._cleanup_signal_handling()
    
    def _setup_signal_handling(self) -> None:
        """
        Setup signal handling for graceful shutdown.
        
        Registers handlers for SIGINT and SIGTERM.
        """
        try:
            self.signal_handler = SignalHandler(system_coordinator, self.logger)
            self.signal_handler.register_handlers()
            self.logger.debug("Signal handlers registered")
        except Exception as e:
            self.logger.warning(f"Failed to setup signal handling: {e}")
            # Continue without signal handling rather than failing
    
    def _cleanup_signal_handling(self) -> None:
        """
        Restore default signal handlers.
        
        Safe to call even if signal handling was never setup.
        """
        if self.signal_handler:
            try:
                self.signal_handler.restore_handlers()
                self.logger.debug("Signal handlers restored")
            except Exception as e:
                self.logger.warning(f"Failed to restore signal handlers: {e}")
    
    def _log_startup(self, args) -> None:
        """
        Log startup information.
        
        Args:
            args: Parsed command line arguments
        """
        self.logger.info("Map Pro starting...")
        self.logger.info(f"Data root: {map_pro_paths.data_root}")
        self.logger.info(f"Log directory: {map_pro_paths.logs_root}")
        
        # Log active mode
        if args.interactive:
            self.logger.info("Mode: Interactive")
        elif args.daemon:
            self.logger.info("Mode: Daemon")
        elif args.validate:
            self.logger.info("Mode: Validation")
        elif args.health:
            self.logger.info("Mode: Health Check")
        elif args.status:
            self.logger.info("Mode: Status")
        else:
            self.logger.info("Mode: Help/Default")
        
        # Log debug mode if enabled
        if args.debug:
            self.logger.info("Debug mode enabled")
    
    async def _run_selected_mode(self, args) -> int:
        """
        Run application in selected mode based on arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code from the selected mode
        """
        try:
            # System operation modes (validation, health, status)
            if args.validate:
                return await self._run_validation_mode()
            
            elif args.health:
                return await self._run_health_mode()
            
            elif args.status:
                return await self._run_status_mode()
            
            # Operational modes (interactive, daemon)
            elif args.interactive:
                return await self._run_interactive_mode()
            
            elif args.daemon:
                return await self._run_daemon_mode(args)
            
            # Default - show help
            else:
                self._show_default_help()
                return ApplicationConstants.EXIT_SUCCESS
        
        except Exception as e:
            self.logger.error(f"Error in mode execution: {e}", exc_info=True)
            raise
    
    async def _run_validation_mode(self) -> int:
        """
        Run validation mode.
        
        Returns:
            Exit code from validation
        """
        self.logger.info("Starting validation mode")
        try:
            return await ValidationMode().run()
        except Exception as e:
            self.logger.error(f"Validation mode failed: {e}", exc_info=True)
            print(f"[FAIL] Validation failed: {e}")
            return ApplicationConstants.EXIT_FAILURE
    
    async def _run_health_mode(self) -> int:
        """
        Run health check mode.
        
        Returns:
            Exit code from health check
        """
        self.logger.info("Starting health check mode")
        try:
            return await HealthCheckMode().run()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}", exc_info=True)
            print(f"[FAIL] Health check failed: {e}")
            return ApplicationConstants.EXIT_FAILURE
    
    async def _run_status_mode(self) -> int:
        """
        Run status mode.
        
        Returns:
            Exit code from status check
        """
        self.logger.info("Starting status mode")
        try:
            return await StatusMode().run()
        except Exception as e:
            self.logger.error(f"Status mode failed: {e}", exc_info=True)
            print(f"[FAIL] Status check failed: {e}")
            return ApplicationConstants.EXIT_FAILURE
    
    async def _run_interactive_mode(self) -> int:
        """
        Run interactive mode.
        
        Returns:
            Exit code from interactive session
        """
        self.logger.info("Starting interactive mode")
        try:
            return await InteractiveMode(self.state).run()
        except Exception as e:
            self.logger.error(f"Interactive mode failed: {e}", exc_info=True)
            print(f"[FAIL] Interactive mode failed: {e}")
            return ApplicationConstants.EXIT_FAILURE
    
    async def _run_daemon_mode(self, args) -> int:
        """
        Run daemon mode.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code from daemon
        """
        self.logger.info("Starting daemon mode")
        try:
            return await DaemonMode(args).run()
        except Exception as e:
            self.logger.error(f"Daemon mode failed: {e}", exc_info=True)
            print(f"[FAIL] Daemon mode failed: {e}")
            return ApplicationConstants.EXIT_FAILURE
    
    def _show_default_help(self) -> None:
        """
        Show default help message when no mode specified.
        
        Displays available modes and basic usage information.
        """
        print("=" * ApplicationConstants.BANNER_WIDTH)
        print("Map Pro - XBRL Financial Data Mapper".center(ApplicationConstants.BANNER_WIDTH))
        print("=" * ApplicationConstants.BANNER_WIDTH)
        print("\nNo mode specified. Available modes:")
        print("\nOperational Modes:")
        print("  --interactive : Interactive workflow (recommended for single runs)")
        print("  --daemon      : Background processing mode")
        print("\nSystem Modes:")
        print("  --validate    : Validate system configuration")
        print("  --health      : Run health check")
        print("  --status      : Show system status")
        print("\nOptions:")
        print("  --config PATH : Specify configuration file")
        print("  --debug       : Enable debug mode")
        print("\nUse --help for detailed information and examples")
        print("=" * ApplicationConstants.BANNER_WIDTH)


__all__ = ['MapProApplication']