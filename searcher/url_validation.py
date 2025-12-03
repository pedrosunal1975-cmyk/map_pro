"""
File: engines/searcher/url_validation.py
Path: engines/searcher/url_validation.py

Map Pro URL Validation Utilities
================================

Generic URL validation utilities for search operations.
Validates and normalizes URLs from different markets.

Architecture: Utility component providing validation functions without market-specific logic.
"""

from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse

from core.system_logger import get_logger
from engines.searcher.url_constants import (
    VALID_URL_SCHEMES,
    TRUSTED_DOMAINS,
    DOWNLOADABLE_FILE_EXTENSIONS,
    DEFAULT_PORTS,
    MAX_EXTENSION_LENGTH
)
from engines.searcher.url_domain_validator import URLDomainValidator
from engines.searcher.url_normalizer import URLNormalizer
from engines.searcher.url_parser import URLParser
from engines.searcher.url_file_detector import URLFileDetector

logger = get_logger(__name__, 'engine')


class URLValidator:
    """
    URL validation and normalization utilities.
    
    Responsibilities:
    - Coordinate URL validation operations
    - Delegate to specialized validators
    - Provide high-level validation interface
    
    Does NOT handle:
    - Market-specific URL patterns (market plugins handle this)
    - Actual HTTP requests (downloader engine handles this)
    - URL downloading (downloader engine handles this)
    """
    
    def __init__(self) -> None:
        """Initialize URL validator with specialized components."""
        self.domain_validator = URLDomainValidator(TRUSTED_DOMAINS)
        self.normalizer = URLNormalizer(DEFAULT_PORTS)
        self.parser = URLParser()
        self.file_detector = URLFileDetector(DOWNLOADABLE_FILE_EXTENSIONS, MAX_EXTENSION_LENGTH)
        
        logger.debug("URL validator initialized with specialized components")
    
    def validate_url(self, url: str, market_type: Optional[str] = None) -> bool:
        """
        Validate URL format and structure.
        
        Args:
            url: URL to validate
            market_type: Optional market type for domain validation
            
        Returns:
            True if URL is valid, False otherwise
            
        Raises:
            TypeError: If url is not a string
        """
        if not isinstance(url, str):
            logger.error(f"URL must be a string, got {type(url).__name__}")
            return False
        
        if not url or not url.strip():
            logger.debug("Empty URL provided")
            return False
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            
            if not self._validate_scheme(parsed.scheme):
                return False
            
            if not self._validate_netloc(parsed.netloc):
                return False
            
            if not self.domain_validator.is_valid_domain(parsed.netloc):
                logger.debug(f"Invalid domain format: {parsed.netloc}")
                return False
            
            if market_type:
                self._check_trusted_domain(parsed.netloc, market_type)
            
            return True
            
        except (ValueError, AttributeError) as e:
            logger.debug(f"URL validation error: {e}")
            return False
    
    def _validate_scheme(self, scheme: str) -> bool:
        """
        Validate URL scheme.
        
        Args:
            scheme: URL scheme to validate
            
        Returns:
            True if scheme is valid
        """
        if scheme not in VALID_URL_SCHEMES:
            logger.debug(f"Invalid URL scheme: {scheme}")
            return False
        return True
    
    def _validate_netloc(self, netloc: str) -> bool:
        """
        Validate network location (domain).
        
        Args:
            netloc: Network location to validate
            
        Returns:
            True if netloc is present
        """
        if not netloc:
            logger.debug("URL missing domain")
            return False
        return True
    
    def _check_trusted_domain(self, netloc: str, market_type: str) -> None:
        """
        Check and log if domain is trusted for market.
        
        Args:
            netloc: Network location to check
            market_type: Market type for validation
        """
        if not self.domain_validator.is_trusted_domain(netloc, market_type):
            logger.warning(
                f"URL domain not in trusted list for {market_type}: {netloc}"
            )
    
    def normalize_url(self, url: str) -> Optional[str]:
        """
        Normalize URL to consistent format.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL or None if invalid
            
        Raises:
            TypeError: If url is not a string
        """
        if not isinstance(url, str):
            logger.error(f"URL must be a string, got {type(url).__name__}")
            return None
        
        return self.normalizer.normalize(url)
    
    def extract_components(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract URL components.
        
        Args:
            url: URL to parse
            
        Returns:
            Dictionary with URL components or None if invalid
            
        Raises:
            TypeError: If url is not a string
        """
        if not isinstance(url, str):
            logger.error(f"URL must be a string, got {type(url).__name__}")
            return None
        
        return self.parser.extract_components(url)
    
    def get_file_extension(self, url: str) -> Optional[str]:
        """
        Extract file extension from URL.
        
        Args:
            url: URL to analyze
            
        Returns:
            File extension (including dot) or None
            
        Raises:
            TypeError: If url is not a string
        """
        if not isinstance(url, str):
            logger.error(f"URL must be a string, got {type(url).__name__}")
            return None
        
        return self.file_detector.get_file_extension(url)
    
    def is_download_url(self, url: str) -> bool:
        """
        Check if URL appears to be a downloadable file.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to point to a downloadable file
            
        Raises:
            TypeError: If url is not a string
        """
        if not isinstance(url, str):
            logger.error(f"URL must be a string, got {type(url).__name__}")
            return False
        
        return self.file_detector.is_download_url(url)
    
    def validate_filing_url(self, url: str, market_type: str) -> Dict[str, Any]:
        """
        Comprehensive validation of filing URL.
        
        Args:
            url: URL to validate
            market_type: Market type for domain validation
            
        Returns:
            Dictionary with validation results containing:
                - valid: bool
                - normalized_url: Optional[str]
                - file_extension: Optional[str]
                - is_downloadable: bool
                - trusted_domain: bool
                - issues: List[str]
                
        Raises:
            TypeError: If url or market_type are not strings
        """
        if not isinstance(url, str):
            return self._create_error_result("URL must be a string")
        
        if not isinstance(market_type, str):
            return self._create_error_result("Market type must be a string")
        
        result = self._create_validation_result()
        
        if not self.validate_url(url, market_type):
            result['issues'].append('Invalid URL format')
            return result
        
        result['valid'] = True
        
        self._add_normalized_url(result, url)
        self._add_file_extension(result, url)
        self._add_downloadable_status(result, url)
        self._add_trusted_domain_status(result, url, market_type)
        
        return result
    
    def _create_validation_result(self) -> Dict[str, Any]:
        """
        Create initial validation result structure.
        
        Returns:
            Dictionary with default validation result values
        """
        return {
            'valid': False,
            'normalized_url': None,
            'file_extension': None,
            'is_downloadable': False,
            'trusted_domain': False,
            'issues': []
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create error result with message.
        
        Args:
            error_message: Error message to include
            
        Returns:
            Dictionary with error result
        """
        result = self._create_validation_result()
        result['issues'].append(error_message)
        return result
    
    def _add_normalized_url(self, result: Dict[str, Any], url: str) -> None:
        """
        Add normalized URL to result.
        
        Args:
            result: Result dictionary to update
            url: URL to normalize
        """
        normalized = self.normalize_url(url)
        if normalized:
            result['normalized_url'] = normalized
        else:
            result['issues'].append('URL normalization failed')
    
    def _add_file_extension(self, result: Dict[str, Any], url: str) -> None:
        """
        Add file extension to result.
        
        Args:
            result: Result dictionary to update
            url: URL to extract extension from
        """
        extension = self.get_file_extension(url)
        if extension:
            result['file_extension'] = extension
    
    def _add_downloadable_status(self, result: Dict[str, Any], url: str) -> None:
        """
        Add downloadable status to result.
        
        Args:
            result: Result dictionary to update
            url: URL to check
        """
        result['is_downloadable'] = self.is_download_url(url)
    
    def _add_trusted_domain_status(
        self, 
        result: Dict[str, Any], 
        url: str, 
        market_type: str
    ) -> None:
        """
        Add trusted domain status to result.
        
        Args:
            result: Result dictionary to update
            url: URL to check
            market_type: Market type for validation
        """
        try:
            parsed = urlparse(url)
            result['trusted_domain'] = self.domain_validator.is_trusted_domain(
                parsed.netloc, 
                market_type
            )
            
            if not result['trusted_domain']:
                result['issues'].append(
                    f'Domain not in trusted list for {market_type}'
                )
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to check trusted domain: {e}")
            result['issues'].append('Domain validation failed')


# Global validator instance
url_validator = URLValidator()


# Convenience functions
def validate_url(url: str, market_type: Optional[str] = None) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        market_type: Optional market type for domain validation
        
    Returns:
        True if URL is valid, False otherwise
    """
    return url_validator.validate_url(url, market_type)


def normalize_url(url: str) -> Optional[str]:
    """
    Normalize URL to consistent format.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL or None if invalid
    """
    return url_validator.normalize_url(url)


def get_file_extension(url: str) -> Optional[str]:
    """
    Extract file extension from URL.
    
    Args:
        url: URL to analyze
        
    Returns:
        File extension (including dot) or None
    """
    return url_validator.get_file_extension(url)


def validate_filing_url(url: str, market_type: str) -> Dict[str, Any]:
    """
    Comprehensive filing URL validation.
    
    Args:
        url: URL to validate
        market_type: Market type for domain validation
        
    Returns:
        Dictionary with validation results
    """
    return url_validator.validate_filing_url(url, market_type)