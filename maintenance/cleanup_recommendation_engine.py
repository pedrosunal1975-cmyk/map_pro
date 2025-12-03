# File: /map_pro/tools/maintenance/cleanup_recommendation_engine.py

"""
Cleanup Recommendation Engine
==============================

Generates cleanup recommendations based on system statistics.
Analyzes system state and provides actionable advice.

SINGLE RESPONSIBILITY: Generate cleanup recommendations.
"""

from typing import Dict, Any, List

from core.system_logger import get_logger
from tools.maintenance.cleanup_config import CleanupConfig
from tools.maintenance.connection_pool_manager import ConnectionPoolManager

from .cleanup_scheduler_constants import (
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW
)

logger = get_logger(__name__, 'maintenance')


class CleanupRecommendationEngine:
    """
    Generates cleanup recommendations.
    
    SINGLE RESPONSIBILITY: Analyze statistics and generate recommendations.
    
    Responsibilities:
    - Analyze system statistics
    - Compare against thresholds
    - Generate prioritized recommendations
    - Aggregate recommendation metrics
    
    Does NOT:
    - Gather statistics (cleanup_statistics does this)
    - Execute cleanup (cleanup_executor does this)
    - Log history (history_logger does this)
    """
    
    def __init__(
        self,
        config: CleanupConfig,
        connection_pool_manager: ConnectionPoolManager
    ):
        """
        Initialize recommendation engine.
        
        Args:
            config: Cleanup configuration
            connection_pool_manager: Connection pool manager for health checks
        """
        self.config = config
        self.connection_pool_manager = connection_pool_manager
        self.logger = logger
    
    def generate_recommendations(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate recommendations based on system statistics.
        
        Args:
            stats: System statistics dictionary
            
        Returns:
            Dictionary with recommendations and counts by priority
        """
        recommendations = []
        
        # Check temp directory
        temp_rec = self._check_temp_directory(stats)
        if temp_rec:
            recommendations.append(temp_rec)
        
        # Check log directory
        log_rec = self._check_log_directory(stats)
        if log_rec:
            recommendations.append(log_rec)
        
        # Check old jobs
        old_jobs_rec = self._check_old_jobs(stats)
        if old_jobs_rec:
            recommendations.append(old_jobs_rec)
        
        # Check failed jobs
        failed_jobs_rec = self._check_failed_jobs(stats)
        if failed_jobs_rec:
            recommendations.append(failed_jobs_rec)
        
        # Check connection pool
        conn_rec = self._check_connection_health()
        if conn_rec:
            recommendations.append(conn_rec)
        
        return self._create_recommendation_summary(recommendations)
    
    def create_error_recommendations(self, error: str) -> Dict[str, Any]:
        """
        Create empty recommendations result with error.
        
        Args:
            error: Error message
            
        Returns:
            Empty recommendations dictionary with error
        """
        return {
            'recommendations': [],
            'total_recommendations': 0,
            'high_priority': 0,
            'medium_priority': 0,
            'low_priority': 0,
            'error': error
        }
    
    def _check_temp_directory(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check temp directory size against threshold.
        
        Args:
            stats: System statistics
            
        Returns:
            Recommendation dictionary or None
        """
        temp_size = stats.get('temp_directory_size_gb', 0)
        
        if temp_size > self.config.max_temp_size_gb:
            return {
                'type': 'temp_cleanup',
                'priority': PRIORITY_HIGH,
                'message': (
                    f"Temp directory ({temp_size:.2f}GB) "
                    f"exceeds threshold ({self.config.max_temp_size_gb}GB)"
                ),
                'action': 'Run temp files cleanup'
            }
        
        return None
    
    def _check_log_directory(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check log directory size against threshold.
        
        Args:
            stats: System statistics
            
        Returns:
            Recommendation dictionary or None
        """
        log_size = stats.get('logs_size_gb', 0)
        
        if log_size > self.config.max_log_size_gb:
            return {
                'type': 'log_cleanup',
                'priority': PRIORITY_MEDIUM,
                'message': (
                    f"Logs directory ({log_size:.2f}GB) "
                    f"exceeds threshold ({self.config.max_log_size_gb}GB)"
                ),
                'action': 'Run log rotation or cleanup'
            }
        
        return None
    
    def _check_old_jobs(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check old jobs count against threshold.
        
        Args:
            stats: System statistics
            
        Returns:
            Recommendation dictionary or None
        """
        old_jobs = stats.get('old_jobs_count', 0)
        
        if old_jobs > self.config.old_jobs_threshold:
            return {
                'type': 'database_cleanup',
                'priority': PRIORITY_MEDIUM,
                'message': f"{old_jobs} old completed jobs found",
                'action': 'Run database cleanup'
            }
        
        return None
    
    def _check_failed_jobs(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check failed jobs count against threshold.
        
        Args:
            stats: System statistics
            
        Returns:
            Recommendation dictionary or None
        """
        failed_jobs = stats.get('failed_jobs_count', 0)
        
        if failed_jobs > self.config.failed_jobs_threshold:
            return {
                'type': 'database_cleanup',
                'priority': PRIORITY_LOW,
                'message': f"{failed_jobs} old failed jobs found",
                'action': 'Run database cleanup'
            }
        
        return None
    
    def _check_connection_health(self) -> Dict[str, Any]:
        """
        Check connection pool health.
        
        Returns:
            Recommendation dictionary or None
        """
        try:
            conn_health = self.connection_pool_manager.check_health()
            
            if not conn_health.get('healthy', True):
                return {
                    'type': 'connection_cleanup',
                    'priority': PRIORITY_HIGH,
                    'message': (
                        f"Connection pool unhealthy: "
                        f"{conn_health.get('warnings', [])}"
                    ),
                    'action': 'Run connection pool cleanup'
                }
        
        except Exception as exception:
            self.logger.warning(
                f"Could not check connection pool health: {exception}"
            )
        
        return None
    
    def _create_recommendation_summary(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create summary of recommendations with counts by priority.
        
        Args:
            recommendations: List of recommendation dictionaries
            
        Returns:
            Summary dictionary
        """
        return {
            'recommendations': recommendations,
            'total_recommendations': len(recommendations),
            'high_priority': self._count_by_priority(recommendations, PRIORITY_HIGH),
            'medium_priority': self._count_by_priority(recommendations, PRIORITY_MEDIUM),
            'low_priority': self._count_by_priority(recommendations, PRIORITY_LOW)
        }
    
    def _count_by_priority(
        self,
        recommendations: List[Dict[str, Any]],
        priority: str
    ) -> int:
        """
        Count recommendations by priority level.
        
        Args:
            recommendations: List of recommendation dictionaries
            priority: Priority level to count
            
        Returns:
            Count of recommendations with specified priority
        """
        return len([r for r in recommendations if r['priority'] == priority])


__all__ = ['CleanupRecommendationEngine']