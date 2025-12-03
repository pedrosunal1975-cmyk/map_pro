"""
Performance Trend Analyzer
==========================

File: tools/monitoring/performance_trend_analyzer.py

Analyzes performance trends over time.
"""

from typing import Dict, Any, List
from statistics import mean

from core.system_logger import get_logger

from .performance_config import PerformanceConfig

logger = get_logger(__name__, 'monitoring')


class PerformanceTrendAnalyzer:
    """
    Analyze performance trends over time.
    
    Responsibilities:
    - Compare recent vs historical performance
    - Identify trending patterns
    - Detect performance degradation
    """
    
    def __init__(
        self,
        performance_history: List[Dict[str, Any]],
        config: PerformanceConfig
    ):
        """
        Initialize trend analyzer.
        
        Args:
            performance_history: Reference to performance history list
            config: Performance configuration
        """
        self.performance_history = performance_history
        self.config = config
        self.logger = get_logger(__name__, 'monitoring')
    
    async def analyze(self) -> Dict[str, Any]:
        """
        Analyze performance trends over time.
        
        Returns:
            Dictionary with trend analysis
        """
        if len(self.performance_history) < self.config.min_history_for_trends:
            return {'status': 'insufficient_data'}
        
        try:
            trends = self._initialize_trends()
            
            # Get recent and older analyses
            recent, older = self._split_history()
            
            if older:
                # Analyze failure rate trend
                trends['failure_rate_trend'] = self._analyze_failure_rate_trend(
                    recent,
                    older
                )
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Failed to analyze trends: {e}")
            return {'error': str(e)}
    
    def _initialize_trends(self) -> Dict[str, str]:
        """
        Initialize trend dictionary with default values.
        
        Returns:
            Dictionary with default trend values
        """
        return {
            'processing_time_trend': 'stable',
            'failure_rate_trend': 'stable',
            'queue_depth_trend': 'stable'
        }
    
    def _split_history(self) -> tuple:
        """
        Split history into recent and older analyses.
        
        Returns:
            Tuple of (recent_analyses, older_analyses)
        """
        comparison_size = self.config.trend_comparison_size
        
        recent = self.performance_history[-comparison_size:]
        older = (
            self.performance_history[:-comparison_size]
            if len(self.performance_history) > comparison_size
            else []
        )
        
        return recent, older
    
    def _analyze_failure_rate_trend(
        self,
        recent: List[Dict[str, Any]],
        older: List[Dict[str, Any]]
    ) -> str:
        """
        Analyze failure rate trend.
        
        Args:
            recent: Recent analyses
            older: Older analyses
            
        Returns:
            Trend status ('increasing', 'decreasing', or 'stable')
        """
        recent_rates = self._extract_failure_rates(recent)
        older_rates = self._extract_failure_rates(older)
        
        if not recent_rates or not older_rates:
            return 'stable'
        
        recent_avg = mean(recent_rates)
        older_avg = mean(older_rates)
        
        return self._determine_trend(recent_avg, older_avg)
    
    def _extract_failure_rates(
        self,
        analyses: List[Dict[str, Any]]
    ) -> List[float]:
        """
        Extract failure rates from analyses.
        
        Args:
            analyses: List of performance analyses
            
        Returns:
            List of failure rates
        """
        rates = []
        
        for analysis in analyses:
            job_stats = analysis.get('job_statistics', {})
            failure_rate = job_stats.get('failure_rate')
            
            if failure_rate is not None:
                rates.append(failure_rate)
        
        return rates
    
    def _determine_trend(self, recent_avg: float, older_avg: float) -> str:
        """
        Determine trend direction from averages.
        
        Args:
            recent_avg: Recent average value
            older_avg: Older average value
            
        Returns:
            Trend status ('increasing', 'decreasing', or 'stable')
        """
        if recent_avg > older_avg * self.config.trend_increase_threshold:
            return 'increasing'
        elif recent_avg < older_avg * self.config.trend_decrease_threshold:
            return 'decreasing'
        else:
            return 'stable'