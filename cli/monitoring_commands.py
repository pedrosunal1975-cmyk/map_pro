"""
Map Pro Monitoring CLI Commands.

Main entry point for monitoring commands that delegates to specialized handlers.

This module provides the command-line interface for system monitoring operations
including health checks, status display, performance metrics, resource monitoring,
alerts, logs, and validation.

Architecture:
    Delegates to specialized handler modules:
    - monitoring_health.py - Health check operations
    - monitoring_status.py - System status display
    - monitoring_performance.py - Performance metrics
    - monitoring_resources.py - Resource usage monitoring
    - monitoring_alerts.py - Alert management
    - monitoring_logs.py - Log viewing
    - monitoring_validation.py - System validation

Location: tools/cli/monitoring_commands.py

Example:
    >>> from tools.cli.monitoring_commands import MonitoringCommands
    >>> commands = MonitoringCommands()
    >>> commands.execute(args)
"""

import argparse
from typing import Optional

from core.system_logger import get_logger

from .monitoring_health import HealthCheckHandler
from .monitoring_status import StatusHandler
from .monitoring_performance import PerformanceHandler
from .monitoring_resources import ResourcesHandler
from .monitoring_alerts import AlertsHandler
from .monitoring_logs import LogsHandler
from .monitoring_validation import ValidationHandler


logger = get_logger(__name__, 'maintenance')


# Default limits
DEFAULT_ALERT_LIMIT = 50
DEFAULT_LOG_TAIL = 50


class MonitoringCommands:
    """
    Main monitoring commands coordinator.
    
    Delegates to specialized handlers for different monitoring operations.
    This class provides the CLI interface and routing logic.
    
    Attributes:
        logger: Logger instance
        health_handler: Health check operations handler
        status_handler: System status handler
        performance_handler: Performance metrics handler
        resources_handler: Resource usage handler
        alerts_handler: Alerts management handler
        logs_handler: Log viewing handler
        validation_handler: System validation handler
    
    Example:
        >>> commands = MonitoringCommands()
        >>> parser = argparse.ArgumentParser()
        >>> commands.setup_parser(parser)
        >>> args = parser.parse_args()
        >>> exit_code = commands.execute(args)
    """
    
    def __init__(self):
        """Initialize monitoring commands with all handlers."""
        self.logger = logger
        
        # Initialize specialized handlers
        self.health_handler = HealthCheckHandler()
        self.status_handler = StatusHandler()
        self.performance_handler = PerformanceHandler()
        self.resources_handler = ResourcesHandler()
        self.alerts_handler = AlertsHandler()
        self.logs_handler = LogsHandler()
        self.validation_handler = ValidationHandler()
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup monitoring command parser with all subcommands.
        
        Args:
            parser: Argument parser to configure
        """
        subparsers = parser.add_subparsers(
            dest='monitoring_action',
            help='Monitoring actions'
        )
        
        # Setup each handler's parser
        self._setup_health_parser(subparsers)
        self._setup_status_parser(subparsers)
        self._setup_performance_parser(subparsers)
        self._setup_resources_parser(subparsers)
        self._setup_alerts_parser(subparsers)
        self._setup_logs_parser(subparsers)
        self._setup_validation_parser(subparsers)
    
    def _setup_health_parser(self, subparsers) -> None:
        """Setup health check command parser."""
        health_parser = subparsers.add_parser(
            'health',
            help='Run comprehensive health check'
        )
        health_parser.add_argument(
            '--component',
            help='Check specific component'
        )
        health_parser.add_argument(
            '--verbose',
            action='store_true',
            help='Detailed output'
        )
    
    def _setup_status_parser(self, subparsers) -> None:
        """Setup status command parser."""
        status_parser = subparsers.add_parser(
            'status',
            help='Show system status overview'
        )
        status_parser.add_argument(
            '--refresh',
            type=int,
            help='Auto-refresh interval (seconds)'
        )
    
    def _setup_performance_parser(self, subparsers) -> None:
        """Setup performance command parser."""
        perf_parser = subparsers.add_parser(
            'performance',
            help='Show performance metrics'
        )
        perf_parser.add_argument(
            '--component',
            help='Specific component metrics'
        )
        perf_parser.add_argument(
            '--period',
            choices=['1h', '24h', '7d'],
            default='1h',
            help='Time period for metrics'
        )
    
    def _setup_resources_parser(self, subparsers) -> None:
        """Setup resources command parser."""
        resources_parser = subparsers.add_parser(
            'resources',
            help='Show resource usage'
        )
        resources_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Detailed breakdown'
        )
    
    def _setup_alerts_parser(self, subparsers) -> None:
        """Setup alerts command parser."""
        alerts_parser = subparsers.add_parser(
            'alerts',
            help='Show active alerts'
        )
        alerts_parser.add_argument(
            '--level',
            choices=['info', 'warning', 'critical'],
            help='Filter by alert level'
        )
        alerts_parser.add_argument(
            '--limit',
            type=int,
            default=DEFAULT_ALERT_LIMIT,
            help='Limit number of results'
        )
    
    def _setup_logs_parser(self, subparsers) -> None:
        """Setup logs command parser."""
        logs_parser = subparsers.add_parser(
            'logs',
            help='Show recent system logs'
        )
        logs_parser.add_argument(
            '--component',
            help='Filter by component'
        )
        logs_parser.add_argument(
            '--level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Filter by log level'
        )
        logs_parser.add_argument(
            '--tail',
            type=int,
            default=DEFAULT_LOG_TAIL,
            help='Number of recent lines'
        )
        logs_parser.add_argument(
            '--follow',
            action='store_true',
            help='Follow log output'
        )
    
    def _setup_validation_parser(self, subparsers) -> None:
        """Setup validation command parser."""
        validate_parser = subparsers.add_parser(
            'validate',
            help='Run system validation'
        )
        validate_parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix issues'
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute monitoring command based on arguments.
        
        Routes to appropriate handler based on action.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        action = args.monitoring_action
        
        if action == 'health':
            return self.health_handler.run(args.component, args.verbose)
        
        elif action == 'status':
            return self.status_handler.show(args.refresh)
        
        elif action == 'performance':
            return self.performance_handler.show(args.component, args.period)
        
        elif action == 'resources':
            return self.resources_handler.show(args.detailed)
        
        elif action == 'alerts':
            return self.alerts_handler.show(args.level, args.limit)
        
        elif action == 'logs':
            return self.logs_handler.show(
                args.component,
                args.level,
                args.tail,
                args.follow
            )
        
        elif action == 'validate':
            return self.validation_handler.run(args.fix)
        
        else:
            print(f"Unknown monitoring action: {action}")
            return 1
    
    def execute_health_check(self) -> int:
        """
        Quick health check shortcut command.
        
        Returns:
            Exit code from health check
        """
        return self.health_handler.run(None, False)
    
    def execute_system_status(self) -> int:
        """
        Quick system status shortcut command.
        
        Returns:
            Exit code from status display
        """
        return self.status_handler.show(None)


__all__ = ['MonitoringCommands']