"""
Map Pro Cleanup Operations
==========================

Concrete cleanup operations for files, directories, and database records.

Save location: tools/maintenance/cleanup_operations.py
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from core.database_coordinator import db_coordinator

logger = get_logger(__name__, 'maintenance')


class CleanupOperations:
    """Handles concrete cleanup operations for different system components."""
    
    def __init__(
        self, 
        temp_retention_days: int = 7,
        download_retention_days: int = 14,
        failed_job_retention_days: int = 30,
        old_job_retention_days: int = 90
    ):
        """Initialize cleanup operations."""
        self.logger = logger
        self.temp_retention_days = temp_retention_days
        self.download_retention_days = download_retention_days
        self.failed_job_retention_days = failed_job_retention_days
        self.old_job_retention_days = old_job_retention_days
    
    def cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean temporary files and workspaces."""
        self.logger.info("Starting temporary files cleanup")
        
        result = {
            'success': False,
            'files_removed': 0,
            'directories_removed': 0,
            'space_freed_mb': 0,
            'errors': []
        }
        
        try:
            temp_root = map_pro_paths.data_temp
            
            if not temp_root.exists():
                result['success'] = True
                return result
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.temp_retention_days)
            
            # Process temp directories
            for item in temp_root.iterdir():
                try:
                    if item.is_file():
                        # Check file age
                        file_mtime = datetime.fromtimestamp(item.stat().st_mtime, timezone.utc)
                        if file_mtime < cutoff_date:
                            size_mb = item.stat().st_size / (1024 * 1024)
                            item.unlink()
                            result['files_removed'] += 1
                            result['space_freed_mb'] += size_mb
                    
                    elif item.is_dir():
                        # Handle workspace directories
                        if self._should_cleanup_workspace(item, cutoff_date):
                            size_mb = self._get_directory_size_mb(item)
                            shutil.rmtree(item)
                            result['directories_removed'] += 1
                            result['space_freed_mb'] += size_mb
                            self.logger.debug(f"Removed workspace: {item.name}")
                
                except (OSError, PermissionError) as e:
                    error_msg = f"Failed to remove {item}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.warning(error_msg)
            
            result['success'] = True
            self.logger.info(f"Temp cleanup: {result['files_removed']} files, "
                           f"{result['directories_removed']} dirs, "
                           f"{result['space_freed_mb']:.2f}MB freed")
        
        except Exception as e:
            error_msg = f"Temp cleanup failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def cleanup_old_downloads(self) -> Dict[str, Any]:
        """Clean old download files."""
        self.logger.info("Starting downloads cleanup")
        
        result = {
            'success': False,
            'files_removed': 0,
            'space_freed_mb': 0,
            'errors': []
        }
        
        try:
            downloads_root = map_pro_paths.data_root / 'downloads'
            
            if not downloads_root.exists():
                result['success'] = True
                return result
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.download_retention_days)
            
            # Process download files
            for item in downloads_root.rglob('*'):
                try:
                    if item.is_file():
                        file_mtime = datetime.fromtimestamp(item.stat().st_mtime, timezone.utc)
                        if file_mtime < cutoff_date:
                            size_mb = item.stat().st_size / (1024 * 1024)
                            item.unlink()
                            result['files_removed'] += 1
                            result['space_freed_mb'] += size_mb
                
                except (OSError, PermissionError) as e:
                    error_msg = f"Failed to remove download {item}: {e}"
                    result['errors'].append(error_msg)
                    self.logger.warning(error_msg)
            
            result['success'] = True
            self.logger.info(f"Downloads cleanup: {result['files_removed']} files, "
                           f"{result['space_freed_mb']:.2f}MB freed")
        
        except Exception as e:
            error_msg = f"Downloads cleanup failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def cleanup_database(self) -> Dict[str, Any]:
        """Clean database records."""
        self.logger.info("Starting database cleanup")
        
        result = {
            'success': False,
            'jobs_removed': 0,
            'orphaned_records_removed': 0,
            'errors': []
        }
        
        try:
            # Clean old completed/failed jobs
            old_jobs_result = self._cleanup_old_jobs()
            result.update(old_jobs_result)
            
            # Clean orphaned records (if any patterns found)
            orphaned_result = self._cleanup_orphaned_records()
            result['orphaned_records_removed'] = orphaned_result.get('records_removed', 0)
            if orphaned_result.get('errors'):
                result['errors'].extend(orphaned_result['errors'])
            
            result['success'] = len(result['errors']) == 0
            
            self.logger.info(f"Database cleanup: {result['jobs_removed']} jobs, "
                           f"{result['orphaned_records_removed']} orphaned records removed")
        
        except Exception as e:
            error_msg = f"Database cleanup failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg, exc_info=True)
        
        return result
    
    def cleanup_old_logs(self) -> Dict[str, Any]:
        """Clean very old log files (backup to log_rotator)."""
        result = {
            'success': True,
            'files_removed': 0,
            'space_freed_mb': 0,
            'errors': []
        }
        
        # This is usually handled by log_rotator, but can be backup cleanup
        # for extremely old files that might have been missed
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)  # Very old logs
            
            log_directories = [
                map_pro_paths.logs_engines,
                map_pro_paths.logs_system,
                map_pro_paths.logs_alerts,
                map_pro_paths.logs_integrations
            ]
            
            for log_dir in log_directories:
                if not log_dir.exists():
                    continue
                
                for log_file in log_dir.rglob('*.log.*'):
                    try:
                        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime, timezone.utc)
                        if file_mtime < cutoff_date:
                            size_mb = log_file.stat().st_size / (1024 * 1024)
                            log_file.unlink()
                            result['files_removed'] += 1
                            result['space_freed_mb'] += size_mb
                    
                    except (OSError, PermissionError) as e:
                        error_msg = f"Failed to remove log {log_file}: {e}"
                        result['errors'].append(error_msg)
        
        except Exception as e:
            error_msg = f"Log cleanup failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
            result['success'] = False
        
        return result
    
    def _cleanup_old_jobs(self) -> Dict[str, Any]:
        """Clean old job records."""
        result = {
            'jobs_removed': 0,
            'errors': []
        }
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.old_job_retention_days)
            failed_cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.failed_job_retention_days)
            
            # Connect to core database
            with db_coordinator.get_connection('core') as conn:
                with conn.cursor() as cursor:
                    # Remove old completed jobs
                    cursor.execute("""
                        DELETE FROM jobs 
                        WHERE status = 'completed' 
                        AND updated_at < %s
                    """, (cutoff_date,))
                    completed_removed = cursor.rowcount
                    
                    # Remove old failed jobs (shorter retention)
                    cursor.execute("""
                        DELETE FROM jobs 
                        WHERE status IN ('failed', 'error') 
                        AND updated_at < %s
                    """, (failed_cutoff_date,))
                    failed_removed = cursor.rowcount
                    
                    result['jobs_removed'] = completed_removed + failed_removed
                    
                    self.logger.debug(f"Removed {completed_removed} old completed jobs, "
                                    f"{failed_removed} old failed jobs")
        
        except Exception as e:
            error_msg = f"Job cleanup failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def _cleanup_orphaned_records(self) -> Dict[str, Any]:
        """Clean orphaned database records."""
        result = {
            'records_removed': 0,
            'errors': []
        }
        
        try:
            # Example: Clean orphaned entity references where files don't exist
            # This would need to be customized based on actual orphan patterns discovered
            
            with db_coordinator.get_connection('parsed') as conn:
                with conn.cursor() as cursor:
                    # Find facts with missing entity files
                    cursor.execute("""
                        SELECT DISTINCT entity_id, market_type
                        FROM parsed_facts 
                        WHERE entity_id IS NOT NULL
                    """)
                    
                    orphaned_count = 0
                    for row in cursor.fetchall():
                        entity_id, market_type = row
                        
                        # Check if entity file exists
                        entity_path = map_pro_paths.get_entity_data_path(market_type, entity_id)
                        if not entity_path.exists():
                            # Remove orphaned facts
                            cursor.execute("""
                                DELETE FROM parsed_facts 
                                WHERE entity_id = %s AND market_type = %s
                            """, (entity_id, market_type))
                            orphaned_count += cursor.rowcount
                    
                    result['records_removed'] = orphaned_count
        
        except Exception as e:
            error_msg = f"Orphaned records cleanup failed: {e}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def _should_cleanup_workspace(self, workspace_dir: Path, cutoff_date: datetime) -> bool:
        """Determine if workspace directory should be cleaned up."""
        try:
            # Check directory age
            dir_mtime = datetime.fromtimestamp(workspace_dir.stat().st_mtime, timezone.utc)
            if dir_mtime >= cutoff_date:
                return False
            
            # Don't cleanup active workspaces (check for lock files, etc.)
            if (workspace_dir / '.active').exists():
                return False
            
            # Check if it's a test workspace (always safe to clean)
            if 'test' in workspace_dir.name.lower():
                return True
            
            # Check if workspace appears abandoned (no recent activity)
            recent_activity = False
            for item in workspace_dir.rglob('*'):
                if item.is_file():
                    item_mtime = datetime.fromtimestamp(item.stat().st_mtime, timezone.utc)
                    if item_mtime >= cutoff_date:
                        recent_activity = True
                        break
            
            return not recent_activity
        
        except (OSError, PermissionError):
            # If we can't access it, probably safe to try cleanup
            return True
    
    def _get_directory_size_mb(self, directory: Path) -> float:
        """Calculate directory size in megabytes."""
        try:
            total_size = sum(
                f.stat().st_size for f in directory.rglob('*') 
                if f.is_file()
            )
            return total_size / (1024 * 1024)
        except (OSError, PermissionError):
            return 0.0


__all__ = ['CleanupOperations']