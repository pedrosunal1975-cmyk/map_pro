# File: /map_pro/markets/sec/sec_searcher/sec_error_handler.py

"""
SEC API Error Handler
======================

Handles HTTP errors and retry logic for SEC EDGAR API requests.
Separates error handling concerns from HTTP client logic.

Responsibilities:
- Process HTTP error status codes
- Implement retry logic with exponential backoff
- Classify and log errors appropriately
- Generate user-friendly error messages
"""

import asyncio
from typing import Optional
import aiohttp

from core.system_logger import get_logger
from .sec_api_constants import (
    HTTP_STATUS_NOT_FOUND,
    MAX_REQUEST_RETRIES,
    BASE_RETRY_DELAY_SECONDS,
    SEC_ERROR_MESSAGES,
    ERROR_MSG_RESOURCE_NOT_FOUND,
    ERROR_MSG_HTTP_ERROR
)

logger = get_logger(__name__, 'market')


class ErrorSeverity:
    """Classification of error severity levels."""
    FATAL = 'fatal'          # Don't retry (404, invalid request)
    TRANSIENT = 'transient'  # Retry possible (network, timeout)
    UNKNOWN = 'unknown'      # Unknown error type


class SECErrorHandler:
    """
    Handler for SEC API HTTP errors and retry logic.
    
    Handles:
    - HTTP status code processing
    - Error classification by severity
    - Retry logic with exponential backoff
    - Error logging and user messaging
    """
    
    def __init__(self):
        """Initialize SEC error handler."""
        self.logger = logger
    
    async def handle_error_status(
        self,
        response: aiohttp.ClientResponse,
        url: str,
        attempt: int
    ) -> None:
        """
        Handle non-200 HTTP status codes.
        
        Args:
            response: aiohttp response object
            url: Request URL for logging
            attempt: Current attempt number (0-indexed)
            
        Raises:
            FileNotFoundError: If status is 404
            aiohttp.ClientError: For other error statuses
        """
        status_code = response.status
        error_message = self._get_error_message(status_code)
        
        self.logger.error(f"SEC API error: {error_message} - {url}")
        
        # Check if this is a fatal error (don't retry)
        if self._is_fatal_error(status_code):
            self._handle_fatal_error(status_code, url)
            return
        
        # Handle retryable errors
        if self._should_retry(attempt):
            await self._schedule_retry(attempt, error_message)
            raise aiohttp.ClientError(f"HTTP {status_code}")
        
        # Max retries reached, raise for status
        response.raise_for_status()
    
    def _get_error_message(self, status_code: int) -> str:
        """
        Get error message for HTTP status code.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            Error message string
        """
        return SEC_ERROR_MESSAGES.get(
            status_code,
            ERROR_MSG_HTTP_ERROR.format(status=status_code)
        )
    
    def _is_fatal_error(self, status_code: int) -> bool:
        """
        Check if error is fatal (should not retry).
        
        Args:
            status_code: HTTP status code
            
        Returns:
            True if error is fatal
        """
        fatal_codes = {
            HTTP_STATUS_NOT_FOUND,  # 404
            400,  # Bad Request
            401,  # Unauthorized
            403   # Forbidden
        }
        return status_code in fatal_codes
    
    def _handle_fatal_error(self, status_code: int, url: str) -> None:
        """
        Handle fatal error that should not be retried.
        
        Args:
            status_code: HTTP status code
            url: Request URL
            
        Raises:
            FileNotFoundError: For 404 errors
        """
        if status_code == HTTP_STATUS_NOT_FOUND:
            raise FileNotFoundError(ERROR_MSG_RESOURCE_NOT_FOUND.format(url=url))
    
    def _should_retry(self, attempt: int) -> bool:
        """
        Determine if request should be retried.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            True if should retry
        """
        return attempt < MAX_REQUEST_RETRIES - 1
    
    async def _schedule_retry(self, attempt: int, error_message: str) -> None:
        """
        Schedule retry with exponential backoff.
        
        Args:
            attempt: Current attempt number
            error_message: Error message for logging
        """
        delay = self._calculate_retry_delay(attempt)
        self.logger.warning(
            f"{error_message}, retrying in {delay}s..."
        )
        await asyncio.sleep(delay)
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        return BASE_RETRY_DELAY_SECONDS
    
    async def handle_retry(
        self,
        error: Exception,
        attempt: int,
        context: str
    ) -> None:
        """
        Handle retry logic with exponential backoff.
        
        Args:
            error: Exception that triggered retry
            attempt: Current attempt number (0-indexed)
            context: Context string for logging
        """
        delay = self._calculate_exponential_backoff(attempt)
        self.logger.warning(f"{context}: {error}, retrying in {delay}s...")
        await asyncio.sleep(delay)
    
    def _calculate_exponential_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        exponent = 2 ** attempt
        return BASE_RETRY_DELAY_SECONDS * exponent
    
    def classify_error_severity(self, error: Exception) -> str:
        """
        Classify error by severity.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error severity string (ErrorSeverity enum value)
        """
        if isinstance(error, FileNotFoundError):
            return ErrorSeverity.FATAL
        
        if isinstance(error, (asyncio.TimeoutError, aiohttp.ClientError)):
            return ErrorSeverity.TRANSIENT
        
        return ErrorSeverity.UNKNOWN
    
    def log_index_fetch_error(
        self,
        error: aiohttp.ClientError,
        accession_number: str
    ) -> None:
        """
        Log index.json fetch error appropriately.
        
        Args:
            error: Client error that occurred
            accession_number: Accession number for context
        """
        error_msg = str(error)
        error_lower = error_msg.lower()
        
        if ERROR_KEYWORD_RATE_LIMIT in error_lower:
            self.logger.warning(f"Rate limit hit for {accession_number}")
        else:
            self.logger.debug(
                f"Network error fetching index.json for {accession_number}: {error}"
            )


# Import ERROR_KEYWORD_RATE_LIMIT for rate limit detection
from .sec_api_constants import ERROR_KEYWORD_RATE_LIMIT


__all__ = ['SECErrorHandler', 'ErrorSeverity']