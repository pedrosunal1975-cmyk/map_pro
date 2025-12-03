"""
Performance Recommendation Engine
=================================

File: tools/monitoring/performance_recommendation_engine.py

Generates optimization recommendations based on analysis.
"""

from typing import Dict, Any, List

from .performance_config import PerformanceConfig


class PerformanceRecommendationEngine:
    """
    Generate performance recommendations.
    
    Responsibilities:
    - Analyze performance data
    - Generate actionable recommendations
    - Prioritize issues by severity
    """
    
    def __init__(self, config: PerformanceConfig):
        """
        Initialize recommendation engine.
        
        Args:
            config: Performance configuration
        """
        self.config = config
    
    def generate(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate optimization recommendations based on analysis.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check bottlenecks
        recommendations.extend(self._recommend_for_bottlenecks(analysis))
        
        # Check failure rates
        recommendations.extend(self._recommend_for_failure_rates(analysis))
        
        # Check engine performance
        recommendations.extend(self._recommend_for_engine_performance(analysis))
        
        # Check trends
        recommendations.extend(self._recommend_for_trends(analysis))
        
        if not recommendations:
            recommendations.append(
                "System performance is within normal parameters"
            )
        
        return recommendations
    
    def _recommend_for_bottlenecks(
        self,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations for bottlenecks.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        bottlenecks = analysis.get('bottlenecks', [])
        
        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'queue_bottleneck':
                recommendations.append(
                    f"Consider scaling up {bottleneck['job_type']} "
                    f"processing capacity ({bottleneck['queued_jobs']} jobs queued)"
                )
            elif bottleneck['type'] == 'slow_processing':
                recommendations.append(
                    f"Investigate slow {bottleneck['job_type']} processing "
                    f"(average {bottleneck['average_time']}s)"
                )
        
        return recommendations
    
    def _recommend_for_failure_rates(
        self,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations for failure rates.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        job_stats = analysis.get('job_statistics', {})
        failure_rate = job_stats.get('failure_rate', 0)
        
        if failure_rate > self.config.high_failure_rate:
            recommendations.append(
                f"High failure rate detected ({failure_rate*100:.1f}%). "
                "Review error logs and retry mechanisms"
            )
        
        return recommendations
    
    def _recommend_for_engine_performance(
        self,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations for engine performance.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        engine_perf = analysis.get('engine_performance', {})
        
        for engine_name, engine_data in engine_perf.items():
            overall = engine_data.get('overall', {})
            failure_rate = overall.get('average_failure_rate', 0)
            
            if failure_rate > self.config.engine_failure_threshold:
                recommendations.append(
                    f"Engine '{engine_name}' has high failure rate "
                    f"({failure_rate*100:.1f}%). Review engine logs"
                )
        
        return recommendations
    
    def _recommend_for_trends(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations for trends.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        trends = analysis.get('trends', {})
        
        if trends.get('failure_rate_trend') == 'increasing':
            recommendations.append(
                "Failure rate is increasing over time. "
                "Investigate recent changes and error patterns"
            )
        
        return recommendations