# File: /map_pro/tools/database_cleanup.py

"""
Map Pro Database Cleanup Tool - SAFE VERSION
=============================================

CRITICAL SAFETY CHANGES:
- REMOVED cleanup_orphaned_files() - too dangerous
- Taxonomy libraries are PROTECTED and never touched
- Only cleans database records and temp files
- File system cleanup requires explicit paths, never scans data_root

Usage:
    python tools/database_cleanup.py --all                    # Safe cleanup
    python tools/database_cleanup.py --jobs                   # Clean jobs only
    python tools/database_cleanup.py --failed                 # Clean failed jobs only
    python tools/database_cleanup.py --reset-statuses         # Reset pending statuses
    python tools/database_cleanup.py --orphaned               # Remove orphaned records
    python tools/database_cleanup.py --logs                   # Clean old logs
    python tools/database_cleanup.py --vacuum                 # Vacuum databases
    python tools/database_cleanup.py --temp-only              # Clean temp files only

Related Files:
- cleanup_orchestrator.py: Main cleanup orchestration
- cleanup_operations.py: Individual cleanup operations
- cleanup_reporter.py: Statistics and reporting
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.system_logger import get_logger
from tools.cleanup_orchestrator import CleanupOrchestrator
from tools.cleanup_command_parser import CleanupCommandParser
from tools.cleanup_result_formatter import CleanupResultFormatter

logger = get_logger(__name__, 'cleanup')


class CleanupDefaults:
    """Default values for cleanup operations."""
    DAYS_OLD = 30
    DRY_RUN = False


class ExitCodes:
    """Exit codes for cleanup tool."""
    SUCCESS = 0
    ERROR = 1


def main() -> int:
    """
    Main entry point for database cleanup tool.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Parse command line arguments
    parser = _create_argument_parser()
    args = parser.parse_args()
    
    # Create cleanup orchestrator
    try:
        orchestrator = CleanupOrchestrator(dry_run=args.dry_run)
    except Exception as exception:
        logger.error(f"Failed to initialize cleanup tool: {exception}")
        print(f"[FAIL] Cleanup initialization failed: {exception}")
        return ExitCodes.ERROR
    
    # Parse and execute cleanup commands
    try:
        command_parser = CleanupCommandParser()
        operations = command_parser.parse_arguments(args)
        
        if not operations:
            print("No operations specified. Use --help for options.")
            return ExitCodes.SUCCESS
        
        # Execute cleanup operations
        result = _execute_cleanup_operations(
            orchestrator=orchestrator,
            operations=operations,
            args=args
        )
        
        # Format and display results
        formatter = CleanupResultFormatter(dry_run=args.dry_run)
        formatter.print_results(result)
        
        # Return appropriate exit code
        has_errors = result.get('errors', []) or any(
            op_result.get('errors', [])
            for _, op_result in result.get('operations', [])
        )
        
        return ExitCodes.ERROR if has_errors else ExitCodes.SUCCESS
        
    except Exception as exception:
        logger.error(f"Cleanup execution failed: {exception}", exc_info=True)
        print(f"[FAIL] Cleanup failed: {exception}")
        return ExitCodes.ERROR


def _create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure argument parser for cleanup tool.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description='Map Pro SAFE Database Cleanup Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/database_cleanup.py --all              # Complete safe cleanup
  python tools/database_cleanup.py --jobs --days 60   # Clean jobs older than 60 days
  python tools/database_cleanup.py --failed --dry-run # Preview failed job cleanup
  python tools/database_cleanup.py --temp-only        # Clean temp files only
        """
    )
    
    # Operation flags
    parser.add_argument(
        '--all',
        action='store_true',
        help='Safe cleanup (no file deletion from data directories)'
    )
    parser.add_argument(
        '--jobs',
        action='store_true',
        help='Clean up processing jobs'
    )
    parser.add_argument(
        '--failed',
        action='store_true',
        help='Clean failed jobs only'
    )
    parser.add_argument(
        '--reset-statuses',
        action='store_true',
        help='Reset stuck statuses to allow reprocessing'
    )
    parser.add_argument(
        '--orphaned',
        action='store_true',
        help='Clean orphaned database records'
    )
    parser.add_argument(
        '--temp-only',
        action='store_true',
        help='Clean temp files only (safe operation)'
    )
    parser.add_argument(
        '--logs',
        action='store_true',
        help='Clean old log files'
    )
    parser.add_argument(
        '--vacuum',
        action='store_true',
        help='Vacuum and analyze databases'
    )
    
    # Configuration options
    parser.add_argument(
        '--days',
        type=int,
        default=CleanupDefaults.DAYS_OLD,
        help=f'Age threshold in days (default: {CleanupDefaults.DAYS_OLD})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    
    return parser


def _execute_cleanup_operations(
    orchestrator: CleanupOrchestrator,
    operations: Dict[str, Any],
    args: argparse.Namespace
) -> Dict[str, Any]:
    """
    Execute cleanup operations based on parsed commands.
    
    Args:
        orchestrator: CleanupOrchestrator instance
        operations: Dictionary of operations to execute
        args: Parsed command line arguments
        
    Returns:
        Dictionary with operation results
    """
    if operations.get('all'):
        return orchestrator.cleanup_all(days_old=args.days)
    
    # Execute individual operations
    result = {'operations': []}
    
    operation_map = {
        'jobs': lambda: orchestrator.cleanup_jobs(days_old=args.days),
        'failed': lambda: orchestrator.cleanup_failed_jobs(),
        'reset_statuses': lambda: orchestrator.reset_pending_statuses(),
        'orphaned': lambda: orchestrator.cleanup_orphaned_records(),
        'temp_only': lambda: orchestrator.cleanup_temp_files_only(),
        'logs': lambda: orchestrator.cleanup_old_logs(args.days),
        'vacuum': lambda: orchestrator.vacuum_databases()
    }
    
    for op_name, op_func in operation_map.items():
        if operations.get(op_name):
            try:
                op_result = op_func()
                result['operations'].append((op_name, op_result))
            except Exception as exception:
                error_result = {
                    'success': False,
                    'error': str(exception),
                    'errors': [str(exception)]
                }
                result['operations'].append((op_name, error_result))
                logger.error(f"Operation {op_name} failed: {exception}")
    
    return result


if __name__ == '__main__':
    sys.exit(main())