# File: /map_pro/markets/sec/sec_searcher/sec_api_client.py

"""
SEC EDGAR API Client
====================

High-level HTTP client for SEC EDGAR API with proper rate limiting and error handling.
Handles user-agent requirements, rate limiting, and retry logic.

This module provides a clean interface to the SEC EDGAR API by orchestrating
specialized components for HTTP operations, response parsing, error handling,
and URL construction.

Features:
- HTML response detection and handling
- Proper error classification (not found vs rate limit vs invalid JSON)
- Intelligent logging (info for expected failures, warnings for problems)
- Session-per-request pattern to avoid event loop issues
- Automatic retry with exponential backoff

Architecture:
- SECAPIClient: High-level API facade
- SECHTTPClient: Low-level HTTP operations
- SECRequestExecutor: Request execution with retry
- SECResponseParser: Response parsing and validation
- SECErrorHandler: Error handling and retry logic
- SECURLBuilder: URL construction
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# Optional .env file loading
# Only log if in development/debug mode to avoid noise in production
_env_loaded = False
try:
    from dotenv import load_dotenv
    from core.data_paths import map_pro_paths
    
    env_file = map_pro_paths.program_root / '.env'
    if env_file.exists():
        load_dotenv(env_file, interpolate=True)
        _env_loaded = True
        # Only log in debug mode
        if os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes'):
            logging.debug(f"Loaded environment variables from {env_file}")
    else:
        # Only log in debug mode
        if os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes'):
            logging.debug(f"No .env file found at {env_file}")
            
except ImportError as e:
    # python-dotenv not installed - this is fine for production
    # Only log in debug mode to avoid unnecessary warnings
    if os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes'):
        logging.debug(f"python-dotenv not available: {e}. Using system environment variables only.")
        
except Exception as e:
    # Unexpected error loading environment - this should be logged
    logging.warning(f"Unexpected error loading .env file: {type(e).__name__}: {e}")

import aiohttp

from core.system_logger import get_logger
from .sec_api_constants import (
    SEC_BASE_URL,
    DEFAULT_USER_AGENT,
    ENV_USER_AGENT_KEY,
    DEFAULT_TIMEOUT_SECONDS,
    CIK_LENGTH
)
from .sec_http_client import SECHTTPClient
from .sec_request_executor import SECRequestExecutor
from .sec_response_parser import SECResponseParser
from .sec_error_handler import SECErrorHandler
from .sec_url_builder import SECURLBuilder

logger = get_logger(__name__, 'market')


class SECAPIClient:
    """
    High-level HTTP client for SEC EDGAR API.
    
    This class provides a clean, easy-to-use interface for accessing SEC data.
    It delegates specialized responsibilities to focused components while
    maintaining backward compatibility with existing code.
    
    Handles:
    - User-agent header requirement
    - Rate limiting (10 requests/second)
    - Automatic retries with exponential backoff
    - Error classification and handling
    - HTML vs JSON response detection
    - Session-per-request pattern (no persistent sessions)
    """
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize SEC API client.
        
        Args:
            user_agent: User-Agent header value (required by SEC).
                       If None, will use environment variable or default.
        """
        self.user_agent = self._resolve_user_agent(user_agent)
        self.base_url = SEC_BASE_URL
        
        # Initialize specialized components
        self._http_client = SECHTTPClient(
            user_agent=self.user_agent,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )
        self._response_parser = SECResponseParser()
        self._error_handler = SECErrorHandler()
        self._request_executor = SECRequestExecutor(
            http_client=self._http_client,
            response_parser=self._response_parser,
            error_handler=self._error_handler
        )
        self._url_builder = SECURLBuilder(base_url=self.base_url)
        
        logger.info(f"SEC API client initialized with user agent: {self.user_agent}")
    
    def _resolve_user_agent(self, user_agent: Optional[str]) -> str:
        """
        Resolve user agent from parameter, environment, or default.
        
        Args:
            user_agent: Optional user agent override
            
        Returns:
            User agent string
        """
        if user_agent is not None:
            return user_agent
        
        env_user_agent = os.environ.get(ENV_USER_AGENT_KEY)
        if env_user_agent is not None:
            return env_user_agent
        
        logger.warning(
            f"Using default user agent for SEC API - "
            f"consider setting {ENV_USER_AGENT_KEY}"
        )
        return DEFAULT_USER_AGENT
    
    async def close(self):
        """
        Close HTTP client resources.
        
        Note: With session-per-request pattern, no persistent resources to close.
        """
        await self._http_client.close()
        logger.debug("SEC API client cleanup completed")
    
    async def get(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make GET request to SEC API with automatic retry.
        
        Args:
            url: Full URL or path relative to base_url
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            FileNotFoundError: If resource not found (404)
            aiohttp.ClientError: On request failure after retries
        """
        full_url = self._http_client.build_full_url(url, self.base_url)
        return await self._request_executor.execute_request(full_url, params)
    
    async def get_company_tickers(self) -> Dict[str, Any]:
        """
        Get company tickers JSON from SEC.
        
        This file contains ticker-to-CIK mappings for all public companies.
        
        Returns:
            Dictionary with company ticker information
            
        Raises:
            aiohttp.ClientError: On request failure
        """
        url = self._url_builder.build_company_tickers_url()
        return await self._request_executor.execute_request(url)
    
    async def get_submissions(self, cik: str) -> Dict[str, Any]:
        """
        Get company submissions (filings) from SEC.
        
        Args:
            cik: CIK (any length, will be formatted to 10 digits)
            
        Returns:
            Dictionary with company filing information
            
        Raises:
            FileNotFoundError: If company not found
            aiohttp.ClientError: On request failure
        """
        url = self._url_builder.build_submissions_url(cik)
        return await self._request_executor.execute_request(url)
    
    async def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """
        Get company XBRL facts from SEC.
        
        Args:
            cik: CIK (any length, will be formatted to 10 digits)
            
        Returns:
            Dictionary with XBRL facts
            
        Raises:
            FileNotFoundError: If company facts not found
            aiohttp.ClientError: On request failure
        """
        url = self._url_builder.build_company_facts_url(cik)
        return await self._request_executor.execute_request(url)
    
    async def get_filing_index(
        self,
        cik: str,
        accession_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get filing index.json which lists all documents in a filing.
        
        CRITICAL: Many filings don't have index.json files. This is NORMAL.
        We handle it gracefully by returning None WITHOUT any warnings.
        
        Args:
            cik: CIK with leading zeros
            accession_number: Filing accession number (with dashes)
            
        Returns:
            Dictionary with filing index or None if not found
        """
        url = self._url_builder.build_filing_index_url(cik, accession_number)
        
        try:
            response_data = await self._fetch_index_json_safely(url, accession_number)
            return response_data
            
        except FileNotFoundError:
            logger.debug(f"index.json not found for {accession_number}")
            return None
        
        except aiohttp.ClientError as e:
            self._error_handler.log_index_fetch_error(e, accession_number)
            return None
        
        except Exception as e:
            logger.debug(
                f"Unexpected error fetching index.json for {accession_number}: "
                f"{type(e).__name__}: {e}"
            )
            return None
    
    async def _fetch_index_json_safely(
        self,
        url: str,
        accession_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse index.json file with minimal error handling.
        
        Args:
            url: Full URL to index.json
            accession_number: Accession number for logging context
            
        Returns:
            Parsed JSON or None if not found/invalid
            
        Raises:
            FileNotFoundError: If index.json not found (404 or HTML response)
            aiohttp.ClientError: On network error
        """
        logger.debug(f"GET {url}")
        
        async with aiohttp.ClientSession(
            headers=self._http_client.build_headers(),
            timeout=self._http_client.create_timeout()
        ) as session:
            async with session.get(url) as response:
                return await self._process_index_response(
                    response,
                    accession_number
                )
    
    async def _process_index_response(
        self,
        response: aiohttp.ClientResponse,
        accession_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process index.json response.
        
        Args:
            response: aiohttp response object
            accession_number: Accession number for logging
            
        Returns:
            Parsed JSON or None if invalid
            
        Raises:
            FileNotFoundError: If not found or HTML response
        """
        from .sec_api_constants import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
        
        if response.status == HTTP_STATUS_NOT_FOUND:
            raise FileNotFoundError("index.json not found (404)")
        
        if response.status != HTTP_STATUS_OK:
            logger.debug(
                f"index.json request failed with status {response.status}"
            )
            return None
        
        response_text = await response.text()
        
        # Check for HTML response
        content_type = self._response_parser.detect_content_type(
            response,
            response_text
        )
        
        from .sec_response_parser import ResponseContentType
        if content_type == ResponseContentType.HTML:
            logger.debug("index.json returned HTML (file doesn't exist)")
            raise FileNotFoundError("index.json returned HTML")
        
        # Parse JSON
        try:
            import json
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.debug(f"index.json contains invalid JSON: {e}")
            return None
    
    async def check_url_exists(self, url: str) -> bool:
        """
        Check if a URL exists using HEAD request.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL exists (HTTP 200), False otherwise
        """
        try:
            async with aiohttp.ClientSession(
                headers=self._http_client.build_headers(),
                timeout=self._http_client.create_timeout()
            ) as session:
                async with session.head(url, allow_redirects=True) as response:
                    from .sec_api_constants import HTTP_STATUS_OK
                    return response.status == HTTP_STATUS_OK
                
        except Exception as e:
            logger.debug(f"URL check failed for {url}: {e}")
            return False
    
    async def search_company_by_name(
        self,
        company_name: str
    ) -> List[Dict[str, Any]]:
        """
        Search for company by name using company tickers file.
        
        Args:
            company_name: Company name to search
            
        Returns:
            List of matching companies with cik, ticker, and name
        """
        tickers_data = await self.get_company_tickers()
        
        matches = []
        search_term = company_name.lower()
        
        for key, company in tickers_data.items():
            if key == 'fields':
                continue
            
            company_title = company.get('title', '').lower()
            
            if search_term in company_title:
                cik_str = str(company.get('cik_str'))
                formatted_cik = self._url_builder.format_cik(cik_str)
                
                matches.append({
                    'cik': formatted_cik,
                    'ticker': company.get('ticker'),
                    'name': company.get('title')
                })
        
        return matches


def create_sec_client(user_agent: Optional[str] = None) -> SECAPIClient:
    """
    Create SEC API client with optional user-agent override.
    
    Factory function for creating properly configured SEC API client instances.
    
    Args:
        user_agent: Optional user agent string. If None, will use environment
                   variable or default value.
        
    Returns:
        Configured SECAPIClient instance
    """
    return SECAPIClient(user_agent)


__all__ = ['SECAPIClient', 'create_sec_client']