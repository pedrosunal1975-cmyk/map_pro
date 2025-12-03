"""
Library Analysis Stage Processor
=================================

Handles library dependency analysis stage of filing processing workflow.
Triggered after parsing completes to ensure required taxonomies are available
before mapping begins.

Architecture:
- Coordinates library analysis job creation and execution
- Waits for library analysis completion
- Validates that required libraries are downloaded
- Reports library status and readiness for mapping

Location: /map_pro/core/filing_stages/library_analysis_stage.py
"""

from typing import Dict, Any, Optional

from core.system_logger import get_logger
from core.database_coordinator import db_coordinator
from core.job_orchestrator import job_orchestrator
from database.models.core_models import Filing
from shared.constants.job_constants import JobType

logger = get_logger(__name__, 'core')


class LibraryAnalysisStageProcessor:
    """
    Processes library analysis stage for a filing.
    
    Responsibilities:
    - Create library analysis job
    - Wait for job completion
    - Verify library availability
    - Report analysis results
    
    Does NOT handle:
    - Actual library downloading (librarian engine handles this)
    - Library scanning logic (library_dependency_analyzer handles this)
    - Prerequisite checking (mapping_prerequisites handles this)
    """
    
    def __init__(self, job_waiter):
        """
        Initialize library analysis stage processor.
        
        Args:
            job_waiter: JobWaiter utility for waiting on jobs
        """
        self.job_waiter = job_waiter
        logger.debug("Library analysis stage processor initialized")
    
    async def process(
        self,
        filing_id: str,
        market_type: str,
        workflow_status: Dict[str, str],
        results: Dict[str, Any]
    ) -> bool:
        """
        Process library analysis stage for a filing.
        
        Args:
            filing_id: Filing UUID
            market_type: Market type (sec, fca, esma, etc.)
            workflow_status: Current workflow status dict
            results: Results dictionary to update
            
        Returns:
            True if stage completed successfully, False otherwise
        """
        logger.info(f"\n{'-'*70}")
        logger.info(f"[LIBRARY] Analysis stage STARTING for filing {filing_id}")
        logger.info(f"{'-'*70}")
        
        try:
            # Check if analysis already completed (avoid duplicate work)
            if workflow_status.get('library_analysis') == 'completed':
                logger.info("Library analysis already completed")
                results['library_analysis_completed'] = True
                return True
            
            # Create library analysis job
            job_id = self._create_library_analysis_job(filing_id, market_type)
            
            if not job_id:
                logger.error("Failed to create library analysis job")
                results['stage_failed'] = 'library_analysis'
                results['error'] = "Failed to create library analysis job"
                return False
            
            logger.info(f"Created library analysis job: {job_id}")
            
            # Wait for job completion
            job_result = await self.job_waiter.wait_for_job_completion(
                job_id,
                'library_analysis'
            )
            
            if not job_result or not job_result.get('success'):
                error_msg = job_result.get('error', 'Unknown error') if job_result else 'Job failed'
                logger.info(f"{'-'*70}")
                logger.error(f"[LIBRARY] Analysis stage FAILED: {error_msg}")
                logger.info(f"{'-'*70}\n")
                results['stage_failed'] = 'library_analysis'
                results['error'] = f"Library analysis failed: {error_msg}"
                return False
            
            # Extract analysis results
            self._extract_analysis_results(job_result, results)
            
            # Mark stage as completed
            results['library_analysis_completed'] = True
            
            # Log detailed success information
            libs_found = results.get('libraries_analyzed', 0)
            libs_available = results.get('libraries_available', 0)
            
            logger.info(f"{'-'*70}")
            logger.info(f"[LIBRARY] Analysis stage COMPLETED for filing {filing_id}")
            logger.info(f"[LIBRARY] Libraries found: {libs_found}, Available: {libs_available}")
            logger.info(f"{'-'*70}\n")
            
            return True
            
        except Exception as e:
            logger.info(f"{'-'*70}")
            logger.error(f"[LIBRARY] Analysis stage ERROR: {e}")
            logger.info(f"{'-'*70}\n")
            logger.error(f"Library analysis error details", exc_info=True)
            results['stage_failed'] = 'library_analysis'
            results['error'] = f"Library analysis error: {str(e)}"
            return False
    
    def _create_library_analysis_job(
        self,
        filing_id: str,
        market_type: str
    ) -> Optional[str]:
        """
        Create library analysis job.
        
        Args:
            filing_id: Filing UUID
            market_type: Market type
            
        Returns:
            Job ID or None if creation failed
        """
        try:
            # Get entity_id from database (following extraction_stage pattern)
            entity_id = self._get_entity_id(filing_id)
            
            if not entity_id:
                logger.error(f"Cannot get entity_id for filing {filing_id}")
                return None
            
            # FIXED: Put market_type in parameters so it ends up in job_data
            # The library_dependency_analyzer expects market_type in job_data
            job_id = job_orchestrator.create_job(
                job_type=JobType.ANALYZE_LIBRARY_DEPENDENCIES,
                entity_id=entity_id,
                market_type=market_type,
                parameters={
                    'filing_universal_id': filing_id,
                    'filing_id': filing_id,
                    'market_type': market_type  # Include in parameters for job_data
                }
            )
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to create library analysis job: {e}")
            return None
    
    def _get_entity_id(self, filing_id: str) -> Optional[str]:
        """
        Get entity_id from filing record in database.
        
        Database as journalist: Just reading reported metadata.
        Pattern borrowed from extraction_stage._get_filing_metadata()
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Entity ID string or None if not found
        """
        try:
            with db_coordinator.get_session('core') as session:
                filing = session.query(Filing).filter_by(
                    filing_universal_id=filing_id
                ).first()
                
                if not filing:
                    logger.error(f"Filing {filing_id} not found in database")
                    return None
                
                if not filing.entity:
                    logger.error(f"Filing {filing_id} has no associated entity")
                    return None
                
                entity_id = str(filing.entity_universal_id)
                logger.debug(f"Found entity_id {entity_id} for filing {filing_id}")
                
                return entity_id
                
        except Exception as e:
            logger.error(f"Error getting entity_id from database: {e}")
            return None
    
    def _extract_analysis_results(
        self,
        job_result: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """
        Extract library analysis results from job result.
        
        Args:
            job_result: Job completion result
            results: Results dictionary to update
        """
        # Extract library count if available
        result_data = job_result.get('result', {})
        
        if isinstance(result_data, dict):
            libraries_found = result_data.get('libraries_found', 0)
            libraries_downloaded = result_data.get('libraries_downloaded', 0)
            
            results['libraries_analyzed'] = libraries_found
            results['libraries_available'] = libraries_downloaded
            
            logger.info(
                f"Library analysis results: {libraries_found} found, "
                f"{libraries_downloaded} available"
            )
        else:
            # If result format is unexpected, log it
            logger.debug(f"Library analysis result format: {type(result_data)}")


__all__ = ['LibraryAnalysisStageProcessor']