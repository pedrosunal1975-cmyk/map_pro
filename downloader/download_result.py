# File: /map_pro/engines/downloader/download_result.py

"""
Map Pro Download Result
=======================

Standardized result objects for download operations.
Provides consistent return types across all download components.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

BYTES_PER_KILOBYTE = 1024
BYTES_PER_MEGABYTE = BYTES_PER_KILOBYTE * 1024
DECIMAL_PRECISION_SIZE_MB = 2
DECIMAL_PRECISION_DURATION = 2
DECIMAL_PRECISION_SPEED = 2
DECIMAL_PRECISION_SUCCESS_RATE = 1
DEFAULT_PROTOCOL = 'unknown'
DEFAULT_FILE_SIZE_BYTES = 0
DEFAULT_DURATION_SECONDS = 0.0
DEFAULT_RETRY_COUNT = 0
DEFAULT_TOTAL_FILES = 0
DEFAULT_SUCCESSFUL_DOWNLOADS = 0
DEFAULT_FAILED_DOWNLOADS = 0
DEFAULT_TOTAL_SIZE_MB = 0.0
DEFAULT_TOTAL_DURATION_SECONDS = 0.0


@dataclass
class DownloadResult:
    """
    Result of a single file download operation.
    
    Used by protocol handlers to return standardized results.
    """
    success: bool
    file_path: Optional[Path] = None
    file_size_bytes: int = DEFAULT_FILE_SIZE_BYTES
    duration_seconds: float = DEFAULT_DURATION_SECONDS
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    retry_count: int = DEFAULT_RETRY_COUNT
    protocol: str = DEFAULT_PROTOCOL
    
    @property
    def file_size_mb(self) -> float:
        """File size in megabytes."""
        return self.file_size_bytes / BYTES_PER_MEGABYTE if self.file_size_bytes > 0 else 0.0
    
    @property
    def download_speed_mbps(self) -> float:
        """Download speed in MB/s."""
        if self.duration_seconds > 0 and self.file_size_bytes > 0:
            return self.file_size_mb / self.duration_seconds
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            'success': self.success,
            'file_path': str(self.file_path) if self.file_path else None,
            'file_size_bytes': self.file_size_bytes,
            'file_size_mb': round(self.file_size_mb, DECIMAL_PRECISION_SIZE_MB),
            'duration_seconds': round(self.duration_seconds, DECIMAL_PRECISION_DURATION),
            'download_speed_mbps': round(self.download_speed_mbps, DECIMAL_PRECISION_SPEED),
            'checksum': self.checksum,
            'error_message': self.error_message,
            'http_status': self.http_status,
            'retry_count': self.retry_count,
            'protocol': self.protocol
        }


@dataclass
class BatchDownloadResult:
    """
    Result of a batch download operation (multiple files).
    
    Used by download coordinator for job-level reporting.
    """
    success: bool
    total_files: int = DEFAULT_TOTAL_FILES
    successful_downloads: int = DEFAULT_SUCCESSFUL_DOWNLOADS
    failed_downloads: int = DEFAULT_FAILED_DOWNLOADS
    total_size_mb: float = DEFAULT_TOTAL_SIZE_MB
    total_duration_seconds: float = DEFAULT_TOTAL_DURATION_SECONDS
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    download_results: List[DownloadResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful_downloads / self.total_files) * 100
    
    @property
    def average_speed_mbps(self) -> float:
        """Average download speed across all files."""
        if self.total_duration_seconds > 0:
            return self.total_size_mb / self.total_duration_seconds
        return 0.0
    
    def add_result(self, result: DownloadResult):
        """Add a download result to the batch."""
        self.download_results.append(result)
        self.total_files += 1
        
        if result.success:
            self.successful_downloads += 1
            self.total_size_mb += result.file_size_mb
        else:
            self.failed_downloads += 1
            if result.error_message:
                self.errors.append(result.error_message)
        
        self.total_duration_seconds += result.duration_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            'success': self.success,
            'total_files': self.total_files,
            'successful_downloads': self.successful_downloads,
            'failed_downloads': self.failed_downloads,
            'success_rate': round(self.success_rate, DECIMAL_PRECISION_SUCCESS_RATE),
            'total_size_mb': round(self.total_size_mb, DECIMAL_PRECISION_SIZE_MB),
            'total_duration_seconds': round(self.total_duration_seconds, DECIMAL_PRECISION_DURATION),
            'average_speed_mbps': round(self.average_speed_mbps, DECIMAL_PRECISION_SPEED),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


@dataclass
class ValidationResult:
    """
    Result of file validation (pre or post download).
    
    Used by download validator.
    """
    valid: bool
    file_path: Optional[Path] = None
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    file_size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    
    def add_check(self, check_name: str, passed: bool, message: Optional[str] = None):
        """Add a validation check result."""
        if passed:
            self.checks_passed.append(check_name)
        else:
            self.checks_failed.append(check_name)
            if message:
                self.warnings.append(f"{check_name}: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'valid': self.valid,
            'file_path': str(self.file_path) if self.file_path else None,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'warnings': self.warnings,
            'file_size_bytes': self.file_size_bytes,
            'checksum': self.checksum
        }