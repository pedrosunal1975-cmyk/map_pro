"""
Map Pro Main CLI
================

Main command-line interface for Map Pro system administration.

Save location: tools/cli/main_cli.py

Responsibilities:
- Setup argument parser with all commands
- Route commands to appropriate handlers
- Manage global CLI options (verbose, quiet)
- Provide CLI entry point

This file now uses the Command pattern via CommandRegistry to decouple
the CLI from command implementations, reducing complexity and improving
testability.

Design Patterns:
- Command Pattern: Commands implement CommandHandler interface
- Registry Pattern: CommandRegistry manages command routing
- Facade Pattern: CLI provides unified interface

Dependencies:
- sys (exit codes)
- argparse (argument parsing)
- core.system_logger (logging)
- tools.cli.cli_command_registry (command routing)
- tools.cli.database_commands (database operations)
- tools.cli.engine_commands (engine operations)
- tools.cli.migration_commands (migration operations)
- tools.cli.monitoring_commands (monitoring operations)
- tools.cli.cli_backup_handler (backup operations)
- tools.cli.cli_cleanup_handler (cleanup operations)
- tools.cli.cli_jobs_handler (job management)
- tools.cli.cli_quick_commands (quick access commands)
"""

import sys
import argparse
from typing import List, Optional

from core.system_logger import get_logger
from tools.cli.cli_command_registry import CommandRegistry
from tools.cli.database_commands import DatabaseCommands
from tools.cli.engine_commands import EngineCommands
from tools.cli.migration_commands import MigrationCommands
from tools.cli.monitoring_commands import MonitoringCommands
from tools.cli.cli_backup_handler import BackupCommandHandler
from tools.cli.cli_cleanup_handler import CleanupCommandHandler
from tools.cli.cli_jobs_handler import JobsCommandHandler
from tools.cli.cli_quick_commands import HealthCommandHandler, StatusCommandHandler


logger = get_logger(__name__, 'maintenance')


# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 130


class MapProCLI:
    """
    Main CLI coordinator for Map Pro system administration.
    
    Provides unified command-line interface for all system operations.
    Uses Command pattern via CommandRegistry for flexible command routing.
    
    Attributes:
        registry: Command registry for routing
        parser: Main argument parser
        logger: Logger instance for CLI
    """
    
    def __init__(self):
        """Initialize CLI with command registry and parser."""
        self.logger = logger
        self.registry = self._create_command_registry()
        self.parser = self._setup_parser()
    
    def _create_command_registry(self) -> CommandRegistry:
        """
        Create and populate command registry.
        
        Returns:
            Configured CommandRegistry instance
        """
        registry = CommandRegistry()
        
        # Register main command modules
        registry.register('db', DatabaseCommands())
        registry.register('engine', EngineCommands())
        registry.register('migration', MigrationCommands())
        registry.register('monitoring', MonitoringCommands())
        
        # Register specialized handlers
        registry.register('backup', BackupCommandHandler())
        registry.register('cleanup', CleanupCommandHandler())
        registry.register('jobs', JobsCommandHandler())
        
        # Register quick access commands
        registry.register('health', HealthCommandHandler())
        registry.register('status', StatusCommandHandler())
        
        return registry
    
    def _setup_parser(self) -> argparse.ArgumentParser:
        """
        Setup the main argument parser with subcommands.
        
        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            prog='mapro',
            description='Map Pro System Administration CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_usage_examples()
        )
        
        # Add global options
        self._add_global_options(parser)
        
        # Create subparsers for commands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands',
            metavar='COMMAND'
        )
        
        # Setup each registered command
        self._setup_command_parsers(subparsers)
        
        return parser
    
    def _get_usage_examples(self) -> str:
        """
        Get usage examples text.
        
        Returns:
            Formatted usage examples string
        """
        return """
Examples:
  mapro db status                    # Check database status
  mapro engine start searcher        # Start searcher engine
  mapro backup create                # Create system backup
  mapro health check                 # Run health check
  mapro jobs list --status failed    # List failed jobs
  mapro cleanup run                  # Run system cleanup

For more help on a specific command:
  mapro <command> --help
        """
    
    def _add_global_options(self, parser: argparse.ArgumentParser) -> None:
        """
        Add global CLI options.
        
        Args:
            parser: Parser to add options to
        """
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress output except errors'
        )
    
    def _setup_command_parsers(
        self,
        subparsers: argparse._SubParsersAction
    ) -> None:
        """
        Setup subparsers for all registered commands.
        
        Args:
            subparsers: Subparsers action to add commands to
        """
        for command_name, handler in self.registry.get_all_commands().items():
            command_parser = subparsers.add_parser(
                command_name,
                help=handler.help_text
            )
            handler.setup_parser(command_parser)
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI with given arguments.
        
        Args:
            args: Command line arguments (defaults to sys.argv[1:])
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            parsed_args = self.parser.parse_args(args)
            
            # Handle case where no command is provided
            if not parsed_args.command:
                self.parser.print_help()
                return EXIT_ERROR
            
            # Configure logging based on verbosity
            self._configure_logging(parsed_args)
            
            # Execute command via registry
            return self._execute_command(parsed_args)
        
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return EXIT_INTERRUPTED
        
        except Exception as e:
            self._handle_error(e, parsed_args if 'parsed_args' in locals() else None)
            return EXIT_ERROR
    
    def _configure_logging(self, args: argparse.Namespace) -> None:
        """
        Configure logging based on verbosity flags.
        
        Args:
            args: Parsed arguments containing verbosity flags
        """
        if args.verbose:
            logger.setLevel('DEBUG')
        elif args.quiet:
            logger.setLevel('ERROR')
    
    def _execute_command(self, args: argparse.Namespace) -> int:
        """
        Execute the parsed command via registry.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code from command handler
        """
        command_name = args.command
        
        try:
            return self.registry.execute_command(command_name, args)
            
        except ValueError as e:
            # Command not found
            self.logger.error(f"Unknown command: {command_name}")
            print(f"Error: {e}")
            return EXIT_ERROR
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            print(f"[ERROR] Command failed: {e}")
            return EXIT_ERROR
    
    def _handle_error(
        self,
        error: Exception,
        args: Optional[argparse.Namespace]
    ) -> None:
        """
        Handle CLI error with appropriate logging.
        
        Args:
            error: Exception that occurred
            args: Parsed arguments if available
        """
        verbose = args.verbose if args and hasattr(args, 'verbose') else False
        
        if verbose:
            self.logger.error(f"CLI error: {error}", exc_info=True)
        else:
            self.logger.error(f"Error: {error}")


def main() -> None:
    """
    Main entry point for the CLI.
    
    Creates CLI instance and executes with command line arguments.
    """
    cli = MapProCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()


__all__ = ['MapProCLI', 'main']