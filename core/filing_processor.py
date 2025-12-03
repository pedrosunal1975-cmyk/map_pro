# File: /map_pro/core/filing_processor.py

"""
Map Pro Filing Processor
========================

Processes individual filings through all workflow stages.
Handles download, extract, parse, library analysis, and map stages with job management.

This module has been refactored to maintain <400 line file limit and reduce complexity.
The actual stage processing logic is delegated to specialized processors in filing_stages/.

Architecture:
- Single filing processing responsibility
- Job waiting utility for stages
- Stage-specific error handling
- Market-agnostic job management
"""

from typing import Dict, Any

from .system_logger import get_logger
from .interactive_interface import (
    display_workflow_progress,
    display_filing_progress
)
from .filing_stages import (
    DownloadStageProcessor,
    ExtractionStageProcessor,
    ParsingStageProcessor,
    MappingStageProcessor,
    OutputVerifier,
    JobWaiter
)
# Import library analysis stage (will be added to filing_stages module)
from core.filing_stages.library_analysis_stage import LibraryAnalysisStageProcessor

logger = get_logger(__name__, 'core')

# Default timeout values
DEFAULT_POLL_INTERVAL = 2
DEFAULT_MAX_WAIT_PER_STAGE = 600


class FilingProcessor:
    """
    Process individual filings through all workflow stages.
    
    This class coordinates the processing of a single filing through
    download, extraction, parsing, library analysis, and mapping stages. 
    It delegates the actual work to specialized stage processors.
    
    Responsibilities:
    - Orchestrate stage execution in correct order
    - Initialize stage processors and utilities
    - Provide unified API for filing processing
    - Handle display updates
    
    Does NOT handle:
    - Workflow orchestration (WorkflowCoordinator handles this)
    - Result aggregation (WorkflowResultsAggregator handles this)
    - Market-specific logic (market plugins handle this)
    """
    
    def __init__(self):
        """
        Initialize filing processor with stage processors.
        
        Creates specialized processors for each stage and utility classes
        for job waiting and output verification.
        """
        logger.info("Initializing filing processor")
        
        # Initialize utilities
        self.job_waiter = JobWaiter(
            poll_interval=DEFAULT_POLL_INTERVAL,
            max_wait_per_stage=DEFAULT_MAX_WAIT_PER_STAGE
        )
        self.output_verifier = OutputVerifier()
        
        # Initialize stage processors
        self.download_processor = DownloadStageProcessor(self.job_waiter)
        self.extraction_processor = ExtractionStageProcessor(self.job_waiter)
        self.parsing_processor = ParsingStageProcessor(
            self.job_waiter,
            self.output_verifier
        )
        self.library_analysis_processor = LibraryAnalysisStageProcessor(self.job_waiter)
        self.mapping_processor = MappingStageProcessor(
            self.job_waiter,
            self.output_verifier
        )
        
        logger.info("Filing processor initialized")
    
    async def process_single_filing(
        self,
        filing_id: str,
        market_type: str,
        filing_number: int,
        total_filings: int,
        filing_info: Dict[str, Any],
        workflow_status: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process single filing through all stages (market-agnostic).
        
        Stages executed in order:
        1. Download (checks prerequisites, creates own job)
        2. Extract (checks prerequisites, creates own job)
        3. Parse (checks prerequisites, creates own job)
        4. Map (checks prerequisites, creates own job)
        
        Args:
            filing_id: Filing UUID
            market_type: Target market
            filing_number: Current filing number (for display)
            total_filings: Total number of filings (for display)
            filing_info: Filing information dict
            workflow_status: Workflow status dict for display updates
            
        Returns:
            Processing results for this filing
        """
        # Initialize results
        results = self._initialize_results(filing_id)
        
        try:
            # Display progress
            display_filing_progress(filing_number, total_filings, filing_info)
            
            # Execute stages in sequence
            if not await self._execute_download_stage(
                filing_id, filing_info, market_type, workflow_status, results
            ):
                return results
            
            if not await self._execute_extraction_stage(
                filing_id, workflow_status, results
            ):
                return results
            
            if not await self._execute_parsing_stage(
                filing_id, workflow_status, results
            ):
                return results
            
            if not await self._execute_library_analysis_stage(
                filing_id, market_type, workflow_status, results
            ):
                return results
            
            if not await self._execute_mapping_stage(
                filing_id, workflow_status, results
            ):
                return results
            
            # All stages completed successfully
            results['success'] = True
            return results
            
        except Exception as e:
            logger.error(f"Filing processing failed: {e}", exc_info=True)
            results['error'] = str(e)
            return results
    
    def _initialize_results(self, filing_id: str) -> Dict[str, Any]:
        """
        Initialize results dictionary for filing processing.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Empty results dictionary with default values
        """
        return {
            'filing_id': filing_id,
            'success': False,
            'stages_completed': [],
            'facts_parsed': 0,
            'facts_mapped': 0,
            'total_facts': 0,
            'unmapped_facts': 0,
            'success_rate': 0.0
        }
    
    async def _execute_download_stage(
        self,
        filing_id: str,
        filing_info: Dict[str, Any],
        market_type: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Execute download stage.
        
        Args:
            filing_id: Filing UUID
            filing_info: Filing information
            market_type: Market type
            workflow_status: Workflow status dictionary
            results: Results dictionary
            
        Returns:
            True if successful, False otherwise
        """
        display_workflow_progress(workflow_status)
        
        return await self.download_processor.process(
            filing_id,
            filing_info,
            market_type,
            workflow_status,
            results
        )
    
    async def _execute_extraction_stage(
        self,
        filing_id: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Execute extraction stage.
        
        Args:
            filing_id: Filing UUID
            workflow_status: Workflow status dictionary
            results: Results dictionary
            
        Returns:
            True if successful, False otherwise
        """
        display_workflow_progress(workflow_status)
        
        return await self.extraction_processor.process(
            filing_id,
            workflow_status,
            results
        )
    
    async def _execute_parsing_stage(
        self,
        filing_id: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Execute parsing stage.
        
        Args:
            filing_id: Filing UUID
            workflow_status: Workflow status dictionary
            results: Results dictionary
            
        Returns:
            True if successful, False otherwise
        """
        display_workflow_progress(workflow_status)
        
        return await self.parsing_processor.process(
            filing_id,
            workflow_status,
            results
        )
    
    async def _execute_library_analysis_stage(
        self,
        filing_id: str,
        market_type: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Execute library analysis stage.
        
        Args:
            filing_id: Filing UUID
            market_type: Market type
            workflow_status: Workflow status dictionary
            results: Results dictionary
            
        Returns:
            True if successful, False otherwise
        """
        display_workflow_progress(workflow_status)
        
        return await self.library_analysis_processor.process(
            filing_id,
            market_type,
            workflow_status,
            results
        )
    
    async def _execute_mapping_stage(
        self,
        filing_id: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Execute mapping stage.
        
        Args:
            filing_id: Filing UUID
            workflow_status: Workflow status dictionary
            results: Results dictionary
            
        Returns:
            True if successful, False otherwise
        """
        display_workflow_progress(workflow_status)
        
        return await self.mapping_processor.process(
            filing_id,
            workflow_status,
            results
        )
    
    async def wait_for_job_completion(
        self,
        job_id: str,
        stage_name: str
    ):
        """
        Wait for job to complete (delegation method for backward compatibility).
        
        This method delegates to job_waiter.wait_for_job_completion() to maintain
        backward compatibility with WorkflowCoordinator and other modules that
        call filing_processor.wait_for_job_completion().
        
        Args:
            job_id: Job ID to monitor
            stage_name: Stage name for logging
            
        Returns:
            Job result data or None if failed/timeout
        """
        return await self.job_waiter.wait_for_job_completion(job_id, stage_name)
    
    def configure_timeouts(
        self,
        poll_interval: int = None,
        max_wait_per_stage: int = None
    ) -> None:
        """
        Configure timeout settings.
        
        Args:
            poll_interval: Seconds between status checks
            max_wait_per_stage: Maximum seconds to wait per stage
        """
        if poll_interval is not None:
            self.job_waiter.poll_interval = poll_interval
        if max_wait_per_stage is not None:
            self.job_waiter.max_wait_per_stage = max_wait_per_stage
        
        logger.info("Filing processor timeouts configured")


__all__ = ['FilingProcessor']