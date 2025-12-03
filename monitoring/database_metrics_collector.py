"""
Map Pro Database Metrics Collector
===================================

Collects database health and connection pool metrics.

Save location: tools/monitoring/database_metrics_collector.py
"""

from typing import Dict, Any

from core.system_logger import get_logger
from .database_health import DatabaseHealthChecker
from .monitoring_constants import DATABASE_NAMES

logger = get_logger(__name__, 'monitoring')


class DatabaseMetricsCollector:
    """
    Collects database metrics.
    
    Responsibilities:
    - Collect database health metrics
    - Collect connection pool metrics
    """
    
    def __init__(self, db_coordinator) -> None:
        """
        Initialize database metrics collector.
        
        Args:
            db_coordinator: Database coordinator instance
        """
        self.db_coordinator = db_coordinator
        self.db_checker = DatabaseHealthChecker()
    
    async def collect(
        self,
        enable_detailed: bool = True
    ) -> Dict[str, Any]:
        """
        Collect database metrics.
        
        Args:
            enable_detailed: Whether to include detailed connection pool metrics
            
        Returns:
            Dictionary with database metrics
        """
        try:
            db_health = await self.db_checker.check_all_databases()
            
            db_metrics = {
                'overall_healthy': db_health['overall_healthy'],
                'databases': db_health['databases']
            }
            
            if enable_detailed:
                db_metrics['connection_pools'] = await self._get_connection_pool_metrics()
            
            return db_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            return {'error': str(e)}
    
    async def _get_connection_pool_metrics(self) -> Dict[str, Any]:
        """
        Get database connection pool metrics.
        
        Returns:
            Dictionary with connection pool metrics for each database
        """
        pool_metrics = {}
        
        try:
            for db_name in DATABASE_NAMES:
                engine = self.db_coordinator.get_engine(db_name)
                if engine:
                    pool = engine.pool
                    pool_metrics[db_name] = {
                        'size': pool.size(),
                        'checked_in': pool.checkedin(),
                        'checked_out': pool.checkedout(),
                        'overflow': pool.overflow(),
                        'status': pool.status()
                    }
            
            return pool_metrics
            
        except Exception as e:
            logger.error(f"Failed to get connection pool metrics: {e}")
            return {'error': str(e)}