"""
Map Pro Engine CLI Commands - Refactored
=========================================

Engine management commands for the CLI.

This module coordinates engine and library operations, delegating
actual operations to specialized modules.

Location: tools/cli/engine_commands.py
"""

import argparse
from typing import Optional

from core.system_logger import get_logger
from tools.cli.engine_operations import EngineOperations
from tools.cli.library_operations import LibraryOperations
from tools.cli.engine_display import ExitCode, MessageDisplay


logger = get_logger(__name__, 'maintenance')


class ComponentLoader:
    """Lazy loading manager for system components."""
    
    def __init__(self):
        """Initialize component loader."""
        self.logger = logger
        self._component_manager = None
        self._job_orchestrator = None
        self._library_analyzer = None
    
    def get_component_manager(self):
        """
        Lazy initialization of component manager.
        
        Returns:
            ComponentManager instance or None
        """
        if self._component_manager is None:
            try:
                from core.component_manager import ComponentManager
                self._component_manager = ComponentManager()
            except ImportError:
                self.logger.warning("ComponentManager not available")
                self._component_manager = None
        return self._component_manager
    
    def get_job_orchestrator(self):
        """
        Lazy initialization of job orchestrator.
        
        Returns:
            Job orchestrator instance or None
        """
        if self._job_orchestrator is None:
            try:
                from core.job_orchestrator import job_orchestrator
                self._job_orchestrator = job_orchestrator
            except ImportError:
                self.logger.warning("Job orchestrator not available")
                self._job_orchestrator = None
        return self._job_orchestrator
    
    def get_library_analyzer(self):
        """
        Lazy initialization of library dependency analyzer.
        
        Returns:
            Library analyzer instance or None
        """
        if self._library_analyzer is None:
            try:
                from engines.librarian import create_library_dependency_analyzer
                self._library_analyzer = create_library_dependency_analyzer()
            except ImportError:
                self.logger.warning("Library dependency analyzer not available")
                self._library_analyzer = None
        return self._library_analyzer


class EngineCommands:
    """
    Engine management command coordinator.
    
    Responsibilities:
    - CLI argument parsing
    - Command routing
    - Component initialization
    - Operation delegation
    
    Does NOT handle:
    - Engine lifecycle operations (engine_operations.py)
    - Library operations (library_operations.py)
    - Display formatting (engine_display.py)
    """
    
    def __init__(self):
        """Initialize engine commands."""
        self.logger = logger
        self.engines = [
            'searcher',
            'downloader',
            'extractor',
            'parser',
            'librarian',
            'mapper'
        ]
        
        # Component loader
        self.loader = ComponentLoader()
        
        # Operation handlers (lazy initialized)
        self._engine_ops: Optional[EngineOperations] = None
        self._library_ops: Optional[LibraryOperations] = None
        
        # Display helper
        self.message = MessageDisplay()
    
    def _get_available_markets(self) -> list:
        """
        Get list of available markets from the markets directory.
        
        Returns:
            List of available market names
        """
        try:
            from core.data_paths import map_pro_paths
            from pathlib import Path
            
            markets_path = map_pro_paths.markets
            if not markets_path.exists():
                self.logger.warning(f"Markets directory not found: {markets_path}")
                return []
            
            available_markets = []
            for market_dir in markets_path.iterdir():
                if market_dir.is_dir() and market_dir.name not in ['base', '__pycache__', '__init__.py']:
                    available_markets.append(market_dir.name)
            
            return sorted(available_markets)
        except Exception as e:
            self.logger.warning(f"Could not load available markets: {e}")
            return []
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup engine command parser.
        
        Args:
            parser: Argument parser to configure
        """
        subparsers = parser.add_subparsers(dest='engine_action', help='Engine actions')
        
        # List engines
        subparsers.add_parser('list', help='List all engines and their status')
        
        # Engine status
        status_parser = subparsers.add_parser('status', help='Show engine status')
        status_parser.add_argument(
            'engine',
            nargs='?',
            choices=self.engines,
            help='Specific engine (optional)'
        )
        
        # Start engine
        start_parser = subparsers.add_parser('start', help='Start an engine')
        start_parser.add_argument('engine', choices=self.engines, help='Engine to start')
        start_parser.add_argument(
            '--force',
            action='store_true',
            help='Force start even if already running'
        )
        
        # Stop engine
        stop_parser = subparsers.add_parser('stop', help='Stop an engine')
        stop_parser.add_argument('engine', choices=self.engines, help='Engine to stop')
        stop_parser.add_argument('--force', action='store_true', help='Force stop')
        
        # Restart engine
        restart_parser = subparsers.add_parser('restart', help='Restart an engine')
        restart_parser.add_argument('engine', choices=self.engines, help='Engine to restart')
        
        # Show jobs
        jobs_parser = subparsers.add_parser('jobs', help='Show engine jobs')
        jobs_parser.add_argument('engine', choices=self.engines, help='Engine name')
        jobs_parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Limit results (default: 20)'
        )
        
        # Health check
        health_parser = subparsers.add_parser('health', help='Check engine health')
        health_parser.add_argument(
            'engine',
            nargs='?',
            choices=self.engines,
            help='Specific engine (optional)'
        )
        
        # Performance metrics
        perf_parser = subparsers.add_parser('performance', help='Show engine performance')
        perf_parser.add_argument(
            'engine',
            nargs='?',
            choices=self.engines,
            help='Specific engine (optional)'
        )
        
        # Library commands
        self._setup_library_parser(subparsers)
    
    def _setup_library_parser(self, subparsers) -> None:
        """
        Setup library command parser.
        
        Args:
            subparsers: Subparsers to add library commands to
        """
        library_parser = subparsers.add_parser('library', help='Library management commands')
        library_subparsers = library_parser.add_subparsers(
            dest='library_action',
            help='Library actions'
        )
        
        # Library status
        library_subparsers.add_parser('status', help='Show library status')
        
        # Get available markets dynamically
        available_markets = self._get_available_markets()
        market_help = 'Download libraries for specific market'
        if available_markets:
            market_help += f" (available: {', '.join(available_markets)})"
        
        # Download libraries
        download_parser = library_subparsers.add_parser('download', help='Download libraries')
        download_parser.add_argument(
            '--market',
            choices=available_markets if available_markets else None,
            help=market_help
        )
        download_parser.add_argument(
            '--all',
            action='store_true',
            help='Download all configured libraries'
        )
        
        # Analyze dependencies
        analyze_parser = library_subparsers.add_parser(
            'analyze',
            help='Analyze library dependencies'
        )
        analyze_parser.add_argument('filing_id', help='Filing ID to analyze')
        analyze_market_help = 'Market type (required)'
        if available_markets:
            analyze_market_help += f" (available: {', '.join(available_markets)})"
        analyze_parser.add_argument(
            '--market',
            choices=available_markets if available_markets else None,
            required=True,
            help=analyze_market_help
        )
        
        # Manual processing
        manual_parser = library_subparsers.add_parser(
            'manual',
            help='Process manual downloads'
        )
        manual_parser.add_argument(
            '--list',
            action='store_true',
            help='List files in manual directory'
        )
        manual_parser.add_argument('--process', help='Process specific file')
        
        # Library validation
        library_subparsers.add_parser('validate', help='Validate all libraries')
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute engine command.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code
        """
        action = args.engine_action
        
        try:
            # Route to appropriate handler
            if action == 'library':
                return self._execute_library_command(args)
            else:
                return self._execute_engine_command(action, args)
        
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}", exc_info=True)
            self.message.error(f"Command failed: {e}")
            return ExitCode.ERROR
    
    def _execute_engine_command(self, action: str, args: argparse.Namespace) -> int:
        """
        Execute engine-related command.
        
        Args:
            action: Command action
            args: Parsed arguments
            
        Returns:
            Exit code
        """
        # Initialize engine operations if needed
        if not self._engine_ops:
            self._engine_ops = EngineOperations(
                engines=self.engines,
                component_manager=self.loader.get_component_manager(),
                job_orchestrator=self.loader.get_job_orchestrator()
            )
        
        # Route to appropriate method
        if action == 'list':
            return self._engine_ops.list_engines()
        
        elif action == 'status':
            return self._engine_ops.show_status(
                getattr(args, 'engine', None)
            )
        
        elif action == 'start':
            return self._engine_ops.start_engine(
                args.engine,
                getattr(args, 'force', False)
            )
        
        elif action == 'stop':
            return self._engine_ops.stop_engine(
                args.engine,
                getattr(args, 'force', False)
            )
        
        elif action == 'restart':
            return self._engine_ops.restart_engine(args.engine)
        
        elif action == 'jobs':
            return self._engine_ops.show_jobs(
                args.engine,
                getattr(args, 'limit', 20)
            )
        
        elif action == 'health':
            return self._engine_ops.check_health(
                getattr(args, 'engine', None)
            )
        
        elif action == 'performance':
            return self._engine_ops.show_performance(
                getattr(args, 'engine', None)
            )
        
        else:
            self.message.error(f"Unknown engine action: {action}")
            return ExitCode.ERROR
    
    def _execute_library_command(self, args: argparse.Namespace) -> int:
        """
        Execute library management command.
        
        Args:
            args: Parsed arguments
            
        Returns:
            Exit code
        """
        # Initialize library operations if needed
        if not self._library_ops:
            self._library_ops = LibraryOperations(
                library_analyzer=self.loader.get_library_analyzer()
            )
        
        library_action = args.library_action
        
        # Route to appropriate method
        if library_action == 'status':
            return self._library_ops.show_library_status()
        
        elif library_action == 'download':
            return self._library_ops.download_libraries(
                market_type=getattr(args, 'market', None),
                download_all=getattr(args, 'all', False)
            )
        
        elif library_action == 'analyze':
            # Market is now a required argument, so args.market will always be set
            return self._library_ops.analyze_dependencies(
                args.filing_id,
                args.market
            )
        
        elif library_action == 'manual':
            return self._library_ops.process_manual_downloads(
                list_files=getattr(args, 'list', False),
                process_file=getattr(args, 'process', None)
            )
        
        elif library_action == 'validate':
            return self._library_ops.validate_libraries()
        
        else:
            self.message.error(f"Unknown library action: {library_action}")
            return ExitCode.ERROR


__all__ = ['EngineCommands']