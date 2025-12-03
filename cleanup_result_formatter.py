# File: /map_pro/tools/cleanup_result_formatter.py

"""
Cleanup Result Formatter
=========================

Formats and displays cleanup operation results in a human-readable format.

Responsibilities:
- Format operation results for display
- Handle dry-run vs actual cleanup display
- Format error messages clearly
- Provide consistent output formatting

Related Files:
- database_cleanup.py: Main entry point
- cleanup_orchestrator.py: Orchestration
"""

from typing import Dict, Any, List, Tuple


class DisplayLabels:
    """Labels for display formatting."""
    DRY_RUN_HEADER = "[PREVIEW] DRY RUN RESULTS (no changes made):"
    CLEANUP_HEADER = "[COMPLETE] CLEANUP RESULTS:"
    ERROR_PREFIX = "[FAIL]"
    OPERATION_PREFIX = "  "
    ERROR_INDENT = "    "


class CleanupResultFormatter:
    """
    Formats cleanup operation results for display.
    
    This class provides methods for formatting and displaying cleanup
    results in a consistent, readable format.
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize result formatter.
        
        Args:
            dry_run: Whether this was a dry run operation
        """
        self.dry_run = dry_run
    
    def print_results(self, result: Dict[str, Any]) -> None:
        """
        Print formatted cleanup results to console.
        
        Args:
            result: Result dictionary from cleanup operations
        """
        # Print header
        header = (
            DisplayLabels.DRY_RUN_HEADER if self.dry_run
            else DisplayLabels.CLEANUP_HEADER
        )
        print(f"\n{header}")
        
        # Print individual operation results or summary
        if 'operations' in result:
            self._print_operation_results(result['operations'])
        else:
            self._print_summary_result(result)
    
    def _print_operation_results(
        self,
        operations: List[Tuple[str, Dict[str, Any]]]
    ) -> None:
        """
        Print results for individual operations.
        
        Args:
            operations: List of (operation_name, result) tuples
        """
        for op_name, op_result in operations:
            # Format operation name
            display_name = self._format_operation_name(op_name)
            summary = op_result.get('summary', 'Completed')
            
            print(f"{DisplayLabels.OPERATION_PREFIX}{display_name}: {summary}")
            
            # Print errors if any
            if op_result.get('errors'):
                for error in op_result['errors']:
                    print(
                        f"{DisplayLabels.ERROR_INDENT}"
                        f"{DisplayLabels.ERROR_PREFIX} {error}"
                    )
    
    def _print_summary_result(self, result: Dict[str, Any]) -> None:
        """
        Print summary result for comprehensive cleanup.
        
        Args:
            result: Result dictionary with summary
        """
        summary = result.get('summary', 'Completed')
        print(f"{DisplayLabels.OPERATION_PREFIX}{summary}")
        
        # Print errors if any
        if result.get('errors'):
            for error in result['errors']:
                print(
                    f"{DisplayLabels.OPERATION_PREFIX}"
                    f"{DisplayLabels.ERROR_PREFIX} {error}"
                )
    
    def _format_operation_name(self, op_name: str) -> str:
        """
        Format operation name for display.
        
        Args:
            op_name: Internal operation name
            
        Returns:
            Formatted display name
        """
        # Map internal names to display names
        name_map = {
            'jobs': 'Jobs',
            'failed': 'Failed Jobs',
            'reset_statuses': 'Reset Statuses',
            'orphaned': 'Orphaned Records',
            'temp_only': 'Temp Files',
            'logs': 'Old Logs',
            'vacuum': 'Vacuum Databases'
        }
        
        return name_map.get(op_name, op_name.replace('_', ' ').title())
    
    def format_summary_line(self, result: Dict[str, Any]) -> str:
        """
        Format a single-line summary of results.
        
        Args:
            result: Result dictionary from cleanup operations
            
        Returns:
            Single-line summary string
        """
        if 'summary' in result:
            return result['summary']
        
        # Build summary from operations
        if 'operations' in result:
            total_operations = len(result['operations'])
            successful = sum(
                1 for _, op_result in result['operations']
                if not op_result.get('errors')
            )
            return f"{successful}/{total_operations} operations completed successfully"
        
        return "No operations executed"


__all__ = ['CleanupResultFormatter', 'DisplayLabels']