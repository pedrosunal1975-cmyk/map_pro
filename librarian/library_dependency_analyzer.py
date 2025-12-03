# File: /map_pro/engines/librarian/library_dependency_analyzer.py

"""
Library Dependency Analyzer
============================

Main engine for analyzing filing requirements and ensuring taxonomy libraries
are available. Orchestrates the complete dependency analysis workflow.

Architecture: Part of librarian engine, triggered by workflow after parsing completion.
Integration: Uses map_pro system patterns for logging, database access, and job processing.

Responsibilities:
- Job processing coordination
- Workflow orchestration
- High-level dependency analysis coordination
- Result reporting and statistics aggregation

Delegates detailed work to:
- DependencyAnalysisValidator: Filing validation
- LibraryAvailabilityChecker: Library availability and downloads
- DependencyAnalysisCache: Result caching
- LibraryDependencyScanner: File scanning operations
- LibraryAnalysisWorkflow: Workflow execution
- LibraryAnalysisReporter: Report generation

Related Files:
- library_analysis_workflow.py: Workflow execution logic
- library_analysis_reporter.py: Report generation and statistics
- dependency_analysis_validator.py: Filing validation
- library_availability_checker.py: Library operations
- dependency_analysis_cache.py: Result caching
"""

import traceback
from typing import Dict, Any, List, Optional

from core.system_logger import get_logger
from engines.base.engine_base import BaseEngine
from shared.constants.job_constants import JobType
from shared.exceptions.custom_exceptions import EngineError

from .library_dependency_scanner import LibraryDependencyScanner
from .dependency_analysis_validator import DependencyAnalysisValidator
from .library_availability_checker import LibraryAvailabilityChecker
from .dependency_analysis_cache import DependencyAnalysisCache
from .library_analysis_workflow import LibraryAnalysisWorkflow
from .library_analysis_reporter import LibraryAnalysisReporter

logger = get_logger(__name__, 'engine')


class JobParameterKeys:
    """Constants for job parameter dictionary keys."""
    PARAMETERS = 'parameters'
    FILING_UNIVERSAL_ID = 'filing_universal_id'
    MARKET_TYPE = 'market_type'


class LibraryDependencyAnalyzer(BaseEngine):
    """
    Analyzes filing requirements and ensures taxonomy libraries are available.
    
    Workflow Integration:
    1. Triggered after PARSE_XBRL completion via job_workflow_manager
    2. Analyzes parsed facts and XBRL files for requirements  
    3. Ensures required libraries are available
    4. Reports status before MAP_FACTS stage begins
    
    Does NOT handle:
    - Detailed file scanning (LibraryDependencyScanner handles this)
    - Actual library downloads (LibraryCoordinator handles this)
    - Job queue management (job_orchestrator handles this)
    """
    
    def __init__(self):
        """Initialize library dependency analyzer with component modules."""
        super().__init__("library_dependency_analyzer")
        
        # Initialize library operations
        self._initialize_library_operations()
        
        # Initialize component modules
        self.validator = DependencyAnalysisValidator()
        self.availability_checker = LibraryAvailabilityChecker(
            self.library_operations
        )
        self.cache = DependencyAnalysisCache()
        self.dependency_scanner = LibraryDependencyScanner()
        
        # Initialize workflow executor and reporter
        self.workflow_executor = LibraryAnalysisWorkflow(
            validator=self.validator,
            scanner=self.dependency_scanner,
            availability_checker=self.availability_checker,
            logger=self.logger
        )
        
        self.reporter = LibraryAnalysisReporter(
            cache=self.cache,
            logger=self.logger
        )
        
        self.logger.info("Library dependency analyzer initialized")
    
    def _initialize_library_operations(self) -> None:
        """
        Initialize library operations components.
        
        Creates and configures the library operations coordinator with all
        necessary sub-components for taxonomy management.
        """
        from .library_operations import LibraryOperations
        from .taxonomy_downloader import TaxonomyDownloader
        from .library_organizer import LibraryOrganizer
        from .concept_indexer import ConceptIndexer
        from .validation_checker import ValidationChecker
        
        downloader = TaxonomyDownloader()
        organizer = LibraryOrganizer()
        indexer = ConceptIndexer()
        validator = ValidationChecker()
        
        self.library_operations = LibraryOperations(
            downloader, organizer, indexer, validator
        )
    
    def get_primary_database(self) -> str:
        """
        Return primary database name for this engine.
        
        Returns:
            Database name string ('library')
        """
        return 'library'
    
    def get_supported_job_types(self) -> List[str]:
        """
        Return list of job types this engine can process.
        
        Returns:
            List containing supported job type strings
        """
        return [JobType.ANALYZE_LIBRARY_DEPENDENCIES.value]
    
    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process library dependency analysis job.
        
        Args:
            job_data: Dictionary containing:
                - parameters.filing_universal_id: Filing UUID to analyze
                - parameters.market_type or market_type: Market type for library selection
                
        Returns:
            Dictionary with analysis results containing:
                - success (bool): Whether analysis succeeded
                - analysis_report (dict): Detailed analysis report
                - filing_universal_id (str): Filing ID analyzed
                - namespaces_detected (list): List of detected namespaces
                - libraries_required (list): List of required library names
                - libraries_ready (bool): Whether all libraries are available
                - manual_downloads_needed (list): Libraries requiring manual download
                - error (str): Error message if failed
        """
        # Extract and validate parameters
        filing_id, market_type = self._extract_job_parameters(job_data)
        
        if not filing_id:
            return {
                'success': False,
                'error': 'Missing filing_universal_id in job parameters'
            }
        
        # Check cache first for previously completed analysis
        cached_result = self.cache.get_cached_result(filing_id)
        if cached_result:
            self.logger.info(
                f"Returning cached result for filing {filing_id}"
            )
            return cached_result
        
        self.logger.info(
            f"Analyzing library dependencies for filing {filing_id}"
        )
        
        try:
            # Execute analysis workflow
            result = await self.workflow_executor.execute_analysis_workflow(
                filing_id=filing_id,
                market_type=market_type
            )
            
            # Cache successful results for future use
            if result['success']:
                self.cache.cache_result(filing_id, result)
                self.logger.info(
                    f"Cached successful analysis for filing {filing_id}"
                )
            
            return result
            
        except Exception as exception:
            return self._handle_analysis_error(exception, filing_id)
    
    def _extract_job_parameters(
        self, 
        job_data: Dict[str, Any]
    ) -> tuple[Optional[str], str]:
        """
        Extract and validate job parameters from job data.
        
        Args:
            job_data: Job data dictionary containing parameters
            
        Returns:
            Tuple of (filing_id, market_type) where:
                - filing_id: Filing universal ID (may be None if not provided)
                - market_type: Market type string (must be provided)
                
        Raises:
            EngineError: If market_type is not specified
        """
        parameters = job_data.get(JobParameterKeys.PARAMETERS, {})
        filing_id = parameters.get(JobParameterKeys.FILING_UNIVERSAL_ID)
        
        # FIXED: Check both parameters and job_data for market_type
        # Parameters takes precedence as it's set by library_analysis_stage
        market_type = parameters.get(JobParameterKeys.MARKET_TYPE) or job_data.get(JobParameterKeys.MARKET_TYPE)
        
        if not market_type:
            raise EngineError(
                "market_type must be specified in job_data or parameters. "
                "This should be set by the workflow coordinator based on the entity's market."
            )
        
        if filing_id:
            self.logger.debug(
                f"Extracted parameters - Filing ID: {filing_id}, "
                f"Market: {market_type}"
            )
        else:
            self.logger.warning("No filing_universal_id found in job parameters")
        
        return filing_id, market_type
    
    def _handle_analysis_error(
        self,
        exception: Exception,
        filing_id: str
    ) -> Dict[str, Any]:
        """
        Handle errors during analysis workflow execution.
        
        Args:
            exception: Exception that occurred
            filing_id: Filing ID being analyzed
            
        Returns:
            Dictionary with error information
        """
        error_message = str(exception)
        
        self.logger.error(
            f"Library dependency analysis failed for filing {filing_id}: "
            f"{error_message}"
        )
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'success': False,
            'error': error_message,
            'filing_universal_id': filing_id
        }
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive analysis statistics for monitoring and reporting.
        
        Returns:
            Dictionary with current statistics including:
                - filings_analyzed: Total filings processed
                - namespaces_detected: Total namespaces found
                - libraries_required: Total libraries needed
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
                - cache_size: Number of cached results
        """
        return self.reporter.get_comprehensive_statistics()


__all__ = ['LibraryDependencyAnalyzer']