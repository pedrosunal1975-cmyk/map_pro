"""
Map Pro Migration Manager
=========================

Central coordinator for database schema migrations across Map Pro's four-database architecture.
Orchestrates migration execution without implementing specific migration logic.

Architecture: Core coordination only - delegates execution to specialized components.
"""

from pathlib import Path
from typing import Dict

from core.data_paths import map_pro_paths
from core.system_logger import get_logger
from sqlalchemy import text
from core.database_coordinator import db_coordinator
from .schema_initializer import SchemaInitializer
from .migration_executor import MigrationExecutor
from .schema_validator import SchemaValidator

logger = get_logger(__name__, 'core')


class MigrationManager:
    """
    Central coordinator for database migrations across all four Map Pro databases.
    
    Responsibilities:
    - Migration orchestration and coordination
    - Status tracking across databases
    - Integration with other core components
    - Migration workflow management
    
    Does NOT handle:
    - SQL generation (schema_initializer handles this)
    - Migration execution (migration_executor handles this)
    - Schema validation (schema_validator handles this)
    """
    
    def __init__(self):
        self.database_names = ['core', 'parsed', 'library', 'mapped']
        self.current_schema_version = 'v1.0.0'
        
        # Initialize specialized components
        self.schema_initializer = SchemaInitializer()
        self.migration_executor = MigrationExecutor()
        self.schema_validator = SchemaValidator()
        
        logger.info("Migration manager initialized")
    
    def get_current_version(self, db_name: str) -> str:
        """Get current schema version from database."""
        try:
            with db_coordinator.get_session(db_name) as session:
                result = session.execute(text("SELECT config_value FROM system_config WHERE config_key = 'schema_version'")).fetchone()
                return result[0] if result else 'v0.0.0'
        except Exception as e:
            logger.warning(f"Could not get version for {db_name}: {e}")
            return 'v0.0.0'
    
    def check_schema_exists(self, db_name: str) -> bool:
        """Check if basic schema exists in database."""
        return self.schema_validator.validate_schema_exists(db_name)
    
    def initialize_database(self, db_name: str) -> bool:
        """Initialize database with base schema."""
        logger.info(f"Initializing {db_name} database schema")
        
        try:
            # Get initialization SQL from schema initializer
            migration_sql = self.schema_initializer.get_init_sql(db_name)
            
            if not migration_sql:
                logger.error(f"No initialization SQL found for {db_name}")
                return False
            
            # Execute migration using migration executor
            success = self.migration_executor.execute_migration(
                db_name, migration_sql, self.current_schema_version
            )
            
            if success:
                logger.info(f"Successfully initialized {db_name} database")
            else:
                logger.error(f"Failed to initialize {db_name} database")
            
            return success
            
        except Exception as e:
            logger.error(f"Database initialization error for {db_name}: {e}")
            return False
    
    def migrate_all_databases(self) -> Dict[str, bool]:
        """Initialize all databases to current schema version."""
        results = {}
        
        for db_name in self.database_names:
            try:
                if not self.check_schema_exists(db_name):
                    logger.info(f"Database {db_name} needs initialization")
                    results[db_name] = self.initialize_database(db_name)
                else:
                    logger.info(f"Database {db_name} already initialized")
                    results[db_name] = True
                    
            except Exception as e:
                logger.error(f"Error processing {db_name}: {e}")
                results[db_name] = False
        
        return results
    
    def get_migration_status(self) -> Dict[str, Dict[str, str]]:
        """Get migration status for all databases."""
        status = {}
        
        for db_name in self.database_names:
            try:
                schema_exists = self.check_schema_exists(db_name)
                current_version = self.get_current_version(db_name) if schema_exists else 'none'
                
                status[db_name] = {
                    'schema_exists': schema_exists,
                    'current_version': current_version,
                    'target_version': self.current_schema_version,
                    'needs_migration': current_version != self.current_schema_version
                }
                
            except Exception as e:
                status[db_name] = {
                    'error': str(e),
                    'schema_exists': False,
                    'current_version': 'unknown'
                }
        
        return status
    
    def validate_all_schemas(self) -> Dict[str, Dict[str, any]]:
        """Validate schema integrity across all databases."""
        validation_results = {}
        
        for db_name in self.database_names:
            validation_results[db_name] = self.schema_validator.validate_database_schema(db_name)
        
        return validation_results


# Global migration manager instance
migration_manager = MigrationManager()


def initialize_all_databases() -> bool:
    """Convenience function to initialize all databases."""
    results = migration_manager.migrate_all_databases()
    success_count = sum(1 for success in results.values() if success)
    
    logger.info(f"Database initialization: {success_count}/{len(results)} successful")
    return all(results.values())


def get_database_status() -> Dict[str, any]:
    """Convenience function to get database status."""
    return migration_manager.get_migration_status()


def validate_database_schemas() -> Dict[str, any]:
    """Convenience function to validate all database schemas."""
    return migration_manager.validate_all_schemas()