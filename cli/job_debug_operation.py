"""
Database Schema Verification - Job Debug Operation
===================================================

Location: tools/cli/job_debug_operation.py

Orchestrates the job data structure debugging operation.
"""

import traceback
from core.database_coordinator import db_coordinator

from .db_check_constants import DiagnosticConstants, DiagnosticMessages
from .database_initializer import DatabaseInitializer
from .job_diagnostic_reporter import JobDiagnosticReporter
from .job_parameter_analyzer import JobParameterAnalyzer


class JobDebugOperation:
    """Orchestrates job data structure debugging."""
    
    @staticmethod
    def execute() -> None:
        """Debug job data structure to find entity_id parameter issues."""
        separator = "=" * DiagnosticConstants.SEPARATOR_LENGTH
        print(f"\n{separator}")
        print(DiagnosticMessages.HEADER_DEBUG_TITLE)
        print(f"{separator}")
        
        if not DatabaseInitializer.ensure_initialized():
            return
        
        try:
            with db_coordinator.get_session(DiagnosticConstants.CORE_DATABASE) as session:
                reporter = JobDiagnosticReporter(session)
                
                # Get recent find_filings job
                job_info = reporter.get_recent_find_filings_job()
                
                if not job_info:
                    print(DiagnosticMessages.WARNING_NO_JOBS_FOUND.format(
                        DiagnosticConstants.FIND_FILINGS_JOB_TYPE
                    ))
                    statistics = reporter.get_job_statistics()
                    reporter.print_job_statistics(statistics)
                    return
                
                # Print basic job information
                reporter.print_job_basic_info(job_info)
                
                # Analyze parameters
                JobDebugOperation._print_parameter_analysis(job_info)
                
                # Analyze entity_id
                JobDebugOperation._print_entity_id_analysis(job_info)
                
                # Simulate job orchestrator
                simulated_job_data = reporter.simulate_job_orchestrator_behavior(job_info)
                JobDebugOperation._print_orchestrator_simulation(simulated_job_data)
                
                # Simulate searcher engine
                searcher_analysis = reporter.analyze_searcher_engine_access(
                    simulated_job_data,
                    job_info.parameters
                )
                JobDebugOperation._print_searcher_simulation(searcher_analysis)
                
                # Diagnose issues
                reporter.diagnose_entity_id_issue(searcher_analysis)
                
                # Check entity existence
                reporter.print_entity_existence_check(job_info.entity_id_raw)
                
        except Exception as e:
            print(DiagnosticMessages.ERROR_DEBUG_SCRIPT.format(e))
            traceback.print_exc()
        
        print(f"\n{separator}\n")
    
    @staticmethod
    def _print_parameter_analysis(job_info) -> None:
        """Print parameter analysis section."""
        print(f"\n{DiagnosticMessages.INFO_JOB_PARAMS_ANALYSIS}")
        print(f"   Parameters JSON: {job_info.parameters}")
        print(f"   Parameters type: {type(job_info.parameters).__name__}")
        
        JobParameterAnalyzer.print_parameter_details(job_info.parameters)
    
    @staticmethod
    def _print_entity_id_analysis(job_info) -> None:
        """Print entity ID analysis section."""
        entity_analysis = JobParameterAnalyzer.analyze_entity_id(
            job_info.entity_id_raw,
            job_info.parameters
        )
        
        print(f"\n{DiagnosticMessages.INFO_ENTITY_ID_ANALYSIS}")
        print(f"   From DB column: {entity_analysis.db_column}")
        print(f"   From parameters: {entity_analysis.from_parameters}")
        print(f"   From params type: {entity_analysis.param_type}")
        print(f"   From params valid: {entity_analysis.param_valid}")
    
    @staticmethod
    def _print_orchestrator_simulation(simulated_job_data) -> None:
        """Print job orchestrator simulation section."""
        print(f"\n{DiagnosticMessages.INFO_SIMULATION_ORCHESTRATOR}")
        print(f"   job_data['entity_id']: {simulated_job_data.get('entity_id')}")
        print(f"   job_data['parameters']: {simulated_job_data.get('parameters')}")
    
    @staticmethod
    def _print_searcher_simulation(searcher_analysis) -> None:
        """Print searcher engine simulation section."""
        print(f"\n{DiagnosticMessages.INFO_SIMULATION_SEARCHER}")
        print(f"   job_data.get('entity_id'): {searcher_analysis.from_job_data}")
        print(f"   parameters.get('entity_id'): {searcher_analysis.from_parameters}")
        print(f"   Final entity_id (OR logic): {searcher_analysis.final_entity_id}")
        print(f"   Is final entity_id truthy: {searcher_analysis.is_truthy}")