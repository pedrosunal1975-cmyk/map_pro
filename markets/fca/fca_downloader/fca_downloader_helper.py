"""
FCA Download Helper
==================

Helper utilities for FCA-specific download operations.
Bridges FCA constants with the generic engines/downloader/ engine.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from core.system_logger import get_logger
from .fca_constants import (
    FCA_DOCUMENTS_BASE_URL,
    FCA_FILE_FORMATS,
    FCA_PRIMARY_FORMAT,
    FCA_REQUIRES_EXTRACTION,
    FCA_URL_PATTERNS,
    FCA_FILE_NAME_PATTERN,
    FCA_DOWNLOAD_PATH_PATTERN,
    FCA_VALIDATION_RULES,
    FCA_ERROR_MESSAGES
)

logger = get_logger(__name__, 'market')


class FCADownloadHelper:
    """
    Helper class for FCA download operations.
    
    Provides FCA-specific URL building, path generation, and validation
    while keeping the generic downloader engine clean.
    """
    
    def __init__(self):
        """Initialize FCA download helper."""
        self.base_url = FCA_DOCUMENTS_BASE_URL
        self.url_patterns = FCA_URL_PATTERNS
        self.file_name_pattern = FCA_FILE_NAME_PATTERN
        self.path_pattern = FCA_DOWNLOAD_PATH_PATTERN
        self.validation_rules = FCA_VALIDATION_RULES
        
        logger.info("FCA download helper initialized")
    
    def build_download_url(self, company_number: str, filing_type: str, 
                          filing_date: str, **kwargs) -> str:
        """
        Build FCA filing download URL.
        
        Args:
            company_number: UK company number (e.g., "00000001")
            filing_type: Filing type (e.g., "ANNUAL", "INTERIM")
            filing_date: Filing date in YYYY-MM-DD format
            **kwargs: Additional parameters for URL construction
            
        Returns:
            Complete download URL
        """
        # Determine URL pattern based on filing type
        if filing_type.upper() == 'ANNUAL':
            pattern = self.url_patterns['annual_report']
            year = filing_date[:4]
            url = pattern.format(
                base_url=self.base_url,
                company_number=company_number,
                year=year
            )
        elif filing_type.upper() in ['HALF', 'QUARTERLY']:
            pattern = self.url_patterns['interim_report']
            year = filing_date[:4]
            period = kwargs.get('period', 'H1')
            url = pattern.format(
                base_url=self.base_url,
                company_number=company_number,
                year=year,
                period=period
            )
        else:
            pattern = self.url_patterns['announcement']
            date_str = filing_date.replace('-', '')
            announcement_id = kwargs.get('announcement_id', '001')
            url = pattern.format(
                base_url=self.base_url,
                company_number=company_number,
                date=date_str,
                id=announcement_id
            )
        
        logger.debug(f"Built FCA URL: {url}")
        return url
    
    def generate_file_name(self, company_number: str, filing_type: str,
                          filing_date: str, extension: Optional[str] = None) -> str:
        """
        Generate FCA file name following naming convention.
        
        Args:
            company_number: UK company number
            filing_type: Filing type
            filing_date: Filing date
            extension: File extension (defaults to PRIMARY_FORMAT)
            
        Returns:
            Generated filename
        """
        if extension is None:
            extension = FCA_PRIMARY_FORMAT.lstrip('.')
        
        date_str = filing_date.replace('-', '')
        
        filename = self.file_name_pattern.format(
            company_number=company_number,
            filing_type=filing_type.lower(),
            date=date_str,
            extension=extension
        )
        
        return filename
    
    def generate_download_path(self, company_number: str, filing_type: str,
                              filename: str, base_path: Path) -> Path:
        """
        Generate complete download path for FCA filing.
        
        Args:
            company_number: UK company number
            filing_type: Filing type
            filename: Generated filename
            base_path: Base data directory path
            
        Returns:
            Complete Path object for download
        """
        relative_path = self.path_pattern.format(
            market_type='fca',
            company_number=company_number,
            filing_type=filing_type.lower(),
            filename=filename
        )
        
        full_path = base_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        return full_path
    
    def validate_file_format(self, file_path: Path) -> bool:
        """
        Validate FCA file format.
        
        Args:
            file_path: Path to downloaded file
            
        Returns:
            True if valid format
        """
        extension = file_path.suffix.lower()
        
        if extension not in FCA_FILE_FORMATS:
            logger.error(f"Invalid FCA file format: {extension}")
            return False
        
        return True
    
    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate FCA file size against rules.
        
        Args:
            file_size: File size in bytes
            
        Returns:
            True if size is valid
        """
        min_size = self.validation_rules['min_file_size']
        max_size = self.validation_rules['max_file_size']
        
        if file_size < min_size:
            logger.error(f"File too small: {file_size} bytes (min: {min_size})")
            return False
        
        if file_size > max_size:
            logger.error(f"File too large: {file_size} bytes (max: {max_size})")
            return False
        
        return True
    
    def requires_extraction(self, file_path: Path) -> bool:
        """
        Check if file requires extraction.
        
        FCA files are direct downloads - no extraction needed.
        
        Args:
            file_path: Path to downloaded file
            
        Returns:
            Always False for FCA files
        """
        return FCA_REQUIRES_EXTRACTION
    
    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from FCA file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Metadata dictionary
        """
        return {
            'file_format': file_path.suffix.lower(),
            'file_format_description': FCA_FILE_FORMATS.get(file_path.suffix.lower(), 'Unknown'),
            'requires_extraction': False,
            'market_type': 'fca',
            'download_timestamp': datetime.utcnow().isoformat(),
            'validation_rules_applied': list(self.validation_rules.keys())
        }


def create_fca_download_helper() -> FCADownloadHelper:
    """
    Factory function to create FCA download helper.
    
    Returns:
        FCADownloadHelper instance
    """
    return FCADownloadHelper()


def build_fca_download_url(company_number: str, filing_type: str,
                          filing_date: str, **kwargs) -> str:
    """
    Convenience function to build FCA download URL.
    
    Args:
        company_number: UK company number
        filing_type: Filing type
        filing_date: Filing date
        **kwargs: Additional parameters
        
    Returns:
        Download URL
    """
    helper = create_fca_download_helper()
    return helper.build_download_url(company_number, filing_type, filing_date, **kwargs)


def validate_fca_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to validate FCA file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Validation result dictionary
    """
    helper = create_fca_download_helper()
    
    if not file_path.exists():
        return {
            'valid': False,
            'error': 'File does not exist'
        }
    
    file_size = file_path.stat().st_size
    
    format_valid = helper.validate_file_format(file_path)
    size_valid = helper.validate_file_size(file_size)
    
    return {
        'valid': format_valid and size_valid,
        'format_valid': format_valid,
        'size_valid': size_valid,
        'file_size': file_size,
        'file_format': file_path.suffix.lower(),
        'metadata': helper.get_file_metadata(file_path)
    }