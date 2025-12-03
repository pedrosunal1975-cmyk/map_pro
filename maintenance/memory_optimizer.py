"""
Memory Optimizer
===============

File: tools/maintenance/memory_optimizer.py

Analyzes memory usage and generates optimization recommendations.
"""

import os
from typing import Dict, Any, List

from .optimizer_config import OptimizerConfig


class MemoryOptimizer:
    """
    Memory usage optimization analyzer.
    
    Responsibilities:
    - Analyze memory usage patterns
    - Generate memory optimization recommendations
    - Suggest connection pool adjustments
    - Recommend cache size changes
    """
    
    def __init__(self, config: OptimizerConfig):
        """
        Initialize memory optimizer.
        
        Args:
            config: Optimizer configuration
        """
        self.config = config
    
    def analyze(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze memory usage and generate recommendations.
        
        Args:
            analysis_data: System analysis data
            
        Returns:
            List of memory optimization recommendations
        """
        recommendations = []
        system_resources = analysis_data.get('system_resources', {})
        memory_percent = system_resources.get('memory_percent', 0)
        
        if memory_percent > self.config.max_memory_usage_percent:
            recommendations.append(
                self._create_high_memory_recommendation(memory_percent)
            )
        elif memory_percent < self.config.low_memory_threshold and memory_percent > 0:
            recommendations.append(
                self._create_low_memory_recommendation(memory_percent)
            )
        
        return recommendations
    
    def _create_high_memory_recommendation(
        self,
        memory_percent: float
    ) -> Dict[str, Any]:
        """
        Create high memory usage recommendation.
        
        Args:
            memory_percent: Current memory usage percent
            
        Returns:
            Recommendation dictionary
        """
        current_pool = int(os.getenv('MAP_PRO_DB_POOL_SIZE', '10'))
        current_cache = int(os.getenv('MAP_PRO_CACHE_SIZE_MB', '1000'))
        
        new_pool = max(self.config.min_pool_size, current_pool - 5)
        new_cache = max(self.config.min_cache_size_mb, current_cache - 200)
        
        return {
            'type': 'memory_optimization',
            'priority': 'high',
            'priority_score': 90,
            'title': 'High Memory Usage Detected',
            'description': (
                f'Memory usage is {memory_percent:.1f}%, exceeding threshold of '
                f'{self.config.max_memory_usage_percent}%'
            ),
            'recommendations': [
                'Reduce database connection pool sizes',
                'Implement cache size limits',
                'Consider adding more RAM to the system',
                'Review and optimize memory-intensive processes'
            ],
            'auto_applicable': True,
            'env_changes': {
                'MAP_PRO_DB_POOL_SIZE': new_pool,
                'MAP_PRO_CACHE_SIZE_MB': new_cache
            }
        }
    
    def _create_low_memory_recommendation(
        self,
        memory_percent: float
    ) -> Dict[str, Any]:
        """
        Create low memory utilization recommendation.
        
        Args:
            memory_percent: Current memory usage percent
            
        Returns:
            Recommendation dictionary
        """
        current_pool = int(os.getenv('MAP_PRO_DB_POOL_SIZE', '10'))
        current_cache = int(os.getenv('MAP_PRO_CACHE_SIZE_MB', '1000'))
        
        new_pool = min(self.config.max_pool_size, current_pool + 5)
        new_cache = min(self.config.max_cache_size_mb, current_cache + 200)
        
        return {
            'type': 'memory_optimization',
            'priority': 'medium',
            'priority_score': 40,
            'title': 'Memory Underutilization',
            'description': (
                f'Memory usage is only {memory_percent:.1f}%, '
                f'could increase for better performance'
            ),
            'recommendations': [
                'Increase database connection pool sizes',
                'Increase cache sizes for better performance',
                'Consider enabling more concurrent processing'
            ],
            'auto_applicable': True,
            'env_changes': {
                'MAP_PRO_DB_POOL_SIZE': new_pool,
                'MAP_PRO_CACHE_SIZE_MB': new_cache
            }
        }