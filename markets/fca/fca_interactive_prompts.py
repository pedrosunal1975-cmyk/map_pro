"""
FCA Interactive Prompts
=======================

FCA-specific interactive prompts for workflow execution.
Handles FCA-specific input types: company numbers, filing types.

Architecture: Market-specific implementation of MarketPromptsInterface

Save location: markets/fca/fca_interactive_prompts.py
"""

from typing import Optional
from core.system_logger import get_logger
from .fca_searcher.fca_validators import FCAValidator
from .fca_searcher.fca_constants import FCA_FILING_TYPES, MAJOR_FILING_TYPES

logger = get_logger(__name__, 'market')


class FCAInteractivePrompts:
    """
    FCA-specific interactive prompts.
    
    Implements the prompts interface for UK FCA market.
    """
    
    def __init__(self):
        """Initialize FCA interactive prompts."""
        self.validator = FCAValidator()
        logger.info("FCA interactive prompts initialized")
    
    def prompt_for_company_identifier(self) -> str:
        """
        Prompt for FCA company identifier (company number).
        
        Returns:
            Company number (e.g., '00000001')
        """
        print("\nFCA Company Identifier:")
        print("  Enter UK company registration number")
        print("  Example: 00000001, 12345678")
        print("  Note: This is a stub implementation for testing")
        
        while True:
            identifier = input("\nEnter company number: ").strip()
            
            if not identifier:
                print("[FAIL] Company number cannot be empty")
                continue
            
            # Validate company number format
            if self.validator.validate_company_number(identifier):
                return identifier
            
            print(f"[WARNING]  '{identifier}' doesn't match UK company number format")
            confirm = input("Continue anyway? (y/n): ").strip().lower()
            if confirm == 'y':
                return identifier
    
    def prompt_for_filing_type(self) -> str:
        """
        Prompt for FCA filing type.
        
        Returns:
            Filing type (e.g., 'Annual Report', 'Half-Yearly Report')
        """
        print("\nFCA Filing Types:")
        print("  Common types:")
        
        # Display major filing types
        for i, filing_type in enumerate(MAJOR_FILING_TYPES, 1):
            print(f"    {i}. {filing_type}")
        
        print(f"    {len(MAJOR_FILING_TYPES) + 1}. Other (enter manually)")
        
        while True:
            choice_input = input(f"\nSelect filing type (1-{len(MAJOR_FILING_TYPES) + 1}): ").strip()
            
            try:
                choice = int(choice_input)
                
                if 1 <= choice <= len(MAJOR_FILING_TYPES):
                    return MAJOR_FILING_TYPES[choice - 1]
                
                elif choice == len(MAJOR_FILING_TYPES) + 1:
                    # Manual entry
                    custom_type = input("Enter filing type: ").strip()
                    if custom_type:
                        return custom_type
                    print("[FAIL] Filing type cannot be empty")
                else:
                    print(f"[FAIL] Please enter a number between 1 and {len(MAJOR_FILING_TYPES) + 1}")
            
            except ValueError:
                print("[FAIL] Please enter a valid number")


__all__ = ['FCAInteractivePrompts']