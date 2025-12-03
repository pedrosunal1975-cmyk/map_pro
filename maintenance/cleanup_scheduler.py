# File: /map_pro/tools/maintenance/cleanup_scheduler.py

"""
Map Pro Cleanup Scheduler
=========================

Main cleanup scheduler coordinating all cleanup operations.

This module has been refactored into:
- cleanup_scheduler.py (this file) - Pure orchestration
- cleanup_recommendation_engine.py - Recommendation generation
- cleanup_history_logger.py - Cleanup history management
- cleanup_scheduler_constants.py - Constants

Responsibilities:
- Orchestrate cleanup operations
- Coordinate specialized components
- Provide public API for cleanup

Does NOT handle:
- Recommendation logic (recommendation_engine handles this)
- History logging (history_logger handles this)
- Statistics gathering (cleanup_statistics handles this)
- Execution logic (cleanup_executor handles this)

Configuration:
- Uses .env for retention settings and thresholds
- Reports activities to dedicated log

Related Files:
- cleanup_operations.py: Individual cleanup operations
- cleanup_statistics.py: Statistics gathering
- connection_pool_manager.py: Connection pool management
- cleanup_config.py: Configuration management
- cleanup_executor.py: Cleanup execution logic
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.system_logger import get_logger
from tools.maintenance.cleanup_operations import CleanupOperations
from tools.maintenance.cleanup_statistics import CleanupStatistics
from tools.maintenance.connection_pool_manager import ConnectionPoolManager
from tools.maintenance.cleanup_config import CleanupConfig
from tools.maintenance.cleanup_executor import CleanupExecutor

from .cleanup_recommendation_engine import CleanupRecommendationEngine
from .cleanup_history_logger import CleanupHistoryLogger
from .cleanup_scheduler_constants import CLEANUP_NAME_PREFIX, TARGETED_CLEANUP_PREFIX

logger = get_logger(__name__, 'maintenance')


class CleanupScheduler:
    """
    Main cleanup scheduler managing system maintenance operations.
    
    SINGLE RESPONSIBILITY: Orchestrate cleanup operations and coordinate components.
    
    This class is now a pure coordinator:
    - Initializes specialized components
    - Delegates to specialized handlers
    - Provides clean public API
    - Zero implementation logic
    
    Responsibilities:
    - Coordinate cleanup workflow
    - Delegate to specialized components
    - Provide public API
    
    Does NOT:
    - Generate recommendations (recommendation_engine does this)
    - Log history (history_logger does this)
    - Gather statistics (cleanup_statistics does this)
    - Execute cleanup (cleanup_executor does this)
    """
    
    def __init__(
        self,
        config: Optional[CleanupConfig] = None,
        cleanup_ops: Optional[CleanupOperations] = None,
        cleanup_stats: Optional[CleanupStatistics] = None,
        connection_pool_manager: Optional[ConnectionPoolManager] = None,
        executor: Optional[CleanupExecutor] = None,
        recommendation_engine: Optional[CleanupRecommendationEngine] = None,
        history_logger: Optional[CleanupHistoryLogger] = None
    ):
        """
        Initialize cleanup scheduler with optional dependencies.
        
        Args:
            config: Configuration manager (created if None)
            cleanup_ops: Cleanup operations handler (created if None)
            cleanup_stats: Statistics collector (created if None)
            connection_pool_manager: Connection pool manager (created if None)
            executor: Cleanup executor (created if None)
            recommendation_engine: Recommendation engine (created if None)
            history_logger: History logger (created if None)
        """
        self.logger = logger
        
        # Load configuration
        self.config = config or CleanupConfig()
        
        # Initialize operation handlers
        self.cleanup_ops = cleanup_ops or self._create_cleanup_operations()
        self.cleanup_stats = cleanup_stats or self._create_cleanup_statistics()
        self.connection_pool_manager = connection_pool_manager or ConnectionPoolManager()
        
        # Initialize executor
        self.executor = executor or CleanupExecutor(
            cleanup_ops=self.cleanup_ops,
            connection_pool_manager=self.connection_pool_manager,
            config=self.config,
            logger=self.logger
        )
        
        # Initialize recommendation engine
        self.recommendation_engine = recommendation_engine or CleanupRecommendationEngine(
            config=self.config,
            connection_pool_manager=self.connection_pool_manager
        )
        
        # Initialize history logger
        self.history_logger = history_logger or CleanupHistoryLogger()
        
        self._log_initialization()
    
    def _create_cleanup_operations(self) -> CleanupOperations:
        """
        Create CleanupOperations with configured retention days.
        
        Returns:
            Configured CleanupOperations instance
        """
        return CleanupOperations(
            temp_retention_days=self.config.temp_retention_days,
            download_retention_days=self.config.download_retention_days,
            failed_job_retention_days=self.config.failed_job_retention_days,
            old_job_retention_days=self.config.old_job_retention_days
        )
    
    def _create_cleanup_statistics(self) -> CleanupStatistics:
        """
        Create CleanupStatistics with configured thresholds.
        
        Returns:
            Configured CleanupStatistics instance
        """
        return CleanupStatistics(
            max_temp_size_gb=self.config.max_temp_size_gb,
            max_log_size_gb=self.config.max_log_size_gb
        )
    
    def _log_initialization(self) -> None:
        """Log initialization parameters for monitoring."""
        self.logger.info("Cleanup scheduler initialized")
        self.logger.info(f"Temp retention: {self.config.temp_retention_days} days")
        self.logger.info(f"Download retention: {self.config.download_retention_days} days")
        self.logger.info(f"Database retention: {self.config.old_job_retention_days} days")
        self.logger.info(f"Connection cleanup: {self.config.cleanup_connections}")
    
    def run_full_cleanup(self) -> Dict[str, Any]:
        """
        Run complete system cleanup.
        
        Executes all enabled cleanup operations:
        - Temporary files cleanup
        - Downloads cleanup
        - Database cleanup
        - Connection pool cleanup
        - Log cleanup (if enabled)
        
        Returns:
            Dictionary with cleanup results
        """
        start_time = datetime.now(timezone.utc)
        cleanup_name = self._generate_cleanup_name(start_time, CLEANUP_NAME_PREFIX)
        
        self.logger.info(f"Starting full system cleanup: {cleanup_name}")
        
        try:
            # Execute cleanup
            results = self.executor.execute_full_cleanup(cleanup_name, start_time)
            
            # Log history
            self.history_logger.log_cleanup(results)
            
            # Log completion
            self._log_completion(results, start_time, cleanup_name)
            
            return results
            
        except Exception as exception:
            return self._handle_cleanup_error(
                cleanup_name, start_time, exception
            )
    
    def run_targeted_cleanup(self, cleanup_types: List[str]) -> Dict[str, Any]:
        """
        Run specific types of cleanup.
        
        Args:
            cleanup_types: List of cleanup types to run. Valid types:
                - 'temp': Temporary files cleanup
                - 'downloads': Old downloads cleanup
                - 'database': Database records cleanup
                - 'connections': Connection pool cleanup
                - 'logs': Old logs cleanup
            
        Returns:
            Dictionary with cleanup results
        """
        start_time = datetime.now(timezone.utc)
        cleanup_name = self._generate_cleanup_name(start_time, TARGETED_CLEANUP_PREFIX)
        
        self.logger.info(
            f"Starting targeted cleanup: {cleanup_name} - {cleanup_types}"
        )
        
        try:
            # Execute cleanup
            results = self.executor.execute_targeted_cleanup(
                cleanup_name, start_time, cleanup_types
            )
            
            # Log history
            self.history_logger.log_cleanup(results)
            
            # Log completion
            self._log_completion(results, start_time, cleanup_name)
            
            return results
            
        except Exception as exception:
            return self._handle_targeted_cleanup_error(
                cleanup_name, start_time, exception, cleanup_types
            )
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """
        Get current system statistics for cleanup planning.
        
        Delegates to CleanupStatistics.
        
        Returns:
            Dictionary with system statistics
        """
        return self.cleanup_stats.get_cleanup_statistics()
    
    def get_cleanup_recommendations(self) -> Dict[str, Any]:
        """
        Get cleanup recommendations based on current system state.
        
        Delegates to CleanupRecommendationEngine.
        
        Returns:
            Dictionary with recommendations
        """
        try:
            stats = self.get_cleanup_statistics()
            return self.recommendation_engine.generate_recommendations(stats)
            
        except Exception as exception:
            self.logger.error(f"Failed to get cleanup statistics: {exception}")
            return self.recommendation_engine.create_error_recommendations(
                str(exception)
            )
    
    def _generate_cleanup_name(self, timestamp: datetime, prefix: str) -> str:
        """
        Generate unique cleanup name with timestamp.
        
        Args:
            timestamp: Cleanup start timestamp
            prefix: Name prefix
            
        Returns:
            Unique cleanup name string
        """
        return f"{prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    
    def _log_completion(
        self,
        results: Dict[str, Any],
        start_time: datetime,
        cleanup_name: str
    ) -> None:
        """
        Log cleanup completion.
        
        Args:
            results: Cleanup results
            start_time: Start timestamp
            cleanup_name: Cleanup identifier
        """
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        if results.get('success'):
            self.logger.info(
                f"Cleanup completed successfully in {duration:.2f}s: {cleanup_name}"
            )
        else:
            self.logger.warning(
                f"Cleanup completed with errors in {duration:.2f}s: {cleanup_name}"
            )
    
    def _handle_cleanup_error(
        self,
        cleanup_name: str,
        start_time: datetime,
        exception: Exception
    ) -> Dict[str, Any]:
        """
        Handle full cleanup error.
        
        Args:
            cleanup_name: Cleanup identifier
            start_time: Start timestamp
            exception: Exception that occurred
            
        Returns:
            Error result dictionary
        """
        self.logger.error(f"Full cleanup failed: {exception}", exc_info=True)
        
        return {
            'cleanup_name': cleanup_name,
            'timestamp': start_time.isoformat(),
            'success': False,
            'errors': [str(exception)],
            'total_space_freed_mb': 0
        }
    
    def _handle_targeted_cleanup_error(
        self,
        cleanup_name: str,
        start_time: datetime,
        exception: Exception,
        cleanup_types: List[str]
    ) -> Dict[str, Any]:
        """
        Handle targeted cleanup error.
        
        Args:
            cleanup_name: Cleanup identifier
            start_time: Start timestamp
            exception: Exception that occurred
            cleanup_types: Types that were attempted
            
        Returns:
            Error result dictionary
        """
        self.logger.error(
            f"Targeted cleanup failed: {exception}",
            exc_info=True
        )
        
        return {
            'cleanup_name': cleanup_name,
            'timestamp': start_time.isoformat(),
            'success': False,
            'cleanup_types': cleanup_types,
            'errors': [str(exception)],
            'total_space_freed_mb': 0
        }


def run_cleanup() -> Dict[str, Any]:
    """
    Convenience function to run full system cleanup.
    
    Creates a CleanupScheduler instance and executes full cleanup.
    
    Returns:
        Dictionary with cleanup results
    """
    scheduler = CleanupScheduler()
    return scheduler.run_full_cleanup()


__all__ = ['CleanupScheduler', 'run_cleanup']