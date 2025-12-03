# File: /map_pro/core/ui/user_prompts.py

"""
Map Pro User Prompts Module
===========================

Handles all user input collection for interactive workflows.
Market-agnostic parameter collection with validation.

Responsibilities:
- Collect workflow parameters from user
- Validate user inputs
- Confirm workflow execution
- Market-agnostic prompts only

Does NOT handle:
- Display/formatting (progress_display handles this)
- Results output (results_display handles this)
- Business logic (workflow_coordinator handles this)
"""

from typing import Tuple

from core.system_logger import get_logger
from core.market_selector import select_market, load_market_prompts

logger = get_logger(__name__, 'core')

MIN_INSTANCES = 1
MAX_INSTANCES = 10
SEPARATOR_LENGTH = 70


def prompt_user_for_workflow() -> Tuple[str, str, str, int]:
    """
    Prompt user for workflow parameters (market-agnostic).
    
    Returns:
        Tuple of (market_type, company_identifier, filing_type, num_instances)
    """
    _display_workflow_header()
    
    market_type = select_market()
    
    print(f"\n[OK] Selected Market: {market_type.upper()}\n")
    
    market_prompts = load_market_prompts(market_type)
    
    company_identifier = market_prompts.prompt_for_company_identifier()
    filing_type = market_prompts.prompt_for_filing_type()
    num_instances = prompt_for_num_instances()
    
    _display_workflow_summary(market_type, company_identifier, filing_type, num_instances)
    
    if not _confirm_workflow_execution():
        print("\n[STOP] Workflow cancelled by user\n")
        exit(0)
    
    return market_type, company_identifier, filing_type, num_instances


def prompt_for_num_instances() -> int:
    """
    Prompt for number of historical instances (market-agnostic).
    
    Returns:
        Number of instances (1-10)
    """
    while True:
        try:
            num_input = input(f"\nNumber of historical filings to process ({MIN_INSTANCES}-{MAX_INSTANCES}): ").strip()
            num_instances = int(num_input)
            
            if MIN_INSTANCES <= num_instances <= MAX_INSTANCES:
                return num_instances
            
            print(f"[WARNING] Please enter a number between {MIN_INSTANCES} and {MAX_INSTANCES}")
            
        except ValueError:
            print("[WARNING] Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n[STOP] Workflow cancelled by user\n")
            exit(0)


def _display_workflow_header():
    """Display workflow introduction header."""
    print("\n" + "=" * SEPARATOR_LENGTH)
    print("MAP PRO INTERACTIVE WORKFLOW")
    print("=" * SEPARATOR_LENGTH + "\n")
    
    print("This will process complete workflow:")
    print("  Search -> Download -> Extract -> Parse -> Map\n")


def _display_workflow_summary(
    market_type: str,
    company_identifier: str,
    filing_type: str,
    num_instances: int
):
    """Display workflow parameter summary."""
    print("\n" + "=" * SEPARATOR_LENGTH)
    print("WORKFLOW PARAMETERS")
    print("=" * SEPARATOR_LENGTH)
    print(f"  Market:             {market_type.upper()}")
    print(f"  Company:            {company_identifier}")
    print(f"  Filing Type:        {filing_type}")
    print(f"  Filings to Process: {num_instances}")
    print("=" * SEPARATOR_LENGTH + "\n")


def _confirm_workflow_execution() -> bool:
    """
    Ask user to confirm workflow execution.
    
    Returns:
        True if user confirms, False otherwise
    """
    try:
        confirm = input("Proceed with workflow? (y/n): ").strip().lower()
        return confirm == 'y'
    except KeyboardInterrupt:
        return False


__all__ = [
    'prompt_user_for_workflow',
    'prompt_for_num_instances',
]