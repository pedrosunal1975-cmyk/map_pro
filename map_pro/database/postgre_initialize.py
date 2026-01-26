#!/usr/bin/env python3
# Path: database/postgre_initialize.py
"""
PostgreSQL Database Initialization

Handles complete PostgreSQL server initialization:
1. Verifies data directory exists (created by core/data_paths.py)
2. Runs initdb if data directory is empty
3. Starts PostgreSQL service
4. Seeds markets table

Architecture:
- Uses configuration from .env via database/core/config_loader.py
- Depends on core/data_paths.py for directory creation
- No hardcoded paths - all from configuration
- Idempotent - safe to run multiple times

Usage:
    # As module
    from database.postgre_initialize import initialize_postgresql
    result = initialize_postgresql()

    # As script
    python -m database.postgre_initialize
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

# Import configuration from database module
from database.core.config_loader import ConfigLoader
from database.core.logger import get_logger

# Get logger
logger = get_logger(__name__, 'core')


class PostgreSQLInitializer:
    """
    Handles PostgreSQL server initialization.

    Ensures PostgreSQL is properly initialized and running
    before the application can use the database.

    Example:
        initializer = PostgreSQLInitializer()
        result = initializer.initialize()
        if result['success']:
            print("PostgreSQL ready")
    """

    def __init__(self, config: Optional[ConfigLoader] = None):
        """
        Initialize PostgreSQL initializer.

        Args:
            config: Optional ConfigLoader instance. If None, creates new one.
        """
        self.config = config if config else ConfigLoader()
        self._pg_data_dir = self.config.get('db_postgresql_data_dir')

    def get_data_directory(self) -> Path:
        """
        Get PostgreSQL data directory from configuration.

        Returns:
            Path to PostgreSQL data directory
        """
        return self._pg_data_dir

    def is_directory_initialized(self) -> bool:
        """
        Check if PostgreSQL data directory is initialized.

        Checks for PG_VERSION file which indicates initdb was run.

        Returns:
            True if directory is initialized, False otherwise
        """
        if not self._pg_data_dir:
            return False

        pg_version_file = self._pg_data_dir / 'PG_VERSION'
        return pg_version_file.exists()

    def is_directory_exists(self) -> bool:
        """
        Check if PostgreSQL data directory exists.

        Returns:
            True if directory exists, False otherwise
        """
        if not self._pg_data_dir:
            return False
        return self._pg_data_dir.exists()

    def is_postgresql_running(self) -> bool:
        """
        Check if PostgreSQL service is running.

        Returns:
            True if PostgreSQL is running, False otherwise
        """
        try:
            result = subprocess.run(
                ['pg_isready', '-h', 'localhost', '-p', '5432'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def run_initdb(self) -> Dict:
        """
        Run initdb to initialize PostgreSQL data directory.

        Returns:
            Dictionary with result:
                - success: bool
                - message: str
                - output: str (command output)
        """
        if not self._pg_data_dir:
            return {
                'success': False,
                'message': 'PostgreSQL data directory not configured',
                'output': ''
            }

        # First, ensure directory has correct ownership
        logger.info(f"Initializing PostgreSQL data directory: {self._pg_data_dir}")

        try:
            # Set ownership to postgres user
            chown_cmd = ['sudo', 'chown', '-R', 'postgres:postgres', str(self._pg_data_dir)]
            logger.info(f"Setting ownership: {' '.join(chown_cmd)}")

            chown_result = subprocess.run(
                chown_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if chown_result.returncode != 0:
                logger.warning(f"chown warning: {chown_result.stderr}")

            # Run initdb as postgres user
            initdb_cmd = [
                'sudo', '-u', 'postgres',
                'initdb',
                '--locale=C.UTF-8',
                '--encoding=UTF8',
                '-D', str(self._pg_data_dir)
            ]

            logger.info(f"Running initdb: {' '.join(initdb_cmd)}")

            result = subprocess.run(
                initdb_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info("initdb completed successfully")
                return {
                    'success': True,
                    'message': 'PostgreSQL data directory initialized successfully',
                    'output': result.stdout
                }
            else:
                logger.error(f"initdb failed: {result.stderr}")
                return {
                    'success': False,
                    'message': f'initdb failed: {result.stderr}',
                    'output': result.stdout + result.stderr
                }

        except subprocess.TimeoutExpired:
            logger.error("initdb timed out")
            return {
                'success': False,
                'message': 'initdb timed out after 120 seconds',
                'output': ''
            }
        except FileNotFoundError as e:
            logger.error(f"Command not found: {e}")
            return {
                'success': False,
                'message': f'Required command not found: {e}',
                'output': ''
            }
        except Exception as e:
            logger.error(f"initdb error: {e}")
            return {
                'success': False,
                'message': f'initdb error: {e}',
                'output': ''
            }

    def start_postgresql(self) -> Dict:
        """
        Start PostgreSQL service.

        Returns:
            Dictionary with result:
                - success: bool
                - message: str
        """
        logger.info("Starting PostgreSQL service...")

        try:
            # Start PostgreSQL using systemctl
            result = subprocess.run(
                ['sudo', 'systemctl', 'start', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Wait for PostgreSQL to be ready
                for i in range(10):
                    if self.is_postgresql_running():
                        logger.info("PostgreSQL started successfully")
                        return {
                            'success': True,
                            'message': 'PostgreSQL started successfully'
                        }
                    time.sleep(1)

                logger.warning("PostgreSQL started but not responding")
                return {
                    'success': False,
                    'message': 'PostgreSQL started but not responding to connections'
                }
            else:
                logger.error(f"Failed to start PostgreSQL: {result.stderr}")
                return {
                    'success': False,
                    'message': f'Failed to start PostgreSQL: {result.stderr}'
                }

        except subprocess.TimeoutExpired:
            logger.error("PostgreSQL start timed out")
            return {
                'success': False,
                'message': 'PostgreSQL start timed out'
            }
        except Exception as e:
            logger.error(f"Failed to start PostgreSQL: {e}")
            return {
                'success': False,
                'message': f'Failed to start PostgreSQL: {e}'
            }

    def seed_markets(self) -> Dict:
        """
        Seed markets table with supported markets.

        Uses market data from searcher.constants.MARKETS_SEED_DATA.
        Idempotent - safe to run multiple times.

        Returns:
            Dictionary with result:
                - success: bool
                - message: str
                - markets_added: int
                - markets_existing: int
        """
        logger.info("Seeding markets table...")

        try:
            # Import here to avoid circular imports and ensure DB is ready
            from database import initialize_database, session_scope
            from database.models import Market
            from searcher.constants import MARKETS_SEED_DATA

            # Initialize database (creates tables if needed)
            initialize_database()

            markets_added = 0
            markets_existing = 0

            with session_scope() as session:
                for market_data in MARKETS_SEED_DATA:
                    existing = session.query(Market).filter_by(
                        market_id=market_data['market_id']
                    ).first()

                    if existing:
                        logger.info(f"Market '{market_data['market_id']}' already exists")
                        markets_existing += 1
                    else:
                        market = Market(**market_data)
                        session.add(market)
                        logger.info(f"Added market '{market_data['market_id']}': {market_data['market_name']}")
                        markets_added += 1

                session.commit()

            logger.info(f"Markets seeding complete: {markets_added} added, {markets_existing} existing")

            return {
                'success': True,
                'message': 'Markets seeded successfully',
                'markets_added': markets_added,
                'markets_existing': markets_existing
            }

        except Exception as e:
            logger.error(f"Failed to seed markets: {e}")
            return {
                'success': False,
                'message': f'Failed to seed markets: {e}',
                'markets_added': 0,
                'markets_existing': 0
            }

    def initialize(self, seed_markets: bool = True) -> Dict:
        """
        Complete PostgreSQL initialization.

        Performs all steps:
        1. Verify data directory exists
        2. Run initdb if needed
        3. Start PostgreSQL
        4. Seed markets (optional)

        Args:
            seed_markets: Whether to seed markets table after initialization

        Returns:
            Dictionary with complete result
        """
        result = {
            'success': False,
            'steps': {},
            'message': ''
        }

        print("\n" + "=" * 70)
        print("POSTGRESQL INITIALIZATION")
        print("=" * 70)

        # Step 1: Check data directory exists
        print("\nStep 1: Checking data directory...")
        if not self.is_directory_exists():
            result['steps']['directory_check'] = {
                'success': False,
                'message': f'Data directory does not exist: {self._pg_data_dir}'
            }
            result['message'] = 'Data directory not found. Run core/data_paths.py first.'
            print(f"  ✗ Directory not found: {self._pg_data_dir}")
            print("  Run the application to create directories first.")
            return result

        result['steps']['directory_check'] = {
            'success': True,
            'message': f'Data directory exists: {self._pg_data_dir}'
        }
        print(f"  ✓ Directory exists: {self._pg_data_dir}")

        # Step 2: Run initdb if needed
        print("\nStep 2: Checking initialization status...")
        if not self.is_directory_initialized():
            print("  Directory not initialized. Running initdb...")
            initdb_result = self.run_initdb()
            result['steps']['initdb'] = initdb_result

            if not initdb_result['success']:
                result['message'] = initdb_result['message']
                print(f"  ✗ initdb failed: {initdb_result['message']}")
                return result

            print("  ✓ initdb completed successfully")
        else:
            result['steps']['initdb'] = {
                'success': True,
                'message': 'Already initialized (PG_VERSION exists)'
            }
            print("  ✓ Already initialized")

        # Step 3: Start PostgreSQL
        print("\nStep 3: Starting PostgreSQL...")
        if self.is_postgresql_running():
            result['steps']['start'] = {
                'success': True,
                'message': 'PostgreSQL already running'
            }
            print("  ✓ PostgreSQL already running")
        else:
            start_result = self.start_postgresql()
            result['steps']['start'] = start_result

            if not start_result['success']:
                result['message'] = start_result['message']
                print(f"  ✗ Failed to start: {start_result['message']}")
                return result

            print("  ✓ PostgreSQL started successfully")

        # Step 4: Seed markets (optional)
        if seed_markets:
            print("\nStep 4: Seeding markets...")
            seed_result = self.seed_markets()
            result['steps']['seed_markets'] = seed_result

            if seed_result['success']:
                print(f"  ✓ Markets: {seed_result['markets_added']} added, {seed_result['markets_existing']} existing")
            else:
                print(f"  ✗ Failed to seed markets: {seed_result['message']}")
                # Don't fail initialization if seeding fails - PostgreSQL is still ready

        result['success'] = True
        result['message'] = 'PostgreSQL initialized successfully'

        print("\n" + "=" * 70)
        print("POSTGRESQL READY")
        print("=" * 70 + "\n")

        return result


def initialize_postgresql(seed_markets: bool = True) -> Dict:
    """
    Convenience function to initialize PostgreSQL.

    Args:
        seed_markets: Whether to seed markets table

    Returns:
        Dictionary with initialization result
    """
    initializer = PostgreSQLInitializer()
    return initializer.initialize(seed_markets=seed_markets)


def check_postgresql_status() -> Dict:
    """
    Check PostgreSQL status without making changes.

    Returns:
        Dictionary with status information
    """
    initializer = PostgreSQLInitializer()

    return {
        'data_directory': str(initializer.get_data_directory()),
        'directory_exists': initializer.is_directory_exists(),
        'directory_initialized': initializer.is_directory_initialized(),
        'postgresql_running': initializer.is_postgresql_running()
    }


def main():
    """Main entry point for script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Initialize PostgreSQL for Map Pro',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m database.postgre_initialize              # Full initialization
    python -m database.postgre_initialize --status     # Check status only
    python -m database.postgre_initialize --no-seed    # Skip market seeding
        """
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Check status without making changes'
    )
    parser.add_argument(
        '--no-seed',
        action='store_true',
        help='Skip market seeding'
    )

    args = parser.parse_args()

    if args.status:
        status = check_postgresql_status()
        print("\nPostgreSQL Status:")
        print(f"  Data directory: {status['data_directory']}")
        print(f"  Directory exists: {status['directory_exists']}")
        print(f"  Directory initialized: {status['directory_initialized']}")
        print(f"  PostgreSQL running: {status['postgresql_running']}")
        sys.exit(0)

    result = initialize_postgresql(seed_markets=not args.no_seed)

    if result['success']:
        print("\n[SUCCESS] PostgreSQL initialization complete")
        sys.exit(0)
    else:
        print(f"\n[ERROR] {result['message']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
