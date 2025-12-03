# File: /map_pro/core/ui/progress_display.py

"""
Map Pro Progress Display Module
===============================

Handles all progress visualization during workflow execution.
Market-agnostic progress tracking and display.

Responsibilities:
- Display workflow stage progress
- Show individual filing progress
- Format progress indicators
- Visual separators

Does NOT handle:
- User input (user_prompts handles this)
- Final results (results_display handles this)
- Business logic (workflow_coordinator handles this)
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger

logger = get_logger(__name__, 'core')

SEPARATOR_LENGTH = 70
STAGE_NAME_WIDTH = 10

STAGE_ICONS = {
    'pending': '[ ]',
    'running': '[WAIT]',
    'completed': '[OK]',
    'failed': '[FAIL]'
}

WORKFLOW_STAGES = [
    ('search', 'Search Company & Filings'),
    ('download', 'Download Files'),
    ('extract', 'Extract Archives'),
    ('parse', 'Parse XBRL'),
    ('map', 'Map to Statements')
]


def display_workflow_stage(stage: str, status: str, details: Optional[str] = None):
    """
    Display single workflow stage status.
    
    Args:
        stage: Stage name (search, download, extract, parse, map)
        status: Status (pending, running, completed, failed)
        details: Optional details to display
    """
    icon = STAGE_ICONS.get(status, '[?]')
    stage_display = stage.upper().ljust(STAGE_NAME_WIDTH)
    
    line = f"{icon} {stage_display} {status}"
    if details:
        line += f" - {details}"
    
    print(line)


def display_workflow_progress(workflow_status: Dict[str, str]):
    """
    Display complete workflow progress.
    
    Args:
        workflow_status: Dictionary with stage statuses
            Example: {'search': 'completed', 'download': 'running', ...}
    """
    print("\n" + "-" * SEPARATOR_LENGTH)
    print("WORKFLOW PROGRESS")
    print("-" * SEPARATOR_LENGTH)
    
    for stage_key, stage_name in WORKFLOW_STAGES:
        status = workflow_status.get(stage_key, 'pending')
        display_workflow_stage(stage_name, status)
    
    print("-" * SEPARATOR_LENGTH + "\n")


def display_filing_progress(
    current: int,
    total: int,
    filing_info: Optional[Dict[str, Any]] = None
):
    """
    Display progress for individual filing.
    
    Args:
        current: Current filing number (1-based)
        total: Total number of filings
        filing_info: Optional filing information
    """
    print(f"\n{'-' * SEPARATOR_LENGTH}")
    print(f"PROCESSING FILING {current} OF {total}")
    print(f"{'-' * SEPARATOR_LENGTH}")
    
    if filing_info:
        _display_filing_details(filing_info)
        print()


def _display_filing_details(filing_info: Dict[str, Any]):
    """Display filing details if available."""
    if 'filing_type' in filing_info:
        print(f"  Form Type: {filing_info['filing_type']}")
    
    if 'filing_date' in filing_info:
        print(f"  Date: {filing_info['filing_date']}")
    
    if 'market_filing_id' in filing_info:
        print(f"  ID: {filing_info['market_filing_id']}")


def display_stage_separator():
    """Display visual separator between stages."""
    print(f"\n{'=' * SEPARATOR_LENGTH}\n")


__all__ = [
    'display_workflow_stage',
    'display_workflow_progress',
    'display_filing_progress',
    'display_stage_separator',
]