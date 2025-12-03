"""
ESMA Interactive Prompts (STUB)
===============================

ESMA-specific interactive prompts for workflow execution.
This is a STUB implementation for architecture validation.

Architecture: Market-specific implementation of MarketPromptsInterface

Save location: markets/esma/esma_interactive_prompts.py
"""

from typing import Optional
from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


class ESMAInteractivePrompts:
    """
    ESMA-specific interactive prompts (STUB).
    
    This is a stub implementation for testing market abstraction.
    Full implementation would be Phase 3.
    """
    
    def __init__(self):
        """Initialize ESMA interactive prompts."""
        logger.info("ESMA interactive prompts initialized (STUB)")
    
    def prompt_for_company_identifier(self) -> str:
        """
        Prompt for ESMA company identifier.
        
        Returns:
            Company identifier
        """
        print("\nESMA Company Identifier:")
        print("  [WARNING]  ESMA support is in STUB mode")
        print("  Enter company identifier for testing:")
        
        while True:
            identifier = input("\nEnter identifier: ").strip()
            
            if not identifier:
                print("[FAIL] Identifier cannot be empty")
                continue
            
            return identifier
    
    def prompt_for_filing_type(self) -> str:
        """
        Prompt for ESMA filing type.
        
        Returns:
            Filing type
        """
        print("\nESMA Filing Types:")
        print("  [WARNING]  ESMA support is in STUB mode")
        print("  Common types (for reference):")
        print("    Annual Financial Report")
        print("    Half-Yearly Financial Report")
        print("    Interim Management Statement")
        
        while True:
            filing_type = input("\nEnter filing type: ").strip()
            
            if not filing_type:
                print("[FAIL] Filing type cannot be empty")
                continue
            
            return filing_type


__all__ = ['ESMAInteractivePrompts']