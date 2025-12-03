"""
Map Pro Performance Analyzer
============================

Performance analysis and bottleneck detection for all engines.
Analyzes job processing times, identifies bottlenecks, and provides optimization recommendations.

Save location: tools/monitoring/performance_analyzer.py
"""

from typing import Dict, Any, List
from datetime import datetime, timezone

from core.system_logger import get_logger
from core.alert_manager import create_alert

from .performance_config import PerformanceConfig
from .engine_performance_analyzer import EnginePerformanceAnalyzer
from .job_statistics_calculator import JobStatisticsCalculator
from .bottleneck_detector import BottleneckDetector
from .performance_trend_analyzer import PerformanceTrendAnalyzer
from .performance_recommendation_engine import PerformanceRecommendationEngine
from .performance_reporter import PerformanceReporter

logger = get_logger(__name__, 'monitoring')


class PerformanceAnalyzer:
    """
    Performance analysis and bottleneck detection.
    
    Coordinates performance analysis across different aspects of the system.
    
    Responsibilities:
    - Coordinate performance analysis workflow
    - Delegate to specialized analyzers
    - Track performance history
    - Generate alerts for critical issues
    
    Does NOT handle:
    - Metrics collection (system_monitor handles this)
    - Performance remediation (engines handle their own optimization)
    - Alert delivery (alert_generator handles this)
    """
    
    def __init__(self, config: PerformanceConfig = None):
        """
        Initialize performance analyzer.
        
        Args:
            config: Performance configuration (optional)
        """
        self.config = config or PerformanceConfig()
        self.logger = get_logger(__name__, 'monitoring')
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
        
        # Initialize specialized components
        self.engine_analyzer = EnginePerformanceAnalyzer(self.config)
        self.stats_calculator = JobStatisticsCalculator(self.config)
        self.bottleneck_detector = BottleneckDetector(self.config)
        self.trend_analyzer = PerformanceTrendAnalyzer(
            self.performance_history,
            self.config
        )
        self.recommendation_engine = PerformanceRecommendationEngine(self.config)
        self.reporter = PerformanceReporter()
        
        self.logger.info("Performance analyzer initialized")
    
    async def analyze_system_performance(self) -> Dict[str, Any]:
        """
        Perform comprehensive system performance analysis.
        
        Returns:
            Dictionary with complete performance analysis
        """
        analysis_time = datetime.now(timezone.utc)
        
        self.logger.info("Starting performance analysis...")
        
        # Gather analysis components
        analysis = {
            'timestamp': analysis_time.isoformat(),
            'window_hours': self.config.analysis_window_hours,
            'engine_performance': await self.engine_analyzer.analyze(),
            'job_statistics': await self.stats_calculator.calculate(),
            'bottlenecks': await self.bottleneck_detector.detect(),
            'trends': await self.trend_analyzer.analyze(),
            'recommendations': []
        }
        
        # Generate recommendations
        analysis['recommendations'] = self.recommendation_engine.generate(analysis)
        
        # Add to history
        self._add_to_history(analysis)
        
        # Check for alerts
        await self._check_performance_alerts(analysis)
        
        self.logger.info("Performance analysis completed")
        return analysis
    
    async def generate_performance_report(self) -> str:
        """
        Generate comprehensive performance report.
        
        Returns:
            Formatted performance report string
        """
        analysis = await self.analyze_system_performance()
        return self.reporter.generate_report(analysis)
    
    async def get_engine_comparison(self) -> Dict[str, Any]:
        """
        Compare performance across all engines.
        
        Returns:
            Dictionary with comparative engine metrics
        """
        analysis = await self.analyze_system_performance()
        return self.reporter.generate_engine_comparison(
            analysis.get('engine_performance', {})
        )
    
    async def _check_performance_alerts(self, analysis: Dict[str, Any]) -> None:
        """
        Check for performance issues that warrant alerts.
        
        Args:
            analysis: Performance analysis results
        """
        try:
            await self._check_failure_rate_alert(analysis)
            await self._check_bottleneck_alert(analysis)
        except Exception as e:
            self.logger.error(f"Failed to check performance alerts: {e}")
    
    async def _check_failure_rate_alert(self, analysis: Dict[str, Any]) -> None:
        """
        Check for high failure rate alert.
        
        Args:
            analysis: Performance analysis results
        """
        job_stats = analysis.get('job_statistics', {})
        failure_rate = job_stats.get('failure_rate', 0)
        
        if failure_rate > self.config.critical_failure_rate:
            await create_alert(
                alert_type='performance',
                severity='critical',
                title='High Job Failure Rate',
                message=f"System-wide failure rate is {failure_rate*100:.1f}%",
                details={'analysis': job_stats}
            )
    
    async def _check_bottleneck_alert(self, analysis: Dict[str, Any]) -> None:
        """
        Check for severe bottleneck alert.
        
        Args:
            analysis: Performance analysis results
        """
        bottlenecks = analysis.get('bottlenecks', [])
        critical_bottlenecks = [
            b for b in bottlenecks if b.get('severity') == 'high'
        ]
        
        if critical_bottlenecks:
            await create_alert(
                alert_type='performance',
                severity='warning',
                title='Performance Bottlenecks Detected',
                message=f"Found {len(critical_bottlenecks)} critical bottlenecks",
                details={'bottlenecks': critical_bottlenecks}
            )
    
    def _add_to_history(self, analysis: Dict[str, Any]) -> None:
        """
        Add analysis to history buffer.
        
        Args:
            analysis: Performance analysis to store
        """
        self.performance_history.append(analysis)
        
        # Maintain history size limit
        if len(self.performance_history) > self.config.max_history_size:
            self.performance_history.pop(0)