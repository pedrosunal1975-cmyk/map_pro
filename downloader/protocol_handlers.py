"""
Map Pro Protocol Handlers
=========================

Protocol-specific download handlers for HTTP, HTTPS, FTP.
Each handler knows how to download from its specific protocol.
"""

import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import aiohttp
import asyncio

from core.system_logger import get_logger
from .download_result import DownloadResult
from .stream_handler import StreamHandler
from .retry_manager import RetryManager, RetryConfig

logger = get_logger(__name__, 'engine')


class BaseProtocolHandler(ABC):
    """
    Abstract base class for protocol handlers.
    
    All protocol handlers must implement the download method.
    """
    
    def __init__(self, retry_manager: Optional[RetryManager] = None):
        """
        Initialize protocol handler.
        
        Args:
            retry_manager: Retry manager (creates default if None)
        """
        self.retry_manager = retry_manager or RetryManager(RetryConfig(max_retries=3))
        self.logger = logger
    
    @abstractmethod
    async def download(self, url: str, save_path: Path, custom_headers: Optional[Dict[str, str]] = None) -> DownloadResult:
        """
        Download file from URL to save_path.
        
        Args:
            url: Source URL
            save_path: Destination path
            
        Returns:
            DownloadResult with download status
        """
        pass
    
    def get_protocol(self, url: str) -> str:
        """Extract protocol from URL."""
        parsed = urlparse(url)
        return parsed.scheme.lower()


class HTTPHandler(BaseProtocolHandler):
    """
    HTTP/HTTPS download handler using aiohttp.
    
    Features:
    - Streaming downloads (memory-efficient)
    - Automatic retry with exponential backoff
    - User-agent and custom headers support
    - Timeout configuration
    - Progress tracking
    """
    
    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: int = 30,
        chunk_size: int = 8192,
        retry_manager: Optional[RetryManager] = None
    ):
        """
        Initialize HTTP handler.
        
        Args:
            user_agent: User-Agent header (uses default if None)
            timeout: Request timeout in seconds
            chunk_size: Download chunk size in bytes
            retry_manager: Retry manager
        """
        super().__init__(retry_manager)
        
        # Get user-agent from env or use default
        self.user_agent = user_agent or os.getenv(
            'MAP_PRO_USER_AGENT',
            'MapPro/1.0 (+https://github.com/mapro)'
        )
        
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.stream_handler = StreamHandler(chunk_size=chunk_size)
        
        # Session will be created when needed
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate',
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("HTTP session closed")
    
    async def download(self, url: str, save_path: Path, custom_headers: Optional[Dict[str, str]] = None) -> DownloadResult:
        """
        Download file via HTTP/HTTPS.
        
        Args:
            url: Source URL
            save_path: Destination file path
            custom_headers: Optional custom headers for the request
            
        Returns:
            DownloadResult with download status and metrics
        """
        start_time = time.time()
        result = DownloadResult(
            success=False,
            file_path=save_path,
            protocol=self.get_protocol(url)
        )
        
        try:
            self.logger.info(f"Starting HTTP download: {url}")
            
            # Define the download operation
            async def download_operation():
                # Merge custom headers with default headers
                all_headers = {
                    'User-Agent': self.user_agent,
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                }
                if custom_headers:
                    all_headers.update(custom_headers)
                
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(
                    headers=all_headers,
                    timeout=timeout
                ) as session:
                    async with session.get(url) as response:
                        # Check HTTP status
                        result.http_status = response.status
                        
                        if response.status != 200:
                            raise aiohttp.ClientError(
                                f"HTTP {response.status}: {response.reason}"
                            )
                        
                        # Get content length if available
                        total_size = None
                        if 'Content-Length' in response.headers:
                            total_size = int(response.headers['Content-Length'])
                        
                        # Stream to file
                        bytes_downloaded = await self.stream_handler.stream_to_file(
                            response,
                            save_path,
                            total_size
                        )
                        
                        return bytes_downloaded
            
            # Execute with retry
            bytes_downloaded = await self.retry_manager.execute_with_retry(
                download_operation,
                f"HTTP download: {url}"
            )
            
            # Calculate metrics
            duration = time.time() - start_time
            
            # Update result
            result.success = True
            result.file_size_bytes = bytes_downloaded
            result.duration_seconds = duration
            
            self.logger.info(
                f"HTTP download completed: {save_path.name} - "
                f"{result.file_size_mb:.2f}MB at {result.download_speed_mbps:.2f}MB/s in {duration:.1f}s"
            )
            
        except aiohttp.ClientError as e:
            result.error_message = f"HTTP error: {str(e)}"
            result.duration_seconds = time.time() - start_time
            self.logger.error(f"HTTP download failed: {url} - {str(e)}")
            
        except asyncio.TimeoutError:
            result.error_message = f"Download timeout after {self.timeout}s"
            result.duration_seconds = time.time() - start_time
            self.logger.error(f"HTTP download timeout: {url}")
            
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
            result.duration_seconds = time.time() - start_time
            self.logger.error(f"HTTP download error: {url} - {type(e).__name__}: {str(e)}")
        
        return result

class HTTPSHandler(HTTPHandler):
    """
    HTTPS download handler (extends HTTP with SSL verification).
    
    Inherits all HTTP functionality with added SSL certificate validation.
    """
    
    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: int = 30,
        chunk_size: int = 8192,
        verify_ssl: bool = True,
        retry_manager: Optional[RetryManager] = None
    ):
        """
        Initialize HTTPS handler.
        
        Args:
            user_agent: User-Agent header
            timeout: Request timeout in seconds
            chunk_size: Download chunk size in bytes
            verify_ssl: Whether to verify SSL certificates
            retry_manager: Retry manager
        """
        super().__init__(user_agent, timeout, chunk_size, retry_manager)
        self.verify_ssl = verify_ssl
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with SSL configuration."""
        if self._session is None or self._session.closed:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate',
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            # SSL context configuration
            import ssl
            ssl_context = ssl.create_default_context()
            if not self.verify_ssl:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                self.logger.warning("SSL verification disabled")
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                connector=connector
            )
        
        return self._session


class FTPHandler(BaseProtocolHandler):
    """
    FTP download handler.
    
    Placeholder for future FTP support (some regulatory markets use FTP).
    Currently not implemented - returns error result.
    """
    
    async def download(self, url: str, save_path: Path, custom_headers: Optional[Dict[str, str]] = None) -> DownloadResult:
        """
        Download file via FTP.
        
        Args:
            url: FTP URL
            save_path: Destination file path
            
        Returns:
            DownloadResult (currently always fails - not implemented)
        """
        result = DownloadResult(
            success=False,
            file_path=save_path,
            protocol='ftp',
            error_message="FTP downloads not yet implemented"
        )
        
        self.logger.warning(f"FTP download requested but not implemented: {url}")
        
        # TODO: Implement FTP download using aioftp or similar
        # Will be needed for some regulatory markets
        
        return result


class ProtocolHandlerFactory:
    """
    Factory for creating appropriate protocol handlers.
    
    Detects protocol from URL and returns correct handler.
    """
    
    def __init__(
        self,
        default_timeout: int = 30,
        default_chunk_size: int = 8192,
        user_agent: Optional[str] = None
    ):
        """
        Initialize factory.
        
        Args:
            default_timeout: Default timeout for handlers
            default_chunk_size: Default chunk size
            user_agent: Default user-agent string
        """
        self.default_timeout = default_timeout
        self.default_chunk_size = default_chunk_size
        self.user_agent = user_agent
        
        # Cache handlers for reuse
        self._handlers: Dict[str, BaseProtocolHandler] = {}
        
        self.logger = logger
    
    def get_handler(self, url: str) -> BaseProtocolHandler:
        """
        Get appropriate handler for URL protocol.
        
        Args:
            url: URL to download
            
        Returns:
            Protocol handler instance
            
        Raises:
            ValueError: If protocol not supported
        """
        parsed = urlparse(url)
        protocol = parsed.scheme.lower()
        
        # Return cached handler if exists
        if protocol in self._handlers:
            return self._handlers[protocol]
        
        # Create new handler
        if protocol == 'http':
            handler = HTTPHandler(
                user_agent=self.user_agent,
                timeout=self.default_timeout,
                chunk_size=self.default_chunk_size
            )
        elif protocol == 'https':
            handler = HTTPSHandler(
                user_agent=self.user_agent,
                timeout=self.default_timeout,
                chunk_size=self.default_chunk_size,
                verify_ssl=True
            )
        elif protocol in ['ftp', 'ftps']:
            handler = FTPHandler()
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
        
        # Cache handler
        self._handlers[protocol] = handler
        
        self.logger.debug(f"Created {protocol.upper()} handler for {url}")
        
        return handler
    
    async def close_all(self):
        """Close all cached handlers."""
        for protocol, handler in self._handlers.items():
            if hasattr(handler, 'close'):
                await handler.close()
                self.logger.debug(f"Closed {protocol.upper()} handler")
        
        self._handlers.clear()