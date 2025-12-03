"""
Map Pro System Optimizer
========================

System performance optimization and resource management.
Analyzes system performance and applies optimizations automatically or by recommendation.

Responsibilities:
- Database connection pool optimization
- Cache configuration tuning
- Memory management optimization
- Disk space optimization
- Job queue optimization
- Engine performance tuning

Save location: tools/maintenance/system_optimizer.py
"""

from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from core.system_logger import get_logger
from tools.monitoring.performance_analyzer import PerformanceAnalyzer
from tools.monitoring.system_monitor import SystemMonitor
from tools.monitoring.database_health import DatabaseHealthChecker

from .optimizer_config import OptimizerConfig
from .system_data_collector import SystemDataCollector
from .memory_optimizer import MemoryOptimizer
from .database_optimizer import DatabaseOptimizer
from .disk_optimizer import DiskOptimizer
from .queue_optimizer import QueueOptimizer
from .performance_optimizer import PerformanceOptimizer
from .optimization_applicator import OptimizationApplicator

logger = get_logger(__name__, 'maintenance')


class SystemOptimizer:
    """
    System performance optimization and tuning.
    
    Coordinates optimization analysis and application across different subsystems.
    
    Responsibilities:
    - Coordinate optimization workflow
    - Collect system data
    - Generate recommendations
    - Apply safe optimizations
    - Track optimization history
    
    Does NOT handle:
    - Direct engine modifications (engines handle their own tuning)
    - Database schema changes (migration system handles this)
    - Network configuration (external to Map Pro)
    """
    
    def __init__(self, config: OptimizerConfig = None):
        """
        Initialize system optimizer.
        
        Args:
            config: Optimizer configuration (optional)
        """
        self.config = config or OptimizerConfig()
        self.logger = get_logger(__name__, 'maintenance')
        
        # Initialize monitoring components
        self.performance_analyzer = PerformanceAnalyzer()
        self.system_monitor = SystemMonitor()
        self.db_health_checker = DatabaseHealthChecker()
        
        # Initialize optimization components
        self.data_collector = SystemDataCollector(
            self.performance_analyzer,
            self.system_monitor
        )
        
        self.memory_optimizer = MemoryOptimizer(self.config)
        self.database_optimizer = DatabaseOptimizer(self.config)
        self.disk_optimizer = DiskOptimizer(self.config)
        self.queue_optimizer = QueueOptimizer(self.config)
        self.performance_optimizer = PerformanceOptimizer(self.config)
        
        self.applicator = OptimizationApplicator(self.config)
        
        # Optimization tracking
        self.optimization_history: List[Dict[str, Any]] = []
        self.last_optimization = None
        
        self.logger.info("System optimizer initialized")
        self.logger.info(
            f"Auto-optimization: "
            f"{'enabled' if self.config.auto_optimize else 'disabled'}"
        )
    
    async def run_full_optimization(self) -> Dict[str, Any]:
        """
        Run comprehensive system optimization analysis and apply safe optimizations.
        
        Returns:
            Dictionary with optimization results and recommendations
        """
        self.logger.info("Starting full system optimization")
        
        try:
            # Collect system data
            analysis_data = await self.data_collector.collect()
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(analysis_data)
            
            # Apply safe optimizations if enabled
            applied_optimizations = await self._apply_optimizations(recommendations)
            
            # Build result
            optimization_result = self._build_optimization_result(
                analysis_data,
                recommendations,
                applied_optimizations
            )
            
            # Store in history
            self._add_to_history(optimization_result)
            self.last_optimization = datetime.now(timezone.utc)
            
            self.logger.info(
                f"System optimization completed: {len(recommendations)} recommendations, "
                f"{len(applied_optimizations)} applied"
            )
            
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"System optimization failed: {e}", exc_info=True)
            return self._build_error_result(str(e))
    
    async def _generate_recommendations(
        self,
        analysis_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate optimization recommendations based on analysis data.
        
        Args:
            analysis_data: Collected system data
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Collect recommendations from each optimizer
        recommendations.extend(
            self.memory_optimizer.analyze(analysis_data)
        )
        recommendations.extend(
            await self.database_optimizer.analyze(analysis_data)
        )
        recommendations.extend(
            self.disk_optimizer.analyze(analysis_data)
        )
        recommendations.extend(
            self.queue_optimizer.analyze(analysis_data)
        )
        recommendations.extend(
            self.performance_optimizer.analyze(analysis_data)
        )
        
        # Sort by priority
        recommendations.sort(
            key=lambda x: x.get('priority_score', 0),
            reverse=True
        )
        
        return recommendations
    
    async def _apply_optimizations(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply safe optimizations if auto-optimize is enabled.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            List of applied optimizations
        """
        if not self.config.auto_optimize:
            return []
        
        return await self.applicator.apply_safe_optimizations(recommendations)
    
    def _build_optimization_result(
        self,
        analysis_data: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
        applied_optimizations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build optimization result dictionary.
        
        Args:
            analysis_data: Collected system data
            recommendations: Generated recommendations
            applied_optimizations: Applied optimizations
            
        Returns:
            Optimization result dictionary
        """
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': True,
            'analysis_data': analysis_data,
            'recommendations': recommendations,
            'applied_optimizations': applied_optimizations,
            'auto_optimize_enabled': self.config.auto_optimize,
            'next_optimization': self._calculate_next_optimization_time()
        }
    
    def _build_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Build error result dictionary.
        
        Args:
            error_message: Error message
            
        Returns:
            Error result dictionary
        """
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': False,
            'error': error_message,
            'recommendations': [],
            'applied_optimizations': []
        }
    
    def _calculate_next_optimization_time(self) -> str:
        """
        Calculate when the next optimization should run.
        
        Returns:
            ISO format timestamp string
        """
        if self.last_optimization:
            next_time = self.last_optimization + timedelta(
                hours=self.config.optimization_interval_hours
            )
        else:
            next_time = datetime.now(timezone.utc) + timedelta(
                hours=self.config.optimization_interval_hours
            )
        
        return next_time.isoformat()
    
    def _add_to_history(self, optimization_result: Dict[str, Any]) -> None:
        """
        Add optimization result to history.
        
        Args:
            optimization_result: Optimization result to store
        """
        self.optimization_history.append(optimization_result)
        
        # Maintain history size limit
        max_history = self.config.max_history_size
        if len(self.optimization_history) > max_history:
            self.optimization_history.pop(0)
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """
        Get optimization history.
        
        Returns:
            Copy of optimization history list
        """
        return self.optimization_history.copy()
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Get current optimization status.
        
        Returns:
            Dictionary with status information
        """
        return {
            'auto_optimize_enabled': self.config.auto_optimize,
            'optimization_interval_hours': self.config.optimization_interval_hours,
            'last_optimization': (
                self.last_optimization.isoformat()
                if self.last_optimization else None
            ),
            'next_optimization': self._calculate_next_optimization_time(),
            'optimization_count': len(self.optimization_history),
            'max_memory_usage_threshold': self.config.max_memory_usage_percent,
            'max_disk_usage_threshold': self.config.max_disk_usage_percent
        }


# Convenience functions
async def optimize_system() -> Dict[str, Any]:
    """
    Convenience function to run system optimization.
    
    Returns:
        Optimization results
    """
    optimizer = SystemOptimizer()
    return await optimizer.run_full_optimization()


async def get_optimization_recommendations() -> List[Dict[str, Any]]:
    """
    Get optimization recommendations without applying them.
    
    Returns:
        List of recommendations
    """
    optimizer = SystemOptimizer()
    analysis_data = await optimizer.data_collector.collect()
    return await optimizer._generate_recommendations(analysis_data)


__all__ = [
    'SystemOptimizer',
    'optimize_system',
    'get_optimization_recommendations'
]