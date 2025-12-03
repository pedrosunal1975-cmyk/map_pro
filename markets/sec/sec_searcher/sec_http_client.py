# File: /map_pro/markets/sec/sec_searcher/sec_http_client.py

"""
SEC HTTP Client
===============

Core HTTP client for SEC EDGAR API requests.
Handles low-level HTTP operations with proper session management.

Responsibilities:
- HTTP request execution
- Request header management
- Session lifecycle management
- URL construction
- Response retrieval
"""

import aiohttp
from typing import Dict, Any, Optional

from core.system_logger import get_logger
from .sec_api_constants import (
    DEFAULT_TIMEOUT_SECONDS,
    CONTENT_TYPE_JSON,
    HTTP_STATUS_OK
)

logger = get_logger(__name__, 'market')


class SECHTTPClient:
    """
    Low-level HTTP client for SEC API requests.
    
    Handles:
    - HTTP session management (session-per-request pattern)
    - Request header construction
    - URL building
    - Response retrieval
    - Timeout configuration
    """
    
    def __init__(self, user_agent: str, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        """
        Initialize HTTP client.
        
        Args:
            user_agent: User-Agent header value (required by SEC)
            timeout: Request timeout in seconds
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.logger = logger
    
    def build_headers(self) -> Dict[str, str]:
        """
        Build HTTP headers for SEC request.
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            'User-Agent': self.user_agent,
            'Accept': CONTENT_TYPE_JSON,
            'Accept-Encoding': 'gzip, deflate',
        }
    
    def build_full_url(self, url: str, base_url: str) -> str:
        """
        Build full URL from relative or absolute path.
        
        Args:
            url: URL or path
            base_url: Base URL for relative paths
            
        Returns:
            Full URL string
        """
        if url.startswith('http'):
            return url
        return f"{base_url}/{url.lstrip('/')}"
    
    def create_timeout(self) -> aiohttp.ClientTimeout:
        """
        Create aiohttp timeout configuration.
        
        Returns:
            ClientTimeout object
        """
        return aiohttp.ClientTimeout(total=self.timeout)
    
    async def execute_get_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> aiohttp.ClientResponse:
        """
        Execute HTTP GET request.
        
        Args:
            url: Full URL to request
            params: Optional query parameters
            
        Returns:
            aiohttp ClientResponse object
            
        Note:
            Caller is responsible for managing the response context
        """
        headers = self.build_headers()
        timeout = self.create_timeout()
        
        session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
        
        return await session.get(url, params=params)
    
    async def execute_head_request(
        self,
        url: str,
        allow_redirects: bool = True
    ) -> aiohttp.ClientResponse:
        """
        Execute HTTP HEAD request.
        
        Args:
            url: Full URL to check
            allow_redirects: Whether to follow redirects
            
        Returns:
            aiohttp ClientResponse object
            
        Note:
            Caller is responsible for managing the response context
        """
        headers = self.build_headers()
        timeout = self.create_timeout()
        
        session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
        
        return await session.head(url, allow_redirects=allow_redirects)
    
    async def fetch_response_text(
        self,
        response: aiohttp.ClientResponse
    ) -> str:
        """
        Fetch response text from aiohttp response.
        
        Args:
            response: aiohttp response object
            
        Returns:
            Response body as text
        """
        return await response.text()
    
    def check_status_ok(self, response: aiohttp.ClientResponse) -> bool:
        """
        Check if response status is OK (200).
        
        Args:
            response: aiohttp response object
            
        Returns:
            True if status is 200
        """
        return response.status == HTTP_STATUS_OK
    
    async def close(self):
        """
        Close HTTP client resources.
        
        Note:
            With session-per-request pattern, no persistent resources to close
        """
        self.logger.debug("HTTP client cleanup completed")


__all__ = ['SECHTTPClient']