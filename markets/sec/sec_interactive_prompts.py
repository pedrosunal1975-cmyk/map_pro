"""
SEC Interactive Prompts
=======================

SEC-specific interactive prompts for workflow execution.
Handles SEC-specific input types: tickers, CIKs, form types.

Architecture: Market-specific implementation of MarketPromptsInterface

Save location: markets/sec/sec_interactive_prompts.py
"""

from typing import Optional
from core.system_logger import get_logger
from .sec_searcher.sec_validators import SECValidator

logger = get_logger(__name__, 'market')


class SECInteractivePrompts:
    """
    SEC-specific interactive prompts.
    
    Implements the prompts interface for SEC EDGAR market.
    """
    
    def __init__(self):
        """Initialize SEC interactive prompts."""
        self.validator = SECValidator()
        logger.info("SEC interactive prompts initialized")
    
    def prompt_for_company_identifier(self) -> str:
        """
        Prompt for SEC company identifier (ticker or CIK).
        
        Returns:
            Company identifier (ticker or CIK)
        """
        print("\nSEC Company Identifier:")
        print("  You can enter either:")
        print("    * Stock ticker (e.g., AAPL, MSFT, GOOGL)")
        print("    * CIK number (e.g., 0000320193 for Apple)")
        
        while True:
            identifier = input("\nEnter ticker or CIK: ").strip().upper()
            
            if not identifier:
                print("[FAIL] Identifier cannot be empty")
                continue
            
            # Validate identifier
            identifier_type = self.validator.identify_identifier_type(identifier)
            
            if identifier_type == 'unknown':
                print(f"[WARNING]  '{identifier}' doesn't look like a valid ticker or CIK")
                confirm = input("Continue anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue
            
            return identifier
    
    def prompt_for_filing_type(self) -> str:
        """
        Prompt for SEC filing type.
        
        Returns:
            Filing type (e.g., '10-K', '10-Q')
        """
        print("\nSEC Filing Types:")
        print("  Common types:")
        print("    10-K   = Annual report")
        print("    10-Q   = Quarterly report")
        print("    20-F   = Foreign issuer annual report")
        print("    8-K    = Current report")
        print("    DEF 14A = Proxy statement")
        print("    S-1    = IPO registration")
        
        while True:
            filing_type = input("\nEnter filing type: ").strip().upper()
            
            if not filing_type:
                print("[FAIL] Filing type cannot be empty")
                continue
            
            # Validate filing type
            if self.validator.validate_filing_type(filing_type):
                return filing_type
            
            # Unknown filing type - confirm
            print(f"[WARNING]  '{filing_type}' is not a common SEC filing type")
            confirm = input("Continue anyway? (y/n): ").strip().lower()
            if confirm == 'y':
                return filing_type


__all__ = ['SECInteractivePrompts']