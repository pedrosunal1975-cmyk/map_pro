"""
Database Schema Verification and Diagnostic Tools
==================================================

Location: tools/cli/db_check.py

This module provides utilities for verifying database integrity, checking foreign key
constraints, diagnosing job data issues, and fixing orphaned records in the MapPro system.

The tools are market-agnostic and work across all supported markets (SEC, FCA, ESMA).

REFACTORED: Split into focused, testable components.
"""

import sys
from pathlib import Path

# Find the map_pro root directory by looking for main.py
current_dir = Path(__file__).parent
while current_dir != current_dir.parent:
    if (current_dir / 'main.py').exists():
        map_pro_root = current_dir
        break
    current_dir = current_dir.parent
else:
    raise RuntimeError("Could not find map_pro root directory (looking for main.py)")

sys.path.insert(0, str(map_pro_root))

from .db_check_constants import DiagnosticChoice, DiagnosticMessages
from .db_check_user_interface import UserInterface
from .constraint_check_operation import ConstraintCheckOperation
from .job_debug_operation import JobDebugOperation
from .orphaned_job_fix_operation import OrphanedJobFixOperation


class DiagnosticOrchestrator:
    """
    Orchestrates diagnostic operations based on user choice.
    
    Responsibilities:
    - Coordinating different diagnostic operations
    - Managing execution flow
    - Handling user interactions
    """
    
    def __init__(self):
        """Initialize the diagnostic orchestrator."""
        self.ui = UserInterface()
    
    def run(self) -> None:
        """Main entry point for database diagnostic tools."""
        choice = self.ui.get_user_choice()
        
        if not choice:
            return
        
        # Execute chosen operations
        if choice in (DiagnosticChoice.CHECK_CONSTRAINTS, DiagnosticChoice.BOTH):
            ConstraintCheckOperation.execute()
        
        if choice in (DiagnosticChoice.DEBUG_JOB_STRUCTURE, DiagnosticChoice.BOTH):
            JobDebugOperation.execute()
        
        # Offer to fix orphaned jobs
        if choice in (DiagnosticChoice.CHECK_CONSTRAINTS, DiagnosticChoice.BOTH):
            if self.ui.confirm_action(DiagnosticMessages.CONFIRM_REMOVE_ORPHANED):
                OrphanedJobFixOperation.execute()
                print(DiagnosticMessages.RESULT_DONE)


def main() -> None:
    """Main entry point for the diagnostic tool."""
    orchestrator = DiagnosticOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()