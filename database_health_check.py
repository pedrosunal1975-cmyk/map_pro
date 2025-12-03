#!/usr/bin/env python3
"""
Map Pro Database Health Check Tool - Refactored
===============================================

Checks synchronization between filesystem and database.
Follows Single Responsibility Principle.

Architecture:
- IssueTracker: Manages and aggregates issues
- HealthCheckOrchestrator: Coordinates check operations
- RepairOrchestrator: Coordinates repair operations
- HealthCheckCLI: Command-line interface

Usage:
    python tools/database_health_check.py --check           # Check only
    python tools/database_health_check.py --check --repair  # Check and repair
    python tools/database_health_check.py --stats           # Show statistics
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator

from tools.health_check_config import HealthCheckConfig
from tools.parsed_db_checker import ParsedDatabaseChecker
from tools.mapped_db_checker import MappedDatabaseChecker
from tools.health_check_repairer import HealthCheckRepairer
from tools.health_check_reporter import HealthCheckReporter

logger = get_logger(__name__, 'health_check')


# =============================================================================
# ISSUE TRACKING
# =============================================================================

@dataclass
class IssueTracker:
    """
    Single Responsibility: Track and aggregate health check issues.
    
    Maintains a centralized registry of all issues found during health checks.
    Provides methods to add, query, and summarize issues.
    """
    
    missing_parsed_records: List[Dict] = field(default_factory=list)
    phantom_parsed_records: List[Dict] = field(default_factory=list)
    missing_mapped_records: List[Dict] = field(default_factory=list)
    phantom_mapped_records: List[Dict] = field(default_factory=list)
    path_mismatches: List[Dict] = field(default_factory=list)
    
    def merge(self, new_issues: Dict[str, List[Dict]]) -> None:
        """
        Merge new issues into tracker.
        
        Args:
            new_issues: Dictionary of issues to merge
        """
        for issue_type, issue_list in new_issues.items():
            if hasattr(self, issue_type):
                getattr(self, issue_type).extend(issue_list)
    
    def get_total_count(self) -> int:
        """Get total number of issues."""
        return sum([
            len(self.missing_parsed_records),
            len(self.phantom_parsed_records),
            len(self.missing_mapped_records),
            len(self.phantom_mapped_records),
            len(self.path_mismatches)
        ])
    
    def to_dict(self) -> Dict[str, List[Dict]]:
        """Convert to dictionary format."""
        return {
            'missing_parsed_records': self.missing_parsed_records,
            'phantom_parsed_records': self.phantom_parsed_records,
            'missing_mapped_records': self.missing_mapped_records,
            'phantom_mapped_records': self.phantom_mapped_records,
            'path_mismatches': self.path_mismatches
        }
    
    def has_issues(self) -> bool:
        """Check if any issues exist."""
        return self.get_total_count() > 0


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

class DatabaseInitializer:
    """
    Single Responsibility: Initialize database connections.
    
    Ensures database coordinator is ready before health checks.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__, 'db_initializer')
    
    def ensure_initialized(self) -> None:
        """
        Ensure database coordinator is initialized.
        
        Raises:
            RuntimeError: If database initialization fails
        """
        if not db_coordinator._is_initialized:
            self.logger.info("Initializing database coordinator...")
            if not db_coordinator.initialize():
                raise RuntimeError("Failed to initialize database")
        
        self.logger.debug("Database coordinator ready")


# =============================================================================
# HEALTH CHECK ORCHESTRATION
# =============================================================================

class HealthCheckOrchestrator:
    """
    Single Responsibility: Orchestrate health check operations.
    
    Coordinates parsed and mapped database checks, delegating
    actual checking to specialized checker components.
    """
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        """
        Initialize orchestrator.
        
        Args:
            config: Health check configuration (optional)
        """
        self.config = config or HealthCheckConfig()
        self.logger = get_logger(__name__, 'health_check_orchestrator')
        
        # Initialize database
        self.db_initializer = DatabaseInitializer()
        self.db_initializer.ensure_initialized()
        
        # Initialize specialized checkers
        self.parsed_checker = ParsedDatabaseChecker(self.config)
        self.mapped_checker = MappedDatabaseChecker(self.config)
        
        # Initialize issue tracker
        self.issues = IssueTracker()
    
    def check_parsed_database(self) -> None:
        """Check parsed database synchronization with filesystem."""
        self.logger.info("Checking parsed database synchronization...")
        
        parsed_issues = self.parsed_checker.check()
        self.issues.merge(parsed_issues)
        
        self.logger.info(
            f"Parsed database check complete. "
            f"Found {len(parsed_issues.get('missing_parsed_records', []))} "
            f"+ {len(parsed_issues.get('phantom_parsed_records', []))} issues"
        )
    
    def check_mapped_database(self) -> None:
        """Check mapped database synchronization with filesystem."""
        self.logger.info("Checking mapped database synchronization...")
        
        mapped_issues = self.mapped_checker.check()
        self.issues.merge(mapped_issues)
        
        self.logger.info(
            f"Mapped database check complete. "
            f"Found {len(mapped_issues.get('missing_mapped_records', []))} "
            f"+ {len(mapped_issues.get('phantom_mapped_records', []))} issues"
        )
    
    def check_all(self) -> IssueTracker:
        """
        Run all health checks.
        
        Returns:
            IssueTracker with all issues found
        """
        self.check_parsed_database()
        self.check_mapped_database()
        return self.issues


# =============================================================================
# REPAIR ORCHESTRATION
# =============================================================================

@dataclass
class RepairStatistics:
    """Statistics from repair operations."""
    records_created: int = 0
    records_deleted: int = 0
    paths_updated: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            'records_created': self.records_created,
            'records_deleted': self.records_deleted,
            'paths_updated': self.paths_updated
        }


class RepairOrchestrator:
    """
    Single Responsibility: Orchestrate repair operations.
    
    Coordinates repair of issues found during health checks.
    """
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        """
        Initialize repair orchestrator.
        
        Args:
            config: Health check configuration (optional)
        """
        self.config = config or HealthCheckConfig()
        self.logger = get_logger(__name__, 'repair_orchestrator')
        self.repairer = HealthCheckRepairer(self.config)
    
    def repair(
        self, 
        issues: IssueTracker, 
        dry_run: bool = True
    ) -> RepairStatistics:
        """
        Repair issues found during health checks.
        
        Args:
            issues: Issues to repair
            dry_run: If True, only simulate repairs
            
        Returns:
            Repair statistics
        """
        self.logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Starting repair operations..."
        )
        
        # Repair parsed database issues
        repair_stats = self.repairer.repair_parsed_issues(
            issues.to_dict(), 
            dry_run
        )
        
        # Convert to statistics object
        stats = RepairStatistics(
            records_created=repair_stats.get('records_created', 0),
            records_deleted=repair_stats.get('records_deleted', 0),
            paths_updated=repair_stats.get('paths_updated', 0)
        )
        
        self.logger.info(
            f"Repair complete: {stats.records_created} created, "
            f"{stats.records_deleted} deleted, {stats.paths_updated} updated"
        )
        
        return stats


# =============================================================================
# REPORTING
# =============================================================================

class ReportGenerator:
    """
    Single Responsibility: Generate health check reports.
    
    Formats and displays health check results.
    """
    
    def __init__(self):
        self.reporter = HealthCheckReporter()
    
    def print_report(self, issues: IssueTracker) -> None:
        """
        Print comprehensive health check report.
        
        Args:
            issues: Issues to report
        """
        self.reporter.print_report(issues.to_dict())
    
    def print_repair_summary(self, stats: RepairStatistics) -> None:
        """
        Print repair operation summary.
        
        Args:
            stats: Repair statistics
        """
        print(f"\n[REPAIR COMPLETE]")
        print(f"  Records created: {stats.records_created}")
        print(f"  Records deleted: {stats.records_deleted}")
        print(f"  Paths updated: {stats.paths_updated}")
        print(f"\nRun --check again to verify repairs.")


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

class HealthCheckCLI:
    """
    Single Responsibility: Handle command-line interface.
    
    Parses arguments and coordinates operations based on user input.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__, 'health_check_cli')
    
    def run_check(self) -> IssueTracker:
        """
        Run health check operations.
        
        Returns:
            IssueTracker with all issues found
        """
        print("\n[STEP 1] Checking parsed database...")
        print("[STEP 2] Checking mapped database...")
        
        orchestrator = HealthCheckOrchestrator()
        return orchestrator.check_all()
    
    def run_repair(self, issues: IssueTracker) -> Optional[RepairStatistics]:
        """
        Run repair operations with user confirmation.
        
        Args:
            issues: Issues to repair
            
        Returns:
            Repair statistics, or None if cancelled
        """
        if not issues.has_issues():
            print("\nNo issues to repair!")
            return None
        
        # Ask for confirmation
        total_issues = issues.get_total_count()
        response = input(f"\nRepair {total_issues} issues? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Repair cancelled.")
            return None
        
        orchestrator = RepairOrchestrator()
        return orchestrator.repair(issues, dry_run=False)
    
    def show_statistics(self) -> None:
        """Show database statistics."""
        print("\n[DATABASE STATISTICS]")
        # TODO: Add statistics reporting
        print("Statistics feature coming soon...")
    
    def execute(self, args) -> int:
        """
        Execute CLI commands based on arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            if args.check:
                # Run health check
                issues = self.run_check()
                
                # Generate report
                print("\n[STEP 3] Generating report...")
                report_gen = ReportGenerator()
                report_gen.print_report(issues)
                
                # Run repair if requested
                if args.repair:
                    print("\n[STEP 4] Repairing issues...")
                    stats = self.run_repair(issues)
                    if stats:
                        report_gen.print_repair_summary(stats)
            
            if args.stats:
                self.show_statistics()
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}", exc_info=True)
            print(f"\n[ERROR] Health check failed: {e}")
            return 1


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Map Pro Database Health Check Tool'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check database-filesystem synchronization'
    )
    parser.add_argument(
        '--repair',
        action='store_true',
        help='Repair issues found (requires --check)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    
    args = parser.parse_args()
    
    if not any([args.check, args.stats]):
        parser.print_help()
        return 1
    
    cli = HealthCheckCLI()
    return cli.execute(args)


if __name__ == '__main__':
    sys.exit(main())