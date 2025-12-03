"""
CLI Cleanup Command Handler
============================

Handles cleanup-related CLI commands.

Save location: tools/cli/cli_cleanup_handler.py

Responsibilities:
- Execute system cleanup
- Show cleanup statistics
- Provide cleanup recommendations
- Format cleanup output

Dependencies:
- argparse (argument parsing)
- tools.maintenance.cleanup_scheduler (cleanup operations)
- tools.cli.cli_command_registry (command interface)
"""

import argparse
from typing import Dict, Any

from tools.maintenance.cleanup_scheduler import CleanupScheduler
from tools.cli.cli_command_registry import CommandHandler
from core.system_logger import get_logger


logger = get_logger(__name__, 'maintenance')


# Priority icon mapping
PRIORITY_ICONS = {
    'high': '[!]',
    'medium': '[*]',
    'low': '[+]'
}

# Size display precision
SIZE_DECIMAL_PLACES = 2


class CleanupCommandHandler(CommandHandler):
    """
    Handles cleanup-related CLI commands.
    
    Provides interface for system cleanup operations, statistics,
    and recommendations through the command line.
    
    Attributes:
        cleanup_scheduler: CleanupScheduler instance for operations
        logger: Logger instance for this handler
    """
    
    def __init__(self):
        """Initialize cleanup command handler."""
        self.cleanup_scheduler = CleanupScheduler()
        self.logger = logger
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup cleanup command arguments.
        
        Args:
            parser: ArgumentParser to configure
        """
        subparsers = parser.add_subparsers(
            dest='cleanup_action',
            help='Cleanup operations',
            required=True
        )
        
        # Run cleanup subcommand
        run_parser = subparsers.add_parser(
            'run',
            help='Run full system cleanup'
        )
        run_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without performing cleanup'
        )
        
        # Show statistics subcommand
        subparsers.add_parser(
            'stats',
            help='Show cleanup statistics'
        )
        
        # Show recommendations subcommand
        subparsers.add_parser(
            'recommendations',
            help='Get cleanup recommendations'
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute cleanup command.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        action = args.cleanup_action
        
        if action == 'run':
            dry_run = getattr(args, 'dry_run', False)
            return self._handle_run(dry_run)
        elif action == 'stats':
            return self._handle_stats()
        elif action == 'recommendations':
            return self._handle_recommendations()
        else:
            self.logger.error(f"Unknown cleanup action: {action}")
            return 1
    
    def _handle_run(self, dry_run: bool) -> int:
        """
        Handle cleanup run command.
        
        Args:
            dry_run: Whether to simulate cleanup without actually removing files
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            if dry_run:
                print("Running cleanup simulation (dry run)...")
                # Note: Implement dry run in CleanupScheduler if needed
                print("[INFO] Dry run not yet implemented")
                return 0
            
            print("Running system cleanup...")
            result = self.cleanup_scheduler.run_full_cleanup()
            
            if result['success']:
                space_freed = result.get('total_space_freed_mb', 0)
                print(f"[OK] Cleanup completed: {space_freed:.{SIZE_DECIMAL_PLACES}f}MB freed")
                self._print_cleanup_details(result)
                return 0
            else:
                print("[FAIL] Cleanup failed")
                self._print_errors(result.get('errors', []))
                return 1
                
        except Exception as e:
            self.logger.error(f"Cleanup run failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _handle_stats(self) -> int:
        """
        Handle cleanup statistics command.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            stats = self.cleanup_scheduler.get_cleanup_statistics()
            
            print("\n[STATS] Cleanup Statistics:")
            
            # Directory sizes
            temp_size = stats.get('temp_directory_size_gb', 0)
            downloads_size = stats.get('downloads_size_gb', 0)
            logs_size = stats.get('logs_size_gb', 0)
            
            print(f"  Temp Directory: {temp_size:.{SIZE_DECIMAL_PLACES}f}GB")
            print(f"  Downloads: {downloads_size:.{SIZE_DECIMAL_PLACES}f}GB")
            print(f"  Logs: {logs_size:.{SIZE_DECIMAL_PLACES}f}GB")
            
            # Job counts
            old_jobs = stats.get('old_jobs_count', 0)
            print(f"  Old Jobs: {old_jobs}")
            
            # Additional stats if available
            if 'total_size_gb' in stats:
                total = stats['total_size_gb']
                print(f"\n  Total Cleanable: {total:.{SIZE_DECIMAL_PLACES}f}GB")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Get cleanup stats failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _handle_recommendations(self) -> int:
        """
        Handle cleanup recommendations command.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            recommendations = self.cleanup_scheduler.get_cleanup_recommendations()
            
            total_recs = recommendations.get('total_recommendations', 0)
            
            if total_recs == 0:
                print("[OK] No cleanup recommendations - system is clean!")
                return 0
            
            print(f"\n[WARNING] {total_recs} Cleanup Recommendations:")
            
            rec_list = recommendations.get('recommendations', [])
            for rec in rec_list:
                self._print_recommendation(rec)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Get recommendations failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _print_cleanup_details(self, result: Dict[str, Any]) -> None:
        """
        Print detailed cleanup results.
        
        Args:
            result: Cleanup result dictionary
        """
        print("\nCleanup Details:")
        
        # Files removed by category
        if 'files_removed' in result:
            files = result['files_removed']
            for category, count in files.items():
                print(f"  {category}: {count} files")
        
        # Space freed by category
        if 'space_freed_by_category' in result:
            space = result['space_freed_by_category']
            for category, size_mb in space.items():
                print(f"  {category}: {size_mb:.{SIZE_DECIMAL_PLACES}f}MB")
    
    def _print_recommendation(self, rec: Dict[str, Any]) -> None:
        """
        Print a single cleanup recommendation.
        
        Args:
            rec: Recommendation dictionary
        """
        priority = rec.get('priority', 'low')
        icon = PRIORITY_ICONS.get(priority, '[?]')
        message = rec.get('message', 'No message')
        action = rec.get('action', 'No action specified')
        
        print(f"\n  {icon} {message}")
        print(f"     Action: {action}")
        
        # Print additional details if available
        if 'size' in rec:
            print(f"     Size: {rec['size']}")
        if 'impact' in rec:
            print(f"     Impact: {rec['impact']}")
    
    def _print_errors(self, errors: list) -> None:
        """
        Print error messages.
        
        Args:
            errors: List of error messages
        """
        for error in errors:
            print(f"  - {error}")
    
    @property
    def help_text(self) -> str:
        """Get command help text."""
        return "Cleanup operations"


__all__ = ['CleanupCommandHandler']