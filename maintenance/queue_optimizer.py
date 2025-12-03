"""
Queue Optimizer
==============

File: tools/maintenance/queue_optimizer.py

Analyzes job queue performance and generates optimization recommendations.
"""

import os
from typing import Dict, Any, List

from .optimizer_config import OptimizerConfig


class QueueOptimizer:
    """
    Job queue optimization analyzer.
    
    Responsibilities:
    - Analyze queue depth
    - Check for old jobs
    - Generate queue optimization recommendations
    """
    
    def __init__(self, config: OptimizerConfig):
        """
        Initialize queue optimizer.
        
        Args:
            config: Optimizer configuration
        """
        self.config = config
    
    def analyze(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze job queue and generate recommendations.
        
        Args:
            analysis_data: System analysis data
            
        Returns:
            List of queue optimization recommendations
        """
        recommendations = []
        queue_metrics = analysis_data.get('queue_metrics', {})
        
        # Check queue depth
        depth_rec = self._analyze_queue_depth(queue_metrics)
        if depth_rec:
            recommendations.append(depth_rec)
        
        # Check oldest job age
        age_rec = self._analyze_oldest_job(queue_metrics)
        if age_rec:
            recommendations.append(age_rec)
        
        return recommendations
    
    def _analyze_queue_depth(
        self,
        queue_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze queue depth.
        
        Args:
            queue_metrics: Queue metrics data
            
        Returns:
            Queue depth recommendation or None
        """
        total_queued = queue_metrics.get('total_queued_jobs', 0)
        
        if total_queued <= self.config.high_queue_threshold:
            return None
        
        current_concurrent = int(
            os.getenv('MAP_PRO_MAX_CONCURRENT_JOBS', '10')
        )
        new_concurrent = min(
            self.config.max_concurrent_jobs,
            current_concurrent + self.config.concurrent_jobs_increment
        )
        
        return {
            'type': 'queue_optimization',
            'priority': 'high',
            'priority_score': 80,
            'title': 'High Job Queue Depth',
            'description': f'{total_queued} jobs currently queued',
            'recommendations': [
                'Increase concurrent job processing',
                'Review for stuck or failing jobs',
                'Consider scaling processing capacity',
                'Optimize job processing times'
            ],
            'auto_applicable': True,
            'env_changes': {
                'MAP_PRO_MAX_CONCURRENT_JOBS': new_concurrent
            }
        }
    
    def _analyze_oldest_job(
        self,
        queue_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze oldest job in queue.
        
        Args:
            queue_metrics: Queue metrics data
            
        Returns:
            Old job recommendation or None
        """
        oldest_job_age = queue_metrics.get('oldest_job_age_seconds', 0)
        
        if oldest_job_age <= self.config.old_job_threshold_seconds:
            return None
        
        hours = oldest_job_age / 3600
        
        return {
            'type': 'queue_optimization',
            'priority': 'medium',
            'priority_score': 70,
            'title': 'Old Jobs in Queue',
            'description': f'Oldest queued job is {hours:.1f} hours old',
            'recommendations': [
                'Investigate stuck job processing',
                'Review engine health status',
                'Consider manual job retry or cancellation'
            ],
            'auto_applicable': False
        }