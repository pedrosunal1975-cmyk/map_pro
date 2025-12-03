# File: /map_pro/markets/sec/sec_searcher/sec_request_executor.py

"""
SEC Request Executor
====================

Executes SEC API requests with retry logic and error handling.
Orchestrates HTTP client, response parser, and error handler.

Responsibilities:
- Coordinate request execution
- Implement retry logic
- Process responses
- Handle errors appropriately
"""

from typing import Dict, Any, Optional
import aiohttp

from core.system_logger import get_logger
from .sec_http_client import SECHTTPClient
from .sec_response_parser import SECResponseParser, ResponseContentType
from .sec_error_handler import SECErrorHandler
from .sec_api_constants import (
    MAX_REQUEST_RETRIES,
    HTTP_STATUS_OK,
    ERROR_MSG_FAILED_AFTER_RETRIES
)

logger = get_logger(__name__, 'market')


class SECRequestExecutor:
    """
    Executor for SEC API requests with retry logic.
    
    Handles:
    - Request orchestration
    - Retry loop implementation
    - Response processing coordination
    - Error handling delegation
    """
    
    def __init__(
        self,
        http_client: SECHTTPClient,
        response_parser: SECResponseParser,
        error_handler: SECErrorHandler
    ):
        """
        Initialize request executor.
        
        Args:
            http_client: HTTP client for making requests
            response_parser: Parser for processing responses
            error_handler: Handler for errors and retries
        """
        self.http_client = http_client
        self.response_parser = response_parser
        self.error_handler = error_handler
        self.logger = logger
    
    async def execute_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute HTTP GET request with automatic retry.
        
        Args:
            url: Full URL to request
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            FileNotFoundError: If resource not found (404)
            aiohttp.ClientError: On request failure after retries
        """
        for attempt in range(MAX_REQUEST_RETRIES):
            try:
                result = await self._attempt_request(url, params, attempt)
                return result
                
            except FileNotFoundError:
                # Don't retry for 404s
                raise
            
            except aiohttp.ClientError as e:
                if not self._should_continue_retry(attempt):
                    raise
                await self.error_handler.handle_retry(e, attempt, "Request failed")
                continue
            
            except Exception as e:
                if not self._should_continue_retry(attempt):
                    raise
                await self.error_handler.handle_retry(e, attempt, "Unexpected error")
                continue
        
        raise aiohttp.ClientError(
            ERROR_MSG_FAILED_AFTER_RETRIES.format(retries=MAX_REQUEST_RETRIES)
        )
    
    def _should_continue_retry(self, attempt: int) -> bool:
        """
        Determine if should continue retrying.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            True if should continue retrying
        """
        return attempt < MAX_REQUEST_RETRIES - 1
    
    async def _attempt_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]],
        attempt: int
    ) -> Dict[str, Any]:
        """
        Attempt a single HTTP request.
        
        Args:
            url: Full URL to request
            params: Optional query parameters
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Parsed JSON response
            
        Raises:
            FileNotFoundError: If resource not found
            aiohttp.ClientError: On HTTP error
        """
        self._log_request_attempt(url, attempt)
        
        async with aiohttp.ClientSession(
            headers=self.http_client.build_headers(),
            timeout=self.http_client.create_timeout()
        ) as session:
            async with session.get(url, params=params) as response:
                return await self._process_response(response, url, attempt)
    
    def _log_request_attempt(self, url: str, attempt: int) -> None:
        """
        Log request attempt.
        
        Args:
            url: Request URL
            attempt: Current attempt number (0-indexed)
        """
        self.logger.debug(
            f"GET {url} (attempt {attempt + 1}/{MAX_REQUEST_RETRIES})"
        )
    
    async def _process_response(
        self,
        response: aiohttp.ClientResponse,
        url: str,
        attempt: int
    ) -> Dict[str, Any]:
        """
        Process HTTP response and handle errors.
        
        Args:
            response: aiohttp response object
            url: Request URL for logging
            attempt: Current attempt number
            
        Returns:
            Parsed JSON response
            
        Raises:
            FileNotFoundError: If resource not found
            aiohttp.ClientError: On HTTP error or invalid response
        """
        # Check HTTP status
        if response.status != HTTP_STATUS_OK:
            await self.error_handler.handle_error_status(response, url, attempt)
        
        # Get response text
        response_text = await response.text()
        
        # Detect content type
        content_type = self.response_parser.detect_content_type(
            response,
            response_text
        )
        
        # Handle HTML responses (usually errors)
        if content_type == ResponseContentType.HTML:
            self.response_parser.classify_html_error(
                response_text,
                url,
                attempt
            )
        
        # Parse JSON
        return self.response_parser.parse_json_response(
            response_text,
            url,
            attempt
        )


__all__ = ['SECRequestExecutor']