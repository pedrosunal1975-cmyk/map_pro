"""
Database Schema Verification - Job Diagnostic Reporter
=======================================================

Location: tools/cli/job_diagnostic_reporter.py

Reports diagnostic information about job data structure.
"""

from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db_check_constants import (
    DiagnosticConstants, 
    DiagnosticMessages, 
    SQLQueries
)
from .db_check_models import JobDebugInfo, SearcherEngineAnalysis
from .job_parameter_analyzer import JobParameterAnalyzer


class JobDiagnosticReporter:
    """Reports diagnostic information about job data structure."""
    
    def __init__(self, session: Session):
        """
        Initialize the diagnostic reporter.
        
        Args:
            session: Database session
        """
        self.session = session
        self.analyzer = JobParameterAnalyzer()
    
    def get_recent_find_filings_job(self) -> Optional[JobDebugInfo]:
        """
        Get the most recent find_filings job for debugging.
        
        Returns:
            JobDebugInfo object or None if no job found
        """
        query = text(
            SQLQueries.RECENT_JOB_BY_TYPE.format(
                jobs_table=DiagnosticConstants.PROCESSING_JOBS_TABLE
            )
        )
        
        result = self.session.execute(
            query,
            {'job_type': DiagnosticConstants.FIND_FILINGS_JOB_TYPE}
        ).fetchone()
        
        if not result:
            return None
        
        parameters = self.analyzer.parse_parameters(result[3])
        
        return JobDebugInfo(
            job_id=result[0],
            job_type=result[1],
            entity_id_raw=result[2],
            parameters=parameters,
            status=result[4],
            created_at=str(result[5])
        )
    
    def print_job_basic_info(self, job_info: JobDebugInfo) -> None:
        """
        Print basic job information.
        
        Args:
            job_info: Job debug information
        """
        print(DiagnosticMessages.INFO_RECENT_JOB.format(
            DiagnosticConstants.FIND_FILINGS_JOB_TYPE
        ))
        print(f"   Job ID: {job_info.job_id}")
        print(f"   Job Type: {job_info.job_type}")
        print(f"   Status: {job_info.status}")
        print(f"   Created: {job_info.created_at}")
        print(f"   Entity ID (raw): {job_info.entity_id_raw}")
        print(f"   Entity ID (type): {type(job_info.entity_id_raw).__name__}")
        print(f"   Entity ID (str): {str(job_info.entity_id_raw) if job_info.entity_id_raw else 'None'}")
    
    def simulate_job_orchestrator_behavior(
        self, 
        job_info: JobDebugInfo
    ) -> Dict[str, Any]:
        """
        Simulate how job orchestrator would process this job.
        
        Args:
            job_info: Job debug information
            
        Returns:
            Simulated job data dictionary
        """
        return {
            'job_id': str(job_info.job_id),
            'job_type': job_info.job_type,
            'entity_id': str(job_info.entity_id_raw) if job_info.entity_id_raw else None,
            'parameters': job_info.parameters
        }
    
    def analyze_searcher_engine_access(
        self, 
        simulated_job_data: Dict[str, Any], 
        parameters: Dict[str, Any]
    ) -> SearcherEngineAnalysis:
        """
        Simulate how searcher engine would access entity_id.
        
        Args:
            simulated_job_data: Simulated job data from orchestrator
            parameters: Job parameters
            
        Returns:
            SearcherEngineAnalysis object with analysis results
        """
        entity_id_from_job_data = simulated_job_data.get('entity_id')
        entity_id_from_params = parameters.get('entity_id')
        final_entity_id = entity_id_from_job_data or entity_id_from_params
        
        return SearcherEngineAnalysis(
            from_job_data=entity_id_from_job_data,
            from_parameters=entity_id_from_params,
            final_entity_id=final_entity_id,
            is_truthy=bool(final_entity_id)
        )
    
    def diagnose_entity_id_issue(self, analysis: SearcherEngineAnalysis) -> None:
        """
        Diagnose and print entity_id issues.
        
        Args:
            analysis: Analysis results from searcher engine access
        """
        print(DiagnosticMessages.HEADER_DIAGNOSIS)
        
        from_job_data = analysis.from_job_data
        from_params = analysis.from_parameters
        
        if not from_job_data and not from_params:
            # CRITICAL: Missing from both locations
            print(DiagnosticMessages.ERROR_CRITICAL_MISSING_BOTH)
            print(DiagnosticMessages.ROOT_CAUSE_JOB_CREATION)
            print(DiagnosticMessages.SOLUTION_CHECK_WORKFLOW)
        elif from_job_data == "None" or from_params == "None":
            # CRITICAL: String "None" instead of actual UUID
            print(DiagnosticMessages.ERROR_CRITICAL_STRING_NONE)
            print(DiagnosticMessages.ROOT_CAUSE_UUID_CONVERSION)
            print(DiagnosticMessages.SOLUTION_FIX_UUID)
        elif not from_job_data:
            # WARNING: Missing from job_data but exists in parameters
            print(DiagnosticMessages.WARNING_MISSING_JOB_DATA)
            print(DiagnosticMessages.ROOT_CAUSE_ORCHESTRATOR)
            print(DiagnosticMessages.SOLUTION_FIX_GET_NEXT_JOB)
        elif not from_params:
            # WARNING: Missing from parameters but exists in job_data
            print(DiagnosticMessages.WARNING_MISSING_PARAMS)
            print(DiagnosticMessages.ROOT_CAUSE_PARAM_STORAGE)
            print(DiagnosticMessages.SOLUTION_FIX_JOB_CREATION)
        else:
            # SUCCESS: entity_id present in both locations - this is CORRECT!
            print("   [OK] entity_id is present in both job_data and parameters")
            print("   [STATUS] Data structure is correct - no issues detected")
            print("   [INFO] Searcher engine should be able to process this job successfully")
    
    def check_entity_existence(self, entity_id: Optional[str]) -> Optional[Tuple]:
        """
        Check if entity exists in database.
        
        Args:
            entity_id: Entity universal ID to check
            
        Returns:
            Entity information tuple or None
        """
        if not entity_id:
            return None
        
        query = text(
            SQLQueries.ENTITY_LOOKUP.format(
                entities_table=DiagnosticConstants.ENTITIES_TABLE
            )
        )
        
        return self.session.execute(query, {'entity_id': str(entity_id)}).fetchone()
    
    def print_entity_existence_check(self, entity_id: Optional[str]) -> None:
        """
        Print entity existence check results.
        
        Args:
            entity_id: Entity ID to check
        """
        if not entity_id:
            return
        
        entity_info = self.check_entity_existence(entity_id)
        
        print(DiagnosticMessages.INFO_ENTITY_CHECK)
        if entity_info:
            print(DiagnosticMessages.INFO_ENTITY_EXISTS.format(
                entity_info[1], entity_info[2]
            ))
        else:
            print(DiagnosticMessages.ERROR_ENTITY_NOT_EXISTS)
            print(DiagnosticMessages.ROOT_CAUSE_ALERT)
    
    def get_job_statistics(self) -> List[Tuple]:
        """
        Get statistics about jobs by type and status.
        
        Returns:
            List of tuples containing job statistics
        """
        query = text(
            SQLQueries.JOB_STATISTICS.format(
                jobs_table=DiagnosticConstants.PROCESSING_JOBS_TABLE
            )
        )
        
        return self.session.execute(query).fetchall()
    
    def print_job_statistics(self, statistics: List[Tuple]) -> None:
        """
        Print job statistics.
        
        Args:
            statistics: List of job statistics tuples
        """
        if statistics:
            print(DiagnosticMessages.INFO_JOB_STATS)
            for job_type, status, count in statistics:
                print(f"   {job_type} ({status}): {count}")
        else:
            print(DiagnosticMessages.WARNING_NO_JOBS_AT_ALL)