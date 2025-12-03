"""
SEC Download Validator
=====================

SEC-specific validation for download operations.
Extends generic DownloadValidator with SEC EDGAR requirements.

SEC-Specific Validations:
- User-agent header present and valid
- CIK format valid
- Accession number format valid
- URL points to SEC EDGAR domain
- ZIP file naming pattern matches expectations

Save location: markets/sec/sec_downloader/sec_download_validator.py
"""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from core.system_logger import get_logger
from engines.downloader.download_validator import DownloadValidator
from engines.downloader.download_result import ValidationResult
from markets.sec.sec_searcher.sec_validators import SECValidator
from markets.sec.sec_searcher.sec_constants import SEC_ARCHIVES_BASE_URL

logger = get_logger(__name__, 'market')


class SECDownloadValidator(DownloadValidator):
    """
    SEC-specific download validator.
    
    Adds SEC EDGAR validation on top of generic download validation.
    """
    
    def __init__(
        self,
        user_agent: Optional[str] = None,
        max_file_size_mb: float = 500.0,
        min_free_space_mb: float = 1000.0,
        verify_checksums: bool = True
    ):
        """
        Initialize SEC validator.
        
        Args:
            user_agent: Required SEC user-agent string
            max_file_size_mb: Maximum file size
            min_free_space_mb: Minimum free space required
            verify_checksums: Whether to calculate checksums
        """
        super().__init__(max_file_size_mb, min_free_space_mb, verify_checksums)
        
        self.user_agent = user_agent
        self.sec_base_domain = 'sec.gov'
        
        # SEC accession number pattern: 0000000000-00-000000
        self.accession_pattern = re.compile(r'^\d{10}-\d{2}-\d{6}$')
        
        logger.debug("SEC download validator initialized")
    
    def validate_sec_url(self, url: str) -> ValidationResult:
        """
        Validate SEC-specific URL requirements.
        
        Args:
            url: URL to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        try:
            parsed = urlparse(url)
            
            # Check domain is SEC
            if self.sec_base_domain not in parsed.netloc.lower():
                result.valid = False
                result.add_check(
                    'sec_domain',
                    False,
                    f'URL is not from {self.sec_base_domain}: {parsed.netloc}'
                )
            else:
                result.add_check('sec_domain', True)
            
            # Check URL structure for archives
            if 'archives/edgar/data' in parsed.path.lower():
                result.add_check('archives_path', True)
            else:
                result.warnings.append('URL does not follow standard Archives path pattern')
            
            # Check for ZIP extension
            if url.lower().endswith('.zip'):
                result.add_check('zip_extension', True)
            else:
                result.warnings.append('URL does not end with .zip')
            
        except Exception as e:
            result.valid = False
            result.add_check('url_parse', False, str(e))
            logger.error(f"SEC URL validation error: {e}")
        
        return result
    
    def validate_user_agent(self) -> ValidationResult:
        """
        Validate user-agent is configured.
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        if not self.user_agent:
            result.valid = False
            result.add_check(
                'user_agent_configured',
                False,
                'SEC user-agent not configured (required by SEC)'
            )
        else:
            result.add_check('user_agent_configured', True)
            
            # Check format (should contain email)
            if '@' in self.user_agent and '(' in self.user_agent:
                result.add_check('user_agent_format', True)
            else:
                result.warnings.append(
                    'User-agent may not follow SEC recommended format: '
                    '"CompanyName/Version (email@example.com)"'
                )
        
        return result
    
    def validate_cik(self, cik: str) -> ValidationResult:
        """
        Validate CIK format.
        
        Args:
            cik: CIK to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        if SECValidator.validate_cik(cik):
            result.add_check('cik_format', True)
        else:
            result.valid = False
            result.add_check('cik_format', False, f'Invalid CIK: {cik}')
        
        return result
    
    def validate_accession_number(self, accession_number: str) -> ValidationResult:
        """
        Validate accession number format.
        
        Args:
            accession_number: Accession number to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        if self.accession_pattern.match(accession_number):
            result.add_check('accession_format', True)
        else:
            result.valid = False
            result.add_check(
                'accession_format',
                False,
                f'Invalid accession number format: {accession_number}'
            )
        
        return result
    
    def validate_zip_filename(self, filename: str) -> ValidationResult:
        """
        Validate ZIP filename matches SEC patterns.
        
        Args:
            filename: Filename to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        filename_lower = filename.lower()
        
        # Must be ZIP
        if not filename_lower.endswith('.zip'):
            result.valid = False
            result.add_check('is_zip', False, 'Not a ZIP file')
            return result
        
        result.add_check('is_zip', True)
        
        # Check common SEC patterns
        sec_patterns = ['_htm.zip', '_xbrl.zip', '-xbrl.zip', 'r2.zip']
        matches_pattern = any(pattern in filename_lower for pattern in sec_patterns)
        
        if matches_pattern:
            result.add_check('sec_pattern', True)
        else:
            result.warnings.append(
                f'Filename does not match common SEC patterns: {filename}'
            )
        
        return result
    
    def validate_sec_pre_download(
        self,
        url: str,
        target_path: Path,
        cik: Optional[str] = None,
        accession_number: Optional[str] = None
    ) -> ValidationResult:
        """
        Comprehensive SEC pre-download validation.
        
        Args:
            url: URL to download
            target_path: Target save path
            cik: Optional CIK for validation
            accession_number: Optional accession number for validation
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True, file_path=target_path)
        
        # Generic validations
        generic_result = self.validate_pre_download(url, target_path)
        result.checks_passed.extend(generic_result.checks_passed)
        result.checks_failed.extend(generic_result.checks_failed)
        result.warnings.extend(generic_result.warnings)
        
        if not generic_result.valid:
            result.valid = False
        
        # SEC-specific validations
        
        # User-agent check
        ua_result = self.validate_user_agent()
        result.checks_passed.extend(ua_result.checks_passed)
        result.checks_failed.extend(ua_result.checks_failed)
        result.warnings.extend(ua_result.warnings)
        if not ua_result.valid:
            result.valid = False
        
        # URL checks
        url_result = self.validate_sec_url(url)
        result.checks_passed.extend(url_result.checks_passed)
        result.checks_failed.extend(url_result.checks_failed)
        result.warnings.extend(url_result.warnings)
        if not url_result.valid:
            result.valid = False
        
        # CIK validation (if provided)
        if cik:
            cik_result = self.validate_cik(cik)
            result.checks_passed.extend(cik_result.checks_passed)
            result.checks_failed.extend(cik_result.checks_failed)
            if not cik_result.valid:
                result.valid = False
        
        # Accession number validation (if provided)
        if accession_number:
            acc_result = self.validate_accession_number(accession_number)
            result.checks_passed.extend(acc_result.checks_passed)
            result.checks_failed.extend(acc_result.checks_failed)
            if not acc_result.valid:
                result.valid = False
        
        # ZIP filename validation
        filename = target_path.name
        zip_result = self.validate_zip_filename(filename)
        result.checks_passed.extend(zip_result.checks_passed)
        result.checks_failed.extend(zip_result.checks_failed)
        result.warnings.extend(zip_result.warnings)
        # Note: ZIP pattern validation is warning-only, not failure
        
        if result.valid:
            logger.debug(f"SEC pre-download validation passed for {url}")
        else:
            logger.warning(
                f"SEC pre-download validation failed",
                failed_checks=result.checks_failed
            )
        
        return result
    
    def validate_sec_post_download(
        self,
        file_path: Path,
        expected_checksum: Optional[str] = None
    ) -> ValidationResult:
        """
        SEC post-download validation.
        
        Args:
            file_path: Downloaded file path
            expected_checksum: Optional expected checksum
            
        Returns:
            ValidationResult
        """
        # Use generic post-download validation
        result = self.validate_post_download(file_path, expected_checksum)
        
        # Add SEC-specific checks if needed
        # (Currently generic validation is sufficient for downloaded ZIPs)
        
        return result


# Convenience functions

def validate_sec_download_ready(
    url: str,
    target_path: Path,
    user_agent: str,
    cik: Optional[str] = None,
    accession_number: Optional[str] = None
) -> bool:
    """
    Quick SEC download readiness check.
    
    Args:
        url: URL to download
        target_path: Target save path
        user_agent: SEC user-agent
        cik: Optional CIK
        accession_number: Optional accession number
        
    Returns:
        True if ready to download
    """
    validator = SECDownloadValidator(user_agent=user_agent)
    result = validator.validate_sec_pre_download(url, target_path, cik, accession_number)
    return result.valid