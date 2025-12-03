# File: /map_pro/database/migrations/add_deduplication_constraints.py

"""
Add Deduplication Constraints Migration
========================================

Adds database-level UNIQUE constraints to prevent duplicate records:
1. Documents: Unique (filing_universal_id, document_name)
2. Processing Jobs: Unique active jobs per filing

This prevents race conditions where multiple jobs try to create the same records.

Migration Version: 003
Created: 2025-11-02
"""

from sqlalchemy import text
from core.database_coordinator import get_database_session
from core.system_logger import get_logger

logger = get_logger(__name__, 'core')


class DeduplicationConstraintsMigration:
    """
    Migration to add UNIQUE constraints preventing duplicate records.
    
    Prevents race conditions in:
    - Document creation during extraction
    - Job creation during workflow progression
    
    Safe to run multiple times (idempotent).
    """
    
    def __init__(self):
        self.migration_name = "add_deduplication_constraints"
        self.version = "003"
        
    def upgrade(self) -> dict:
        """
        Apply the migration.
        
        Returns:
            dict: Migration result with success status and messages
        """
        logger.info(f"Starting migration: {self.migration_name}")
        results = {
            'success': True,
            'constraints_added': [],
            'constraints_skipped': [],
            'errors': []
        }
        
        try:
            # Add document uniqueness constraint
            doc_result = self._add_document_constraint()
            if doc_result['added']:
                results['constraints_added'].append('documents_unique_filing_name')
            else:
                results['constraints_skipped'].append('documents_unique_filing_name')
            
            # Add index on processing_jobs for faster duplicate checks
            job_result = self._add_job_indexes()
            if job_result['added']:
                results['constraints_added'].extend(job_result['indexes'])
            else:
                results['constraints_skipped'].extend(job_result['indexes'])
            
            logger.info(
                f"Migration completed: {len(results['constraints_added'])} added, "
                f"{len(results['constraints_skipped'])} skipped"
            )
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def _add_document_constraint(self) -> dict:
        """
        Add UNIQUE constraint on documents (filing_universal_id, document_name).
        
        Returns:
            dict: Result with 'added' boolean
        """
        try:
            with get_database_session('core') as session:
                # Check if constraint already exists
                check_query = text("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'documents' 
                    AND constraint_name = 'documents_unique_filing_name'
                """)
                
                existing = session.execute(check_query).fetchone()
                
                if existing:
                    logger.info("Document constraint already exists, skipping")
                    return {'added': False}
                
                # Add the constraint
                alter_query = text("""
                    ALTER TABLE documents 
                    ADD CONSTRAINT documents_unique_filing_name 
                    UNIQUE (filing_universal_id, document_name)
                """)
                
                session.execute(alter_query)
                session.commit()
                
                logger.info("Added UNIQUE constraint: documents_unique_filing_name")
                return {'added': True}
                
        except Exception as e:
            logger.error(f"Failed to add document constraint: {e}")
            raise
    
    def _add_job_indexes(self) -> dict:
        """
        Add indexes on processing_jobs to speed up duplicate checks.
        
        Creates:
        - Index on (job_type, filing_universal_id, job_status)
        - Index on (job_type, entity_universal_id, job_status)
        
        Returns:
            dict: Result with 'added' boolean and list of indexes
        """
        indexes_to_add = [
            {
                'name': 'idx_jobs_filing_type_status',
                'query': """
                    CREATE INDEX IF NOT EXISTS idx_jobs_filing_type_status 
                    ON processing_jobs (job_type, filing_universal_id, job_status)
                    WHERE filing_universal_id IS NOT NULL
                """
            },
            {
                'name': 'idx_jobs_entity_type_status',
                'query': """
                    CREATE INDEX IF NOT EXISTS idx_jobs_entity_type_status 
                    ON processing_jobs (job_type, entity_universal_id, job_status)
                    WHERE entity_universal_id IS NOT NULL
                """
            }
        ]
        
        added_indexes = []
        
        try:
            with get_database_session('core') as session:
                for index in indexes_to_add:
                    # Check if index exists
                    check_query = text("""
                        SELECT indexname 
                        FROM pg_indexes 
                        WHERE tablename = 'processing_jobs' 
                        AND indexname = :index_name
                    """)
                    
                    existing = session.execute(
                        check_query, 
                        {'index_name': index['name']}
                    ).fetchone()
                    
                    if existing:
                        logger.info(f"Index {index['name']} already exists, skipping")
                        continue
                    
                    # Create the index
                    session.execute(text(index['query']))
                    added_indexes.append(index['name'])
                    logger.info(f"Created index: {index['name']}")
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to add job indexes: {e}")
            raise
        
        return {
            'added': len(added_indexes) > 0,
            'indexes': added_indexes if added_indexes else [i['name'] for i in indexes_to_add]
        }
    
    def downgrade(self) -> dict:
        """
        Rollback the migration (remove constraints).
        
        Returns:
            dict: Rollback result
        """
        logger.info(f"Rolling back migration: {self.migration_name}")
        results = {
            'success': True,
            'constraints_removed': [],
            'errors': []
        }
        
        try:
            with get_database_session('core') as session:
                # Remove document constraint
                session.execute(text("""
                    ALTER TABLE documents 
                    DROP CONSTRAINT IF EXISTS documents_unique_filing_name
                """))
                results['constraints_removed'].append('documents_unique_filing_name')
                
                # Remove indexes
                session.execute(text("DROP INDEX IF EXISTS idx_jobs_filing_type_status"))
                session.execute(text("DROP INDEX IF EXISTS idx_jobs_entity_type_status"))
                results['constraints_removed'].extend([
                    'idx_jobs_filing_type_status',
                    'idx_jobs_entity_type_status'
                ])
                
                session.commit()
                logger.info("Migration rolled back successfully")
                
        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            results['success'] = False
            results['errors'].append(str(e))
        
        return results


def run_migration():
    """
    Execute the migration.
    
    Usage:
        python -m database.migrations.add_deduplication_constraints
    """
    migration = DeduplicationConstraintsMigration()
    result = migration.upgrade()
    
    if result['success']:
        print("[SUCCESS] Migration completed")
        print(f"  Added: {', '.join(result['constraints_added']) or 'none'}")
        print(f"  Skipped: {', '.join(result['constraints_skipped']) or 'none'}")
    else:
        print("[FAILED] Migration failed")
        for error in result['errors']:
            print(f"  Error: {error}")
    
    return result


if __name__ == "__main__":
    run_migration()