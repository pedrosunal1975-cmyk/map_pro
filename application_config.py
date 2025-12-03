# application_config.py
"""
MapPro Application Configuration.

This module contains application-wide constants, configuration classes,
and command-line argument parsing.

Location: /map_pro/application_config.py

Improvements Made:
- Fixed naming conventions (UPPER_SNAKE_CASE for constants)
- Enhanced documentation with comprehensive docstrings
- Improved type hints throughout
- Added validation method for ApplicationState
- Enhanced error handling in argument parsing
- Better structured help text
- No splitting (file is manageable at ~140 lines)
"""

import argparse
from dataclasses import dataclass
from typing import Optional


class ApplicationConstants:
    """
    Constants used throughout the application.
    
    All constants use UPPER_SNAKE_CASE naming convention.
    """
    
    # Auto-cleanup threshold
    WORKFLOWS_PER_CLEANUP = 10
    
    # Exit codes
    EXIT_SUCCESS = 0
    EXIT_FAILURE = 1
    EXIT_SIGINT = 130
    
    # Display constants
    BANNER_WIDTH = 50


@dataclass
class ApplicationState:
    """
    Application runtime state.
    
    Tracks workflow execution count, shutdown status, and exit code.
    Provides validation and state management methods.
    
    Attributes:
        workflow_count: Number of workflows executed (for auto-cleanup)
        shutdown_requested: Whether shutdown has been requested
        exit_code: Exit code to return on application exit
    """
    workflow_count: int = 0
    shutdown_requested: bool = False
    exit_code: int = ApplicationConstants.EXIT_SUCCESS
    
    def increment_workflow_count(self) -> int:
        """
        Increment workflow count and return new value.
        
        Returns:
            Updated workflow count
        """
        self.workflow_count += 1
        return self.workflow_count
    
    def should_cleanup(self) -> bool:
        """
        Check if auto-cleanup threshold has been reached.
        
        Returns:
            True if cleanup should be performed
        """
        return self.workflow_count >= ApplicationConstants.WORKFLOWS_PER_CLEANUP
    
    def request_shutdown(self, exit_code: Optional[int] = None) -> None:
        """
        Request application shutdown with optional exit code.
        
        Args:
            exit_code: Exit code to set (defaults to current exit_code)
        """
        self.shutdown_requested = True
        if exit_code is not None:
            self.exit_code = exit_code
    
    def reset_workflow_count(self) -> None:
        """Reset workflow count after cleanup."""
        self.workflow_count = 0
    
    def validate(self) -> bool:
        """
        Validate state values are within acceptable ranges.
        
        Returns:
            True if state is valid
        """
        return (
            self.workflow_count >= 0 and
            self.exit_code in (
                ApplicationConstants.EXIT_SUCCESS,
                ApplicationConstants.EXIT_FAILURE,
                ApplicationConstants.EXIT_SIGINT
            )
        )


class ArgumentParser:
    """
    Handles command line argument parsing.
    
    Provides a clean interface for parsing and validating command line arguments.
    Supports multiple operational modes: interactive, daemon, validation, health, status.
    """
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """
        Create argument parser with all options.
        
        Returns:
            Configured ArgumentParser instance with all application modes
        """
        parser = argparse.ArgumentParser(
            description='Map Pro - XBRL Financial Data Mapper',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  Interactive mode (prompts for input):
    python main.py --interactive
  
  Daemon mode (background processing):
    python main.py --daemon
  
  System validation:
    python main.py --validate
  
  Health check:
    python main.py --health
  
  System status:
    python main.py --status
  
  Debug mode with interactive:
    python main.py --interactive --debug
            """
        )
        
        # Operational mode arguments
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run in daemon mode (background process)'
        )
        
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Run in interactive mode (prompt for workflow parameters)'
        )
        
        # System operation arguments
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate system configuration and exit'
        )
        
        parser.add_argument(
            '--health',
            action='store_true',
            help='Perform health check and exit'
        )
        
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show system status and exit'
        )
        
        # Configuration arguments
        parser.add_argument(
            '--config',
            type=str,
            metavar='PATH',
            help='Path to configuration file'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode with verbose logging'
        )
        
        return parser
    
    @staticmethod
    def parse_arguments(args: Optional[list] = None) -> argparse.Namespace:
        """
        Parse command line arguments.
        
        Args:
            args: Optional list of arguments (for testing). If None, uses sys.argv
            
        Returns:
            Parsed arguments namespace
            
        Raises:
            SystemExit: If argument parsing fails or --help is used
        """
        parser = ArgumentParser.create_parser()
        return parser.parse_args(args)
    
    @staticmethod
    def validate_arguments(args: argparse.Namespace) -> tuple[bool, Optional[str]]:
        """
        Validate parsed arguments for conflicts and requirements.
        
        Args:
            args: Parsed argument namespace
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if arguments are valid
            - error_message: None if valid, error description if invalid
        """
        # Check for mutually exclusive mode flags
        mode_flags = [
            args.daemon,
            args.interactive,
            args.validate,
            args.health,
            args.status
        ]
        
        active_modes = sum(1 for flag in mode_flags if flag)
        
        if active_modes > 1:
            return False, "Only one operational mode can be specified at a time"
        
        # Validate config file path if provided
        if args.config:
            from pathlib import Path
            config_path = Path(args.config)
            if not config_path.exists():
                return False, f"Configuration file not found: {args.config}"
            if not config_path.is_file():
                return False, f"Configuration path is not a file: {args.config}"
        
        return True, None


__all__ = ['ApplicationConstants', 'ApplicationState', 'ArgumentParser']