# File: /map_pro/core/ui/results_display.py

"""
Map Pro Results Display Module
==============================

Handles all result formatting and display for completed workflows.
Market-agnostic results presentation with detailed breakdowns.

Responsibilities:
- Display final workflow results
- Format per-filing breakdowns
- Show aggregate statistics
- Display errors and warnings
- Quality indicators

Does NOT handle:
- User input (user_prompts handles this)
- Progress display (progress_display handles this)
- Business logic (workflow_coordinator handles this)
"""

from typing import Dict, Any, Optional, List

from core.system_logger import get_logger
from core.data_paths import map_pro_paths

logger = get_logger(__name__, 'core')

SEPARATOR_LENGTH = 70
QUALITY_THRESHOLD_EXCELLENT = 95
QUALITY_THRESHOLD_VERY_GOOD = 90
QUALITY_THRESHOLD_GOOD = 80
QUALITY_THRESHOLD_ACCEPTABLE = 70
MAX_FILES_TO_DISPLAY = 4
SECONDS_PER_MINUTE = 60


def display_final_results(results: Dict[str, Any]):
    """
    Display final workflow results with per-filing details.
    
    Args:
        results: Final results dictionary from workflow
    """
    print("\n" + "=" * SEPARATOR_LENGTH)
    print("WORKFLOW RESULTS")
    print("=" * SEPARATOR_LENGTH + "\n")
    
    if results.get('success'):
        _display_success_results(results)
    else:
        _display_failure_results(results)
    
    print("\n" + "=" * SEPARATOR_LENGTH + "\n")


def _display_success_results(results: Dict[str, Any]):
    """Display results for successful workflow."""
    print("[OK] WORKFLOW COMPLETED SUCCESSFULLY\n")
    
    if 'entity_name' in results:
        print(f"[INFO] Company: {results['entity_name']}")
    
    _display_per_filing_breakdown(results)
    _display_aggregate_statistics(results)
    _display_output_files(results)
    _display_database_health_warning(results)
    _display_next_steps()

def _display_per_filing_breakdown(results: Dict[str, Any]):
    """Display individual filing results."""
    # Check if we have individual filing data
    if 'individual_filings' in results and results['individual_filings']:
        print(f"\n[FILINGS] Individual Filing Results:")
        
        for idx, filing_result in enumerate(results['individual_filings'], 1):
            _display_single_filing_result(idx, filing_result)
    
    # If we only have processing_summary (aggregated data), skip per-filing display
    elif 'processing_summary' in results:
        summary = results['processing_summary']
        
        # Only display if it's actually a dict with summary data
        if isinstance(summary, dict):
            logger.debug("Processing summary is aggregated data, not individual filings")
            # Skip per-filing breakdown - the aggregate stats will show this data
            return
        
        # If it's a list, process as before
        elif isinstance(summary, list):
            print(f"\n[FILINGS] Individual Filing Results:")
            for idx, filing_result in enumerate(summary, 1):
                _display_single_filing_result(idx, filing_result)


def _display_single_filing_result(idx: int, filing_result: Any):
    """Display result for a single filing."""
    if isinstance(filing_result, str):
        logger.error(f"DEBUG: Filing {idx} is a STRING, not a dict!")
        print(f"        Filing {idx}: {filing_result}")
        return
    
    if not isinstance(filing_result, dict):
        logger.error(f"DEBUG: Filing {idx} is unexpected type: {type(filing_result)}")
        return
    
    success = filing_result.get('success', False)
    filing_date = filing_result.get('filing_date', 'unknown')
    stage_failed = filing_result.get('stage_failed', 'none')
    facts_parsed = filing_result.get('facts_parsed', 0)
    facts_mapped = filing_result.get('facts_mapped', 0)
    
    status_icon, status_text = _get_filing_status(success, stage_failed)
    
    print(f"        Filing {idx}: {filing_date}")
    print(f"            Status: {status_icon} {status_text}")
    
    if facts_parsed > 0:
        print(f"            Facts Parsed: {facts_parsed:,}")
    
    if facts_mapped > 0:
        print(f"            Facts Mapped: {facts_mapped:,}")
    
    _check_filing_anomalies(success, facts_parsed, facts_mapped)
    
    print()


def _get_filing_status(success: bool, stage_failed: str) -> tuple:
    """Get status icon and text for filing."""
    if success:
        return "[OK]", "Success"
    else:
        return "[FAIL]", f"Failed at: {stage_failed}"


def _check_filing_anomalies(success: bool, facts_parsed: int, facts_mapped: int):
    """Check and report filing processing anomalies."""
    if not success and facts_mapped > 0:
        print("            [WARNING] Database says failed but mapping succeeded!")
        print("            This indicates a database tracking issue.")
    
    if not success and facts_parsed > 0 and facts_mapped == 0:
        print("            [WARNING] Parsing succeeded but mapping failed")


def _display_aggregate_statistics(results: Dict[str, Any]):
    """Display aggregate processing statistics."""
    print(f"[STATS] Processing Statistics:")
    
    if 'filings_processed' in results:
        processed = results['filings_processed']
        successful = results.get('filings_successful', processed)
        failed = results.get('filings_failed', 0)
        print(f"        Filings Processed: {successful}/{processed}")
        
        if failed > 0:
            print(f"        Filings Failed: {failed}")
    
    if 'facts_parsed' in results:
        print(f"        Facts Parsed: {results['facts_parsed']:,}")
    
    if 'facts_mapped' in results:
        print(f"        Facts Mapped: {results['facts_mapped']:,}")
    
    if 'unmapped_facts' in results:
        print(f"        Facts Not Mapped: {results['unmapped_facts']:,}")
    
    if 'success_rate' in results:
        _display_quality_metrics(results['success_rate'])
    
    if 'duration_seconds' in results:
        _display_duration(results['duration_seconds'])


def _display_quality_metrics(success_rate: float):
    """Display quality metrics and indicators."""
    print(f"        Mapping Success Rate: {success_rate:.1f}%")
    
    quality = _get_quality_indicator(success_rate)
    print(f"        Quality: {quality}")


def _get_quality_indicator(rate: float) -> str:
    """Get quality indicator based on success rate."""
    if rate >= QUALITY_THRESHOLD_EXCELLENT:
        return "***** Excellent"
    elif rate >= QUALITY_THRESHOLD_VERY_GOOD:
        return "**** Very Good"
    elif rate >= QUALITY_THRESHOLD_GOOD:
        return "*** Good"
    elif rate >= QUALITY_THRESHOLD_ACCEPTABLE:
        return "** Acceptable"
    else:
        return "* Needs Review"


def _display_duration(duration_seconds: float):
    """Display processing duration."""
    minutes = int(duration_seconds // SECONDS_PER_MINUTE)
    seconds = int(duration_seconds % SECONDS_PER_MINUTE)
    print(f"        Processing Time: {minutes}m {seconds}s")


def _display_output_files(results: Dict[str, Any]):
    """Display output file paths."""
    if 'output_files' not in results or not results['output_files']:
        return
    
    print(f"\n[FILES] Output Files:")
    
    output_files = results['output_files']
    
    for file_path in output_files[:MAX_FILES_TO_DISPLAY]:
        print(f"        {file_path}")
    
    if len(output_files) > MAX_FILES_TO_DISPLAY:
        remaining = len(output_files) - MAX_FILES_TO_DISPLAY
        print(f"        ... and {remaining} more files")


def _display_database_health_warning(results: Dict[str, Any]):
    """Display database health warning if issues detected."""
    successful = results.get('filings_successful', 0)
    processed = results.get('filings_processed', 0)
    
    if successful < processed:
        print(f"\n[WARNING] Database Health Issue Detected:")
        print(f"        {processed - successful} filings reported as failed")
        print(f"        Run health check to investigate:")
        print(f"        python tools/database_health_check.py --check")


def _display_next_steps():
    """Display recommended next actions."""
    print(f"\n[NEXT] Recommended Actions:")
    print(f"        - Review output files in mapped_statements directory")
    print(f"        - Run database health check if any failures reported")
    print(f"        - Use data_exporter.py to export to Excel/CSV")


def _display_failure_results(results: Dict[str, Any]):
    """Display results for failed workflow."""
    print("[FAIL] WORKFLOW FAILED\n")
    
    if 'error' in results:
        print(f"[ERROR] {results['error']}\n")
    
    _display_completed_stages(results)
    _display_per_filing_status(results)
    _display_troubleshooting_steps()


def _display_completed_stages(results: Dict[str, Any]):
    """Display stages that completed before failure."""
    if 'stages_completed' not in results:
        return
    
    print("[INFO] Stages completed before failure:")
    for stage in results['stages_completed']:
        print(f"        [OK] {stage}")
    print()


def _display_per_filing_status(results: Dict[str, Any]):
    """Display per-filing status for failed workflow."""
    if 'filing_results' not in results or not results['filing_results']:
        return
    
    print("[FILINGS] Individual Filing Status:")
    
    for idx, filing_result in enumerate(results['filing_results'], 1):
        success = filing_result.get('success', False)
        stage_failed = filing_result.get('stage_failed', 'unknown')
        
        if success:
            print(f"        Filing {idx}: [OK] Success")
        else:
            print(f"        Filing {idx}: [FAIL] Failed at {stage_failed}")
    print()


def _display_troubleshooting_steps():
    """Display troubleshooting recommendations."""
    print("[DEBUG] Troubleshooting Steps:")
    print(f"        1. Check logs in {map_pro_paths.logs_root}/")
    print("        2. Run: python tools/database_health_check.py --check")
    print("        3. Check system health: python main.py --health")
    print("        4. Review failed jobs in database")


def display_entity_found(entity_info: Dict[str, Any]):
    """
    Display entity information after search.
    
    Args:
        entity_info: Entity information dictionary
    """
    print("\n[OK] Company Found:")
    
    if 'name' in entity_info:
        print(f"     Name: {entity_info['name']}")
    if 'ticker' in entity_info:
        print(f"     Ticker: {entity_info['ticker']}")
    if 'cik' in entity_info:
        print(f"     CIK: {entity_info['cik']}")
    if 'market_entity_id' in entity_info:
        print(f"     Market ID: {entity_info['market_entity_id']}")
    print()


def display_filings_found(num_filings: int, form_type: str):
    """
    Display number of filings found.
    
    Args:
        num_filings: Number of filings found
        form_type: Form type searched
    """
    print(f"[OK] Found {num_filings} {form_type} filing(s)\n")


def display_error(error_message: str, error_type: Optional[str] = None):
    """
    Display error message.
    
    Args:
        error_message: Error message to display
        error_type: Optional error type for categorization
    """
    print(f"\n{'=' * SEPARATOR_LENGTH}")
    print("ERROR")
    print(f"{'=' * SEPARATOR_LENGTH}\n")
    
    if error_type:
        print(f"Type: {error_type}")
    
    print(f"Message: {error_message}\n")
    print(f"{'=' * SEPARATOR_LENGTH}\n")


def display_warning(warning_message: str):
    """
    Display warning message.
    
    Args:
        warning_message: Warning message to display
    """
    print(f"\n[WARNING] {warning_message}\n")


def display_banner():
    """Display Map Pro banner."""
    banner = """
    ===================================================================
    
                             MAP PRO
                  XBRL Financial Data Mapper
    
                  Interactive Workflow Execution
    
    ===================================================================
    """
    print(banner)


def clear_screen():
    """Clear terminal screen (optional utility)."""
    import os
    os.system('clear' if os.name != 'nt' else 'cls')


__all__ = [
    'display_final_results',
    'display_entity_found',
    'display_filings_found',
    'display_error',
    'display_warning',
    'display_banner',
    'clear_screen',
]