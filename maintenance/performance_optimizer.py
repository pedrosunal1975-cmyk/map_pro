"""
Performance Optimizer
====================

File: tools/maintenance/performance_optimizer.py

Analyzes system performance and generates optimization recommendations.
"""

import os
from typing import Dict, Any, List

from .optimizer_config import OptimizerConfig


class PerformanceOptimizer:
    """
    System performance optimization analyzer.
    
    Responsibilities:
    - Analyze job failure rates
    - Check processing times
    - Generate performance optimization recommendations
    """
    
    def __init__(self, config: OptimizerConfig):
        """
        Initialize performance optimizer.
        
        Args:
            config: Optimizer configuration
        """
        self.config = config
    
    def analyze(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze system performance and generate recommendations.
        
        Args:
            analysis_data: System analysis data
            
        Returns:
            List of performance optimization recommendations
        """
        recommendations = []
        performance_analysis = analysis_data.get('performance_analysis', {})
        
        # Check failure rates
        failure_rec = self._analyze_failure_rate(performance_analysis)
        if failure_rec:
            recommendations.append(failure_rec)
        
        # Check processing times
        processing_rec = self._analyze_processing_time(performance_analysis)
        if processing_rec:
            recommendations.append(processing_rec)
        
        return recommendations
    
    def _analyze_failure_rate(
        self,
        performance_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze job failure rate.
        
        Args:
            performance_analysis: Performance analysis data
            
        Returns:
            Failure rate recommendation or None
        """
        job_stats = performance_analysis.get('job_statistics', {})
        failure_rate = job_stats.get('failure_rate', 0)
        
        if failure_rate <= self.config.high_failure_rate:
            return None
        
        current_retries = int(os.getenv('MAP_PRO_JOB_RETRY_ATTEMPTS', '3'))
        current_timeout = int(os.getenv('MAP_PRO_JOB_TIMEOUT_MINUTES', '60'))
        
        new_retries = min(
            self.config.max_retry_attempts,
            current_retries + self.config.retry_increment
        )
        new_timeout = min(
            self.config.max_timeout_minutes,
            current_timeout + self.config.timeout_increment_minutes
        )
        
        return {
            'type': 'performance_optimization',
            'priority': 'high',
            'priority_score': 85,
            'title': 'High Job Failure Rate',
            'description': f'System failure rate is {failure_rate*100:.1f}%',
            'recommendations': [
                'Review error logs for common failure patterns',
                'Increase retry attempts for transient failures',
                'Check for resource constraints',
                'Review timeout configurations'
            ],
            'auto_applicable': True,
            'env_changes': {
                'MAP_PRO_JOB_RETRY_ATTEMPTS': new_retries,
                'MAP_PRO_JOB_TIMEOUT_MINUTES': new_timeout
            }
        }
    
    def _analyze_processing_time(
        self,
        performance_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze processing time.
        
        Args:
            performance_analysis: Performance analysis data
            
        Returns:
            Processing time recommendation or None
        """
        processing_stats = performance_analysis.get('processing_statistics', {})
        avg_processing_time = processing_stats.get('average_processing_time', 0)
        
        if avg_processing_time <= self.config.slow_processing_threshold_seconds:
            return None
        
        return {
            'type': 'performance_optimization',
            'priority': 'medium',
            'priority_score': 65,
            'title': 'Slow Average Processing Time',
            'description': (
                f'Average job processing time is '
                f'{avg_processing_time/60:.1f} minutes'
            ),
            'recommendations': [
                'Profile slow operations to identify bottlenecks',
                'Consider parallel processing optimizations',
                'Review database query performance',
                'Optimize file I/O operations'
            ],
            'auto_applicable': False
        }