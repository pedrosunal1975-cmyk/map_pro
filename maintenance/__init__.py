"""
Map Pro Maintenance Tools Module
=================================

This module provides maintenance and operational tools for Map Pro system.

Components:
-----------
- backup_manager: Main backup coordination and management
- backup_operations: Database and JSON backup operations  
- restore_operations: Database restore operations
- log_rotator: Log rotation and archival
- cleanup_scheduler: Main cleanup coordination and management
- cleanup_operations: File, directory, and database cleanup operations
- cleanup_statistics: Statistics gathering and analysis for cleanup
- system_optimizer: System performance optimization and tuning

Save location: tools/maintenance/__init__.py
"""

from tools.maintenance.backup_manager import BackupManager, create_backup
from tools.maintenance.backup_operations import BackupOperations
from tools.maintenance.restore_operations import RestoreOperations
from tools.maintenance.cleanup_scheduler import CleanupScheduler, run_cleanup
from tools.maintenance.cleanup_operations import CleanupOperations
from tools.maintenance.cleanup_statistics import CleanupStatistics
from tools.maintenance.system_optimizer import SystemOptimizer, optimize_system, get_optimization_recommendations
from tools.maintenance.connection_pool_manager import ConnectionPoolManager

__all__ = [
    'BackupManager',
    'create_backup',
    'BackupOperations',
    'RestoreOperations',
    'CleanupScheduler',
    'run_cleanup',
    'CleanupOperations',
    'CleanupStatistics',
    'SystemOptimizer',
    'ConnectionPoolManager',
    'optimize_system',
    'get_optimization_recommendations',
]

__version__ = '1.0.0'