"""
CLI Jobs Command Handler
=========================

Handles job management CLI commands.

Save location: tools/cli/cli_jobs_handler.py

Responsibilities:
- List jobs with filters
- Clear failed jobs
- Show job statistics
- Format job output

Dependencies:
- argparse (argument parsing)
- tools.cli.database_commands (database operations)
- tools.cli.cli_command_registry (command interface)
"""

import argparse

from tools.cli.database_commands import DatabaseCommands
from tools.cli.cli_command_registry import CommandHandler
from core.system_logger import get_logger


logger = get_logger(__name__, 'maintenance')


# Default limits
DEFAULT_JOB_LIMIT = 50
MAX_JOB_LIMIT = 1000


class JobsCommandHandler(CommandHandler):
    """
    Handles job management CLI commands.
    
    Provides interface for listing, filtering, and managing jobs
    through the command line.
    
    Attributes:
        db_commands: DatabaseCommands instance for database operations
        logger: Logger instance for this handler
    """
    
    def __init__(self):
        """Initialize jobs command handler."""
        self.db_commands = DatabaseCommands()
        self.logger = logger
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup jobs command arguments.
        
        Args:
            parser: ArgumentParser to configure
        """
        subparsers = parser.add_subparsers(
            dest='jobs_action',
            help='Job management operations',
            required=True
        )
        
        # List jobs subcommand
        list_parser = subparsers.add_parser(
            'list',
            help='List jobs with optional filters'
        )
        list_parser.add_argument(
            '--status',
            help='Filter by job status (e.g., pending, running, completed, failed)'
        )
        list_parser.add_argument(
            '--limit',
            type=int,
            default=DEFAULT_JOB_LIMIT,
            help=f'Limit number of results (default: {DEFAULT_JOB_LIMIT}, max: {MAX_JOB_LIMIT})'
        )
        list_parser.add_argument(
            '--engine',
            help='Filter by engine type (e.g., searcher, downloader, parser)'
        )
        
        # Clear failed jobs subcommand
        clear_parser = subparsers.add_parser(
            'clear-failed',
            help='Clear failed jobs from database'
        )
        clear_parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt'
        )
        
        # Job statistics subcommand
        stats_parser = subparsers.add_parser(
            'stats',
            help='Show job statistics'
        )
        stats_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics by engine'
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute jobs command.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        action = args.jobs_action
        
        if action == 'list':
            return self._handle_list(args)
        elif action == 'clear-failed':
            return self._handle_clear_failed(args)
        elif action == 'stats':
            return self._handle_stats(args)
        else:
            self.logger.error(f"Unknown jobs action: {action}")
            return 1
    
    def _handle_list(self, args: argparse.Namespace) -> int:
        """
        Handle list jobs command.
        
        Args:
            args: Parsed arguments containing filters
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            status_filter = getattr(args, 'status', None)
            limit = self._validate_limit(getattr(args, 'limit', DEFAULT_JOB_LIMIT))
            engine_filter = getattr(args, 'engine', None)
            
            # Call database commands with filters
            return self.db_commands.list_jobs(
                status=status_filter,
                limit=limit,
                engine=engine_filter
            )
            
        except Exception as e:
            self.logger.error(f"List jobs failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _handle_clear_failed(self, args: argparse.Namespace) -> int:
        """
        Handle clear failed jobs command.
        
        Args:
            args: Parsed arguments containing confirmation flag
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            confirm = getattr(args, 'confirm', False)
            
            if not confirm:
                response = input("Are you sure you want to clear all failed jobs? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("Operation cancelled.")
                    return 0
            
            return self.db_commands.clear_failed_jobs()
            
        except Exception as e:
            self.logger.error(f"Clear failed jobs failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _handle_stats(self, args: argparse.Namespace) -> int:
        """
        Handle job statistics command.
        
        Args:
            args: Parsed arguments containing detail flag
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            detailed = getattr(args, 'detailed', False)
            
            return self.db_commands.show_job_stats(detailed=detailed)
            
        except Exception as e:
            self.logger.error(f"Show job stats failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _validate_limit(self, limit: int) -> int:
        """
        Validate and cap job limit.
        
        Args:
            limit: Requested limit
            
        Returns:
            Validated limit value
        """
        if limit < 1:
            self.logger.warning(f"Invalid limit {limit}, using default {DEFAULT_JOB_LIMIT}")
            return DEFAULT_JOB_LIMIT
        
        if limit > MAX_JOB_LIMIT:
            self.logger.warning(f"Limit {limit} exceeds maximum, capping at {MAX_JOB_LIMIT}")
            return MAX_JOB_LIMIT
        
        return limit
    
    @property
    def help_text(self) -> str:
        """Get command help text."""
        return "Job management"


__all__ = ['JobsCommandHandler']