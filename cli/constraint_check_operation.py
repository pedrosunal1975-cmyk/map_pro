"""
Database Schema Verification - Constraint Check Operation
==========================================================

Location: tools/cli/constraint_check_operation.py

Orchestrates the foreign key constraint checking operation.
"""

import traceback
from core.database_coordinator import db_coordinator

from .db_check_constants import DiagnosticConstants, DiagnosticMessages
from .database_initializer import DatabaseInitializer
from .foreign_key_checker import ForeignKeyChecker
from .orphaned_job_detector import OrphanedJobDetector


class ConstraintCheckOperation:
    """Orchestrates foreign key constraint checking."""
    
    @staticmethod
    def execute() -> None:
        """Check if processing_jobs foreign key constraints are properly set up."""
        print(DiagnosticMessages.HEADER_CHECKING_CONSTRAINTS)
        
        if not DatabaseInitializer.ensure_initialized():
            return
        
        try:
            with db_coordinator.get_session(DiagnosticConstants.CORE_DATABASE) as session:
                checker = ForeignKeyChecker(session)
                
                # Get and print table structure
                structure = checker.get_table_structure()
                checker.print_table_structure(structure)
                
                # Get and print foreign keys
                foreign_keys = checker.get_foreign_key_constraints()
                checker.print_foreign_keys(foreign_keys)
                
                # Get and print entity count
                entity_count = checker.get_entity_count()
                print(DiagnosticMessages.RESULT_ENTITIES_COUNT.format(entity_count))
                
                # Check for orphaned jobs
                detector = OrphanedJobDetector(session)
                orphaned_count = detector.count_orphaned_jobs()
                
                if orphaned_count > 0:
                    orphaned_details = detector.get_orphaned_job_details()
                    detector.print_orphaned_job_summary(orphaned_count, orphaned_details)
                else:
                    print(DiagnosticMessages.RESULT_ORPHANED_COUNT.format(0))
                
        except Exception as e:
            print(DiagnosticMessages.ERROR_DB_CHECK.format(e))
            traceback.print_exc()