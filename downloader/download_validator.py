"""
Map Pro Download Validator
==========================

Pre and post download validation.
Ensures downloads are safe, valid, and within limits before and after downloading.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from core.system_logger import get_logger
from core.data_paths import map_pro_paths
from .download_result import ValidationResult

logger = get_logger(__name__, 'engine')


class DownloadValidator:
    """
    Validates downloads before and after execution.
    
    Pre-download:
    - URL format validation
    - Disk space availability
    - Write permissions
    - File size limits (if known)
    
    Post-download:
    - File exists and not empty
    - File size within limits
    - Checksum validation (optional)
    - File format validation (optional)
    """
    
    def __init__(
        self,
        max_file_size_mb: float = 500.0,
        min_free_space_mb: float = 1000.0,
        verify_checksums: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            max_file_size_mb: Maximum allowed file size
            min_free_space_mb: Minimum required free disk space
            verify_checksums: Whether to calculate checksums
        """
        self.max_file_size_mb = max_file_size_mb
        self.min_free_space_mb = min_free_space_mb
        self.verify_checksums = verify_checksums
        self.logger = logger
    
    def validate_url(self, url: str) -> ValidationResult:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            ValidationResult with checks
        """
        result = ValidationResult(valid=True)
        
        try:
            # Check URL not empty
            if not url or not url.strip():
                result.valid = False
                result.add_check('url_not_empty', False, 'URL is empty')
                return result
            
            result.add_check('url_not_empty', True)
            
            # Parse URL
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https', 'ftp', 'ftps']:
                result.valid = False
                result.add_check('valid_scheme', False, f'Unsupported scheme: {parsed.scheme}')
            else:
                result.add_check('valid_scheme', True)
            
            # Check has netloc (domain)
            if not parsed.netloc:
                result.valid = False
                result.add_check('has_domain', False, 'URL has no domain')
            else:
                result.add_check('has_domain', True)
            
            # Check has path
            if not parsed.path or parsed.path == '/':
                result.warnings.append('URL has no specific path')
            
        except Exception as e:
            result.valid = False
            result.add_check('url_parse', False, str(e))
            self.logger.error(f"URL validation failed: {e}")
        
        return result
    
    def check_disk_space(self, target_path: Path, required_mb: Optional[float] = None) -> ValidationResult:
        """
        Check available disk space.
        
        Args:
            target_path: Path where file will be saved
            required_mb: Required space in MB (uses min_free_space if None)
            
        Returns:
            ValidationResult with space check
        """
        result = ValidationResult(valid=True)
        required = required_mb or self.min_free_space_mb
        
        try:
            # Get disk usage stats
            # FIX: Always use parent directory for a file path
            parent_dir = target_path.parent  # <- FIXED LINE
            parent_dir.mkdir(parents=True, exist_ok=True)
            
            stat = shutil.disk_usage(parent_dir)
            available_mb = stat.free / (1024 * 1024)
            
            if available_mb < required:
                result.valid = False
                result.add_check(
                    'sufficient_disk_space',
                    False,
                    f'Only {available_mb:.1f}MB available, need {required:.1f}MB'
                )
            else:
                result.add_check('sufficient_disk_space', True)
                self.logger.debug(f"Disk space OK: {available_mb:.1f}MB available")
            
        except Exception as e:
            result.warnings.append(f"Could not check disk space: {e}")
            self.logger.warning(f"Disk space check failed: {e}")
        
        return result

    
    def check_write_permission(self, target_path: Path) -> ValidationResult:
        """
        Check write permissions for target path.
        
        Args:
            target_path: Path to check
            
        Returns:
            ValidationResult with permission check
        """
        result = ValidationResult(valid=True)
        
        try:
            # Ensure parent directory exists
            parent_dir = target_path.parent
            parent_dir.mkdir(parents=True, exist_ok=True)
            
            # Try creating a test file
            test_file = parent_dir / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
                result.add_check('write_permission', True)
            except PermissionError:
                result.valid = False
                result.add_check('write_permission', False, f'No write permission for {parent_dir}')
            
        except Exception as e:
            result.valid = False
            result.add_check('write_permission', False, str(e))
            self.logger.error(f"Write permission check failed: {e}")
        
        return result
    
    def validate_pre_download(
        self,
        url: str,
        target_path: Path,
        expected_size_mb: Optional[float] = None
    ) -> ValidationResult:
        """
        Comprehensive pre-download validation.
        
        Args:
            url: URL to download from
            target_path: Where file will be saved
            expected_size_mb: Expected file size if known
            
        Returns:
            ValidationResult with all pre-download checks
        """
        result = ValidationResult(valid=True, file_path=target_path)
        
        # URL validation
        url_result = self.validate_url(url)
        result.checks_passed.extend(url_result.checks_passed)
        result.checks_failed.extend(url_result.checks_failed)
        result.warnings.extend(url_result.warnings)
        if not url_result.valid:
            result.valid = False
        
        # Disk space check
        required_space = expected_size_mb + self.min_free_space_mb if expected_size_mb else None
        space_result = self.check_disk_space(target_path, required_space)
        result.checks_passed.extend(space_result.checks_passed)
        result.checks_failed.extend(space_result.checks_failed)
        result.warnings.extend(space_result.warnings)
        if not space_result.valid:
            result.valid = False
        
        # Write permission check
        perm_result = self.check_write_permission(target_path)
        result.checks_passed.extend(perm_result.checks_passed)
        result.checks_failed.extend(perm_result.checks_failed)
        if not perm_result.valid:
            result.valid = False
        
        if result.valid:
            self.logger.debug(f"Pre-download validation passed for {url}")
        else:
            self.logger.warning(
                f"Pre-download validation failed for {url}",
                failed_checks=result.checks_failed
            )
        
        return result
    
    def calculate_checksum(self, file_path: Path, algorithm: str = 'sha256') -> Optional[str]:
        """
        Calculate file checksum.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm ('md5', 'sha256', 'sha512')
            
        Returns:
            Checksum hex string or None if failed
        """
        if not self.verify_checksums:
            return None
        
        try:
            if algorithm == 'md5':
                hasher = hashlib.md5()
            elif algorithm == 'sha512':
                hasher = hashlib.sha512()
            else:  # default sha256
                hasher = hashlib.sha256()
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            
            checksum = hasher.hexdigest()
            self.logger.debug(f"Calculated {algorithm} checksum for {file_path.name}: {checksum[:16]}...")
            return checksum
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate checksum for {file_path}: {e}")
            return None
    
    def validate_file_exists(self, file_path: Path) -> ValidationResult:
        """
        Validate file exists and is not empty.
        
        Args:
            file_path: Path to check
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True, file_path=file_path)
        
        try:
            # Check exists
            if not file_path.exists():
                result.valid = False
                result.add_check('file_exists', False, 'File does not exist')
                return result
            
            result.add_check('file_exists', True)
            
            # Check is file (not directory)
            if not file_path.is_file():
                result.valid = False
                result.add_check('is_file', False, 'Path is not a file')
                return result
            
            result.add_check('is_file', True)
            
            # Check not empty
            file_size = file_path.stat().st_size
            result.file_size_bytes = file_size
            
            if file_size == 0:
                result.valid = False
                result.add_check('not_empty', False, 'File is empty (0 bytes)')
                return result
            
            result.add_check('not_empty', True)
            
        except Exception as e:
            result.valid = False
            result.add_check('file_validation', False, str(e))
            self.logger.error(f"File validation failed for {file_path}: {e}")
        
        return result
    
    def validate_file_size(self, file_path: Path) -> ValidationResult:
        """
        Validate file size is within limits.
        
        Args:
            file_path: Path to check
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True, file_path=file_path)
        
        try:
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            result.file_size_bytes = file_size_bytes
            
            # Check maximum size
            if file_size_mb > self.max_file_size_mb:
                result.valid = False
                result.add_check(
                    'size_within_limit',
                    False,
                    f'File too large: {file_size_mb:.1f}MB exceeds {self.max_file_size_mb}MB limit'
                )
            else:
                result.add_check('size_within_limit', True)
            
        except Exception as e:
            result.valid = False
            result.add_check('size_check', False, str(e))
            self.logger.error(f"Size validation failed for {file_path}: {e}")
        
        return result
    
    def validate_post_download(
        self,
        file_path: Path,
        expected_checksum: Optional[str] = None,
        calculate_checksum: bool = True
    ) -> ValidationResult:
        """
        Comprehensive post-download validation.
        
        Args:
            file_path: Downloaded file path
            expected_checksum: Expected checksum to verify against
            calculate_checksum: Whether to calculate checksum
            
        Returns:
            ValidationResult with all post-download checks
        """
        result = ValidationResult(valid=True, file_path=file_path)
        
        # File exists and not empty
        exists_result = self.validate_file_exists(file_path)
        result.checks_passed.extend(exists_result.checks_passed)
        result.checks_failed.extend(exists_result.checks_failed)
        result.file_size_bytes = exists_result.file_size_bytes
        if not exists_result.valid:
            result.valid = False
            return result  # No point continuing if file doesn't exist
        
        # File size within limits
        size_result = self.validate_file_size(file_path)
        result.checks_passed.extend(size_result.checks_passed)
        result.checks_failed.extend(size_result.checks_failed)
        if not size_result.valid:
            result.valid = False
        
        # Checksum validation
        if calculate_checksum or expected_checksum:
            checksum = self.calculate_checksum(file_path)
            result.checksum = checksum
            
            if expected_checksum and checksum:
                if checksum == expected_checksum:
                    result.add_check('checksum_match', True)
                else:
                    result.valid = False
                    result.add_check('checksum_match', False, 'Checksum mismatch')
            elif checksum:
                result.add_check('checksum_calculated', True)
        
        if result.valid:
            self.logger.debug(
                f"Post-download validation passed for {file_path.name}",
                size_mb=f"{result.file_size_bytes / (1024 * 1024):.2f}MB"
            )
        else:
            self.logger.warning(
                f"Post-download validation failed for {file_path.name}",
                failed_checks=result.checks_failed
            )
        
        return result


# Convenience functions
def validate_download_ready(url: str, target_path: Path) -> bool:
    """Quick check if ready to download."""
    validator = DownloadValidator()
    result = validator.validate_pre_download(url, target_path)
    return result.valid


def validate_download_complete(file_path: Path) -> bool:
    """Quick check if download completed successfully."""
    validator = DownloadValidator()
    result = validator.validate_post_download(file_path)
    return result.valid