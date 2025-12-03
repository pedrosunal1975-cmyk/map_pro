"""
File: engines/searcher/url_parser.py
Path: engines/searcher/url_parser.py

URL Component Parser
===================

Handles extraction of URL components.
Extracted from URLValidator to follow Single Responsibility Principle.
"""

from typing import Optional, Dict
from urllib.parse import urlparse

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')


class URLParser:
    """
    Parses URLs and extracts components.
    
    Responsibilities:
    - Extract URL components
    - Provide structured component data
    """
    
    def __init__(self) -> None:
        """Initialize URL parser."""
        logger.debug("URL parser initialized")
    
    def extract_components(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract URL components into structured dictionary.
        
        Args:
            url: URL to parse
            
        Returns:
            Dictionary with URL components:
                - scheme: URL scheme (http, https)
                - domain: Network location/domain
                - path: URL path
                - query: Query string
                - fragment: Fragment identifier
                - full_url: Complete original URL
            Returns None if parsing fails
        """
        if not url:
            return None
        
        try:
            parsed = urlparse(url)
            
            components = {
                'scheme': parsed.scheme,
                'domain': parsed.netloc,
                'path': parsed.path,
                'query': parsed.query,
                'fragment': parsed.fragment,
                'full_url': url
            }
            
            return components
            
        except (ValueError, AttributeError) as e:
            logger.error(f"URL parsing failed for '{url}': {e}")
            return None