# File: /map_pro/core/workflow_coordinator.py

"""
Map Pro Workflow Coordinator
============================

Pure market-agnostic workflow orchestration for complete filing workflows.
Contains ZERO market-specific code, terminology, or logic.

Architecture:
- 100% market-agnostic workflow orchestration  
- Generic stage coordination
- Progress tracking and display
- No market-specific terminology, logic, or assumptions

Delegates to:
- WorkflowStageExecutor: Stage execution
- WorkflowStatusTracker: Status tracking and display
- WorkflowResultsAggregator: Results aggregation
"""

from typing import Dict, Any, Optional

from .system_logger import get_logger
from .filing_processor import FilingProcessor
from .workflow_results_aggregator import WorkflowResultsAggregator
from .workflow_stage_executor import WorkflowStageExecutor
from .workflow_status_tracker import WorkflowStatusTracker
from .interactive_interface import display_error

logger = get_logger(__name__, 'core')

# Configuration constants
DEFAULT_MAX_WAIT_PER_STAGE = 600  # 10 minutes


class WorkflowCoordinator:
    """
    Coordinate complete workflow execution (100% market-agnostic).
    
    Responsibilities:
    - Orchestrate multi-stage workflows for ANY market
    - Coordinate search and filing discovery
    - Track overall progress
    - Delegate to specialized components
    - Aggregate final results
    
    Does NOT handle:
    - Stage execution details (WorkflowStageExecutor handles this)
    - Status tracking details (WorkflowStatusTracker handles this)
    - Result aggregation (WorkflowResultsAggregator handles this)
    - Market-specific logic (market plugins handle this)
    
    ZERO market-specific code, terminology, or assumptions.
    """
    
    def __init__(self):
        """Initialize workflow coordinator and components."""
        self.filing_processor = FilingProcessor()
        self.results_aggregator = WorkflowResultsAggregator()
        
        # Initialize specialized components
        self.stage_executor = WorkflowStageExecutor(self.filing_processor)
        self.status_tracker = WorkflowStatusTracker()
        
        self.max_wait_per_stage = DEFAULT_MAX_WAIT_PER_STAGE
        
        logger.info("Workflow coordinator initialized")
    
    async def execute_complete_workflow(
            self,
            market_type: str,
            company_identifier: str,
            filing_type: str,
            num_instances: int
        ) -> Dict[str, Any]:
            """
            Execute complete workflow from search to mapping (100% market-agnostic).
            
            Works for ANY market (SEC, FCA, ESMA, etc.) without market-specific logic.
            
            Args:
                market_type: Target market identifier
                company_identifier: Market-agnostic company identifier
                filing_type: Market-specific filing form type
                num_instances: Number of historical filings to process
                
            Returns:
                Results dictionary with success status and details
            """
            logger.info(
                f"Starting workflow: {market_type.upper()} {company_identifier} "
                f"{filing_type} x{num_instances}"
            )
            
            self.status_tracker.start_workflow()
            
            try:
                result = await self._execute_workflow_stages(
                    market_type,
                    company_identifier,
                    filing_type,
                    num_instances
                )
                
                return result
                
            except KeyboardInterrupt:
                logger.warning("Workflow interrupted by user")
                return self._build_interrupted_result()
                
            except Exception as e:
                logger.error(f"Workflow failed: {e}", exc_info=True)
                # FIX: Returns a list containing the error dictionary to satisfy the UI.
                return [self._build_error_result(str(e))]
    
    async def _execute_workflow_stages(
        self,
        market_type: str,
        company_identifier: str,
        filing_type: str,
        num_instances: int
    ) -> Dict[str, Any]:
        """
        Execute all workflow stages.
        
        Args:
            market_type: Target market
            company_identifier: Company identifier
            filing_type: Filing type
            num_instances: Number of instances
            
        Returns:
            Workflow results dictionary
        """
        # Stage 1: Search for entity
        entity_id = await self._execute_entity_search(
            market_type,
            company_identifier,
            filing_type,
            num_instances
        )
        
        if not entity_id:
            return self._build_search_failed_result(
                company_identifier,
                market_type
            )
        
        # Stage 2: Find filings
        filing_ids = await self._execute_filing_discovery(
            entity_id,
            market_type,
            filing_type,
            num_instances
        )
        
        if not filing_ids:
            return self._build_no_filings_result(
                company_identifier,
                filing_type
            )
        
        # Stage 3-7: Process filings
        all_results = await self._execute_filing_processing(
            filing_ids,
            market_type
        )
        
        # Aggregate and return final results
        return self._aggregate_final_results(
            entity_id,
            filing_ids,
            all_results
        )
    
    async def _execute_entity_search(
        self,
        market_type: str,
        company_identifier: str,
        filing_type: str,
        num_instances: int
    ) -> Optional[str]:
        """
        Execute entity search stage.
        
        Args:
            market_type: Target market
            company_identifier: Company identifier
            filing_type: Filing type
            num_instances: Number of instances
            
        Returns:
            Entity ID or None if failed
        """
        logger.info("Stage 1: Searching for entity")
        self.status_tracker.mark_stage_running('search')
        
        search_result = await self.stage_executor.execute_search_stage(
            market_type,
            company_identifier,
            filing_type,
            num_instances
        )
        
        if not search_result or not search_result.get('entity_id'):
            self.status_tracker.mark_stage_failed('search')
            return None
        
        entity_id = search_result['entity_id']
        self.status_tracker.mark_stage_completed('search')
        
        # Display entity information
        entity_info = self.results_aggregator.get_entity_info(entity_id)
        self.status_tracker.display_entity_info(entity_info)
        
        return entity_id
    
    async def _execute_filing_discovery(
        self,
        entity_id: str,
        market_type: str,
        filing_type: str,
        num_instances: int
    ) -> list[str]:
        """
        Execute filing discovery stage.
        
        Args:
            entity_id: Entity ID
            market_type: Target market
            filing_type: Filing type
            num_instances: Number of instances
            
        Returns:
            List of filing IDs
        """
        logger.info("Stage 2: Finding filings")
        
        filing_ids = await self.stage_executor.execute_filing_search_stage(
            entity_id,
            market_type,
            filing_type,
            num_instances
        )
        
        if filing_ids:
            self.status_tracker.mark_stage_completed('find_filings')
            self.status_tracker.display_filings_info(
                len(filing_ids),
                filing_type
            )
        
        return filing_ids
    
    async def _execute_filing_processing(
        self,
        filing_ids: list[str],
        market_type: str
    ) -> list[Dict[str, Any]]:
        """
        Execute filing processing stages.
        
        Args:
            filing_ids: List of filing IDs
            market_type: Target market
            
        Returns:
            List of processing results
        """
        logger.info("Stage 3-7: Processing filings")
        
        workflow_status = self.status_tracker.get_status()
        
        all_results = await self.stage_executor.execute_filing_processing_stage(
            filing_ids,
            market_type,
            workflow_status
        )
        
        # Mark processing stages as completed
        self.status_tracker.mark_processing_stages_completed(all_results)
        
        # Log results for debugging
        self._log_processing_results(all_results)
        
        return all_results
    
    def _log_processing_results(
        self,
        all_results: list[Dict[str, Any]]
    ) -> None:
        """
        Log processing results for debugging.
        
        Args:
            all_results: List of processing results
        """
        logger.info(f"About to aggregate {len(all_results)} results")
        logger.info(
            f"Stages completed: {self.status_tracker.get_stages_completed()}"
        )
        
        for idx, result in enumerate(all_results):
            logger.debug(
                f"Result {idx+1}: success={result.get('success')}, "
                f"facts_mapped={result.get('facts_mapped', 'NOT FOUND')}, "
                f"facts_parsed={result.get('facts_parsed', 'NOT FOUND')}"
            )
    
    def _aggregate_final_results(
        self,
        entity_id: str,
        filing_ids: list[str],
        all_results: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate final workflow results.
        
        Args:
            entity_id: Entity ID
            filing_ids: List of filing IDs
            all_results: List of processing results
            
        Returns:
            Final aggregated results
        """
        logger.info("Aggregating final results")
        
        # Get entity info
        entity_info = self.results_aggregator.get_entity_info(entity_id)
        
        # Get workflow duration
        duration = self.status_tracker.get_duration()
        
        # Get completed stages
        stages_completed = self.status_tracker.get_stages_completed()
        
        # Aggregate results
        final_results = self.results_aggregator.aggregate_workflow_results(
            entity_id=entity_id,
            entity_info=entity_info,
            filing_ids=filing_ids,
            all_results=all_results,
            duration_seconds=duration,
            stages_completed=stages_completed
        )
        
        # Log final results
        self._log_final_results(final_results)
        
        return final_results
    
    def _log_final_results(self, final_results: Dict[str, Any]) -> None:
        """
        Log final results for debugging.
        
        Args:
            final_results: Final aggregated results
        """
        logger.info(f"Final results keys: {list(final_results.keys())}")
        logger.debug(
            f"Has filing_details? {'filing_details' in final_results}"
        )
        logger.debug(
            f"Has processing_summary? {'processing_summary' in final_results}"
        )
        
        if 'processing_summary' in final_results:
            logger.debug(
                f"processing_summary type: "
                f"{type(final_results['processing_summary'])}"
            )
    
    def _build_search_failed_result(
        self,
        company_identifier: str,
        market_type: str
    ) -> Dict[str, Any]:
        """
        Build result for failed entity search.
        
        Args:
            company_identifier: Company identifier
            market_type: Target market
            
        Returns:
            Error result dictionary
        """
        return {
            'success': False,
            'error': (
                f'Company not found: {company_identifier} '
                f'in {market_type.upper()}'
            ),
            'stages_completed': self.status_tracker.get_stages_completed()
        }
    
    def _build_no_filings_result(
        self,
        company_identifier: str,
        filing_type: str
    ) -> Dict[str, Any]:
        """
        Build result for no filings found.
        
        Args:
            company_identifier: Company identifier
            filing_type: Filing type
            
        Returns:
            Error result dictionary
        """
        return {
            'success': False,
            'error': (
                f'No {filing_type} filings found for {company_identifier}'
            ),
            'stages_completed': self.status_tracker.get_stages_completed()
        }
    
    def _build_interrupted_result(self) -> Dict[str, Any]:
        """
        Build result for interrupted workflow.
        
        Returns:
            Interrupted result dictionary
        """
        return {
            'success': False,
            'error': 'Workflow interrupted by user (Ctrl+C)',
            'stages_completed': self.status_tracker.get_stages_completed()
        }
    
    def _build_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Build result for workflow error.
        
        Args:
            error_message: Error message
            
        Returns:
            Error result dictionary
        """
        return {
            'success': False,
            'error': error_message,
            'stages_completed': self.status_tracker.get_stages_completed()
        }
    
    def configure_timeouts(self, max_wait_per_stage: int = None) -> None:
        """
        Configure workflow timeouts.
        
        Args:
            max_wait_per_stage: Maximum seconds to wait per stage
        """
        if max_wait_per_stage is not None:
            self.max_wait_per_stage = max_wait_per_stage
            
            # Propagate to filing processor
            self.filing_processor.configure_timeouts(
                max_wait_per_stage=max_wait_per_stage
            )
        
        logger.info(
            f"Workflow timeouts configured: "
            f"max_stage={self.max_wait_per_stage}s"
        )


__all__ = ['WorkflowCoordinator']