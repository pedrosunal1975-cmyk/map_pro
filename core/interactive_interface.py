# File: /map_pro/core/interactive_interface.py

"""
Map Pro Interactive Interface - Main Coordinator
================================================

Market-agnostic CLI interface coordinator for interactive workflow execution.
Delegates to specialized UI modules for user interaction and display.

Architecture: 
- Market-agnostic orchestration layer
- Delegates to ui.user_prompts for user input
- Delegates to ui.progress_display for progress visualization
- Delegates to ui.results_display for results formatting
- Pure coordination - no direct UI rendering

This module maintains backward compatibility by re-exporting all UI functions.
"""

from .ui.user_prompts import (
    prompt_user_for_workflow,
    prompt_for_num_instances
)

from .ui.progress_display import (
    display_workflow_stage,
    display_workflow_progress,
    display_filing_progress,
    display_stage_separator
)

from .ui.results_display import (
    display_final_results,
    display_entity_found,
    display_filings_found,
    display_error,
    display_warning,
    display_banner,
    clear_screen
)

__all__ = [
    'prompt_user_for_workflow',
    'prompt_for_num_instances',
    'display_workflow_stage',
    'display_workflow_progress',
    'display_filing_progress',
    'display_final_results',
    'display_entity_found',
    'display_filings_found',
    'display_error',
    'display_warning',
    'display_banner',
    'display_stage_separator',
    'clear_screen',
]