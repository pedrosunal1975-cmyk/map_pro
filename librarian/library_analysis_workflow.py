# File: /map_pro/engines/librarian/library_analysis_workflow.py

"""
Library Analysis Workflow Orchestrator
=======================================

Orchestrates the complete library dependency analysis workflow by
coordinating validation, scanning, availability checking, and downloads.

Responsibilities:
- Execute multi-step analysis workflow
- Coordinate component interactions
- Handle workflow errors with proper classification
- Delegate report generation to specialized component

Related Files:
- library_dependency_analyzer.py: Main analyzer orchestrator
- library_workflow_reporter.py: Report generation and recommendations
- dependency_analysis_validator.py: Filing validation
- library_dependency_scanner.py: Requirement scanning
- library_availability_checker.py: Library operations
"""

import traceback
from typing import Dict, Any, List, Set, Optional

from core.system_logger import get_logger
from .library_workflow_reporter import LibraryWorkflowReporter
from .scanner_models import ScanResult

logger = get_logger(__name__, 'engine')


class WorkflowStepNames:
    """Constants for workflow step names."""
    VALIDATE_FILING = 'validate_filing'
    SCAN_REQUIREMENTS = 'scan_requirements'
    CHECK_AVAILABILITY = 'check_availability'
    DOWNLOAD_LIBRARIES = 'download_libraries'
    GENERATE_REPORT = 'generate_report'


class MinimumRequirements:
    """Constants for minimum requirements and thresholds."""
    MIN_LIBRARIES_FOR_SUCCESS = 1


class LibraryAnalysisWorkflow:
    """
    Orchestrates the complete library dependency analysis workflow.
    
    This class coordinates all steps of the analysis process, from initial
    validation through library downloads, delegating report generation to
    a specialized reporter component.
    """
    
    def __init__(
        self,
        validator,
        scanner,
        availability_checker,
        logger
    ):
        """
        Initialize workflow orchestrator with dependencies.
        
        Args:
            validator: DependencyAnalysisValidator instance for filing validation
            scanner: LibraryDependencyScanner instance for requirement scanning
            availability_checker: LibraryAvailabilityChecker for library operations
            logger: Logger instance for workflow logging
        """
        self.validator = validator
        self.scanner = scanner
        self.availability_checker = availability_checker
        self.logger = logger
        
        # Initialize report generator
        self.reporter = LibraryWorkflowReporter(logger=logger)
    
    async def execute_analysis_workflow(
        self,
        filing_id: str,
        market_type: str
    ) -> Dict[str, Any]:
        """
        Execute the complete dependency analysis workflow.
        
        Workflow Steps:
        1. Validate filing exists and has required data
        2. Scan filing for namespace and library requirements
        3. Check availability of required libraries
        4. Download missing libraries (if possible)
        5. Generate comprehensive analysis report
        6. Determine job success status
        
        Args:
            filing_id: Filing universal ID to analyze
            market_type: Market type for library selection
            
        Returns:
            Dictionary with complete analysis results containing:
                - success (bool): Whether analysis succeeded
                - analysis_report (dict): Detailed analysis report
                - filing_universal_id (str): Filing ID analyzed
                - namespaces_detected (list): Detected namespaces
                - libraries_required (list): Required library names
                - libraries_ready (bool): All libraries available
                - manual_downloads_needed (list): Manual downloads required
                - error (str): Error message if failed
        """
        try:
            # Step 1: Validate filing
            filing_info = await self._validate_filing(filing_id)
            if not filing_info['valid']:
                return {
                    'success': False,
                    'error': filing_info['error'],
                    'filing_universal_id': filing_id
                }
            
            facts_json_path = filing_info.get('facts_json_path')
            
            # Step 2: Scan filing requirements
            scan_result = await self._scan_filing_requirements(
                filing_id=filing_id,
                market_type=market_type,
                facts_json_path=facts_json_path
            )
            
            # FIXED: Convert ScanResult dataclass to dict if needed
            if isinstance(scan_result, ScanResult):
                scan_result = scan_result.to_dict()
            
            if not scan_result.get('success', False):
                return {
                    'success': False,
                    'error': scan_result.get('error', 'Unknown scan error'),
                    'filing_universal_id': filing_id
                }
            
            all_namespaces = scan_result.get('namespaces', set())
            required_libraries = scan_result.get('required_libraries', [])
            
            self.logger.info(
                f"Detected {len(all_namespaces)} namespaces, "
                f"{len(required_libraries)} libraries required"
            )
            
            # Step 3: Check library availability
            availability_status = await self._check_library_availability(
                required_libraries
            )
            
            # Step 4: Download missing libraries
            download_results = await self._download_missing_libraries(
                missing_libraries=availability_status['missing_libraries'],
                market_type=market_type
            )
            
            # Step 5: Generate analysis report (delegated to reporter)
            analysis_report = self.reporter.generate_analysis_report(
                namespaces=all_namespaces,
                required_libraries=required_libraries,
                availability_status=availability_status,
                download_results=download_results
            )
            
            # Step 6: Determine job success
            success = self._determine_job_success(analysis_report)
            
            # Step 7: Create final result
            return self._create_workflow_result(
                success=success,
                analysis_report=analysis_report,
                filing_id=filing_id,
                namespaces=all_namespaces,
                required_libraries=required_libraries
            )
            
        except Exception as exception:
            return self._handle_workflow_error(exception, filing_id)
    
    async def _validate_filing(self, filing_id: str) -> Dict[str, Any]:
        """
        Validate filing exists and has required data for analysis.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Dictionary with validation result containing:
                - valid (bool): Whether validation passed
                - error (str): Error message if validation failed
                - facts_json_path (str): Path to facts JSON if valid
        """
        self.logger.info(f"Step 1: Validating filing {filing_id}")
        
        try:
            filing_info = await self.validator.validate_filing(filing_id)
            
            if filing_info['valid']:
                self.logger.info("Filing validation passed")
            else:
                self.logger.warning(
                    f"Filing validation failed: {filing_info.get('error')}"
                )
            
            return filing_info
            
        except Exception as exception:
            self.logger.error(f"Filing validation error: {exception}")
            return {
                'valid': False,
                'error': f"Validation error: {str(exception)}"
            }
    
    async def _scan_filing_requirements(
        self,
        filing_id: str,
        market_type: str,
        facts_json_path: Optional[str]
    ) -> Dict[str, Any]:
        """
        Scan filing for namespace and library requirements.
        
        Args:
            filing_id: Filing universal ID
            market_type: Market type for library selection
            facts_json_path: Path to facts.json file
            
        Returns:
            Dictionary with scan results containing:
                - success (bool): Whether scan succeeded
                - namespaces (set): Set of detected namespaces
                - required_libraries (list): List of required library configs
                - error (str): Error message if scan failed
        """
        self.logger.info(f"Step 2: Scanning filing requirements")
        
        try:
            scan_result = await self.scanner.scan_filing_requirements(
                filing_id, market_type, facts_json_path
            )
            
            # FIXED: Handle both ScanResult dataclass and dict returns
            if isinstance(scan_result, ScanResult):
                result_dict = scan_result.to_dict()
                if result_dict.get('success', False):
                    self.logger.info("Filing scan completed successfully")
                else:
                    self.logger.warning(
                        f"Filing scan failed: {result_dict.get('error')}"
                    )
                return result_dict
            elif isinstance(scan_result, dict):
                if scan_result.get('success', False):
                    self.logger.info("Filing scan completed successfully")
                else:
                    self.logger.warning(
                        f"Filing scan failed: {scan_result.get('error')}"
                    )
                return scan_result
            else:
                # Unexpected type
                self.logger.error(
                    f"Unexpected scan result type: {type(scan_result)}"
                )
                return {
                    'success': False,
                    'error': f"Unexpected scan result type: {type(scan_result)}",
                    'namespaces': set(),
                    'required_libraries': []
                }
            
        except Exception as exception:
            self.logger.error(f"Filing scan error: {exception}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f"Scan error: {str(exception)}",
                'namespaces': set(),
                'required_libraries': []
            }
    
    async def _check_library_availability(
        self,
        required_libraries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check availability status of required libraries.
        
        Args:
            required_libraries: List of required library configurations
            
        Returns:
            Dictionary with availability status containing:
                - available_count (int): Number of available libraries
                - missing_libraries (list): List of missing library configs
        """
        self.logger.info(f"Step 3: Checking library availability")
        
        availability_status = await self.availability_checker.check_library_availability(
            required_libraries
        )
        
        self.logger.info(
            f"Library availability: {availability_status['available_count']} available, "
            f"{len(availability_status['missing_libraries'])} missing"
        )
        
        return availability_status
    
    async def _download_missing_libraries(
        self,
        missing_libraries: List[Dict[str, Any]],
        market_type: str
    ) -> Dict[str, Any]:
        """
        Attempt to download missing libraries.
        
        Args:
            missing_libraries: List of missing library configurations
            market_type: Market type for library selection
            
        Returns:
            Dictionary with download results containing:
                - downloaded_count (int): Number of successfully downloaded libraries
                - failed_count (int): Number of failed downloads
                - manual_required (list): Libraries requiring manual download
                - download_details (list): Detailed results for each library
        """
        self.logger.info(f"Step 4: Downloading missing libraries")
        
        if not missing_libraries:
            self.logger.info("No missing libraries to download")
            return {
                'downloaded_count': 0,
                'failed_count': 0,
                'manual_required': [],
                'download_details': []
            }
        
        download_results = await self.availability_checker.ensure_required_libraries(
            missing_libraries,
            market_type
        )
        
        self.logger.info(
            f"Download results: {download_results['downloaded_count']} downloaded, "
            f"{download_results['failed_count']} failed, "
            f"{len(download_results['manual_required'])} require manual action"
        )
        
        return download_results
    
    def _determine_job_success(self, analysis_report: Dict[str, Any]) -> bool:
        """
        Determine if job should be marked as successful.
        
        Job is considered successful if at least one library is available
        (either pre-existing or successfully downloaded).
        
        Args:
            analysis_report: Complete analysis report from reporter
            
        Returns:
            True if job succeeded, False otherwise
        """
        available_count = analysis_report['available_count']
        downloaded_count = analysis_report['downloaded_count']
        total_available = available_count + downloaded_count
        
        success = total_available >= MinimumRequirements.MIN_LIBRARIES_FOR_SUCCESS
        
        self.logger.info(
            f"Step 6: Job success determination - "
            f"{available_count} available + {downloaded_count} downloaded = "
            f"{total_available} (threshold: {MinimumRequirements.MIN_LIBRARIES_FOR_SUCCESS})"
        )
        self.logger.info(
            f"Job analysis complete - Success: {success}, "
            f"Libraries ready: {analysis_report['libraries_ready']}"
        )
        
        return success
    
    def _create_workflow_result(
        self,
        success: bool,
        analysis_report: Dict[str, Any],
        filing_id: str,
        namespaces: Set[str],
        required_libraries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create standardized workflow result dictionary.
        
        Args:
            success: Whether analysis succeeded
            analysis_report: Complete analysis report from reporter
            filing_id: Filing universal ID
            namespaces: Set of detected namespaces
            required_libraries: List of required library configurations
            
        Returns:
            Standardized result dictionary containing:
                - success (bool): Analysis success status
                - analysis_report (dict): Full analysis report
                - filing_universal_id (str): Filing ID
                - namespaces_detected (list): List of namespaces
                - libraries_required (list): List of library names
                - libraries_ready (bool): All libraries available
                - manual_downloads_needed (list): Manual downloads required
        """
        result = {
            'success': success,
            'analysis_report': analysis_report,
            'filing_universal_id': filing_id,
            'namespaces_detected': list(namespaces),
            'libraries_required': [
                lib.get('taxonomy_name', 'Unknown') 
                for lib in required_libraries
            ],
            'libraries_ready': analysis_report['libraries_ready'],
            'manual_downloads_needed': analysis_report['manual_downloads']
        }
        
        self.logger.info(
            f"Step 7: Workflow result created - Success: {success}"
        )
        
        return result
    
    def _handle_workflow_error(
        self,
        exception: Exception,
        filing_id: str
    ) -> Dict[str, Any]:
        """
        Handle errors during workflow execution.
        
        Args:
            exception: Exception that occurred
            filing_id: Filing ID being analyzed
            
        Returns:
            Dictionary with error information containing:
                - success (bool): False
                - error (str): Error message
                - filing_universal_id (str): Filing ID
        """
        error_message = str(exception)
        
        self.logger.error(
            f"Workflow execution failed for filing {filing_id}: {error_message}"
        )
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'success': False,
            'error': f"Workflow error: {error_message}",
            'filing_universal_id': filing_id
        }


__all__ = [
    'LibraryAnalysisWorkflow',
    'WorkflowStepNames',
    'MinimumRequirements'
]