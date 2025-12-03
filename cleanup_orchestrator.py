# File: /map_pro/tools/cleanup_orchestrator.py

"""
Cleanup Orchestrator
====================

Orchestrates all cleanup operations for the Map Pro database cleanup tool.
Coordinates job cleaning, file cleaning, database operations, and statistics.

SAFETY FEATURES:
- Taxonomy libraries are PROTECTED and never touched
- Only cleans explicit temp directories
- Database-only operations by default
- File operations require explicit paths

Responsibilities:
- Coordinate cleanup operations
- Track statistics across operations
- Initialize database connections
- Generate final reports

Related Files:
- database_cleanup.py: Main entry point
- cleanup_job_operations.py: Job cleanup logic
- cleanup_file_operations.py: File cleanup logic
- cleanup_database_operations.py: Database operations
"""

from typing import Dict, Any, List
from pathlib import Path

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator

from tools.cleanup_job_operations import CleanupJobOperations
from tools.cleanup_file_operations import CleanupFileOperations
from tools.cleanup_database_operations import CleanupDatabaseOperations

logger = get_logger(__name__, 'cleanup')


class ProtectedPaths:
    """Paths that must never be touched by cleanup operations."""
    TAXONOMIES = 'data/taxonomies/libraries'
    ENTITIES = 'data/entities'
    MAPPED_STATEMENTS = 'data/mapped_statements'
    PARSED_FACTS = 'data/parsed_facts'


class CleanupMode:
    """Constants for cleanup mode labels."""
    DRY_RUN = 'DRY RUN'
    CLEANUP = 'CLEANUP'


class CleanupOrchestrator:
    """
    Orchestrates all database and file cleanup operations.
    
    This class coordinates different cleanup operations while maintaining
    safety constraints and tracking statistics.
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize cleanup orchestrator.
        
        Args:
            dry_run: If True, preview changes without applying them
        """
        self.dry_run = dry_run
        self.logger = logger
        
        # Initialize database coordinator
        self._initialize_database()
        
        # Initialize operation handlers
        self.job_ops = CleanupJobOperations(
            logger=logger,
            dry_run=dry_run
        )
        self.file_ops = CleanupFileOperations(
            logger=logger,
            dry_run=dry_run
        )
        self.db_ops = CleanupDatabaseOperations(
            logger=logger,
            dry_run=dry_run
        )
        
        # Initialize statistics
        self.stats = {
            'jobs_removed': 0,
            'statuses_reset': 0,
            'orphaned_removed': 0,
            'temp_files_removed': 0,
            'logs_removed': 0,
            'space_freed_mb': 0.0,
            'errors': []
        }
        
        self._log_initialization()
    
    def _initialize_database(self) -> None:
        """
        Initialize database coordinator if not already initialized.
        
        Raises:
            RuntimeError: If database initialization fails
        """
        if not db_coordinator._is_initialized:
            try:
                self.logger.info("Initializing database coordinator...")
                success = db_coordinator.initialize()
                if not success:
                    raise RuntimeError("Database coordinator initialization failed")
                self.logger.info("Database coordinator initialized successfully")
            except Exception as exception:
                self.logger.error(
                    f"Failed to initialize database coordinator: {exception}"
                )
                raise
    
    def _log_initialization(self) -> None:
        """Log initialization status with mode and safety warnings."""
        if self.dry_run:
            self.logger.info(f"[{CleanupMode.DRY_RUN}] MODE - No changes will be made")
        else:
            self.logger.info(f"[{CleanupMode.CLEANUP}] MODE - Changes will be applied")
            self.logger.warning(
                "[WARNING] Taxonomy libraries are PROTECTED and will never be touched"
            )
    
    def cleanup_all(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Perform comprehensive safe cleanup of all components.
        
        DOES NOT include file system cleanup of data directories - that's too dangerous.
        Only cleans explicit temp directories and log files.
        
        Args:
            days_old: Age threshold in days for old data cleanup
            
        Returns:
            Dictionary with comprehensive cleanup results and statistics
        """
        self.logger.info("[START] Starting safe database cleanup")
        
        operations = [
            ("Failed Jobs", lambda: self.cleanup_failed_jobs()),
            ("Old Jobs", lambda: self.cleanup_old_jobs(days_old)),
            ("Parsed/Mapped DBs", lambda: self.db_ops.cleanup_parsed_mapped_databases(days_old=0)),
            ("Reset Statuses", lambda: self.reset_pending_statuses()),
            ("Orphaned Records", lambda: self.cleanup_orphaned_records()),
            ("Temp Files", lambda: self.cleanup_temp_files_only()),
            ("Old Logs", lambda: self.cleanup_old_logs(days_old)),
            ("Vacuum Databases", lambda: self.vacuum_databases())
        ]
        
        for operation_name, operation_func in operations:
            try:
                self.logger.info(f"[OPERATION] {operation_name}...")
                result = operation_func()
                self._update_stats_from_result(result)
                self.logger.info(
                    f"[SUCCESS] {operation_name}: {result.get('summary', 'Completed')}"
                )
            except Exception as exception:
                error_msg = f"[FAIL] {operation_name} failed: {exception}"
                self.logger.error(error_msg)
                self.stats['errors'].append(error_msg)
        
        return self._generate_final_report()
    
    def cleanup_jobs(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up processing jobs with age threshold.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Dictionary with cleanup results
        """
        result = self.job_ops.cleanup_jobs(days_old=days_old)
        self._update_stats_from_result(result)
        return result
    
    def cleanup_failed_jobs(self) -> Dict[str, Any]:
        """
        Clean up jobs with failed/error/cancelled status.
        
        Returns:
            Dictionary with cleanup results
        """
        result = self.job_ops.cleanup_failed_jobs()
        self._update_stats_from_result(result)
        return result
    
    def cleanup_old_jobs(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old completed jobs.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Dictionary with cleanup results
        """
        result = self.job_ops.cleanup_old_jobs(days_old)
        self._update_stats_from_result(result)
        return result
    
    def reset_pending_statuses(self) -> Dict[str, Any]:
        """
        Reset stuck pending/running statuses to allow reprocessing.
        
        Returns:
            Dictionary with reset results
        """
        result = self.job_ops.reset_pending_statuses()
        self._update_stats_from_result(result)
        return result
    
    def cleanup_orphaned_records(self) -> Dict[str, Any]:
        """
        Remove orphaned database records (documents without filings, etc.).
        
        Returns:
            Dictionary with cleanup results
        """
        result = self.db_ops.cleanup_orphaned_records()
        self._update_stats_from_result(result)
        return result
    
    def cleanup_temp_files_only(self) -> Dict[str, Any]:
        """
        Clean ONLY temp files from /data/temp directory.
        
        This is safe because temp directories are explicitly for temporary data.
        
        Returns:
            Dictionary with cleanup results
        """
        result = self.file_ops.cleanup_temp_files()
        self._update_stats_from_result(result)
        return result
    
    def cleanup_old_logs(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old log files.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Dictionary with cleanup results
        """
        result = self.file_ops.cleanup_old_logs(days_old)
        self._update_stats_from_result(result)
        return result
    
    def vacuum_databases(self) -> Dict[str, Any]:
        """
        Vacuum and analyze all databases for optimization.
        
        Returns:
            Dictionary with vacuum results
        """
        return self.db_ops.vacuum_databases()
    
    def _update_stats_from_result(self, result: Dict[str, Any]) -> None:
        """
        Update orchestrator statistics from operation result.
        
        Args:
            result: Result dictionary from operation
        """
        # Update counters
        self.stats['jobs_removed'] += result.get('jobs_removed', 0)
        self.stats['statuses_reset'] += result.get('statuses_reset', 0)
        self.stats['orphaned_removed'] += result.get('orphaned_removed', 0)
        self.stats['temp_files_removed'] += result.get('files_removed', 0)
        self.stats['logs_removed'] += result.get('files_removed', 0)
        self.stats['space_freed_mb'] += result.get('space_freed_mb', 0.0)
        
        # Collect errors
        if result.get('errors'):
            self.stats['errors'].extend(result['errors'])
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """
        Generate final comprehensive cleanup report.
        
        Returns:
            Dictionary with complete statistics and summary
        """
        self.stats['summary'] = (
            f"Cleanup completed: {self.stats['jobs_removed']} jobs, "
            f"{self.stats['statuses_reset']} statuses reset, "
            f"{self.stats['orphaned_removed']} orphaned records, "
            f"{self.stats['temp_files_removed']} temp files, "
            f"{self.stats['logs_removed']} logs, "
            f"{self.stats['space_freed_mb']:.2f} MB freed"
        )
        
        if self.stats['errors']:
            self.stats['summary'] += f", {len(self.stats['errors'])} errors"
        
        return self.stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current cleanup statistics.
        
        Returns:
            Dictionary with current statistics
        """
        return self.stats.copy()


__all__ = ['CleanupOrchestrator', 'ProtectedPaths', 'CleanupMode']