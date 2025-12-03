# File: /map_pro/markets/sec/sec_searcher/sec_response_parser.py

"""
SEC API Response Parser
========================

Handles parsing and validation of HTTP responses from SEC EDGAR API.
Separates response processing logic from HTTP client logic.

Responsibilities:
- Detect response content types (HTML vs JSON)
- Parse JSON responses with error handling
- Classify error responses
- Generate appropriate exceptions
"""

import json
from typing import Dict, Any
import aiohttp

from core.system_logger import get_logger
from .sec_api_constants import (
    CONTENT_TYPE_HTML,
    HTML_DOCTYPE_PREFIX,
    HTML_TAG_PREFIX,
    ERROR_KEYWORD_NOT_FOUND,
    ERROR_KEYWORD_404,
    ERROR_KEYWORD_RATE_LIMIT,
    ERROR_KEYWORD_TOO_MANY_REQUESTS,
    MAX_RESPONSE_PREVIEW_LENGTH,
    ERROR_MSG_RESOURCE_NOT_FOUND,
    ERROR_MSG_RATE_LIMIT_EXCEEDED,
    ERROR_MSG_HTML_RESPONSE,
    ERROR_MSG_INVALID_JSON
)

logger = get_logger(__name__, 'market')


class ResponseContentType:
    """Enumeration of response content types."""
    JSON = 'json'
    HTML = 'html'
    UNKNOWN = 'unknown'


class SECResponseParser:
    """
    Parser for SEC API HTTP responses.
    
    Handles:
    - Content type detection
    - JSON parsing with error handling
    - HTML response classification
    - Error response analysis
    """
    
    def __init__(self):
        """Initialize SEC response parser."""
        self.logger = logger
    
    def detect_content_type(
        self,
        response: aiohttp.ClientResponse,
        response_text: str
    ) -> str:
        """
        Detect response content type.
        
        Args:
            response: aiohttp response object
            response_text: Response body text
            
        Returns:
            Content type string (ResponseContentType enum value)
        """
        if self._is_html_response(response, response_text):
            return ResponseContentType.HTML
        
        if self._is_json_response(response, response_text):
            return ResponseContentType.JSON
        
        return ResponseContentType.UNKNOWN
    
    def _is_html_response(
        self,
        response: aiohttp.ClientResponse,
        response_text: str
    ) -> bool:
        """
        Check if response is HTML instead of JSON.
        
        Args:
            response: aiohttp response object
            response_text: Response body text
            
        Returns:
            True if response is HTML
        """
        content_type = response.headers.get('Content-Type', '').lower()
        
        if CONTENT_TYPE_HTML in content_type:
            return True
        
        text_start = response_text.strip()
        if text_start.startswith(HTML_DOCTYPE_PREFIX) or text_start.startswith(HTML_TAG_PREFIX):
            return True
        
        return False
    
    def _is_json_response(
        self,
        response: aiohttp.ClientResponse,
        response_text: str
    ) -> bool:
        """
        Check if response appears to be JSON.
        
        Args:
            response: aiohttp response object
            response_text: Response body text
            
        Returns:
            True if response appears to be JSON
        """
        text_start = response_text.strip()
        return text_start.startswith('{') or text_start.startswith('[')
    
    def parse_json_response(
        self,
        response_text: str,
        url: str,
        attempt: int
    ) -> Dict[str, Any]:
        """
        Parse JSON response text.
        
        Args:
            response_text: Response body text
            url: Request URL for logging
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            aiohttp.ClientError: If JSON parsing fails
        """
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            self._handle_json_parse_error(e, response_text, url, attempt)
            raise aiohttp.ClientError(ERROR_MSG_INVALID_JSON.format(error=str(e)))
    
    def _handle_json_parse_error(
        self,
        error: json.JSONDecodeError,
        response_text: str,
        url: str,
        attempt: int
    ) -> None:
        """
        Handle JSON parsing error with appropriate logging.
        
        Args:
            error: JSON decode error
            response_text: Response text that failed to parse
            url: Request URL for context
            attempt: Current attempt number
        """
        preview = self._create_response_preview(response_text)
        self.logger.error(
            f"Invalid JSON from {url}: {error}. Preview: {preview}"
        )
        
        if attempt < 2:  # Less than max retries - 1
            self.logger.warning("JSON parse error, will retry...")
    
    def _create_response_preview(self, response_text: str) -> str:
        """
        Create a preview of response text for logging.
        
        Args:
            response_text: Full response text
            
        Returns:
            Truncated and sanitized preview string
        """
        preview = response_text[:MAX_RESPONSE_PREVIEW_LENGTH]
        preview = preview.replace('\n', ' ')
        return preview
    
    def classify_html_error(
        self,
        response_text: str,
        url: str,
        attempt: int
    ) -> None:
        """
        Classify HTML error response and raise appropriate exception.
        
        Args:
            response_text: Response body text
            url: Request URL for logging
            attempt: Current attempt number
            
        Raises:
            FileNotFoundError: If HTML indicates not found
            aiohttp.ClientError: If HTML indicates rate limit
        """
        text_lower = response_text.lower()
        
        # Check for not found
        if self._is_not_found_error(text_lower):
            raise FileNotFoundError(ERROR_MSG_RESOURCE_NOT_FOUND.format(url=url))
        
        # Check for rate limit
        if self._is_rate_limit_error(text_lower):
            self._handle_rate_limit_error(url, attempt)
            raise aiohttp.ClientError(ERROR_MSG_RATE_LIMIT_EXCEEDED.format(url=url))
        
        # Generic HTML response (likely file doesn't exist)
        raise FileNotFoundError(ERROR_MSG_HTML_RESPONSE.format(url=url))
    
    def _is_not_found_error(self, text_lower: str) -> bool:
        """
        Check if text indicates a not found error.
        
        Args:
            text_lower: Lowercase response text
            
        Returns:
            True if text indicates not found
        """
        return (ERROR_KEYWORD_NOT_FOUND in text_lower or 
                ERROR_KEYWORD_404 in text_lower)
    
    def _is_rate_limit_error(self, text_lower: str) -> bool:
        """
        Check if text indicates a rate limit error.
        
        Args:
            text_lower: Lowercase response text
            
        Returns:
            True if text indicates rate limit
        """
        return (ERROR_KEYWORD_RATE_LIMIT in text_lower or 
                ERROR_KEYWORD_TOO_MANY_REQUESTS in text_lower)
    
    def _handle_rate_limit_error(self, url: str, attempt: int) -> None:
        """
        Handle rate limit error with appropriate logging.
        
        Args:
            url: Request URL
            attempt: Current attempt number
        """
        if attempt < 2:  # Less than max retries - 1
            from .sec_api_constants import (
                BASE_RETRY_DELAY_SECONDS,
                RATE_LIMIT_RETRY_MULTIPLIER
            )
            delay = BASE_RETRY_DELAY_SECONDS * RATE_LIMIT_RETRY_MULTIPLIER
            self.logger.warning(f"Rate limit hit, retrying in {delay}s...")


__all__ = ['SECResponseParser', 'ResponseContentType']