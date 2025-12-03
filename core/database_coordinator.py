# PATH: /map_pro/core/database_coordinator.py

"""
Map Pro Database Coordinator
============================

Central coordination for Map Pro's four-database PostgreSQL architecture.
Provides oversight and session management without implementing specific database operations.

Architecture: Core oversight/coordination only - engines handle their own database logic.
Manages connections to: core_db, parsed_db, library_db, mapped_db

Uses data_paths.py for configuration locations and system_logger.py for all logging.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional, Any, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

from .data_paths import map_pro_paths
from .system_logger import get_logger

logger = get_logger(__name__, 'core')


class DatabaseCoordinator:
    """
    Central coordinator for Map Pro's four-database architecture.
    
    Responsibilities:
    - Connection management and pooling for all four databases
    - Session lifecycle coordination 
    - Health monitoring across databases
    - Configuration management for database connections
    
    Does NOT handle:
    - Specific database operations (engines handle their own queries)
    - Cross-database transactions (application-level coordination only)
    - Schema management (migration system handles this)
    """
    
    def __init__(self):
        self.database_names = ['core', 'parsed', 'library', 'mapped']
        self.engines: Dict[str, Any] = {}
        self.session_factories: Dict[str, Any] = {}
        self.connection_config = {}
        self._is_initialized = False
        
        logger.info("Database coordinator initializing")
    
    def _cleanup_stale_connections(self):
        """
        Cleanup stale database connections before initialization.
        
        Terminates all connections to Map Pro databases except the current one.
        This prevents connection pool exhaustion from previous program runs.
        """
        try:
            logger.info("Cleaning up stale database connections")
            
            # Database names to clean
            target_databases = [
                'map_pro_core',
                'map_pro_parsed', 
                'map_pro_library',
                'map_pro_mapped'
            ]
            
            # Get postgres connection URL for cleanup
            postgres_url = self._get_postgres_admin_url()
            
            if not postgres_url:
                logger.warning("Cannot cleanup connections - no postgres admin URL")
                return
            
            # Import here to avoid circular dependency
            import psycopg2
            
            # Connect to postgres database (not target databases)
            conn = psycopg2.connect(postgres_url)
            conn.autocommit = True
            cursor = conn.cursor()
            
            total_killed = 0
            
            for db_name in target_databases:
                try:
                    # Kill all connections to this database except our own
                    query = """
                    SELECT pg_terminate_backend(pid) 
                    FROM pg_stat_activity 
                    WHERE pid <> pg_backend_pid() 
                    AND datname = %s
                    """
                    
                    cursor.execute(query, (db_name,))
                    killed = cursor.rowcount
                    total_killed += killed
                    
                    if killed > 0:
                        logger.info(f"Terminated {killed} stale connections to {db_name}")
                
                except Exception as e:
                    logger.warning(f"Could not cleanup connections for {db_name}: {e}")
            
            cursor.close()
            conn.close()
            
            if total_killed > 0:
                logger.info(f"Successfully cleaned up {total_killed} stale connections")
            else:
                logger.debug("No stale connections found")
        
        except ImportError:
            logger.warning("psycopg2 not available for connection cleanup")
        except Exception as e:
            logger.warning(f"Connection cleanup failed (non-critical): {e}")
    
    def _get_postgres_admin_url(self) -> Optional[str]:
        """
        Get postgres admin connection URL for cleanup operations.
        
        Returns:
            Connection URL for postgres database, or None if not available
        """
        try:
            # Try to get from environment
            admin_user = os.environ.get('POSTGRES_ADMIN_USER', 'postgres')
            admin_pass = os.environ.get('POSTGRES_ADMIN_PASSWORD', '')
            
            # Build connection string to postgres database (not map_pro databases)
            if admin_pass:
                return f"postgresql://{admin_user}:{admin_pass}@localhost:5432/postgres"
            else:
                # Try without password (peer authentication)
                return f"postgresql://{admin_user}@localhost:5432/postgres"
        
        except Exception as e:
            logger.warning(f"Could not build postgres admin URL: {e}")
            return None
    
    def initialize(self):
        """Initialize all database connections and validate connectivity."""
        # Skip if already initialized (idempotency)
        if self._is_initialized:
            logger.debug("Database coordinator already initialized, skipping")
            return True
        
        # Cleanup stale connections from previous runs
        self._cleanup_stale_connections()
        
        try:
            print("DEBUG: Starting database coordinator initialization")
            
            print("DEBUG: Loading connection config")
            self._load_connection_config()
            
            print("DEBUG: Creating engines")
            self._create_engines()
            
            print("DEBUG: Creating session factories")
            self._create_session_factories()
            
            print("DEBUG: Validating connections")
            self._validate_connections()
            
            self._is_initialized = True
            print("DEBUG: Database coordinator initialized successfully")
            logger.info("Database coordinator initialized successfully")
            
            return True  # <- ADD THIS MISSING LINE!
            
        except Exception as e:
            print(f"DEBUG: Database coordinator initialization failed: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Database coordinator initialization failed: {e}")
            raise
    
    def _load_connection_config(self):
        """Load database connection configuration from correct locations."""
        # First, try to load .env file from correct locations
        try:
            from dotenv import load_dotenv
            
            # Check for .env file in standard locations
            possible_env_paths = [
                Path(__file__).parent.parent / ".env",  # Program root (most likely)
                map_pro_paths.program_root / ".env",     # Program root via data_paths
                map_pro_paths.config_system / ".env",   # Config directory
                Path(".env")  # Current working directory
            ]
            
            env_loaded = False
            for env_path in possible_env_paths:
                if env_path.exists():
                    load_dotenv(str(env_path), interpolate=True)
                    logger.info(f"Loaded environment variables from {env_path}")
                    env_loaded = True
                    break
            
            if not env_loaded:
                logger.info("No .env file found, using system environment variables only")
                
        except ImportError:
            logger.warning("python-dotenv not installed, using system environment variables only")
        except Exception as e:
            logger.warning(f"Error loading .env file: {e}, using system environment variables only")
        
        # Default connection strings
        default_config = {
            'core': 'postgresql://map_pro_user:map_pro_pass@localhost:5432/map_pro_core',
            'parsed': 'postgresql://map_pro_user:map_pro_pass@localhost:5432/map_pro_parsed', 
            'library': 'postgresql://map_pro_user:map_pro_pass@localhost:5432/map_pro_library',
            'mapped': 'postgresql://map_pro_user:map_pro_pass@localhost:5432/map_pro_mapped'
        }
        
        # Load from environment variables (now includes .env if loaded)
        for db_name in self.database_names:
            env_var = f"MAP_PRO_{db_name.upper()}_DB_URL"
            db_url = os.getenv(env_var)
            
            if db_url:
                self.connection_config[db_name] = db_url
                logger.info(f"Loaded {db_name} database URL from environment")
            else:
                self.connection_config[db_name] = default_config[db_name]
                logger.info(f"Using default database URL for {db_name} (set {env_var} to override)")
                    
    def _create_engines(self):
        """Create SQLAlchemy engines for each database - FIXED to read .env pool settings."""
        
        # READ POOL CONFIGURATION FROM ENVIRONMENT/.env FILE
        pool_size = int(os.getenv('MAP_PRO_DB_POOL_SIZE', '5'))  # Default reduced from 10 to 5
        max_overflow = int(os.getenv('MAP_PRO_DB_MAX_OVERFLOW', '10'))  # Default reduced from 20 to 10  
        pool_timeout = int(os.getenv('MAP_PRO_DB_POOL_TIMEOUT', '30'))
        pool_recycle = int(os.getenv('MAP_PRO_DB_POOL_RECYCLE', '3600'))
        
        logger.info(f"Using database pool settings from environment: pool_size={pool_size}, max_overflow={max_overflow}")
        
        for db_name in self.database_names:
            try:
                engine = create_engine(
                    self.connection_config[db_name],
                    poolclass=QueuePool,
                    pool_size=pool_size,           # NOW READS FROM .env
                    max_overflow=max_overflow,     # NOW READS FROM .env  
                    pool_timeout=pool_timeout,     # NOW READS FROM .env
                    pool_recycle=pool_recycle,     # NOW READS FROM .env
                    pool_pre_ping=True,            # Test connections before use
                    echo=False,
                    isolation_level="READ COMMITTED"
                )
                
                self.engines[db_name] = engine
                logger.info(f"Created database engine for {db_name} (pool_size={pool_size}, max_overflow={max_overflow})")
                
            except Exception as e:
                logger.error(f"Failed to create engine for {db_name}: {e}")
                raise
    
    def _create_session_factories(self):
        """Create session factories for each database."""
        for db_name, engine in self.engines.items():
            try:
                session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
                self.session_factories[db_name] = session_factory
                logger.info(f"Created session factory for {db_name}")
                
            except Exception as e:
                logger.error(f"Failed to create session factory for {db_name}: {e}")
                raise
    
    def _validate_connections(self):
        """Validate that all database connections are working."""
        for db_name, engine in self.engines.items():
            try:
                with engine.connect() as connection:
                    # Simple connectivity test
                    result = connection.execute(text("SELECT 1"))
                    result.fetchone()
                    logger.info(f"Database connectivity validated for {db_name}")
            except Exception as e:
                logger.error(f"Database connectivity failed for {db_name}: {e}")
                
                # ADD: Just better error diagnosis without changing behavior
                error_msg = str(e).lower()
                if 'does not exist' in error_msg:
                    logger.error(f"Database {db_name} does not exist - run migrations first")
                elif 'authentication failed' in error_msg:
                    logger.error(f"Authentication failed for {db_name} - check username/password") 
                elif 'connection refused' in error_msg:
                    logger.error(f"Connection refused for {db_name} - check if PostgreSQL is running")
                
                raise  
    
    @contextmanager
    def get_session(self, database_name: str) -> Generator:
        """
        Get database session with automatic cleanup.
        
        Args:
            database_name: One of 'core', 'parsed', 'library', 'mapped'
            
        Yields:
            SQLAlchemy session with automatic commit/rollback/close
            
        Usage:
            with db_coordinator.get_session('core') as session:
                result = session.query(Entity).all()
        """
        if not self._is_initialized:
            raise RuntimeError("Database coordinator not initialized")
        
        if database_name not in self.database_names:
            raise ValueError(f"Unknown database: {database_name}. Must be one of {self.database_names}")
        
        session = self.session_factories[database_name]()
        try:
            yield session
            # Flush pending changes to the database
            session.flush()
            # Commit the transaction (this handles connection-level commit automatically)
            session.commit()
            
        except Exception as e:
            logger.error(f"Database session error in {database_name}: {e}")
            session.rollback()
            raise
            
        finally:
            # CRITICAL: Always close the session to return connection to pool
            session.close()
    
    def get_engine(self, database_name: str):
        """
        Get SQLAlchemy engine for specific database.
        
        Args:
            database_name: One of 'core', 'parsed', 'library', 'mapped'
            
        Returns:
            SQLAlchemy engine instance
        """
        if not self._is_initialized:
            raise RuntimeError("Database coordinator not initialized")
        
        if database_name not in self.engines:
            raise ValueError(f"Unknown database: {database_name}")
        
        return self.engines[database_name]
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check health status of all databases.
        
        Returns:
            Dictionary with health status for each database
        """
        health_status = {
            'coordinator_initialized': self._is_initialized,
            'databases': {}
        }
        
        for db_name in self.database_names:
            try:
                if db_name in self.engines:
                    with self.engines[db_name].connect() as connection:
                        result = connection.execute(text("SELECT 1"))
                        result.fetchone()
                        
                    health_status['databases'][db_name] = {
                        'status': 'healthy',
                        'engine_created': True,
                        'connectivity': 'ok'
                    }
                else:
                    health_status['databases'][db_name] = {
                        'status': 'error',
                        'engine_created': False,
                        'connectivity': 'unknown'
                    }
                    
            except Exception as e:
                health_status['databases'][db_name] = {
                    'status': 'error',
                    'engine_created': db_name in self.engines,
                    'connectivity': 'failed',
                    'error': str(e)
                }
        
        return health_status
    
    def get_connection_info(self) -> Dict[str, str]:
        """
        Get connection information for monitoring (without sensitive details).
        
        Returns:
            Dictionary with connection info for each database
        """
        connection_info = {}
        
        for db_name, url in self.connection_config.items():
            # Remove password from URL for logging/monitoring
            safe_url = url.split('@')[1] if '@' in url else url
            connection_info[db_name] = f"postgresql://***@{safe_url}"
        
        return connection_info
    
    def shutdown(self):
        """Clean shutdown of all database connections."""
        logger.info("Database coordinator shutting down")
        
        for db_name, engine in self.engines.items():
            try:
                engine.dispose()
                logger.info(f"Closed connections for {db_name}")
                
            except Exception as e:
                logger.error(f"Error closing connections for {db_name}: {e}")
        
        self.engines.clear()
        self.session_factories.clear()
        self._is_initialized = False
        
        logger.info("Database coordinator shutdown complete")


# Global database coordinator instance
db_coordinator = DatabaseCoordinator()


@contextmanager
def get_database_session(database_name: str):
    """
    Convenience function to get database session.
    
    Usage:
        with get_database_session('core') as session:
            entities = session.query(Entity).all()
    """
    with db_coordinator.get_session(database_name) as session:
        yield session


def get_database_engine(database_name: str):
    """
    Convenience function to get database engine.
    
    Usage:
        engine = get_database_engine('parsed')
    """
    return db_coordinator.get_engine(database_name)


def check_database_health() -> Dict[str, Any]:
    """
    Convenience function to check database health.
    
    Returns:
        Health status for all databases
    """
    return db_coordinator.check_health()