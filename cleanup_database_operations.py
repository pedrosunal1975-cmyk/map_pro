# File: /map_pro/tools/cleanup_database_operations.py

"""
Cleanup Database Operations
============================

Handles all database-related cleanup operations including orphaned
record removal, duplicate cleanup, and database optimization.

Responsibilities:
- Remove orphaned database records
- Clean duplicate mapped statements
- Vacuum and analyze databases
- Handle database-specific errors

Related Files:
- cleanup_orchestrator.py: Main orchestration
- database_cleanup.py: Entry point
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from core.database_coordinator import db_coordinator
from database.models.core_models import Document, Filing, ProcessingJob
from database.models.mapped_models import MappedStatement, MappedFact
from sqlalchemy import func


class DatabaseList:
    """List of databases for operations."""
    ALL_DATABASES = ['core', 'parsed', 'library', 'mapped']


class CleanupDatabaseOperations:
    """
    Handles database-related cleanup operations.
    
    This class provides methods for cleaning orphaned records, duplicates,
    and optimizing databases.
    """
    
    def __init__(self, logger, dry_run: bool = False):
        """
        Initialize database cleanup operations.
        
        Args:
            logger: Logger instance for operation logging
            dry_run: If True, preview changes without applying them
        """
        self.logger = logger
        self.dry_run = dry_run
    
    def cleanup_orphaned_records(self) -> Dict[str, Any]:
        """
        Remove orphaned database records.
        
        Identifies and removes:
        - Documents without parent filings
        - Jobs without parent filings
        
        Returns:
            Dictionary with cleanup results containing:
                - orphaned_removed (int): Number of orphaned records removed
                - summary (str): Summary of operation
                - errors (list): List of error messages if any
        """
        result = {
            'orphaned_removed': 0,
            'summary': '',
            'errors': []
        }
        
        try:
            with db_coordinator.get_session('core') as session:
                # Find orphaned documents (documents without filings)
                orphaned_docs = session.query(Document).filter(
                    ~Document.filing_universal_id.in_(
                        session.query(Filing.filing_universal_id)
                    )
                ).all()
                
                # Find orphaned jobs (jobs without filings)
                orphaned_jobs = session.query(ProcessingJob).filter(
                    ProcessingJob.filing_universal_id.isnot(None),
                    ~ProcessingJob.filing_universal_id.in_(
                        session.query(Filing.filing_universal_id)
                    )
                ).all()
                
                # Remove orphaned records if not dry run
                if not self.dry_run:
                    for doc in orphaned_docs:
                        session.delete(doc)
                    for job in orphaned_jobs:
                        session.delete(job)
                    session.commit()
                
                total_orphaned = len(orphaned_docs) + len(orphaned_jobs)
                result['orphaned_removed'] = total_orphaned
                result['summary'] = f"Removed {total_orphaned} orphaned records"
                
                self.logger.info(
                    f"Orphaned cleanup: {len(orphaned_docs)} docs, "
                    f"{len(orphaned_jobs)} jobs"
                )
                
        except Exception as exception:
            error_msg = f"Orphaned cleanup failed: {exception}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def cleanup_parsed_mapped_databases(self, days_old: int = 0) -> Dict[str, Any]:
        """
        Clean parsed and mapped databases of duplicate/orphaned records.
        
        Removes duplicate mapped statements, keeping only the most recent version
        for each filing/statement type combination.
        
        Args:
            days_old: If > 0, only clean statements older than this many days
            
        Returns:
            Dictionary with cleanup results containing:
                - mapped_statements_removed (int): Number of statements removed
                - mapped_facts_removed (int): Number of facts removed
                - summary (str): Summary of operation
                - errors (list): List of error messages if any
        """
        result = {
            'mapped_statements_removed': 0,
            'mapped_facts_removed': 0,
            'summary': '',
            'errors': []
        }
        
        try:
            cutoff_date = None
            if days_old > 0:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            with db_coordinator.get_session('mapped') as session:
                if cutoff_date:
                    # Clean statements older than cutoff date
                    statements = session.query(MappedStatement).filter(
                        MappedStatement.mapped_at < cutoff_date
                    ).all()
                else:
                    # Find duplicate statements (keep only latest)
                    statements = self._find_duplicate_statements(session)
                
                # Remove statements and their facts if not dry run
                if not self.dry_run and statements:
                    for stmt in statements:
                        # Delete associated facts first
                        facts = session.query(MappedFact).filter_by(
                            statement_id=stmt.statement_id
                        ).all()
                        for fact in facts:
                            session.delete(fact)
                            result['mapped_facts_removed'] += 1
                    
                    # Delete statements
                    for stmt in statements:
                        session.delete(stmt)
                        result['mapped_statements_removed'] += 1
                    
                    session.commit()
                else:
                    result['mapped_statements_removed'] = len(statements)
            
            result['summary'] = (
                f"Cleaned {result['mapped_statements_removed']} duplicate statements"
            )
            
            self.logger.info(result['summary'])
            
        except Exception as exception:
            error_msg = f"Parsed/mapped cleanup failed: {exception}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def _find_duplicate_statements(self, session) -> list:
        """
        Find duplicate mapped statements, excluding the most recent version.
        
        Args:
            session: Database session
            
        Returns:
            List of duplicate MappedStatement objects to remove
        """
        # Find latest statement for each filing/statement_type combination
        subquery = session.query(
            MappedStatement.filing_universal_id,
            MappedStatement.statement_type,
            func.max(MappedStatement.mapped_at).label('latest_date')
        ).group_by(
            MappedStatement.filing_universal_id,
            MappedStatement.statement_type
        ).subquery()
        
        # Find all statements that are not the latest
        duplicates = session.query(MappedStatement).filter(
            ~session.query(MappedStatement.statement_id).filter(
                MappedStatement.filing_universal_id == subquery.c.filing_universal_id,
                MappedStatement.statement_type == subquery.c.statement_type,
                MappedStatement.mapped_at == subquery.c.latest_date
            ).exists()
        ).all()
        
        return duplicates
    
    def vacuum_databases(self) -> Dict[str, Any]:
        """
        Vacuum and analyze all databases for optimization.
        
        Runs VACUUM ANALYZE on each database to reclaim space and
        update statistics for the query planner.
        
        Returns:
            Dictionary with vacuum results containing:
                - databases_optimized (int): Number of databases optimized
                - summary (str): Summary of operation
                - errors (list): List of error messages if any
        """
        result = {
            'databases_optimized': 0,
            'summary': '',
            'errors': []
        }
        
        for db_name in DatabaseList.ALL_DATABASES:
            try:
                if not self.dry_run:
                    engine = db_coordinator.get_engine(db_name)
                    raw_connection = engine.raw_connection()
                    try:
                        raw_connection.autocommit = True
                        cursor = raw_connection.cursor()
                        cursor.execute("VACUUM ANALYZE")
                        cursor.close()
                    finally:
                        raw_connection.close()
                
                result['databases_optimized'] += 1
                self.logger.info(f"Vacuumed database: {db_name}")
                
            except Exception as exception:
                # VACUUM failures are non-critical - log as warning
                warning_msg = f"VACUUM failed for {db_name} (non-critical): {exception}"
                self.logger.warning(warning_msg)
                result['errors'].append(warning_msg)
        
        result['summary'] = f"Optimized {result['databases_optimized']} databases"
        
        return result


__all__ = ['CleanupDatabaseOperations', 'DatabaseList']