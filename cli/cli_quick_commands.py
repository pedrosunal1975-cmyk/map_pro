"""
CLI Quick Command Handlers
===========================

Handlers for quick-access CLI commands (shortcuts).

Save location: tools/cli/cli_quick_commands.py

Responsibilities:
- Provide quick access to common operations
- Delegate to appropriate command modules
- Simplify common workflows

Dependencies:
- argparse (argument parsing)
- tools.cli.monitoring_commands (monitoring operations)
- tools.cli.cli_command_registry (command interface)
"""

import argparse

from tools.cli.monitoring_commands import MonitoringCommands
from tools.cli.cli_command_registry import CommandHandler
from core.system_logger import get_logger


logger = get_logger(__name__, 'maintenance')


class HealthCommandHandler(CommandHandler):
    """
    Quick access handler for health check command.
    
    Provides simplified interface to system health check without
    needing to navigate full monitoring command structure.
    
    Attributes:
        monitoring_commands: MonitoringCommands instance
        logger: Logger instance for this handler
    """
    
    def __init__(self):
        """Initialize health command handler."""
        self.monitoring_commands = MonitoringCommands()
        self.logger = logger
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup health command arguments.
        
        Args:
            parser: ArgumentParser to configure
        """
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed health information'
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute health check command.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            return self.monitoring_commands.execute_health_check()
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    @property
    def help_text(self) -> str:
        """Get command help text."""
        return "Run system health check"


class StatusCommandHandler(CommandHandler):
    """
    Quick access handler for system status command.
    
    Provides simplified interface to system status without
    needing to navigate full monitoring command structure.
    
    Attributes:
        monitoring_commands: MonitoringCommands instance
        logger: Logger instance for this handler
    """
    
    def __init__(self):
        """Initialize status command handler."""
        self.monitoring_commands = MonitoringCommands()
        self.logger = logger
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup status command arguments.
        
        Args:
            parser: ArgumentParser to configure
        """
        parser.add_argument(
            '--engines',
            action='store_true',
            help='Include engine status'
        )
        parser.add_argument(
            '--jobs',
            action='store_true',
            help='Include job status'
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute system status command.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            return self.monitoring_commands.execute_system_status()
            
        except Exception as e:
            self.logger.error(f"System status failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    @property
    def help_text(self) -> str:
        """Get command help text."""
        return "Show system status"


__all__ = ['HealthCommandHandler', 'StatusCommandHandler']