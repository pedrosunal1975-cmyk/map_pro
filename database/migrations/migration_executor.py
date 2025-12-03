"""
Map Pro Migration Executor
==========================

Handles database migration execution with transaction safety and rollback capability.
Provides low-level migration execution without coordination logic.

Architecture: Specialized component focused on safe SQL execution.
"""

from core.system_logger import get_logger
from sqlalchemy import text
from core.database_coordinator import db_coordinator

logger = get_logger(__name__, 'core')


class MigrationExecutor:
    """
    Executes database migrations with transaction safety.
    
    Responsibilities:
    - Safe SQL execution with rollback capability
    - Transaction management for migrations
    - Error handling and recovery
    - Version tracking updates
    
    Does NOT handle:
    - SQL generation (schema_initializer handles this)
    - Migration coordination (migration_manager handles this)
    - Schema validation (schema_validator handles this)
    """
    
    def __init__(self):
        logger.info("Migration executor initialized")
    
    def execute_migration(self, db_name: str, migration_sql: str, target_version: str) -> bool:
        """
        Execute migration SQL with transaction safety.
        
        Args:
            db_name: Database name to migrate
            migration_sql: SQL to execute
            target_version: Version to set after successful migration
            
        Returns:
            True if migration successful, False otherwise
        """
        logger.info(f"Executing migration for {db_name} to version {target_version}")
        
        try:
            # Ensure db_coordinator is initialized
            if not db_coordinator._is_initialized:
                db_coordinator.initialize()
            
            with db_coordinator.get_session(db_name) as session:
                session.execute(text("BEGIN"))
                try:
                    # Execute the migration SQL
                    self._execute_sql_statements(session, migration_sql)
                    
                    # Update schema version
                    self._update_schema_version(session, target_version)
                    
                    session.execute(text("COMMIT"))
                    logger.info(f"Successfully migrated {db_name} to {target_version}")
                    return True
                    
                except Exception as e:
                    session.execute(text("ROLLBACK"))
                    logger.error(f"Migration failed for {db_name}, rolled back: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Migration execution error for {db_name}: {e}")
            return False
    
    def _execute_sql_statements(self, session, migration_sql: str):
        """Execute SQL statements from migration."""
        # Split SQL into individual statements and execute
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                logger.debug(f"Executing SQL: {statement[:100]}...")
                session.execute(text(statement))
    
    def _update_schema_version(self, session, target_version: str):
        """Update schema version in system_config table."""
        # Check if version record exists
        result = session.execute(text("SELECT config_id FROM system_config WHERE config_key = 'schema_version'")).fetchone()
        
        if result:
            # Update existing version
            session.execute(text("UPDATE system_config SET config_value = :version WHERE config_key = 'schema_version'"), {"version": target_version})
        else:
            # Insert new version record
            session.execute(text("INSERT INTO system_config (config_key, config_value, module_owner) VALUES ('schema_version', :version, 'migration_manager')"), {"version": target_version})
    
    def rollback_migration(self, db_name: str, rollback_sql: str, previous_version: str) -> bool:
        """
        Execute rollback migration with transaction safety.
        
        Args:
            db_name: Database name to rollback
            rollback_sql: SQL to execute for rollback
            previous_version: Version to revert to
            
        Returns:
            True if rollback successful, False otherwise
        """
        logger.warning(f"Rolling back {db_name} to version {previous_version}")
        
        try:
            # Ensure db_coordinator is initialized
            if not db_coordinator._is_initialized:
                db_coordinator.initialize()
            
            with db_coordinator.get_session(db_name) as session:
                session.execute(text("BEGIN"))
                try:
                    # Execute rollback SQL
                    self._execute_sql_statements(session, rollback_sql)
                    
                    # Update version to previous
                    self._update_schema_version(session, previous_version)
                    
                    session.execute(text("COMMIT"))
                    logger.info(f"Successfully rolled back {db_name} to {previous_version}")
                    return True
                    
                except Exception as e:
                    session.execute(text("ROLLBACK"))
                    logger.error(f"Rollback failed for {db_name}: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Rollback execution error for {db_name}: {e}")
            return False