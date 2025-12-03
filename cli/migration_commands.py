"""
Map Pro Migration CLI Commands
==============================

Database migration commands for the CLI.

Save location: tools/cli/migration_commands.py
"""

import argparse
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone

from core.system_logger import get_logger
from database.migrations.migration_manager import migration_manager

logger = get_logger(__name__, 'maintenance')


class MigrationCommands:
    """Database migration management commands."""
    
    def __init__(self):
        """Initialize migration commands."""
        self.logger = logger
        self.databases = ['core', 'parsed', 'library', 'mapped']
    
    def setup_parser(self, parser: argparse.ArgumentParser):
        """Setup migration command parser."""
        subparsers = parser.add_subparsers(dest='migration_action', help='Migration actions')
        
        # List migrations
        list_parser = subparsers.add_parser('list', help='List migrations')
        list_parser.add_argument('--database', choices=self.databases, help='Specific database')
        list_parser.add_argument('--pending', action='store_true', help='Show only pending migrations')
        
        # Show migration status
        status_parser = subparsers.add_parser('status', help='Show migration status')
        status_parser.add_argument('--database', choices=self.databases, help='Specific database')
        
        # Run migrations
        run_parser = subparsers.add_parser('run', help='Run pending migrations')
        run_parser.add_argument('--database', choices=self.databases, help='Specific database')
        run_parser.add_argument('--target', help='Target migration version')
        run_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
        
        # Rollback migration
        rollback_parser = subparsers.add_parser('rollback', help='Rollback last migration')
        rollback_parser.add_argument('database', choices=self.databases, help='Target database')
        rollback_parser.add_argument('--steps', type=int, default=1, help='Number of steps to rollback')
        rollback_parser.add_argument('--to-version', help='Rollback to specific version')
        
        # Create new migration
        create_parser = subparsers.add_parser('create', help='Create new migration')
        create_parser.add_argument('database', choices=self.databases, help='Target database')
        create_parser.add_argument('name', help='Migration name (e.g., add_user_table)')
        create_parser.add_argument('--template', choices=['table', 'index', 'data', 'custom'], 
                                 default='custom', help='Migration template type')
        
        # Validate migrations
        validate_parser = subparsers.add_parser('validate', help='Validate migration files')
        validate_parser.add_argument('--database', choices=self.databases, help='Specific database')
        
        # Migration history
        history_parser = subparsers.add_parser('history', help='Show migration history')
        history_parser.add_argument('--database', choices=self.databases, help='Specific database')
        history_parser.add_argument('--limit', type=int, default=20, help='Limit number of results')
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute migration command."""
        action = args.migration_action
        
        if action == 'list':
            return self.list_migrations(args.database, args.pending)
        
        elif action == 'status':
            return self.show_status(args.database)
        
        elif action == 'run':
            return self.run_migrations(args.database, args.target, args.dry_run)
        
        elif action == 'rollback':
            return self.rollback_migration(args.database, args.steps, args.to_version)
        
        elif action == 'create':
            return self.create_migration(args.database, args.name, args.template)
        
        elif action == 'validate':
            return self.validate_migrations(args.database)
        
        elif action == 'history':
            return self.show_history(args.database, args.limit)
        
        else:
            print(f"Unknown migration action: {action}")
            return 1
    
    def list_migrations(self, database: str = None, pending_only: bool = False) -> int:
        """List available migrations."""
        try:
            databases_to_check = [database] if database else self.databases
            
            print(f"\n[INFO] Migrations {'(Pending Only)' if pending_only else ''}:")
            
            for db_name in databases_to_check:
                migrations = migration_manager.get_migrations(db_name)
                applied_migrations = migration_manager.get_applied_migrations(db_name)
                
                if pending_only:
                    migrations = [m for m in migrations if m['version'] not in applied_migrations]
                
                print(f"\n  {db_name.upper()} Database:")
                
                if not migrations:
                    print("    No migrations found")
                    continue
                
                for migration in migrations:
                    version = migration['version']
                    name = migration['name']
                    applied = version in applied_migrations
                    status_icon = "[OK]" if applied else "[WAIT]"
                    
                    if pending_only and applied:
                        continue
                    
                    print(f"    {status_icon} {version} - {name}")
                    if applied:
                        applied_at = applied_migrations[version].get('applied_at', 'Unknown')
                        print(f"         Applied: {applied_at}")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Failed to list migrations: {e}")
            return 1
    
    def show_status(self, database: str = None) -> int:
        """Show migration status for databases."""
        try:
            databases_to_check = [database] if database else self.databases
            
            print("\n[STATS] Migration Status:")
            
            for db_name in databases_to_check:
                try:
                    status = migration_manager.get_migration_status(db_name)
                    
                    print(f"\n  {db_name.upper()} Database:")
                    print(f"    Current Version: {status.get('current_version', 'None')}")
                    print(f"    Available Migrations: {status.get('total_migrations', 0)}")
                    print(f"    Applied Migrations: {status.get('applied_count', 0)}")
                    print(f"    Pending Migrations: {status.get('pending_count', 0)}")
                    
                    if status.get('pending_count', 0) > 0:
                        print(f"    [WARNING]  {status['pending_count']} migrations pending")
                    else:
                        print(f"    [OK] All migrations applied")
                
                except Exception as e:
                    print(f"  [FAIL] {db_name.upper()}: Failed to get status ({e})")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Failed to get migration status: {e}")
            return 1
    
    def run_migrations(self, database: str = None, target: str = None, dry_run: bool = False) -> int:
        """Run pending migrations."""
        try:
            databases_to_migrate = [database] if database else self.databases
            
            if dry_run:
                print("[SEARCH] DRY RUN - Showing what would be migrated:")
            else:
                print("[START] Running migrations...")
            
            for db_name in databases_to_migrate:
                print(f"\n  {db_name.upper()} Database:")
                
                pending_migrations = migration_manager.get_pending_migrations(db_name)
                
                if target:
                    # Filter migrations up to target version
                    pending_migrations = [m for m in pending_migrations if m['version'] <= target]
                
                if not pending_migrations:
                    print("    No pending migrations")
                    continue
                
                for migration in pending_migrations:
                    version = migration['version']
                    name = migration['name']
                    
                    if dry_run:
                        print(f"    Would apply: {version} - {name}")
                    else:
                        print(f"    Applying: {version} - {name}")
                        
                        try:
                            migration_manager.apply_migration(db_name, migration)
                            print(f"    [OK] Applied: {version}")
                        except Exception as e:
                            print(f"    [FAIL] Failed: {version} - {e}")
                            return 1
            
            if not dry_run:
                print("\n[OK] Migration run completed")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Migration run failed: {e}")
            return 1
    
    def rollback_migration(self, database: str, steps: int = 1, to_version: str = None) -> int:
        """Rollback migrations."""
        try:
            print(f"Rolling back {database} database migrations...")
            
            if to_version:
                print(f"Target version: {to_version}")
                result = migration_manager.rollback_to_version(database, to_version)
            else:
                print(f"Rolling back {steps} step(s)")
                result = migration_manager.rollback_steps(database, steps)
            
            if result['success']:
                rolled_back = result.get('rolled_back', [])
                print(f"[OK] Successfully rolled back {len(rolled_back)} migration(s):")
                for migration in rolled_back:
                    print(f"  * {migration['version']} - {migration['name']}")
                return 0
            else:
                print(f"[FAIL] Rollback failed: {result.get('error', 'Unknown error')}")
                return 1
        
        except Exception as e:
            print(f"[FAIL] Rollback operation failed: {e}")
            return 1
    
    def create_migration(self, database: str, name: str, template: str) -> int:
        """Create new migration file."""
        try:
            print(f"Creating migration for {database} database: {name}")
            
            migration_file = migration_manager.create_migration_file(database, name, template)
            
            print(f"[OK] Migration created: {migration_file}")
            print(f"Edit the file to add your migration logic:")
            print(f"  {migration_file}")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Failed to create migration: {e}")
            return 1
    
    def validate_migrations(self, database: str = None) -> int:
        """Validate migration files."""
        try:
            databases_to_validate = [database] if database else self.databases
            
            print("[SEARCH] Validating migration files...")
            
            all_valid = True
            
            for db_name in databases_to_validate:
                print(f"\n  {db_name.upper()} Database:")
                
                validation_result = migration_manager.validate_migrations(db_name)
                
                if validation_result['valid']:
                    migration_count = validation_result.get('migration_count', 0)
                    print(f"    [OK] All {migration_count} migrations are valid")
                else:
                    all_valid = False
                    print(f"    [FAIL] Validation failed:")
                    for error in validation_result.get('errors', []):
                        print(f"      * {error}")
            
            return 0 if all_valid else 1
        
        except Exception as e:
            print(f"[FAIL] Validation failed: {e}")
            return 1
    
    def show_history(self, database: str = None, limit: int = 20) -> int:
        """Show migration history."""
        try:
            databases_to_check = [database] if database else self.databases
            
            print(f"\n📚 Migration History (limit: {limit}):")
            
            for db_name in databases_to_check:
                print(f"\n  {db_name.upper()} Database:")
                
                history = migration_manager.get_migration_history(db_name, limit=limit)
                
                if not history:
                    print("    No migration history")
                    continue
                
                print("    Version | Name | Applied At | Duration")
                print("    " + "-" * 60)
                
                for entry in history:
                    version = entry.get('version', 'Unknown')
                    name = entry.get('name', 'Unknown')
                    applied_at = entry.get('applied_at', 'Unknown')
                    duration = entry.get('duration_ms', 0)
                    
                    print(f"    {version} | {name} | {applied_at} | {duration}ms")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Failed to get migration history: {e}")
            return 1


__all__ = ['MigrationCommands']