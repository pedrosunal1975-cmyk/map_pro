# File: /map_pro/tools/cleanup_command_parser.py

"""
Cleanup Command Parser
======================

Parses command line arguments into a structured format for the
cleanup orchestrator.

Responsibilities:
- Parse command line arguments
- Validate argument combinations
- Convert arguments to operation dictionary
- Provide clear operation mapping

Related Files:
- database_cleanup.py: Main entry point
- cleanup_orchestrator.py: Orchestration
"""

from typing import Dict, Any
import argparse


class CleanupCommandParser:
    """
    Parses cleanup command line arguments into operation dictionary.
    
    This class converts argparse.Namespace into a clean dictionary
    of operations to execute.
    """
    
    def parse_arguments(self, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Parse command line arguments into operations dictionary.
        
        Args:
            args: Parsed command line arguments from argparse
            
        Returns:
            Dictionary with operation flags:
                - all (bool): Execute all operations
                - jobs (bool): Clean jobs
                - failed (bool): Clean failed jobs
                - reset_statuses (bool): Reset stuck statuses
                - orphaned (bool): Clean orphaned records
                - temp_only (bool): Clean temp files
                - logs (bool): Clean old logs
                - vacuum (bool): Vacuum databases
        """
        operations = {
            'all': args.all,
            'jobs': args.jobs,
            'failed': args.failed,
            'reset_statuses': args.reset_statuses,
            'orphaned': args.orphaned,
            'temp_only': args.temp_only,
            'logs': args.logs,
            'vacuum': args.vacuum
        }
        
        # If no specific operations selected, return empty dict
        if not any(operations.values()):
            return {}
        
        return operations
    
    def get_operation_count(self, operations: Dict[str, Any]) -> int:
        """
        Count number of operations to be executed.
        
        Args:
            operations: Operations dictionary
            
        Returns:
            Number of operations that will be executed
        """
        if operations.get('all'):
            return 8  # All operations includes 8 sub-operations
        
        return sum(1 for value in operations.values() if value)


__all__ = ['CleanupCommandParser']