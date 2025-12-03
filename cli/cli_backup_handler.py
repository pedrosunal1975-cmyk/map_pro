"""
CLI Backup Command Handler
===========================

Handles backup-related CLI commands.

Save location: tools/cli/cli_backup_handler.py

Responsibilities:
- Handle backup creation
- List available backups
- Execute backup cleanup
- Format backup output

Dependencies:
- argparse (argument parsing)
- tools.maintenance.backup_manager (backup operations)
- tools.cli.cli_command_registry (command interface)
"""

import argparse
from typing import Dict, Any

from tools.maintenance.backup_manager import BackupManager
from tools.cli.cli_command_registry import CommandHandler
from core.system_logger import get_logger


logger = get_logger(__name__, 'maintenance')


# Output formatting constants
MAX_BACKUPS_TO_DISPLAY = 5
SIZE_MB_DECIMAL_PLACES = 1


class BackupCommandHandler(CommandHandler):
    """
    Handles backup-related CLI commands.
    
    Provides interface for backup creation, listing, and cleanup
    operations through the command line.
    
    Attributes:
        backup_manager: BackupManager instance for operations
        logger: Logger instance for this handler
    """
    
    def __init__(self):
        """Initialize backup command handler."""
        self.backup_manager = BackupManager()
        self.logger = logger
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup backup command arguments.
        
        Args:
            parser: ArgumentParser to configure
        """
        subparsers = parser.add_subparsers(
            dest='backup_action',
            help='Backup operations',
            required=True
        )
        
        # Create backup subcommand
        subparsers.add_parser(
            'create',
            help='Create full system backup'
        )
        
        # List backups subcommand
        list_parser = subparsers.add_parser(
            'list',
            help='List available backups'
        )
        list_parser.add_argument(
            '--all',
            action='store_true',
            help='Show all backups (default: last 5)'
        )
        
        # Cleanup backups subcommand
        subparsers.add_parser(
            'cleanup',
            help='Remove old backups based on retention policy'
        )
        
        # Status subcommand
        subparsers.add_parser(
            'status',
            help='Show backup system status'
        )
    
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute backup command.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        action = args.backup_action
        
        if action == 'create':
            return self._handle_create()
        elif action == 'list':
            return self._handle_list(args.all if hasattr(args, 'all') else False)
        elif action == 'cleanup':
            return self._handle_cleanup()
        elif action == 'status':
            return self._handle_status()
        else:
            self.logger.error(f"Unknown backup action: {action}")
            return 1
    
    def _handle_create(self) -> int:
        """
        Handle backup creation command.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            print("Creating system backup...")
            result = self.backup_manager.create_full_backup()
            
            if result['success']:
                print(f"[OK] Backup created: {result['backup_name']}")
                self._print_backup_summary(result)
                return 0
            else:
                print(f"[FAIL] Backup failed")
                self._print_errors(result.get('errors', []))
                return 1
                
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _handle_list(self, show_all: bool) -> int:
        """
        Handle list backups command.
        
        Args:
            show_all: Whether to show all backups or just recent ones
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            backups = self.backup_manager.list_backups()
            
            print("\n[PACKAGE] Available Backups:")
            
            # List database backups
            for db_name, backup_list in backups['databases'].items():
                if not backup_list:
                    continue
                
                print(f"\n{db_name.upper()} Database:")
                
                display_count = len(backup_list) if show_all else MAX_BACKUPS_TO_DISPLAY
                for backup in backup_list[:display_count]:
                    size_str = f"{backup['size_mb']:.{SIZE_MB_DECIMAL_PLACES}f}MB"
                    print(f"  * {backup['file']} ({size_str})")
                
                if not show_all and len(backup_list) > MAX_BACKUPS_TO_DISPLAY:
                    remaining = len(backup_list) - MAX_BACKUPS_TO_DISPLAY
                    print(f"  ... and {remaining} more (use --all to see all)")
            
            # List JSON backups
            json_backups = backups.get('json_data', [])
            if json_backups:
                print("\nJSON Data:")
                display_count = len(json_backups) if show_all else MAX_BACKUPS_TO_DISPLAY
                for backup in json_backups[:display_count]:
                    size_str = f"{backup['size_mb']:.{SIZE_MB_DECIMAL_PLACES}f}MB"
                    print(f"  * {backup['file']} ({size_str})")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"List backups failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _handle_cleanup(self) -> int:
        """
        Handle backup cleanup command.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            print("Cleaning old backups...")
            result = self.backup_manager.cleanup_old_backups()
            
            if result['success']:
                files_removed = result['files_removed']
                space_freed = result['space_freed_mb']
                print(f"[OK] Removed {files_removed} files, freed {space_freed:.1f}MB")
                
                if result.get('errors'):
                    print("\nWarnings:")
                    self._print_errors(result['errors'])
                
                return 0
            else:
                print("[FAIL] Cleanup failed")
                self._print_errors(result.get('errors', []))
                return 1
                
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _handle_status(self) -> int:
        """
        Handle backup status command.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            status = self.backup_manager.get_backup_status()
            
            print("\n[INFO] Backup System Status:")
            print(f"  Backup Directory: {status['backup_directory']}")
            print(f"  Retention Policy: {status['retention_days']} days")
            print(f"  Compression: {'Enabled' if status['compression_enabled'] else 'Disabled'}")
            
            print("\n  Available Backups:")
            for backup_type, count in status.get('available_backups', {}).items():
                print(f"    {backup_type}: {count}")
            
            if 'error' in status:
                print(f"\n[WARNING] {status['error']}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Get backup status failed: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            return 1
    
    def _print_backup_summary(self, result: Dict[str, Any]) -> None:
        """
        Print summary of backup operation.
        
        Args:
            result: Backup result dictionary
        """
        print("\nBackup Summary:")
        
        # Database backups
        db_results = result.get('databases', {})
        for db_name, db_result in db_results.items():
            status = "[OK]" if db_result.get('success') else "[FAIL]"
            print(f"  {status} {db_name} database")
        
        # JSON data backup
        json_result = result.get('json_data', {})
        if json_result:
            status = "[OK]" if json_result.get('success') else "[FAIL]"
            print(f"  {status} JSON data")
    
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
        return "Backup operations"


__all__ = ['BackupCommandHandler']