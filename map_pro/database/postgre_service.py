# Path: database/postgre_service.py
"""
PostgreSQL Service Management

Handles PostgreSQL service operations:
- Status checking (running, initialized)
- Starting/stopping service
- Connection verification

Uses configuration from .env via database/core/config_loader.py.
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from database.core.config_loader import ConfigLoader
from database.core.logger import get_logger

logger = get_logger(__name__, 'core')


class PostgreSQLService:
    """Manages PostgreSQL service operations."""

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config if config else ConfigLoader()
        self._pg_data_dir = self.config.get('db_postgresql_data_dir')

    def get_data_directory(self) -> Path:
        """Get PostgreSQL data directory from configuration."""
        return self._pg_data_dir

    def is_directory_exists(self) -> bool:
        """Check if PostgreSQL data directory exists."""
        if not self._pg_data_dir:
            return False
        return self._pg_data_dir.exists()

    def is_directory_initialized(self) -> bool:
        """Check if PostgreSQL data directory is initialized (has PG_VERSION)."""
        if not self._pg_data_dir:
            return False
        pg_version_file = self._pg_data_dir / 'PG_VERSION'
        return pg_version_file.exists()

    def is_service_running(self) -> bool:
        """Check if PostgreSQL service is running using systemctl."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == 'active'
        except Exception:
            return False

    def can_connect(self) -> bool:
        """
        Actually try to connect to PostgreSQL to verify it's working.
        This is more reliable than pg_isready.
        """
        db_user = self.config.get('db_user')
        db_name = self.config.get('db_name')
        db_host = self.config.get('db_host', 'localhost')
        db_port = self.config.get('db_port', 5432)

        try:
            # Try connecting with psql
            result = subprocess.run(
                ['psql', '-h', str(db_host), '-p', str(db_port),
                 '-U', db_user, '-d', db_name, '-c', 'SELECT 1;'],
                capture_output=True,
                text=True,
                timeout=5,
                env={**subprocess.os.environ, 'PGPASSWORD': self.config.get('db_password', '')}
            )
            return result.returncode == 0
        except Exception:
            return False

    def start(self) -> Dict:
        """Start PostgreSQL service."""
        logger.info("Starting PostgreSQL service...")

        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'start', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'message': f'Failed to start: {result.stderr}'
                }

            # Wait for service to be active
            for _ in range(10):
                if self.is_service_running():
                    logger.info("PostgreSQL service started")
                    return {'success': True, 'message': 'PostgreSQL started'}
                time.sleep(1)

            return {
                'success': False,
                'message': 'Service started but not responding'
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'message': 'Start command timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def stop(self) -> Dict:
        """Stop PostgreSQL service."""
        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'stop', 'postgresql'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                'success': result.returncode == 0,
                'message': 'Stopped' if result.returncode == 0 else result.stderr
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def run_initdb(self) -> Dict:
        """Run initdb to initialize PostgreSQL data directory."""
        if not self._pg_data_dir:
            return {'success': False, 'message': 'Data directory not configured'}

        logger.info(f"Running initdb: {self._pg_data_dir}")

        try:
            # Set ownership
            subprocess.run(
                ['sudo', 'chown', '-R', 'postgres:postgres', str(self._pg_data_dir)],
                capture_output=True, timeout=30
            )

            # Run initdb
            result = subprocess.run(
                ['sudo', '-u', 'postgres', 'initdb',
                 '--locale=C.UTF-8', '--encoding=UTF8',
                 '-D', str(self._pg_data_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info("initdb completed")
                return {'success': True, 'message': 'initdb completed'}
            else:
                return {'success': False, 'message': result.stderr}

        except subprocess.TimeoutExpired:
            return {'success': False, 'message': 'initdb timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
