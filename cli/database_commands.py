"""
Map Pro Database CLI Commands
=============================

Database administration commands for the CLI.

Save location: tools/cli/database_commands.py
"""

import argparse
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from tools.maintenance.backup_manager import BackupManager

logger = get_logger(__name__, 'maintenance')


class DatabaseCommands:
    """Database administration commands."""
    
    def __init__(self):
        """Initialize database commands."""
        self.logger = logger
        self.databases = ['core', 'parsed', 'library', 'mapped']
    
    def setup_parser(self, parser: argparse.ArgumentParser):
        """Setup database command parser."""
        subparsers = parser.add_subparsers(dest='db_action', help='Database actions')
        
        # Status command
        subparsers.add_parser('status', help='Check database connection status')
        
        # Connection test
        subparsers.add_parser('test', help='Test database connections')
        
        # Query execution
        query_parser = subparsers.add_parser('query', help='Execute SQL query')
        query_parser.add_argument('database', choices=self.databases, help='Target database')
        query_parser.add_argument('sql', help='SQL query to execute')
        query_parser.add_argument('--limit', type=int, default=100, help='Limit results')
        
        # Backup operations
        backup_parser = subparsers.add_parser('backup', help='Create database backup')
        backup_parser.add_argument('--database', choices=self.databases, help='Specific database')
        
        # Restore operations
        restore_parser = subparsers.add_parser('restore', help='Restore database from backup')
        restore_parser.add_argument('database', choices=self.databases, help='Target database')
        restore_parser.add_argument('backup_file', help='Backup file path')
        restore_parser.add_argument('--drop-existing', action='store_true', help='Drop existing database')
        
        # Statistics
        stats_parser = subparsers.add_parser('stats', help='Show database statistics')
        stats_parser.add_argument('--database', choices=self.databases, help='Specific database')
        
        # Vacuum/optimize
        optimize_parser = subparsers.add_parser('optimize', help='Optimize database')
        optimize_parser.add_argument('database', choices=self.databases, help='Target database')
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute database command."""
        action = args.db_action
        
        if action == 'status':
            return self.show_status()
        
        elif action == 'test':
            return self.test_connections()
        
        elif action == 'query':
            return self.execute_query(args.database, args.sql, args.limit)
        
        elif action == 'backup':
            return self.create_backup(args.database)
        
        elif action == 'restore':
            return self.restore_backup(args.database, args.backup_file, args.drop_existing)
        
        elif action == 'stats':
            return self.show_statistics(args.database)
        
        elif action == 'optimize':
            return self.optimize_database(args.database)
        
        else:
            print(f"Unknown database action: {action}")
            return 1
    
    def show_status(self) -> int:
        """Show database connection status."""
        print("\n🗄️  Database Status:")
        
        all_healthy = True
        
        for db_name in self.databases:
            try:
                with db_coordinator.get_connection(db_name) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                
                print(f"  [OK] {db_name.upper()}: Connected")
            
            except Exception as e:
                print(f"  [FAIL] {db_name.upper()}: Failed ({e})")
                all_healthy = False
        
        return 0 if all_healthy else 1
    
    def test_connections(self) -> int:
        """Test all database connections with detailed info."""
        print("\n[SEARCH] Database Connection Tests:")
        
        all_passed = True
        
        for db_name in self.databases:
            try:
                start_time = __import__('time').time()
                
                with db_coordinator.get_connection(db_name) as conn:
                    with conn.cursor() as cursor:
                        # Test basic query
                        cursor.execute("SELECT version()")
                        version = cursor.fetchone()[0]
                        
                        # Test performance
                        cursor.execute("SELECT COUNT(*) FROM information_schema.tables")
                        table_count = cursor.fetchone()[0]
                
                response_time = (__import__('time').time() - start_time) * 1000
                
                print(f"  [OK] {db_name.upper()}: OK ({response_time:.1f}ms)")
                print(f"     Version: {version}")
                print(f"     Tables: {table_count}")
            
            except Exception as e:
                print(f"  [FAIL] {db_name.upper()}: FAILED")
                print(f"     Error: {e}")
                all_passed = False
        
        return 0 if all_passed else 1
    
    def execute_query(self, database: str, sql: str, limit: int) -> int:
        """Execute SQL query and display results."""
        try:
            print(f"\n[SEARCH] Executing query on {database.upper()} database:")
            print(f"SQL: {sql}")
            
            with db_coordinator.get_connection(database) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    
                    # Handle different query types
                    if sql.strip().upper().startswith('SELECT'):
                        results = cursor.fetchmany(limit)
                        
                        if results:
                            # Show column names
                            columns = [desc[0] for desc in cursor.description]
                            print(f"\nResults ({len(results)} rows):")
                            print("  " + " | ".join(columns))
                            print("  " + "-" * (len(" | ".join(columns))))
                            
                            # Show data
                            for row in results:
                                formatted_row = []
                                for item in row:
                                    if isinstance(item, str) and len(item) > 50:
                                        formatted_row.append(item[:47] + "...")
                                    else:
                                        formatted_row.append(str(item))
                                print("  " + " | ".join(formatted_row))
                        else:
                            print("\nNo results returned.")
                    
                    else:
                        # For non-SELECT queries
                        affected = cursor.rowcount
                        print(f"\nQuery executed. Rows affected: {affected}")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Query failed: {e}")
            return 1
    
    def create_backup(self, database: Optional[str]) -> int:
        """Create database backup."""
        try:
            manager = BackupManager()
            
            if database:
                print(f"Creating backup for {database} database...")
                # This would need individual database backup method
                result = manager.create_full_backup()
                
                if result['success']:
                    print(f"[OK] Backup created for {database}")
                    return 0
                else:
                    print(f"[FAIL] Backup failed: {result['errors']}")
                    return 1
            else:
                print("Creating backup for all databases...")
                result = manager.create_full_backup()
                
                if result['success']:
                    print(f"[OK] Full backup created: {result['backup_name']}")
                    return 0
                else:
                    print(f"[FAIL] Backup failed: {result['errors']}")
                    return 1
        
        except Exception as e:
            print(f"[FAIL] Backup operation failed: {e}")
            return 1
    
    def restore_backup(self, database: str, backup_file: str, drop_existing: bool) -> int:
        """Restore database from backup."""
        try:
            print(f"Restoring {database} database from {backup_file}...")
            
            if drop_existing:
                print("[WARNING]  This will DROP the existing database!")
                response = input("Continue? [y/N]: ")
                if response.lower() != 'y':
                    print("Restore cancelled.")
                    return 0
            
            manager = BackupManager()
            result = manager.restore_database(database, backup_file, drop_existing)
            
            if result['success']:
                print(f"[OK] Database {database} restored successfully")
                return 0
            else:
                print(f"[FAIL] Restore failed: {result['error']}")
                return 1
        
        except Exception as e:
            print(f"[FAIL] Restore operation failed: {e}")
            return 1
    
    def show_statistics(self, database: Optional[str]) -> int:
        """Show database statistics."""
        try:
            databases_to_check = [database] if database else self.databases
            
            print("\n[STATS] Database Statistics:")
            
            for db_name in databases_to_check:
                try:
                    with db_coordinator.get_connection(db_name) as conn:
                        with conn.cursor() as cursor:
                            # Get table count
                            cursor.execute("""
                                SELECT COUNT(*) 
                                FROM information_schema.tables 
                                WHERE table_schema = 'public'
                            """)
                            table_count = cursor.fetchone()[0]
                            
                            # Get database size
                            cursor.execute(f"""
                                SELECT pg_size_pretty(pg_database_size(current_database()))
                            """)
                            db_size = cursor.fetchone()[0]
                            
                            print(f"\n  {db_name.upper()} Database:")
                            print(f"    Tables: {table_count}")
                            print(f"    Size: {db_size}")
                            
                            # Get top tables by size
                            cursor.execute("""
                                SELECT 
                                    schemaname,
                                    tablename,
                                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                                FROM pg_tables 
                                WHERE schemaname = 'public'
                                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                                LIMIT 5
                            """)
                            
                            tables = cursor.fetchall()
                            if tables:
                                print("    Largest Tables:")
                                for schema, table, size in tables:
                                    print(f"      * {table}: {size}")
                
                except Exception as e:
                    print(f"  [FAIL] {db_name.upper()}: Failed to get statistics ({e})")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Statistics operation failed: {e}")
            return 1
    
    def optimize_database(self, database: str) -> int:
        """Optimize database performance."""
        try:
            print(f"Optimizing {database} database...")
            
            with db_coordinator.get_connection(database) as conn:
                with conn.cursor() as cursor:
                    # Run VACUUM ANALYZE
                    cursor.execute("VACUUM ANALYZE")
                    
                    # Update statistics
                    cursor.execute("ANALYZE")
            
            print(f"[OK] Database {database} optimized")
            return 0
        
        except Exception as e:
            print(f"[FAIL] Optimization failed: {e}")
            return 1
    
    def list_jobs(self, status_filter: Optional[str], limit: int) -> int:
        """List jobs with optional status filter."""
        try:
            print(f"\n[INFO] Jobs List (limit: {limit}):")
            
            with db_coordinator.get_connection('core') as conn:
                with conn.cursor() as cursor:
                    # Build query with optional status filter
                    if status_filter:
                        cursor.execute("""
                            SELECT id, job_type, status, created_at, updated_at, error_message
                            FROM jobs 
                            WHERE status = %s
                            ORDER BY updated_at DESC 
                            LIMIT %s
                        """, (status_filter, limit))
                    else:
                        cursor.execute("""
                            SELECT id, job_type, status, created_at, updated_at, error_message
                            FROM jobs 
                            ORDER BY updated_at DESC 
                            LIMIT %s
                        """, (limit,))
                    
                    jobs = cursor.fetchall()
                    
                    if jobs:
                        print("  ID | Type | Status | Created | Updated | Error")
                        print("  " + "-" * 60)
                        
                        for job in jobs:
                            job_id, job_type, status, created, updated, error = job
                            error_preview = (error[:30] + "...") if error else ""
                            print(f"  {job_id} | {job_type} | {status} | {created} | {updated} | {error_preview}")
                    else:
                        print("  No jobs found.")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Failed to list jobs: {e}")
            return 1
    
    def clear_failed_jobs(self) -> int:
        """Clear failed jobs from database."""
        try:
            print("Clearing failed jobs...")
            
            with db_coordinator.get_connection('core') as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM jobs WHERE status IN ('failed', 'error')")
                    cleared_count = cursor.rowcount
            
            print(f"[OK] Cleared {cleared_count} failed jobs")
            return 0
        
        except Exception as e:
            print(f"[FAIL] Failed to clear jobs: {e}")
            return 1
    
    def show_job_stats(self) -> int:
        """Show job statistics."""
        try:
            print("\n[UP] Job Statistics:")
            
            with db_coordinator.get_connection('core') as conn:
                with conn.cursor() as cursor:
                    # Status breakdown
                    cursor.execute("""
                        SELECT status, COUNT(*) as count
                        FROM jobs 
                        GROUP BY status
                        ORDER BY count DESC
                    """)
                    
                    status_counts = cursor.fetchall()
                    
                    print("  Status Breakdown:")
                    for status, count in status_counts:
                        print(f"    {status}: {count}")
                    
                    # Recent activity
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM jobs 
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                    """)
                    recent_count = cursor.fetchone()[0]
                    
                    print(f"\n  Recent Activity (24h): {recent_count} jobs")
            
            return 0
        
        except Exception as e:
            print(f"[FAIL] Failed to get job stats: {e}")
            return 1


__all__ = ['DatabaseCommands']