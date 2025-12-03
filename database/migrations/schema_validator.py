"""
Map Pro Schema Validator
========================

Validates database schema integrity across Map Pro's four-database PostgreSQL architecture.
Ensures schemas are correctly created and maintained without executing migrations.

Architecture: Specialized component focused on schema validation and integrity checking.
"""

from typing import Dict, List, Any, Optional
from core.system_logger import get_logger
from sqlalchemy import text
from core.database_coordinator import db_coordinator

logger = get_logger(__name__, 'core')


class SchemaValidator:
    """
    Validates database schemas for Map Pro's four-database architecture.
    
    Responsibilities:
    - Schema existence validation
    - Table structure verification
    - Index and constraint validation
    - Cross-database reference integrity
    
    Does NOT handle:
    - Schema creation (schema_initializer handles this)
    - Migration execution (migration_executor handles this)
    - Migration coordination (migration_manager handles this)
    """
    
    def __init__(self):
        self.database_schemas = {
            'core': self._get_core_schema_definition(),
            'parsed': self._get_parsed_schema_definition(),
            'library': self._get_library_schema_definition(),
            'mapped': self._get_mapped_schema_definition()
        }
        logger.info("Schema validator initialized")
    
    def validate_schema_exists(self, db_name: str) -> bool:
        """Check if basic schema exists in database."""
        try:
            with db_coordinator.get_session(db_name) as session:
                # Check for system_config table existence (present in all databases)
                result = session.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'system_config')")).fetchone()
                
                if not result or not result[0]:
                    return False
                
                # Try to query the table to ensure it's accessible
                session.execute(text("SELECT 1 FROM system_config LIMIT 1"))
                return True
                
        except Exception as e:
            logger.debug(f"Schema check failed for {db_name}: {e}")
            return False
    
    def validate_database_schema(self, db_name: str) -> Dict[str, Any]:
        """Comprehensive schema validation for specific database."""
        logger.info(f"Validating schema for {db_name} database")
        
        validation_result = {
            'database_name': db_name,
            'schema_exists': False,
            'all_tables_exist': False,
            'missing_tables': [],
            'table_structure_valid': False,
            'invalid_tables': [],
            'indexes_valid': False,
            'missing_indexes': [],
            'constraints_valid': False,
            'missing_constraints': [],
            'overall_valid': False
        }
        
        try:
            # Check if schema exists at all
            validation_result['schema_exists'] = self.validate_schema_exists(db_name)
            
            if not validation_result['schema_exists']:
                return validation_result
            
            # Validate table existence
            table_validation = self._validate_tables_exist(db_name)
            validation_result.update(table_validation)
            
            # Validate table structures
            if validation_result['all_tables_exist']:
                structure_validation = self._validate_table_structures(db_name)
                validation_result.update(structure_validation)
            
            # Validate indexes
            index_validation = self._validate_indexes(db_name)
            validation_result.update(index_validation)
            
            # Validate constraints
            constraint_validation = self._validate_constraints(db_name)
            validation_result.update(constraint_validation)
            
            # Overall validation
            validation_result['overall_valid'] = (
                validation_result['schema_exists'] and
                validation_result['all_tables_exist'] and
                validation_result['table_structure_valid'] and
                validation_result['indexes_valid'] and
                validation_result['constraints_valid']
            )
            
        except Exception as e:
            logger.error(f"Schema validation error for {db_name}: {e}")
            validation_result['error'] = str(e)
        
        return validation_result
    
    def _validate_tables_exist(self, db_name: str) -> Dict[str, Any]:
        """Validate that all required tables exist."""
        expected_tables = self.database_schemas[db_name]['tables']
        missing_tables = []
        
        try:
            with db_coordinator.get_session(db_name) as session:
                for table_name in expected_tables:
                    result = session.execute(text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = :table_name)"
                    ), {"table_name": table_name}).fetchone()
                    
                    if not result or not result[0]:
                        missing_tables.append(table_name)
            
            return {
                'all_tables_exist': len(missing_tables) == 0,
                'missing_tables': missing_tables
            }
            
        except Exception as e:
            logger.error(f"Table validation error for {db_name}: {e}")
            return {
                'all_tables_exist': False,
                'missing_tables': expected_tables,
                'table_validation_error': str(e)
            }
    
    def _validate_table_structures(self, db_name: str) -> Dict[str, Any]:
        """Validate table column structures match expected schema."""
        expected_schema = self.database_schemas[db_name]
        invalid_tables = []
        
        try:
            with db_coordinator.get_session(db_name) as session:
                for table_name, expected_columns in expected_schema['table_columns'].items():
                    # Get actual columns from database
                    actual_columns = session.execute(text(
                        "SELECT column_name, data_type, is_nullable "
                        "FROM information_schema.columns "
                        "WHERE table_name = :table_name "
                        "ORDER BY ordinal_position"
                    ), {"table_name": table_name}).fetchall()
                    
                    actual_column_names = {row[0] for row in actual_columns}
                    expected_column_names = set(expected_columns.keys())
                    
                    # Check for missing or extra columns
                    if actual_column_names != expected_column_names:
                        invalid_tables.append({
                            'table': table_name,
                            'missing_columns': expected_column_names - actual_column_names,
                            'extra_columns': actual_column_names - expected_column_names
                        })
            
            return {
                'table_structure_valid': len(invalid_tables) == 0,
                'invalid_tables': invalid_tables
            }
            
        except Exception as e:
            logger.error(f"Table structure validation error for {db_name}: {e}")
            return {
                'table_structure_valid': False,
                'structure_validation_error': str(e)
            }
    
    def _validate_indexes(self, db_name: str) -> Dict[str, Any]:
        """Validate that required indexes exist."""
        expected_indexes = self.database_schemas[db_name]['indexes']
        missing_indexes = []
        
        try:
            with db_coordinator.get_session(db_name) as session:
                # Get all existing indexes
                existing_indexes = session.execute(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                ).fetchall()
                
                existing_index_names = {row[0] for row in existing_indexes}
                
                for expected_index in expected_indexes:
                    if expected_index not in existing_index_names:
                        missing_indexes.append(expected_index)
            
            return {
                'indexes_valid': len(missing_indexes) == 0,
                'missing_indexes': missing_indexes
            }
            
        except Exception as e:
            logger.error(f"Index validation error for {db_name}: {e}")
            return {
                'indexes_valid': False,
                'index_validation_error': str(e)
            }
    
    def _validate_constraints(self, db_name: str) -> Dict[str, Any]:
        """Validate that required constraints exist."""
        expected_constraints = self.database_schemas[db_name]['constraints']
        missing_constraints = []
        
        try:
            with db_coordinator.get_session(db_name) as session:
                # Get all existing constraints
                existing_constraints = session.execute(
                    "SELECT constraint_name FROM information_schema.table_constraints "
                    "WHERE constraint_schema = 'public'"
                ).fetchall()
                
                existing_constraint_names = {row[0] for row in existing_constraints}
                
                for expected_constraint in expected_constraints:
                    if expected_constraint not in existing_constraint_names:
                        missing_constraints.append(expected_constraint)
            
            return {
                'constraints_valid': len(missing_constraints) == 0,
                'missing_constraints': missing_constraints
            }
            
        except Exception as e:
            logger.error(f"Constraint validation error for {db_name}: {e}")
            return {
                'constraints_valid': False,
                'constraint_validation_error': str(e)
            }
    
    def _get_core_schema_definition(self) -> Dict[str, Any]:
        """Get expected schema definition for core database."""
        return {
            'tables': [
                'system_config', 'markets', 'entities', 'filings', 
                'documents', 'processing_jobs'
            ],
            'table_columns': {
                'system_config': {
                    'config_id': 'uuid',
                    'config_key': 'character varying',
                    'config_value': 'text',
                    'config_type': 'character varying',
                    'module_owner': 'character varying',
                    'created_at': 'timestamp with time zone',
                    'updated_at': 'timestamp with time zone'
                },
                'markets': {
                    'market_id': 'character varying',
                    'market_name': 'character varying',
                    'market_country': 'character varying',
                    'api_base_url': 'text',
                    'is_active': 'boolean',
                    'rate_limit_per_minute': 'integer',
                    'user_agent_required': 'boolean',
                    'created_at': 'timestamp with time zone',
                    'updated_at': 'timestamp with time zone'
                },
                'entities': {
                    'entity_universal_id': 'uuid',
                    'market_type': 'character varying',
                    'market_entity_id': 'character varying',
                    'primary_name': 'character varying',
                    'ticker_symbol': 'character varying',
                    'entity_status': 'character varying',
                    'data_directory_path': 'text',
                    'last_filing_date': 'date',
                    'total_filings_count': 'integer',
                    'identifiers': 'jsonb',
                    'search_history': 'jsonb',
                    'created_at': 'timestamp with time zone',
                    'updated_at': 'timestamp with time zone'
                }
            },
            'indexes': [
                'idx_entities_market_type',
                'idx_entities_status',
                'idx_filings_entity',
                'idx_filings_date',
                'idx_documents_filing',
                'idx_jobs_status_priority'
            ],
            'constraints': [
                'entities_market_entity_unique',
                'entities_filing_count_positive'
            ]
        }
    
    def _get_parsed_schema_definition(self) -> Dict[str, Any]:
        """Get expected schema definition for parsed database."""
        return {
            'tables': ['system_config', 'parsing_sessions', 'parsed_documents'],
            'table_columns': {
                'parsing_sessions': {
                    'session_id': 'uuid',
                    'session_name': 'character varying',
                    'session_type': 'character varying',
                    'market_type': 'character varying'
                }
            },
            'indexes': ['idx_parsed_docs_entity', 'idx_parsed_docs_session'],
            'constraints': []
        }
    
    def _get_library_schema_definition(self) -> Dict[str, Any]:
        """Get expected schema definition for library database."""
        return {
            'tables': ['system_config', 'taxonomy_libraries', 'taxonomy_concepts'],
            'table_columns': {
                'taxonomy_libraries': {
                    'library_id': 'uuid',
                    'taxonomy_name': 'character varying',
                    'taxonomy_version': 'character varying'
                }
            },
            'indexes': ['idx_concepts_qname', 'idx_concepts_library'],
            'constraints': ['taxonomy_name_version_unique']
        }
    
    def _get_mapped_schema_definition(self) -> Dict[str, Any]:
        """Get expected schema definition for mapped database."""
        return {
            'tables': ['system_config', 'mapping_sessions', 'mapped_statements'],
            'table_columns': {
                'mapped_statements': {
                    'statement_id': 'uuid',
                    'entity_universal_id': 'uuid',
                    'statement_type': 'character varying'
                }
            },
            'indexes': ['idx_mapped_statements_entity', 'idx_mapped_statements_period'],
            'constraints': []
        }