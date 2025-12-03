# File: markets/base/error_classifier.py
# Improvement: Refactored classify_exception using internal Strategy Pattern to reduce Cyclomatic Complexity (from 14) 
#              while maintaining all function signatures and preserving the file's single structure.

"""
Map Pro Market Error Classifier
===============================

Classifies errors from market APIs into standardized categories.
Helps distinguish between temporary failures, permanent failures, and rate limits.

Architecture: Utility component for error classification without market-specific logic.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
import re
from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


class ErrorCategory(Enum):
    """Enumeration of error categories."""
    NETWORK_ERROR = "network_error"          # Network connectivity issues
    TIMEOUT_ERROR = "timeout_error"          # Request timeout
    RATE_LIMIT_ERROR = "rate_limit_error"    # API rate limit exceeded
    AUTHENTICATION_ERROR = "auth_error"      # Authentication/authorization failure
    NOT_FOUND_ERROR = "not_found_error"      # Resource not found (404)
    VALIDATION_ERROR = "validation_error"    # Invalid request parameters
    SERVER_ERROR = "server_error"            # API server error (5xx)
    TEMPORARY_ERROR = "temporary_error"      # Temporary failure, retry possible
    PERMANENT_ERROR = "permanent_error"      # Permanent failure, no retry
    UNKNOWN_ERROR = "unknown_error"          # Unknown error type


# --- BEGIN: Internal Strategy Components for Complexity Reduction ---
# These internal classes implement the Strategy Pattern to decouple classification logic.

class _BaseErrorClassificationStrategy:
    """Base interface for all classification strategies."""
    def classify(self, exception: Exception) -> Optional[ErrorCategory]:
        """Attempt to classify the exception. Return None if no match is found."""
        raise NotImplementedError

class _NotFoundStrategy(_BaseErrorClassificationStrategy):
    """Strategy for File Not Found and 404-like exceptions (Must run first)."""
    def classify(self, exception: Exception) -> Optional[ErrorCategory]:
        exception_type = type(exception).__name__.lower()
        
        # Check by type, including our custom FileNotFoundError
        if isinstance(exception, FileNotFoundError) or 'filenotfounderror' in exception_type:
            return ErrorCategory.NOT_FOUND_ERROR
        
        exception_str = str(exception).lower()
        if 'not found' in exception_str or '404' in exception_str:
            return ErrorCategory.NOT_FOUND_ERROR
        return None

class _NetworkTimeoutStrategy(_BaseErrorClassificationStrategy):
    """Strategy for network and timeout issues."""
    def classify(self, exception: Exception) -> Optional[ErrorCategory]:
        exception_str = str(exception).lower()
        if 'connection' in exception_str or 'network' in exception_str:
            return ErrorCategory.NETWORK_ERROR
        if 'timeout' in exception_str or 'timed out' in exception_str:
            return ErrorCategory.TIMEOUT_ERROR
        return None

class _RateLimitAuthStrategy(_BaseErrorClassificationStrategy):
    """Strategy for rate limit and authentication issues."""
    def classify(self, exception: Exception) -> Optional[ErrorCategory]:
        exception_str = str(exception).lower()
        if 'rate limit' in exception_str or 'too many requests' in exception_str:
            return ErrorCategory.RATE_LIMIT_ERROR
        if 'auth' in exception_str or 'unauthorized' in exception_str or 'forbidden' in exception_str:
            return ErrorCategory.AUTHENTICATION_ERROR
        return None

class _ExceptionClassificationContext:
    """Context class that delegates exception classification using a list of strategies."""
    def __init__(self, strategies: List[_BaseErrorClassificationStrategy]):
        self._strategies = strategies
    
    def classify(self, exception: Exception) -> ErrorCategory:
        """Iterate through strategies to find the correct error category."""
        for strategy in self._strategies:
            category = strategy.classify(exception)
            if category:
                return category
        
        return ErrorCategory.UNKNOWN_ERROR

# Define the default sequence of strategies for initialization
_DEFAULT_STRATEGIES = [
    _NotFoundStrategy(), # Preserving the original check order (must be first)
    _NetworkTimeoutStrategy(),
    _RateLimitAuthStrategy(),
]
# --- END: Internal Strategy Components ---


class ErrorClassifier:
    """
    Classifies errors from market APIs into standardized categories.
    
    Responsibilities:
    - Classify HTTP errors by status code
    - Classify exceptions by type (delegates to context)
    - Determine if error is retryable
    - Extract retry-after information
    
    Does NOT handle:
    - Actual error recovery (recovery_manager handles this)
    - Error logging (system_logger handles this)
    - Market-specific error codes (market plugins can extend this)
    """
    
    def __init__(self, exception_context: Optional[_ExceptionClassificationContext] = None):
        """
        Initialize error classifier.
        
        Args:
            exception_context: Optional context for exception classification, used for testing/override.
        """
        # Inject the context to manage complex classification logic
        self._exception_context = exception_context or _ExceptionClassificationContext(_DEFAULT_STRATEGIES)
        logger.debug("Error classifier initialized")
    
    def classify_http_error(self, status_code: int, response_text: Optional[str] = None) -> ErrorCategory:
        """
        Classify HTTP error by status code.
        
        Args:
            status_code: HTTP status code
            response_text: Optional response body text
            
        Returns:
            ErrorCategory enum value
        """
        # 4xx Client Errors
        if 400 <= status_code < 500:
            if status_code == 401 or status_code == 403:
                return ErrorCategory.AUTHENTICATION_ERROR
            elif status_code == 404:
                return ErrorCategory.NOT_FOUND_ERROR
            elif status_code == 429:
                return ErrorCategory.RATE_LIMIT_ERROR
            elif status_code == 400:
                return ErrorCategory.VALIDATION_ERROR
            else:
                return ErrorCategory.PERMANENT_ERROR
        
        # 5xx Server Errors
        elif 500 <= status_code < 600:
            if status_code == 503:
                return ErrorCategory.TEMPORARY_ERROR
            elif status_code == 504:
                return ErrorCategory.TIMEOUT_ERROR
            else:
                return ErrorCategory.SERVER_ERROR
        
        # Other codes
        else:
            return ErrorCategory.UNKNOWN_ERROR
    
    def classify_exception(self, exception: Exception) -> ErrorCategory:
        """
        Classify exception by type.
        
        This method delegates the classification logic to the internal context, 
        significantly reducing its internal complexity.
        
        Args:
            exception: Exception object
            
        Returns:
            ErrorCategory enum value
        """
        return self._exception_context.classify(exception)

    
    def is_retryable(self, error_category: ErrorCategory) -> bool:
        """
        Determine if error is retryable.
        
        Args:
            error_category: Error category
            
        Returns:
            True if error should be retried, False otherwise
        """
        retryable_categories = {
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.TIMEOUT_ERROR,
            ErrorCategory.RATE_LIMIT_ERROR,
            ErrorCategory.TEMPORARY_ERROR,
            ErrorCategory.SERVER_ERROR
        }
        
        return error_category in retryable_categories
    
    def get_retry_delay(
        self, 
        error_category: ErrorCategory, 
        attempt_number: int = 1,
        retry_after: Optional[int] = None
    ) -> int:
        """
        Get recommended retry delay in seconds.
        
        Args:
            error_category: Error category
            attempt_number: Current attempt number (1-based, ensures >= 1)
            retry_after: Optional retry-after value from API response (overrides backoff)
            
        Returns:
            Delay in seconds (capped at 300)
        """
        if attempt_number < 1:
             logger.warning("Attempt number less than 1 provided for retry delay. Resetting to 1.")
             attempt_number = 1
             
        # Use retry-after header if provided
        if retry_after is not None and retry_after > 0:
            return retry_after
        
        # Exponential backoff based on error type
        base_delays = {
            ErrorCategory.NETWORK_ERROR: 5,
            ErrorCategory.TIMEOUT_ERROR: 10,
            ErrorCategory.RATE_LIMIT_ERROR: 60,
            ErrorCategory.TEMPORARY_ERROR: 30,
            ErrorCategory.SERVER_ERROR: 15
        }
        
        base_delay = base_delays.get(error_category, 10)
        
        # Exponential backoff: base_delay * (2 ^ (attempt - 1))
        # Capped at 300 seconds (5 minutes)
        delay = min(base_delay * (2 ** (attempt_number - 1)), 300)
        
        return delay
    
    def extract_retry_after(self, response_headers: Optional[Dict[str, str]] = None) -> Optional[int]:
        """
        Extract retry-after value from response headers.
        
        Args:
            response_headers: HTTP response headers
            
        Returns:
            Retry-after value in seconds, or None if not present or unparseable.
        """
        if not response_headers:
            return None
        
        # Check for Retry-After header (case-insensitive)
        for key, value in response_headers.items():
            if key.lower() == 'retry-after':
                try:
                    # Can be either seconds (int) or HTTP date
                    return int(value)
                except ValueError:
                    # HTTP date format - rely on backoff logic
                    logger.debug(f"Non-integer Retry-After header found: {value}")
                    return None
        
        return None
    
    def create_error_report(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create standardized error report.
        
        Args:
            error: Exception object
            context: Optional context information
            
        Returns:
            Error report dictionary
        """
        category = self.classify_exception(error)
        
        report = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_category': category.value,
            'is_retryable': self.is_retryable(category),
            'context': context or {}
        }
        
        return report


# Global error classifier instance
error_classifier = ErrorClassifier()


# Convenience functions (kept intact for system compatibility)
def classify_http_error(status_code: int, response_text: Optional[str] = None) -> ErrorCategory:
    """Classify HTTP error by status code."""
    return error_classifier.classify_http_error(status_code, response_text)


def classify_exception(exception: Exception) -> ErrorCategory:
    """Classify exception by type."""
    return error_classifier.classify_exception(exception)


def is_retryable_error(error_category: ErrorCategory) -> bool:
    """Determine if error is retryable."""
    return error_classifier.is_retryable(error_category)


def get_retry_delay(error_category: ErrorCategory, attempt_number: int = 1) -> int:
    """Get recommended retry delay in seconds."""
    return error_classifier.get_retry_delay(error_category, attempt_number)