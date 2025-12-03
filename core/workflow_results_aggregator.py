# PATH: /map_pro/core/workflow_results_aggregator.py

"""
Map Pro Workflow Results Aggregator
===================================

Collects and aggregates results from workflow processing.
Handles database queries, statistics calculation, and output file discovery.

Architecture:
- Results collection and aggregation
- Database query abstractions
- Statistics calculation
- Output file discovery

Dependencies: Extracted from synchronous_workflow_executor.py
Save location: core/workflow_results_aggregator.py
"""

from typing import Dict, Any, List

from .system_logger import get_logger
from .database_coordinator import db_coordinator
from database.models.core_models import Entity, Filing
from database.models.mapped_models import MappedStatement

logger = get_logger(__name__, 'core')


class WorkflowResultsAggregator:
    """
    Aggregate results from workflow processing.
    
    Responsibilities:
    - Collect results from multiple filing processes
    - Calculate aggregated statistics
    - Query database for entity/filing information
    - Discover output files
    - Format final results
    
    Does NOT handle:
    - Workflow orchestration (WorkflowCoordinator handles this)
    - Individual filing processing (FilingProcessor handles this)
    - Job management (FilingProcessor handles this)
    """
    
    def __init__(self):
        """Initialize workflow results aggregator."""
        logger.info("Workflow results aggregator initialized")
    
    def aggregate_workflow_results(
        self,
        entity_id: str,
        entity_info: Dict[str, Any],
        filing_ids: List[str],
        all_results: List[Dict[str, Any]],
        duration_seconds: float,
        stages_completed: List[str]
    ) -> Dict[str, Any]:
        """
        Aggregate results from all processed filings.
        
        Args:
            entity_id: Entity UUID
            entity_info: Entity information
            filing_ids: List of filing UUIDs
            all_results: List of individual filing results
            duration_seconds: Total processing duration
            stages_completed: List of completed stage names
            
        Returns:
            Aggregated results dictionary
        """
        logger.info(f"Aggregating results for {len(filing_ids)} filings")
        
        # DEBUG: Log raw input data
        logger.info(f"DEBUG: ========== AGGREGATION START ==========")
        logger.info(f"DEBUG: Entity ID: {entity_id}")
        logger.info(f"DEBUG: Number of filing_ids: {len(filing_ids)}")
        logger.info(f"DEBUG: Number of all_results: {len(all_results)}")
        logger.info(f"DEBUG: Stages completed: {stages_completed}")
        
        # Count successes and failures
        successful_filings = sum(1 for r in all_results if r.get('success'))
        failed_filings = len(all_results) - successful_filings
        
        # DEBUG: Log each filing result in detail
        logger.info(f"DEBUG: Individual Filing Results:")
        for idx, result in enumerate(all_results):
            logger.info(f"DEBUG:   Filing {idx+1}/{len(all_results)}:")
            logger.info(f"DEBUG:     - success: {result.get('success')}")
            logger.info(f"DEBUG:     - facts_parsed: {result.get('facts_parsed', 0)}")
            logger.info(f"DEBUG:     - facts_mapped: {result.get('facts_mapped', 0)}")
            logger.info(f"DEBUG:     - total_facts: {result.get('total_facts', 0)}")
            logger.info(f"DEBUG:     - unmapped_facts: {result.get('unmapped_facts', 0)}")
            logger.info(f"DEBUG:     - success_rate: {result.get('success_rate', 0)}")
            logger.info(f"DEBUG:     - stage_failed: {result.get('stage_failed', 'none')}")
            
            # Show all keys in result
            logger.info(f"DEBUG:     - all keys: {list(result.keys())}")
        
        logger.info(f"DEBUG: Success Summary:")
        logger.info(f"DEBUG:   - successful_filings: {successful_filings}")
        logger.info(f"DEBUG:   - failed_filings: {failed_filings}")
        
        # Aggregate facts across all filings
        aggregated_facts = self._aggregate_facts_statistics(all_results)
        
        # DEBUG: Log aggregated facts
        logger.info(f"DEBUG: Aggregated Facts:")
        logger.info(f"DEBUG:   - total_parsed: {aggregated_facts['total_parsed']}")
        logger.info(f"DEBUG:   - total_mapped: {aggregated_facts['total_mapped']}")
        logger.info(f"DEBUG:   - total_unmapped: {aggregated_facts['total_unmapped']}")
        
        # Calculate overall success rate
        overall_success_rate = self._calculate_overall_success_rate(all_results)
        
        # DEBUG: Log success rate calculation
        logger.info(f"DEBUG: Success Rate Calculation:")
        logger.info(f"DEBUG:   - overall_success_rate: {overall_success_rate}")
        
        # Get output files
        output_files = self.get_output_files(entity_id, filing_ids)
        
        # DEBUG: Log output files
        logger.info(f"DEBUG: Output Files:")
        logger.info(f"DEBUG:   - count: {len(output_files)}")
        if output_files:
            logger.info(f"DEBUG:   - first 3: {output_files[:3]}")
        
        # Determine overall workflow success with strict criteria
        # Success requires:
        # 1. At least one filing succeeded
        # 2. That filing must have completed all core stages
        # 3. That filing must have produced mapped facts
        workflow_success = False
        
        if successful_filings > 0:
            # Verify at least one filing completed the full workflow
            for result in all_results:
                if result.get('success'):
                    # Check that this filing completed required stages
                    filing_stages = result.get('stages_completed', [])
                    required_stages = {'parse', 'map'}  # Core stages that MUST complete
                    
                    # Check if core stages completed
                    if required_stages.issubset(set(filing_stages)):
                        # Verify mapping actually produced results
                        if result.get('facts_mapped', 0) > 0:
                            workflow_success = True
                            break
                        else:
                            logger.warning("Filing marked successful but no facts were mapped")
                    else:
                        missing_stages = required_stages - set(filing_stages)
                        logger.warning(
                            f"Filing marked successful but missing required stages: {missing_stages}"
                        )

        
        # Build comprehensive results
        results = {
            'success': workflow_success,
            'entity_id': entity_id,
            'entity_name': entity_info.get('primary_name', 'Unknown'),
            'company_identifier': (
                entity_info.get('ticker_symbol') or
                entity_info.get('market_entity_id') or
                'Unknown'
            ),
            'market_type': entity_info.get('market_type', 'unknown'),
            'filings_processed': len(filing_ids),
            'filings_successful': successful_filings,
            'filings_failed': failed_filings,
            'facts_parsed': aggregated_facts['total_parsed'],
            'facts_mapped': aggregated_facts['total_mapped'],
            'unmapped_facts': aggregated_facts['total_unmapped'],
            'success_rate': overall_success_rate,
            'duration_seconds': duration_seconds,
            'output_files': output_files,
            'stages_completed': stages_completed,
            'filing_results': all_results,  # Add individual filing results
            'processing_summary': self._create_processing_summary(all_results)
        }
        
        # DEBUG: Log final results dictionary
        logger.info(f"DEBUG: Final Results Dictionary:")
        logger.info(f"DEBUG:   - success: {results['success']}")
        logger.info(f"DEBUG:   - filings_processed: {results['filings_processed']}")
        logger.info(f"DEBUG:   - filings_successful: {results['filings_successful']}")
        logger.info(f"DEBUG:   - filings_failed: {results['filings_failed']}")
        logger.info(f"DEBUG:   - facts_parsed: {results['facts_parsed']}")
        logger.info(f"DEBUG:   - facts_mapped: {results['facts_mapped']}")
        logger.info(f"DEBUG:   - unmapped_facts: {results['unmapped_facts']}")
        logger.info(f"DEBUG:   - success_rate: {results['success_rate']}")
        logger.info(f"DEBUG: ========== AGGREGATION END ==========")
        
        logger.info(f"Results aggregated: {successful_filings}/{len(filing_ids)} filings successful")
        return results
    
    # ========================================================================
    # STATISTICS CALCULATION METHODS
    # ========================================================================
    
    def _aggregate_facts_statistics(self, all_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Aggregate fact statistics across all filing results.
        
        Args:
            all_results: List of individual filing results
            
        Returns:
            Dictionary with aggregated fact statistics
        """
        total_facts_parsed = sum(r.get('facts_parsed', 0) for r in all_results)
        total_facts_mapped = sum(r.get('facts_mapped', 0) for r in all_results)
        total_unmapped_facts = sum(r.get('unmapped_facts', 0) for r in all_results)
        
        return {
            'total_parsed': total_facts_parsed,
            'total_mapped': total_facts_mapped,
            'total_unmapped': total_unmapped_facts
        }
    
    def _calculate_overall_success_rate(self, all_results: List[Dict[str, Any]]) -> float:
        """
        Calculate overall success rate across all filings.
        
        Returns:
            Average success rate as percentage (0.0 to 100.0)
        """
        success_rates = [
            r.get('success_rate', 0.0) 
            for r in all_results 
            if 'success_rate' in r
        ]
        
        if success_rates:
            # Success rates from mapper are already percentages (0-100)
            return round(sum(success_rates) / len(success_rates), 2)
        else:
            return 0.0
    
    def _create_processing_summary(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create detailed processing summary.
        
        Args:
            all_results: List of individual filing results
            
        Returns:
            Processing summary dictionary
        """
        stage_failures = {}
        successful_results = [r for r in all_results if r.get('success')]
        failed_results = [r for r in all_results if not r.get('success')]
        
        # Count failures by stage
        for result in failed_results:
            stage_failed = result.get('stage_failed', 'unknown')
            stage_failures[stage_failed] = stage_failures.get(stage_failed, 0) + 1
        
        return {
            'total_filings': len(all_results),
            'successful_filings': len(successful_results),
            'failed_filings': len(failed_results),
            'stage_failures': stage_failures,
            'has_output_data': len(successful_results) > 0
        }
    
    # ========================================================================
    # DATABASE QUERY METHODS
    # ========================================================================
    
    def get_entity_info(self, entity_id: str) -> Dict[str, Any]:
        """
        Get entity information from database.
        
        Args:
            entity_id: Entity UUID
            
        Returns:
            Entity information dictionary
        """
        try:
            with db_coordinator.get_session('core') as session:
                entity = session.query(Entity).filter_by(
                    entity_universal_id=entity_id
                ).first()
                
                if entity:
                    return {
                        'entity_id': entity.entity_universal_id,
                        'primary_name': entity.primary_name,
                        'ticker_symbol': entity.ticker_symbol,
                        'market_type': entity.market_type,
                        'market_entity_id': entity.market_entity_id
                    }
        
        except Exception as e:
            logger.error(f"Failed to get entity info: {e}")
        
        return {'primary_name': 'Unknown'}
    
    def get_filing_info(self, filing_id: str) -> Dict[str, Any]:
        """
        Get filing information from database.
        
        Args:
            filing_id: Filing UUID
            
        Returns:
            Filing information dictionary
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter_by(
                    filing_universal_id=filing_id
                ).first()
                
                if filing:
                    return {
                        'filing_id': filing.filing_universal_id,
                        'entity_id': filing.entity_universal_id,  # Add entity_id for job creation
                        'filing_type': filing.filing_type,
                        'filing_date': filing.filing_date.isoformat() if filing.filing_date else None,
                        'market_filing_id': filing.market_filing_id,
                        'url': filing.original_url
                    }
        
        except Exception as e:
            logger.error(f"Failed to get filing info: {e}")
        
        return {}
    
    def get_output_files(
        self, 
        entity_id: str, 
        filing_ids: List[str]
    ) -> List[str]:
        """
        Get list of output file paths from mapped database.
        
        Args:
            entity_id: Entity UUID
            filing_ids: List of filing UUIDs
            
        Returns:
            List of output file paths
        """
        output_files = []
        
        try:
            with db_coordinator.get_session('mapped') as session:
                for filing_id in filing_ids:
                    statements = session.query(MappedStatement).filter_by(
                        filing_universal_id=filing_id
                    ).all()
                    
                    for stmt in statements:
                        if stmt.statement_json_path:
                            output_files.append(str(stmt.statement_json_path))
        
        except Exception as e:
            logger.error(f"Failed to get output files: {e}")
        
        return output_files
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_summary_statistics(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics for reporting.
        
        Args:
            all_results: List of individual filing results
            
        Returns:
            Summary statistics dictionary
        """
        if not all_results:
            return {
                'total_filings': 0,
                'success_rate': 0.0,
                'total_facts': 0,
                'mapped_facts': 0
            }
        
        facts_stats = self._aggregate_facts_statistics(all_results)
        success_rate = self._calculate_overall_success_rate(all_results)
        
        return {
            'total_filings': len(all_results),
            'successful_filings': sum(1 for r in all_results if r.get('success')),
            'success_rate': success_rate,
            'total_facts_parsed': facts_stats['total_parsed'],
            'total_facts_mapped': facts_stats['total_mapped'],
            'mapping_efficiency': (
                facts_stats['total_mapped'] / facts_stats['total_parsed']
                if facts_stats['total_parsed'] > 0 else 0.0
            )
        }


__all__ = ['WorkflowResultsAggregator']