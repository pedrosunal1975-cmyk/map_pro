"""
Map Pro CLI Tools Module
========================

Command-line interface tools for Map Pro system administration.

Components:
-----------
- main_cli: Main CLI coordinator and argument parser
- database_commands: Database administration commands
- engine_commands: Engine management commands
- migration_commands: Database migration commands
- monitoring_commands: System monitoring and health checks

Usage:
------
Command line usage:
    mapro --help
    mapro db status
    mapro engine start searcher
    mapro backup create
    mapro health

Programmatic usage:
    from tools.cli.main_cli import MapProCLI
    
    cli = MapProCLI()
    exit_code = cli.run(['db', 'status'])

Save location: tools/cli/__init__.py
"""

from tools.cli.main_cli import MapProCLI, main
from tools.cli.database_commands import DatabaseCommands
from tools.cli.engine_commands import EngineCommands
from tools.cli.migration_commands import MigrationCommands
from tools.cli.monitoring_commands import MonitoringCommands

__all__ = [
    'MapProCLI',
    'main',
    'DatabaseCommands',
    'EngineCommands',
    'MigrationCommands',
    'MonitoringCommands',
]

__version__ = '1.0.0'