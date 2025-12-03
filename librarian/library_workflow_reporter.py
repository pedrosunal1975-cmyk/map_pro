# File: /map_pro/engines/librarian/library_workflow_reporter.py

"""
Library Workflow Reporter
==========================

Generates comprehensive analysis reports and recommendations for library
dependency analysis workflows.

Responsibilities:
- Generate analysis reports with metrics
- Calculate completion percentages
- Generate user recommendations
- Provide actionable insights

Related Files:
- library_analysis_workflow.py: Main workflow orchestrator
- library_analysis_reporter.py: Statistics tracking and aggregation
"""

from typing import Dict, Any, List, Set
from datetime import datetime, timezone

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class PercentageConstants:
    """Constants for percentage calculations."""
    MULTIPLIER = 100
    MAX_PERCENTAGE = 100.0
    MIN_PERCENTAGE = 0.0


class ReportKeys:
    """Constants for report dictionary keys."""
    ANALYSIS_TIMESTAMP = 'analysis_timestamp'
    NAMESPACES_COUNT = 'namespaces_count'
    LIBRARIES_REQUIRED_COUNT = 'libraries_required_count'
    AVAILABLE_COUNT = 'available_count'
    DOWNLOADED_COUNT = 'downloaded_count'
    FAILED_COUNT = 'failed_count'
    MANUAL_DOWNLOADS = 'manual_downloads'
    LIBRARIES_READY = 'libraries_ready'
    COMPLETION_PERCENTAGE = 'completion_percentage'
    RECOMMENDATIONS = 'recommendations'


class DivisionSafety:
    """Constants for safe division operations."""
    MIN_DIVISOR = 1


class LibraryWorkflowReporter:
    """
    Generates analysis reports and recommendations for library workflows.
    
    This class is responsible for creating comprehensive reports about
    library availability, download results, and actionable recommendations
    for users.
    """
    
    def __init__(self, logger):
        """
        Initialize workflow reporter.
        
        Args:
            logger: Logger instance for report generation logging
        """
        self.logger = logger
    
    def generate_analysis_report(
        self,
        namespaces: Set[str],
        required_libraries: List[Dict[str, Any]],
        availability_status: Dict[str, Any],
        download_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report with metrics and recommendations.
        
        Args:
            namespaces: Set of detected namespaces
            required_libraries: List of required library configurations
            availability_status: Library availability status from checker
            download_results: Download attempt results from availability checker
            
        Returns:
            Dictionary with complete analysis report containing:
                - analysis_timestamp (str): ISO timestamp of report generation
                - namespaces_count (int): Number of namespaces detected
                - libraries_required_count (int): Total libraries required
                - available_count (int): Libraries already available
                - downloaded_count (int): Libraries successfully downloaded
                - failed_count (int): Failed download attempts
                - manual_downloads (list): Libraries requiring manual action
                - libraries_ready (bool): All required libraries available
                - completion_percentage (float): Percentage of libraries obtained
                - recommendations (list): User action recommendations (if incomplete)
        """
        self.logger.info("Step 5: Generating analysis report")
        
        total_required = len(required_libraries)
        available_after_downloads = (
            availability_status['available_count'] + 
            download_results['downloaded_count']
        )
        
        libraries_ready = available_after_downloads >= total_required
        
        completion_percentage = self._calculate_completion_percentage(
            available_after_downloads, total_required
        )
        
        report = {
            ReportKeys.ANALYSIS_TIMESTAMP: datetime.now(timezone.utc).isoformat(),
            ReportKeys.NAMESPACES_COUNT: len(namespaces),
            ReportKeys.LIBRARIES_REQUIRED_COUNT: total_required,
            ReportKeys.AVAILABLE_COUNT: availability_status['available_count'],
            ReportKeys.DOWNLOADED_COUNT: download_results['downloaded_count'],
            ReportKeys.FAILED_COUNT: download_results['failed_count'],
            ReportKeys.MANUAL_DOWNLOADS: download_results['manual_required'],
            ReportKeys.LIBRARIES_READY: libraries_ready,
            ReportKeys.COMPLETION_PERCENTAGE: completion_percentage
        }
        
        # Add recommendations if not all libraries are ready
        if not libraries_ready:
            report[ReportKeys.RECOMMENDATIONS] = self._generate_recommendations(
                download_results
            )
        
        self.logger.info(
            f"Analysis report generated: {completion_percentage:.1f}% complete, "
            f"{total_required} required, {available_after_downloads} obtained"
        )
        
        return report
    
    def _calculate_completion_percentage(
        self, 
        available_after_downloads: int, 
        total_required: int
    ) -> float:
        """
        Calculate library availability completion percentage.
        
        Handles edge case of zero required libraries by returning 100%.
        Ensures result is within valid percentage range (0.0-100.0).
        
        Args:
            available_after_downloads: Number of libraries now available
            total_required: Total number of required libraries
            
        Returns:
            Completion percentage as float (0.0-100.0)
        """
        if total_required == 0:
            return PercentageConstants.MAX_PERCENTAGE
        
        # Calculate percentage with safe division
        percentage = (
            available_after_downloads / 
            max(total_required, DivisionSafety.MIN_DIVISOR) * 
            PercentageConstants.MULTIPLIER
        )
        
        # Ensure percentage is within valid range
        return max(
            PercentageConstants.MIN_PERCENTAGE,
            min(percentage, PercentageConstants.MAX_PERCENTAGE)
        )
    
    def _generate_recommendations(
        self, 
        download_results: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable user recommendations based on download results.
        
        Provides specific guidance for:
        - Libraries requiring manual download (with credentials)
        - Failed downloads that should be retried
        - Confirmation when all libraries are available
        
        Args:
            download_results: Results from download attempts containing:
                - manual_required (list): Libraries needing manual download
                - download_details (list): Detailed results per library
            
        Returns:
            List of recommendation strings for user action
        """
        recommendations = []
        
        # Check for manual downloads needed
        manual_required = download_results.get('manual_required', [])
        if manual_required:
            recommendations.append(
                f"Manual download required for {len(manual_required)} "
                f"taxonomies (credentials needed)"
            )
            
            # Add specific details for each manual download
            for lib in manual_required:
                taxonomy_name = lib.get('taxonomy_name', 'Unknown')
                version = lib.get('version', 'Unknown')
                url = lib.get('url', 'No URL')
                recommendations.append(
                    f"  - {taxonomy_name}-{version}: {url}"
                )
        
        # Check for failed downloads that can be retried
        failed_downloads = self._extract_retryable_failures(download_results)
        
        if failed_downloads:
            recommendations.append(
                f"Retry required for {len(failed_downloads)} failed downloads"
            )
        
        # Add confirmation message if no issues found
        if not recommendations:
            recommendations.append(
                "All libraries should be available for mapping"
            )
        
        return recommendations
    
    def _extract_retryable_failures(
        self,
        download_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract download failures that can be retried (not manual downloads).
        
        Args:
            download_results: Download results containing download_details
            
        Returns:
            List of failed downloads that don't require manual intervention
        """
        download_details = download_results.get('download_details', [])
        
        # Filter for failures that aren't manual downloads
        failed_downloads = [
            detail for detail in download_details
            if not detail.get('success', False) 
            and not detail.get('requires_manual', False)
        ]
        
        return failed_downloads
    
    def format_summary_text(self, report: Dict[str, Any]) -> str:
        """
        Format analysis report as human-readable summary text.
        
        Args:
            report: Analysis report dictionary
            
        Returns:
            Formatted multi-line summary string
        """
        lines = [
            "Library Analysis Summary:",
            f"  Namespaces Detected: {report[ReportKeys.NAMESPACES_COUNT]}",
            f"  Libraries Required: {report[ReportKeys.LIBRARIES_REQUIRED_COUNT]}",
            f"  Already Available: {report[ReportKeys.AVAILABLE_COUNT]}",
            f"  Successfully Downloaded: {report[ReportKeys.DOWNLOADED_COUNT]}",
            f"  Failed Downloads: {report[ReportKeys.FAILED_COUNT]}",
            f"  Completion: {report[ReportKeys.COMPLETION_PERCENTAGE]:.1f}%",
            f"  All Libraries Ready: {report[ReportKeys.LIBRARIES_READY]}"
        ]
        
        # Add recommendations if present
        if ReportKeys.RECOMMENDATIONS in report:
            lines.append("")
            lines.append("Recommendations:")
            for recommendation in report[ReportKeys.RECOMMENDATIONS]:
                lines.append(f"  {recommendation}")
        
        return "\n".join(lines)


__all__ = [
    'LibraryWorkflowReporter',
    'PercentageConstants',
    'ReportKeys',
    'DivisionSafety'
]