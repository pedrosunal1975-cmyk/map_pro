# File: /map_pro/markets/sec/sec_downloader/sec_metrics_recorder.py

"""
SEC Metrics Recorder
====================

Records download metrics and outcomes.
Handles both success and failure tracking.
"""

from typing import Optional

from core.system_logger import get_logger
from engines.downloader import DownloadResult
from .sec_download_monitor import SECDownloadMonitor, get_sec_download_monitor

logger = get_logger(__name__, 'market')


class SECMetricsRecorder:
    """
    Records download metrics and outcomes.
    
    Responsibilities:
    - Record download start events
    - Record successful downloads with metrics
    - Record failed downloads with error details
    - Create standardized error results
    """
    
    def __init__(self, monitor: Optional[SECDownloadMonitor] = None):
        """
        Initialize metrics recorder.
        
        Args:
            monitor: Download monitor instance (global if None)
        """
        self.monitor = monitor or get_sec_download_monitor()
        self.logger = logger
    
    def record_download_start(self, filing_id: str, url: str):
        """
        Record download start event.
        
        Args:
            filing_id: Filing universal ID
            url: Download URL (may be empty if not yet resolved)
        """
        self.monitor.record_download_start(filing_id, url)
    
    def record_outcome(
        self,
        filing_id: str,
        download_result: DownloadResult,
        strategy_used: str
    ):
        """
        Record download outcome (success or failure).
        
        Args:
            filing_id: Filing universal ID
            download_result: Result from downloader
            strategy_used: Strategy that resolved the URL
        """
        if download_result.success:
            self._record_success(filing_id, download_result, strategy_used)
        else:
            self._record_failure(filing_id, download_result.error_message)
    
    def _record_success(
        self,
        filing_id: str,
        download_result: DownloadResult,
        strategy_used: str
    ):
        """
        Record successful download.
        
        Args:
            filing_id: Filing universal ID
            download_result: Successful download result
            strategy_used: Strategy that resolved the URL
        """
        self.monitor.record_download_success(
            filing_id,
            download_result.file_size_bytes,
            download_result.duration_seconds,
            strategy_used
        )
        self.logger.info(f"SEC download completed: {filing_id}")
    
    def _record_failure(self, filing_id: str, error_message: str):
        """
        Record failed download.
        
        Args:
            filing_id: Filing universal ID
            error_message: Error description
        """
        self.monitor.record_download_failure(
            filing_id,
            error_message,
            'download_error'
        )
    
    def handle_error(
        self,
        filing_id: str,
        error_message: str,
        error_type: str
    ) -> DownloadResult:
        """
        Handle download error with logging and monitoring.
        
        Creates a standardized error result and records metrics.
        
        Args:
            filing_id: Filing universal ID
            error_message: Error description
            error_type: Error category (metadata_error, validation, etc.)
            
        Returns:
            DownloadResult with failure status
        """
        self.logger.error(error_message)
        self.monitor.record_download_failure(filing_id, error_message, error_type)
        return DownloadResult(success=False, error_message=error_message)