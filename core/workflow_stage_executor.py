# File: /map_pro/core/workflow_stage_executor.py

"""
Workflow Stage Executor
=======================

Executes individual workflow stages in a market-agnostic manner.
Handles search, filing discovery, and filing processing coordination.

100% market-agnostic - works with any market type.
"""

import asyncio
from typing import Dict, Any, List, Optional

from .system_logger import get_logger
from .filing_processor import FilingProcessor
from .job_orchestrator import job_orchestrator
from shared.constants.job_constants import JobType

logger = get_logger(__name__, 'core')


class WorkflowStageExecutor:
    """
    Executes individual workflow stages.
    
    Responsibilities:
    - Entity search execution
    - Filing discovery execution
    - Individual filing processing coordination
    - Job creation and polling
    
    100% market-agnostic implementation.
    """
    
    def __init__(self, filing_processor: FilingProcessor):
        """
        Initialize stage executor.
        
        Args:
            filing_processor: Filing processor for individual filings
        """
        self.filing_processor = filing_processor
        logger.debug("Workflow stage executor initialized")
    
    async def execute_search_stage(
        self,
        market_type: str,
        company_identifier: str,
        filing_type: str,
        num_instances: int
    ) -> Optional[Dict[str, Any]]:
        """
        Execute entity search stage.
        
        Args:
            market_type: Target market identifier
            company_identifier: Company identifier (market-agnostic)
            filing_type: Filing type to search for
            num_instances: Number of instances to process
            
        Returns:
            Search result with entity_id or None if failed
        """
        try:
            # Create search job
            job_id = self._create_search_job(
                market_type,
                company_identifier,
                filing_type,
                num_instances
            )

            logger.info(f"{'='*70}")
            logger.info(f"[STAGE] SEARCH - STARTING for {company_identifier} ({market_type})")
            logger.info(f"{'='*70}")
            logger.info(f"Created search job: {job_id}")
            
            # Wait for completion
            result = await self.filing_processor.wait_for_job_completion(
                job_id,
                'search'
            )
            
            # Log stage completion
            if result and result.get('success'):
                entity_id = result.get('entity_id', 'unknown')
                logger.info(f"{'='*70}")
                logger.info(f"[STAGE] SEARCH - COMPLETED (entity_id: {entity_id})")
                logger.info(f"{'='*70}")
            else:
                logger.info(f"{'='*70}")
                logger.error(f"[STAGE] SEARCH - FAILED")
                logger.info(f"{'='*70}")
            
            return result
            
        except Exception as e:
            logger.info(f"{'='*70}")
            logger.error(f"[STAGE] SEARCH - ERROR: {e}")
            logger.info(f"{'='*70}")
            logger.error(f"Search stage error details", exc_info=True)
            return None
    
    def _create_search_job(
        self,
        market_type: str,
        company_identifier: str,
        filing_type: str,
        num_instances: int
    ) -> str:
        """
        Create entity search job.
        
        Args:
            market_type: Target market
            company_identifier: Company identifier
            filing_type: Filing type
            num_instances: Number of instances
            
        Returns:
            Job ID
        """
        return job_orchestrator.create_job(
            job_type=JobType.SEARCH_ENTITY,
            entity_id=None,
            market_type=market_type,
            parameters={
                'company_identifier': company_identifier,
                'market_type': market_type,
                'search_criteria': {
                    'filing_types': [filing_type],
                    'limit': num_instances
                }
            }
        )
    
    async def execute_filing_search_stage(
        self,
        entity_id: str,
        market_type: str,
        filing_type: str,
        num_instances: int
    ) -> List[str]:
        """
        Execute filing search stage.
        
        Args:
            entity_id: Entity UUID
            market_type: Target market
            filing_type: Filing type to search for
            num_instances: Number of filings to find
            
        Returns:
            List of filing IDs
        """
        try:
            # Create filing search job
            job_id = self._create_filing_search_job(
                entity_id,
                market_type,
                filing_type,
                num_instances
            )
            
            logger.info(f"{'='*70}")
            logger.info(f"[STAGE] FILING_SEARCH - STARTING for entity {entity_id}")
            logger.info(f"{'='*70}")
            logger.info(f"Created filing search job: {job_id}")
            
            # Wait for completion
            result = await self.filing_processor.wait_for_job_completion(
                job_id,
                'filing_search'
            )
            
            if result and result.get('success'):
                filing_ids = result.get('filing_ids', [])
                logger.info(f"{'='*70}")
                logger.info(f"[STAGE] FILING_SEARCH - COMPLETED ({len(filing_ids)} filings found)")
                logger.info(f"{'='*70}")
                return filing_ids
            
            return []
            
        except Exception as e:
            logger.info(f"{'='*70}")
            logger.error(f"[STAGE] FILING_SEARCH - FAILED (no results)")
            logger.info(f"{'='*70}")
            return []
    
    def _create_filing_search_job(
        self,
        entity_id: str,
        market_type: str,
        filing_type: str,
        num_instances: int
    ) -> str:
        """
        Create filing search job.
        
        Args:
            entity_id: Entity UUID
            market_type: Target market
            filing_type: Filing type
            num_instances: Number of instances
            
        Returns:
            Job ID
        """
        return job_orchestrator.create_job(
            job_type=JobType.FIND_FILINGS,
            entity_id=entity_id,
            market_type=market_type,
            parameters={
                'entity_id': entity_id,
                'search_criteria': {
                    'filing_types': [filing_type],
                    'limit': num_instances
                }
            }
        )
    

    async def execute_filing_processing_stage(
            self,
            filing_ids: List[str],
            market_type: str,
            workflow_status: Dict[str, str]
        ) -> List[Dict[str, Any]]:
            """
            Execute filing processing stage for multiple filings.
            
            Args:
                filing_ids: List of filing IDs to process
                market_type: Target market
                workflow_status: Current workflow status dict
                
            Returns:
                List of processing results
            """
            logger.info(f"\n{'='*70}")
            logger.info(f"[STAGE] FILING_PROCESSING - STARTING ({len(filing_ids)} filings)")
            logger.info(f"{'='*70}\n")
            
            all_results = []
            
            for i, filing_id in enumerate(filing_ids):
                try:
                    # Attempt to process the single filing
                    result = await self._process_single_filing(
                        filing_id,
                        market_type,
                        i + 1,
                        len(filing_ids),
                        workflow_status
                    )
                
                except Exception as e:
                    # On catastrophic failure, log error and create a safe dictionary result.
                    logger.error(f"Catastrophic error processing filing {filing_id}: {e}", exc_info=True)
                    result = {
                        'success': False,
                        'filing_id': filing_id,
                        'error': f"UNEXPECTED EXECUTION STAGE ERROR: {str(e)}"
                    }
                
                # Append the result (guaranteed to be a dict)
                all_results.append(result)

                # Check result status using .get()
                if not result.get('success'):
                    logger.warning(f"Filing {i+1} failed, continuing with others")
            
            # Log stage completion summary
            successful_count = sum(1 for r in all_results if r.get('success'))
            logger.info(f"\n{'='*70}")
            logger.info(f"[STAGE] FILING_PROCESSING - COMPLETED ({successful_count}/{len(all_results)} successful)")
            logger.info(f"{'='*70}\n")
            
            return all_results
    
    async def _process_single_filing(
        self,
        filing_id: str,
        market_type: str,
        filing_number: int,
        total_filings: int,
        workflow_status: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process a single filing.
        
        Args:
            filing_id: Filing ID to process
            market_type: Target market
            filing_number: Current filing number (1-indexed)
            total_filings: Total number of filings
            workflow_status: Workflow status dict
            
        Returns:
            Processing result
        """
        # Get filing info for display
        from .workflow_results_aggregator import WorkflowResultsAggregator
        aggregator = WorkflowResultsAggregator()
        filing_info = aggregator.get_filing_info(filing_id)
        
        # Delegate to filing processor
        result = await self.filing_processor.process_single_filing(
            filing_id=filing_id,
            market_type=market_type,
            filing_number=filing_number,
            total_filings=total_filings,
            filing_info=filing_info,
            workflow_status=workflow_status
        )
        
        # Log detailed result
        self._log_filing_result(filing_number, result)
        
        return result
    
    def _log_filing_result(
        self,
        filing_number: int,
        result: Dict[str, Any]
    ) -> None:
        """
        Log detailed filing processing result.
        
        Args:
            filing_number: Filing number
            result: Processing result
        """
        logger.info(f"Filing {filing_number} result received:")
        logger.info(f"  - success: {result.get('success')}")
        logger.info(f"  - facts_parsed: {result.get('facts_parsed', 'NOT FOUND')}")
        logger.info(f"  - facts_mapped: {result.get('facts_mapped', 'NOT FOUND')}")
        logger.info(f"  - total_facts: {result.get('total_facts', 'NOT FOUND')}")
        logger.info(f"  - success_rate: {result.get('success_rate', 'NOT FOUND')}")
        logger.debug(f"  - All keys: {list(result.keys())}")


__all__ = ['WorkflowStageExecutor']