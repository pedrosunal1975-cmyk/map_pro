"""
Database Schema Verification - Database Initializer
====================================================

Location: tools/cli/database_initializer.py

Handles database coordinator initialization for diagnostic tools.
"""

from core.database_coordinator import db_coordinator
from .db_check_constants import DiagnosticMessages


class DatabaseInitializer:
    """Handles database coordinator initialization."""
    
    @staticmethod
    def ensure_initialized() -> bool:
        """
        Ensure database coordinator is initialized.
        
        Returns:
            True if initialized successfully, False otherwise
        """
        if not db_coordinator._is_initialized:
            success = db_coordinator.initialize()
            if not success:
                print(DiagnosticMessages.ERROR_INIT_FAILED)
                return False
        return True
