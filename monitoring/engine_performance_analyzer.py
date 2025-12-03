"""
Engine Performance Analyzer
===========================

File: tools/monitoring/engine_performance_analyzer.py

Analyzes performance of individual engines.
"""

from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from statistics import mean

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from shared.constants.job_constants import JobType, JobStatus

from .performance_config import PerformanceConfig
from .job_metrics_calculator import JobMetricsCalculator

logger = get_logger(__name__, 'monitoring')


class EnginePerformanceAnalyzer:
    """
    Analyze performance of each engine.
    
    Responsibilities:
    - Query engine-specific job metrics
    - Calculate performance statistics per engine
    - Aggregate overall engine performance
    """
    
    # Librarian excluded as it doesn't process standard workflow jobs
    ENGINE_JOB_TYPES = {
        'searcher': [JobType.SEARCH_ENTITY, JobType.FIND_FILINGS],
        'downloader': [JobType.DOWNLOAD_FILING],
        'extractor': [JobType.EXTRACT_FILES],
        'parser': [JobType.PARSE_XBRL],
        'mapper': [JobType.MAP_FACTS]
    }
    
    def __init__(self, config: PerformanceConfig):
        """
        Initialize engine performance analyzer.
        
        Args:
            config: Performance configuration
        """
        self.config = config
        self.metrics_calculator = JobMetricsCalculator(config)
        self.logger = get_logger(__name__, 'monitoring')
    
    async def analyze(self) -> Dict[str, Any]:
        """
        Analyze performance of all engines.
        
        Returns:
            Dictionary mapping engine names to performance data
        """
        engine_performance = {}
        
        for engine_name, job_types in self.ENGINE_JOB_TYPES.items():
            engine_perf = await self._analyze_engine(engine_name, job_types)
            engine_performance[engine_name] = engine_perf
        
        return engine_performance
    
    async def _analyze_engine(
        self,
        engine_name: str,
        job_types: list
    ) -> Dict[str, Any]:
        """
        Analyze performance of a single engine.
        
        Args:
            engine_name: Name of the engine
            job_types: List of job types for this engine
            
        Returns:
            Engine performance data
        """
        engine_perf = {
            'job_types': [jt.value for jt in job_types],
            'metrics': {}
        }
        
        # Get metrics for each job type
        for job_type in job_types:
            type_metrics = await self.metrics_calculator.get_job_type_metrics(
                job_type
            )
            engine_perf['metrics'][job_type.value] = type_metrics
        
        # Calculate overall engine performance
        engine_perf['overall'] = self._calculate_overall_performance(
            engine_perf['metrics']
        )
        
        return engine_perf
    
    def _calculate_overall_performance(
        self,
        metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate overall engine performance from job type metrics.
        
        Args:
            metrics: Dictionary of job type metrics
            
        Returns:
            Overall performance metrics
        """
        all_avg_times = []
        all_failure_rates = []
        total_completed = 0
        
        for job_metrics in metrics.values():
            if job_metrics.get('average_time') is not None:
                all_avg_times.append(job_metrics['average_time'])
            if job_metrics.get('failure_rate') is not None:
                all_failure_rates.append(job_metrics['failure_rate'])
            total_completed += job_metrics.get('jobs_completed', 0)
        
        return {
            'average_processing_time': (
                round(mean(all_avg_times), 2) if all_avg_times else None
            ),
            'average_failure_rate': (
                round(mean(all_failure_rates), 4) if all_failure_rates else 0.0
            ),
            'total_jobs_completed': total_completed
        }