"""
Database Optimizer
=================

File: tools/maintenance/database_optimizer.py

Analyzes database performance and generates optimization recommendations.
"""

from typing import Dict, Any, List

from .optimizer_config import OptimizerConfig


class DatabaseOptimizer:
    """
    Database performance optimization analyzer.
    
    Responsibilities:
    - Analyze connection pool utilization
    - Check database health status
    - Generate database optimization recommendations
    """
    
    def __init__(self, config: OptimizerConfig):
        """
        Initialize database optimizer.
        
        Args:
            config: Optimizer configuration
        """
        self.config = config
    
    async def analyze(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze database performance and generate recommendations.
        
        Args:
            analysis_data: System analysis data
            
        Returns:
            List of database optimization recommendations
        """
        recommendations = []
        db_metrics = analysis_data.get('database_metrics', {})
        
        # Check connection pool utilization
        pool_recs = self._analyze_connection_pools(db_metrics)
        recommendations.extend(pool_recs)
        
        # Check database health
        health_recs = self._analyze_database_health(db_metrics)
        recommendations.extend(health_recs)
        
        return recommendations
    
    def _analyze_connection_pools(
        self,
        db_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze connection pool utilization.
        
        Args:
            db_metrics: Database metrics
            
        Returns:
            List of connection pool recommendations
        """
        recommendations = []
        connection_pools = db_metrics.get('connection_pools', {})
        
        for db_name, pool_info in connection_pools.items():
            utilization = self._calculate_pool_utilization(pool_info)
            
            if utilization > self.config.high_pool_utilization:
                recommendations.append(
                    self._create_high_pool_utilization_recommendation(
                        db_name,
                        pool_info,
                        utilization
                    )
                )
        
        return recommendations
    
    def _calculate_pool_utilization(self, pool_info: Dict[str, Any]) -> float:
        """
        Calculate connection pool utilization percentage.
        
        Args:
            pool_info: Pool information dictionary
            
        Returns:
            Utilization percentage
        """
        pool_size = pool_info.get('size', 10)
        checked_out = pool_info.get('checked_out', 0)
        
        if pool_size == 0:
            return 0.0
        
        return (checked_out / pool_size) * 100
    
    def _create_high_pool_utilization_recommendation(
        self,
        db_name: str,
        pool_info: Dict[str, Any],
        utilization: float
    ) -> Dict[str, Any]:
        """
        Create high pool utilization recommendation.
        
        Args:
            db_name: Database name
            pool_info: Pool information
            utilization: Utilization percentage
            
        Returns:
            Recommendation dictionary
        """
        pool_size = pool_info.get('size', 10)
        new_size = min(
            self.config.max_db_pool_size,
            pool_size + self.config.pool_size_increment
        )
        
        return {
            'type': 'database_optimization',
            'priority': 'high',
            'priority_score': 85,
            'title': f'High Database Connection Pool Utilization - {db_name}',
            'description': (
                f'Connection pool for {db_name} is {utilization:.1f}% utilized'
            ),
            'recommendations': [
                f'Increase connection pool size for {db_name} database',
                'Monitor for connection leaks',
                'Consider query optimization to reduce connection time'
            ],
            'auto_applicable': True,
            'env_changes': {
                f'MAP_PRO_{db_name.upper()}_DB_POOL_SIZE': new_size
            }
        }
    
    def _analyze_database_health(
        self,
        db_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze database health status.
        
        Args:
            db_metrics: Database metrics
            
        Returns:
            List of health-related recommendations
        """
        recommendations = []
        
        if not db_metrics.get('overall_healthy', True):
            unhealthy_dbs = self._find_unhealthy_databases(db_metrics)
            
            if unhealthy_dbs:
                recommendations.append(
                    self._create_database_health_recommendation(unhealthy_dbs)
                )
        
        return recommendations
    
    def _find_unhealthy_databases(
        self,
        db_metrics: Dict[str, Any]
    ) -> List[str]:
        """
        Find unhealthy databases.
        
        Args:
            db_metrics: Database metrics
            
        Returns:
            List of unhealthy database names
        """
        unhealthy_dbs = []
        databases = db_metrics.get('databases', {})
        
        for db_name, db_info in databases.items():
            if not db_info.get('connected', True):
                unhealthy_dbs.append(db_name)
        
        return unhealthy_dbs
    
    def _create_database_health_recommendation(
        self,
        unhealthy_dbs: List[str]
    ) -> Dict[str, Any]:
        """
        Create database health recommendation.
        
        Args:
            unhealthy_dbs: List of unhealthy database names
            
        Returns:
            Recommendation dictionary
        """
        return {
            'type': 'database_optimization',
            'priority': 'critical',
            'priority_score': 100,
            'title': 'Database Connection Issues',
            'description': (
                f'Database connection problems detected: '
                f'{", ".join(unhealthy_dbs)}'
            ),
            'recommendations': [
                'Check database server status',
                'Verify connection configurations',
                'Review database logs for errors',
                'Consider restarting database connections'
            ],
            'auto_applicable': False
        }