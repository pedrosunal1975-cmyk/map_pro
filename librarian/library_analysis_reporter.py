# File: /map_pro/engines/librarian/library_analysis_reporter.py

"""
Library Analysis Reporter
==========================

Manages statistics collection and reporting for library dependency analysis.

Responsibilities:
- Track analysis statistics
- Generate comprehensive reports
- Aggregate cache metrics
- Provide monitoring data

Related Files:
- library_dependency_analyzer.py: Main analyzer orchestrator
- dependency_analysis_cache.py: Cache statistics
"""

from typing import Dict, Any
from datetime import datetime, timezone

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class StatisticsKeys:
    """Constants for statistics dictionary keys."""
    FILINGS_ANALYZED = 'filings_analyzed'
    NAMESPACES_DETECTED = 'namespaces_detected'
    LIBRARIES_REQUIRED = 'libraries_required'
    LIBRARIES_AVAILABLE = 'libraries_available'
    LIBRARIES_DOWNLOADED = 'libraries_downloaded'
    MANUAL_DOWNLOADS_NEEDED = 'manual_downloads_needed'
    TOTAL_ANALYSIS_TIME = 'total_analysis_time_seconds'
    AVERAGE_NAMESPACES_PER_FILING = 'average_namespaces_per_filing'
    AVERAGE_LIBRARIES_PER_FILING = 'average_libraries_per_filing'
    SUCCESS_RATE = 'success_rate_percentage'
    LAST_UPDATED = 'last_updated'


class StatisticsDefaults:
    """Default values for statistics tracking."""
    INITIAL_COUNT = 0
    INITIAL_TIME = 0.0
    MIN_FILINGS_FOR_AVERAGE = 1


class LibraryAnalysisReporter:
    """
    Manages statistics and reporting for library dependency analysis.
    
    This class maintains running totals of analysis operations and provides
    comprehensive statistics for monitoring and debugging purposes.
    """
    
    def __init__(self, cache, logger):
        """
        Initialize reporter with dependencies.
        
        Args:
            cache: DependencyAnalysisCache instance for cache statistics
            logger: Logger instance for reporting operations
        """
        self.cache = cache
        self.logger = logger
        
        # Initialize statistics tracking
        self.stats = self._initialize_statistics()
    
    def _initialize_statistics(self) -> Dict[str, Any]:
        """
        Initialize statistics dictionary with default values.
        
        Returns:
            Dictionary with initialized statistics counters
        """
        return {
            StatisticsKeys.FILINGS_ANALYZED: StatisticsDefaults.INITIAL_COUNT,
            StatisticsKeys.NAMESPACES_DETECTED: StatisticsDefaults.INITIAL_COUNT,
            StatisticsKeys.LIBRARIES_REQUIRED: StatisticsDefaults.INITIAL_COUNT,
            StatisticsKeys.LIBRARIES_AVAILABLE: StatisticsDefaults.INITIAL_COUNT,
            StatisticsKeys.LIBRARIES_DOWNLOADED: StatisticsDefaults.INITIAL_COUNT,
            StatisticsKeys.MANUAL_DOWNLOADS_NEEDED: StatisticsDefaults.INITIAL_COUNT,
            StatisticsKeys.TOTAL_ANALYSIS_TIME: StatisticsDefaults.INITIAL_TIME
        }
    
    def update_analysis_statistics(
        self,
        namespaces_count: int,
        libraries_count: int,
        analysis_time: float = 0.0
    ) -> None:
        """
        Update statistics after completing an analysis.
        
        Args:
            namespaces_count: Number of namespaces detected
            libraries_count: Number of libraries required
            analysis_time: Time taken for analysis in seconds
        """
        self.stats[StatisticsKeys.FILINGS_ANALYZED] += 1
        self.stats[StatisticsKeys.NAMESPACES_DETECTED] += namespaces_count
        self.stats[StatisticsKeys.LIBRARIES_REQUIRED] += libraries_count
        self.stats[StatisticsKeys.TOTAL_ANALYSIS_TIME] += analysis_time
        
        self.logger.debug(
            f"Statistics updated: {self.stats[StatisticsKeys.FILINGS_ANALYZED]} "
            f"filings analyzed, {namespaces_count} namespaces, "
            f"{libraries_count} libraries"
        )
    
    def update_library_statistics(
        self,
        available_count: int = 0,
        downloaded_count: int = 0,
        manual_count: int = 0
    ) -> None:
        """
        Update library-specific statistics.
        
        Args:
            available_count: Number of libraries already available
            downloaded_count: Number of libraries successfully downloaded
            manual_count: Number of libraries requiring manual download
        """
        self.stats[StatisticsKeys.LIBRARIES_AVAILABLE] += available_count
        self.stats[StatisticsKeys.LIBRARIES_DOWNLOADED] += downloaded_count
        self.stats[StatisticsKeys.MANUAL_DOWNLOADS_NEEDED] += manual_count
        
        self.logger.debug(
            f"Library statistics updated: {available_count} available, "
            f"{downloaded_count} downloaded, {manual_count} manual"
        )
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics including calculated metrics and cache data.
        
        Returns:
            Dictionary with all statistics including:
                - Raw counters (filings analyzed, namespaces detected, etc.)
                - Calculated metrics (averages, rates)
                - Cache statistics (hits, misses, size)
                - Timestamp of last update
        """
        stats = self.stats.copy()
        
        # Add calculated metrics
        stats.update(self._calculate_derived_metrics())
        
        # Add cache statistics
        cache_stats = self.cache.get_statistics()
        stats.update(cache_stats)
        
        # Add timestamp
        stats[StatisticsKeys.LAST_UPDATED] = datetime.now(timezone.utc).isoformat()
        
        return stats
    
    def _calculate_derived_metrics(self) -> Dict[str, float]:
        """
        Calculate derived metrics from raw statistics.
        
        Returns:
            Dictionary with calculated metrics
        """
        filings_analyzed = self.stats[StatisticsKeys.FILINGS_ANALYZED]
        
        if filings_analyzed < StatisticsDefaults.MIN_FILINGS_FOR_AVERAGE:
            return {
                StatisticsKeys.AVERAGE_NAMESPACES_PER_FILING: 0.0,
                StatisticsKeys.AVERAGE_LIBRARIES_PER_FILING: 0.0,
                StatisticsKeys.SUCCESS_RATE: 0.0
            }
        
        # Calculate averages
        avg_namespaces = (
            self.stats[StatisticsKeys.NAMESPACES_DETECTED] / filings_analyzed
        )
        avg_libraries = (
            self.stats[StatisticsKeys.LIBRARIES_REQUIRED] / filings_analyzed
        )
        
        # Calculate success rate (libraries available + downloaded / required)
        total_required = self.stats[StatisticsKeys.LIBRARIES_REQUIRED]
        total_obtained = (
            self.stats[StatisticsKeys.LIBRARIES_AVAILABLE] +
            self.stats[StatisticsKeys.LIBRARIES_DOWNLOADED]
        )
        
        success_rate = 0.0
        if total_required > 0:
            success_rate = (total_obtained / total_required) * 100.0
        
        return {
            StatisticsKeys.AVERAGE_NAMESPACES_PER_FILING: round(avg_namespaces, 2),
            StatisticsKeys.AVERAGE_LIBRARIES_PER_FILING: round(avg_libraries, 2),
            StatisticsKeys.SUCCESS_RATE: round(success_rate, 2)
        }
    
    def get_summary_report(self) -> str:
        """
        Generate human-readable summary report.
        
        Returns:
            Formatted string with summary statistics
        """
        stats = self.get_comprehensive_statistics()
        
        report_lines = [
            "=" * 60,
            "Library Dependency Analysis - Summary Report",
            "=" * 60,
            "",
            "Analysis Statistics:",
            f"  Filings Analyzed: {stats[StatisticsKeys.FILINGS_ANALYZED]}",
            f"  Namespaces Detected: {stats[StatisticsKeys.NAMESPACES_DETECTED]}",
            f"  Libraries Required: {stats[StatisticsKeys.LIBRARIES_REQUIRED]}",
            "",
            "Library Operations:",
            f"  Already Available: {stats[StatisticsKeys.LIBRARIES_AVAILABLE]}",
            f"  Successfully Downloaded: {stats[StatisticsKeys.LIBRARIES_DOWNLOADED]}",
            f"  Manual Downloads Needed: {stats[StatisticsKeys.MANUAL_DOWNLOADS_NEEDED]}",
            "",
            "Performance Metrics:",
            f"  Avg Namespaces/Filing: {stats[StatisticsKeys.AVERAGE_NAMESPACES_PER_FILING]}",
            f"  Avg Libraries/Filing: {stats[StatisticsKeys.AVERAGE_LIBRARIES_PER_FILING]}",
            f"  Library Success Rate: {stats[StatisticsKeys.SUCCESS_RATE]}%",
            "",
            "Cache Statistics:",
            f"  Cache Hits: {stats.get('cache_hits', 0)}",
            f"  Cache Misses: {stats.get('cache_misses', 0)}",
            f"  Cache Size: {stats.get('cache_size', 0)}",
            "",
            f"Last Updated: {stats[StatisticsKeys.LAST_UPDATED]}",
            "=" * 60
        ]
        
        return "\n".join(report_lines)
    
    def reset_statistics(self) -> None:
        """
        Reset all statistics to initial values.
        
        Warning: This will clear all accumulated statistics. Use with caution.
        """
        self.stats = self._initialize_statistics()
        self.logger.warning("Analysis statistics have been reset")
    
    def get_current_totals(self) -> Dict[str, int]:
        """
        Get current totals without calculated metrics.
        
        Returns:
            Dictionary with raw counter values only
        """
        return {
            StatisticsKeys.FILINGS_ANALYZED: self.stats[StatisticsKeys.FILINGS_ANALYZED],
            StatisticsKeys.NAMESPACES_DETECTED: self.stats[StatisticsKeys.NAMESPACES_DETECTED],
            StatisticsKeys.LIBRARIES_REQUIRED: self.stats[StatisticsKeys.LIBRARIES_REQUIRED],
            StatisticsKeys.LIBRARIES_AVAILABLE: self.stats[StatisticsKeys.LIBRARIES_AVAILABLE],
            StatisticsKeys.LIBRARIES_DOWNLOADED: self.stats[StatisticsKeys.LIBRARIES_DOWNLOADED],
            StatisticsKeys.MANUAL_DOWNLOADS_NEEDED: self.stats[StatisticsKeys.MANUAL_DOWNLOADS_NEEDED]
        }


__all__ = [
    'LibraryAnalysisReporter',
    'StatisticsKeys',
    'StatisticsDefaults'
]