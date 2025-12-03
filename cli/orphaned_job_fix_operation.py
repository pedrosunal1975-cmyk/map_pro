"""
Database Schema Verification - Orphaned Job Fix Operation
==========================================================

Location: tools/cli/orphaned_job_fix_operation.py

Orchestrates the orphaned job fixing operation.
"""

import traceback
from core.database_coordinator import db_coordinator

from .db_check_constants import DiagnosticConstants, DiagnosticMessages
from .database_initializer import DatabaseInitializer
from .orphaned_job_fixer import OrphanedJobFixer


class OrphanedJobFixOperation:
    """Orchestrates orphaned job fixing."""
    
    @staticmethod
    def execute() -> None:
        """Remove orphaned jobs that reference non-existent entities."""
        print(DiagnosticMessages.HEADER_REMOVING_ORPHANED)
        
        if not DatabaseInitializer.ensure_initialized():
            return
        
        try:
            with db_coordinator.get_session(DiagnosticConstants.CORE_DATABASE) as session:
                fixer = OrphanedJobFixer(session)
                removed_count = fixer.remove_orphaned_jobs()
                print(DiagnosticMessages.RESULT_REMOVED_COUNT.format(removed_count))
                
        except Exception as e:
            print(DiagnosticMessages.ERROR_FIX_ORPHANED.format(e))
            traceback.print_exc()