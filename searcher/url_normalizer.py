"""
File: engines/searcher/url_normalizer.py
Path: engines/searcher/url_normalizer.py

URL Normalization
================

Handles URL normalization to consistent format.
Extracted from URLValidator to follow Single Responsibility Principle.
"""

from typing import Optional, Set
from urllib.parse import urlparse, urlunparse

from core.system_logger import get_logger
from engines.searcher.url_constants import DEFAULT_URL_SCHEME

logger = get_logger(__name__, 'engine')


class URLNormalizer:
    """
    Normalizes URLs to consistent format.
    
    Responsibilities:
    - Add missing schemes
    - Convert domains to lowercase
    - Remove default ports
    - Rebuild URLs consistently
    """
    
    def __init__(self, default_ports: Set[str]) -> None:
        """
        Initialize URL normalizer.
        
        Args:
            default_ports: Set of default port strings to remove (e.g., ':80', ':443')
        """
        self.default_ports = default_ports
        
        logger.debug("URL normalizer initialized")
    
    def normalize(self, url: str) -> Optional[str]:
        """
        Normalize URL to consistent format.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL or None if normalization fails
        """
        if not url:
            return None
        
        url = url.strip()
        
        try:
            parsed = self._parse_with_default_scheme(url)
            netloc = self._normalize_netloc(parsed.netloc)
            
            normalized = urlunparse((
                parsed.scheme.lower(),
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            return normalized
            
        except (ValueError, AttributeError) as e:
            logger.error(f"URL normalization failed for '{url}': {e}")
            return None
    
    def _parse_with_default_scheme(self, url: str) -> urlparse:
        """
        Parse URL, adding default scheme if missing.
        
        Args:
            url: URL to parse
            
        Returns:
            Parsed URL object
        """
        parsed = urlparse(url)
        
        if not parsed.scheme:
            url = f"{DEFAULT_URL_SCHEME}://{url}"
            parsed = urlparse(url)
        
        return parsed
    
    def _normalize_netloc(self, netloc: str) -> str:
        """
        Normalize network location (domain and port).
        
        Args:
            netloc: Network location to normalize
            
        Returns:
            Normalized network location
        """
        netloc = netloc.lower()
        netloc = self._remove_default_ports(netloc)
        return netloc
    
    def _remove_default_ports(self, netloc: str) -> str:
        """
        Remove default ports from network location.
        
        Args:
            netloc: Network location that may include port
            
        Returns:
            Network location without default ports
        """
        for port in self.default_ports:
            netloc = netloc.replace(port, '')
        return netloc