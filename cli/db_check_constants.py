"""
Database Schema Verification - Constants
=========================================

Location: tools/cli/db_check_constants.py

All constants and enums for database diagnostic operations.
"""

from enum import Enum


class DiagnosticConstants:
    """Constants for database diagnostics."""
    DEFAULT_LIMIT = 10
    CORE_DATABASE = 'core'
    PROCESSING_JOBS_TABLE = 'processing_jobs'
    ENTITIES_TABLE = 'entities'
    FIND_FILINGS_JOB_TYPE = 'find_filings'
    SEPARATOR_LENGTH = 80


class DiagnosticChoice(Enum):
    """Available diagnostic operations."""
    CHECK_CONSTRAINTS = '1'
    DEBUG_JOB_STRUCTURE = '2'
    BOTH = '3'


class DiagnosticMessages:
    """User-facing messages for diagnostics."""
    
    # Error messages
    ERROR_INIT_FAILED = "[ERROR] Failed to initialize database coordinator"
    ERROR_DB_CHECK = "[ERROR] Error checking database: {}"
    ERROR_FIX_ORPHANED = "[ERROR] Error fixing orphaned jobs: {}"
    ERROR_DEBUG_SCRIPT = "[ERROR] Debug script error: {}"
    ERROR_INVALID_CHOICE = "[ERROR] Invalid choice: {}"
    ERROR_JSON_PARSE = "   [ERROR] JSON parse error: {}"
    ERROR_CRITICAL_MISSING_BOTH = "   [ERROR] CRITICAL: entity_id is missing from BOTH job_data and parameters"
    ERROR_CRITICAL_STRING_NONE = "   [ERROR] CRITICAL: entity_id is string 'None' instead of actual UUID"
    ERROR_ENTITY_NOT_EXISTS = "   [ERROR] Entity does NOT exist in database!"
    
    # Warning messages
    WARNING_NO_JOBS_FOUND = "[WARNING] No {} jobs found in database"
    WARNING_NO_PARAMETERS = "   [WARNING] No parameters found"
    WARNING_MISSING_JOB_DATA = "   [WARNING] entity_id missing from job_data but exists in parameters"
    WARNING_MISSING_PARAMS = "   [WARNING] entity_id missing from parameters but exists in job_data"
    WARNING_NO_JOBS_AT_ALL = "   [WARNING] No jobs found in database at all"
    
    # Info messages
    INFO_RECENT_JOB = "[INFO] Most Recent {} Job:"
    INFO_PARSED_PARAMS = "[INFO] Parsed Parameters Contents:"
    INFO_JOB_PARAMS_ANALYSIS = "[INFO] Job Parameters Analysis:"
    INFO_ENTITY_ID_ANALYSIS = "[TARGET] Entity ID Analysis:"
    INFO_SIMULATION_ORCHESTRATOR = "[SIMULATION] Job Orchestrator get_next_job Simulation:"
    INFO_SIMULATION_SEARCHER = "[SEARCH] Searcher Engine Parameter Access Simulation:"
    INFO_ENTITY_EXISTS = "   [OK] Entity exists: {} ({})"
    INFO_ENTITY_CHECK = "[SEARCH] Entity Existence Check:"
    INFO_JOB_STATS = "[STATS] Jobs in database by type and status:"
    
    # Diagnosis messages
    DIAGNOSIS_HEADER = "[DIAGNOSIS]"
    ROOT_CAUSE_JOB_CREATION = "   [ROOT CAUSE] Job creation or parameter passing issue"
    ROOT_CAUSE_UUID_CONVERSION = "   [ROOT CAUSE] UUID to string conversion issue"
    ROOT_CAUSE_ORCHESTRATOR = "   [ROOT CAUSE] job_orchestrator.get_next_job not setting entity_id"
    ROOT_CAUSE_PARAM_STORAGE = "   [ROOT CAUSE] Parameter not being stored during job creation"
    ROOT_CAUSE_UNCLEAR = "   [UNCLEAR] entity_id appears present but searcher still fails"
    ROOT_CAUSE_VALIDATION = "   [POSSIBLE CAUSE] Validation logic issue in searcher engine"
    ROOT_CAUSE_ALERT = "   [ALERT] This could be the root cause!"
    
    # Solution messages
    SOLUTION_CHECK_WORKFLOW = "   [SOLUTION] Check job_workflow_manager and job_orchestrator"
    SOLUTION_FIX_UUID = "   [SOLUTION] Fix UUID handling in job creation"
    SOLUTION_FIX_GET_NEXT_JOB = "   [SOLUTION] Fix get_next_job method to include entity_id"
    SOLUTION_FIX_JOB_CREATION = "   [SOLUTION] Fix job creation to include entity_id in parameters"
    SOLUTION_CHECK_SEARCHER = "   [SOLUTION] Check searcher engine validation logic"
    
    # Menu messages
    MENU_TITLE = "Database Diagnostic Options:"
    MENU_OPTION_1 = "1. Check foreign key constraints"
    MENU_OPTION_2 = "2. Debug job data structure (entity_id issue)"
    MENU_OPTION_3 = "3. Both"
    MENU_PROMPT = "Enter choice (1/2/3): "
    
    # Section headers
    HEADER_CHECKING_CONSTRAINTS = "Checking processing_jobs foreign key constraints..."
    HEADER_REMOVING_ORPHANED = "\nRemoving orphaned jobs..."
    HEADER_DEBUG_TITLE = "DEBUGGING JOB DATA STRUCTURE - ENTITY_ID PARAMETER ISSUE"
    HEADER_TABLE_STRUCTURE = "\n{} table structure:"
    HEADER_FOREIGN_KEYS = "\nForeign key constraints:"
    HEADER_DIAGNOSIS = "\n[DIAGNOSIS]:"
    
    # Result messages
    RESULT_ENTITIES_COUNT = "\nEntities table contains {} records"
    RESULT_ORPHANED_COUNT = "\nOrphaned jobs (entity_id not in entities table): {}"
    RESULT_ORPHANED_DETAILS = "\nOrphaned job details:"
    RESULT_REMOVED_COUNT = "Removed {} orphaned jobs"
    RESULT_DONE = "Done. Try running the workflow again."
    
    # Confirmation prompts
    CONFIRM_REMOVE_ORPHANED = "\nRemove orphaned jobs?"
    CONFIRM_YES_NO = " (y/n): "


class SQLQueries:
    """SQL queries for database diagnostics."""
    
    TABLE_STRUCTURE = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = :table_name
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """
    
    FOREIGN_KEY_CONSTRAINTS = """
        SELECT 
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_name = :table_name
    """
    
    ENTITY_COUNT = "SELECT COUNT(*) FROM {table_name}"
    
    ORPHANED_JOBS_COUNT = """
        SELECT COUNT(*) FROM {jobs_table} pj
        LEFT JOIN {entities_table} e 
            ON pj.entity_universal_id = e.entity_universal_id
        WHERE pj.entity_universal_id IS NOT NULL 
        AND e.entity_universal_id IS NULL
    """
    
    ORPHANED_JOBS_DETAILS = """
        SELECT pj.job_id, pj.entity_universal_id, pj.job_type, pj.created_at
        FROM {jobs_table} pj
        LEFT JOIN {entities_table} e 
            ON pj.entity_universal_id = e.entity_universal_id
        WHERE pj.entity_universal_id IS NOT NULL 
        AND e.entity_universal_id IS NULL
        ORDER BY pj.created_at DESC
        LIMIT :limit
    """
    
    DELETE_ORPHANED_JOBS = """
        DELETE FROM {jobs_table}
        WHERE entity_universal_id IS NOT NULL 
        AND entity_universal_id NOT IN (
            SELECT entity_universal_id FROM {entities_table}
        )
    """
    
    RECENT_JOB_BY_TYPE = """
        SELECT job_id, job_type, entity_universal_id, job_parameters, job_status, created_at
        FROM {jobs_table}
        WHERE job_type = :job_type
        ORDER BY created_at DESC 
        LIMIT 1
    """
    
    ENTITY_LOOKUP = """
        SELECT entity_universal_id, primary_name, market_type 
        FROM {entities_table}
        WHERE entity_universal_id = :entity_id
    """
    
    JOB_STATISTICS = """
        SELECT job_type, job_status, count(*) 
        FROM {jobs_table}
        GROUP BY job_type, job_status 
        ORDER BY job_type, job_status
    """