"""
Database Schema Verification - User Interface
==============================================

Location: tools/cli/db_check_user_interface.py

Handles user interaction for diagnostic operations.
"""

from typing import Optional

from .db_check_constants import DiagnosticChoice, DiagnosticMessages


class UserInterface:
    """Handles user interaction for diagnostic operations."""
    
    @staticmethod
    def get_user_choice() -> Optional[DiagnosticChoice]:
        """
        Get user's choice for diagnostic operation.
        
        Returns:
            DiagnosticChoice enum or None if invalid
        """
        print(DiagnosticMessages.MENU_TITLE)
        print(DiagnosticMessages.MENU_OPTION_1)
        print(DiagnosticMessages.MENU_OPTION_2)
        print(DiagnosticMessages.MENU_OPTION_3)
        
        choice = input(DiagnosticMessages.MENU_PROMPT).strip()
        
        try:
            return DiagnosticChoice(choice)
        except ValueError:
            print(DiagnosticMessages.ERROR_INVALID_CHOICE.format(choice))
            return None
    
    @staticmethod
    def confirm_action(prompt: str) -> bool:
        """
        Get user confirmation for an action.
        
        Args:
            prompt: Confirmation prompt to display
            
        Returns:
            True if user confirms, False otherwise
        """
        response = input(f"\n{prompt}{DiagnosticMessages.CONFIRM_YES_NO}").strip().lower()
        return response == 'y'