"""
File: engines/searcher/url_domain_validator.py
Path: engines/searcher/url_domain_validator.py

URL Domain Validation
====================

Handles domain name validation and trusted domain checking.
Extracted from URLValidator to follow Single Responsibility Principle.
"""

import re
from typing import Dict, List

from core.system_logger import get_logger
from engines.searcher.url_constants import (
    MAX_DOMAIN_LABEL_LENGTH,
    DOMAIN_LABEL_START_CHARS,
    DOMAIN_LABEL_MIDDLE_CHARS,
    DOMAIN_LABEL_END_CHARS,
    URL_PORT_SEPARATOR
)

logger = get_logger(__name__, 'engine')


class URLDomainValidator:
    """
    Validates domain names and checks trusted domain lists.
    
    Responsibilities:
    - Validate domain name format
    - Check domain against trusted lists
    - Handle subdomain matching
    """
    
    def __init__(self, trusted_domains: Dict[str, List[str]]) -> None:
        """
        Initialize domain validator.
        
        Args:
            trusted_domains: Dictionary mapping market types to trusted domain lists
        """
        self.trusted_domains = trusted_domains
        self._domain_pattern = self._build_domain_pattern()
        
        logger.debug("URL domain validator initialized")
    
    def _build_domain_pattern(self) -> re.Pattern:
        """
        Build compiled regex pattern for domain validation.
        
        Returns:
            Compiled regex pattern
        """
        pattern = (
            f'^[{DOMAIN_LABEL_START_CHARS}]'
            f'([{DOMAIN_LABEL_MIDDLE_CHARS}]{{0,{MAX_DOMAIN_LABEL_LENGTH}}}'
            f'[{DOMAIN_LABEL_END_CHARS}])?'
            f'(\\.[{DOMAIN_LABEL_START_CHARS}]'
            f'([{DOMAIN_LABEL_MIDDLE_CHARS}]{{0,{MAX_DOMAIN_LABEL_LENGTH}}}'
            f'[{DOMAIN_LABEL_END_CHARS}])?)*$'
        )
        return re.compile(pattern)
    
    def is_valid_domain(self, domain: str) -> bool:
        """
        Validate domain name format.
        
        Args:
            domain: Domain name to validate
            
        Returns:
            True if domain format is valid
        """
        if not domain:
            return False
        
        domain = self._strip_port(domain)
        
        return bool(self._domain_pattern.match(domain))
    
    def _strip_port(self, domain: str) -> str:
        """
        Remove port number from domain if present.
        
        Args:
            domain: Domain that may include port
            
        Returns:
            Domain without port
        """
        if URL_PORT_SEPARATOR in domain:
            return domain.split(URL_PORT_SEPARATOR)[0]
        return domain
    
    def is_trusted_domain(self, domain: str, market_type: str) -> bool:
        """
        Check if domain is in trusted list for market.
        
        Args:
            domain: Domain name to check
            market_type: Market type for validation
            
        Returns:
            True if domain is trusted for this market
        """
        if market_type not in self.trusted_domains:
            logger.debug(f"No trusted domains configured for market: {market_type}")
            return True
        
        trusted_list = self.trusted_domains[market_type]
        domain = self._normalize_domain(domain)
        
        return self._check_domain_match(domain, trusted_list)
    
    def _normalize_domain(self, domain: str) -> str:
        """
        Normalize domain for comparison.
        
        Args:
            domain: Domain to normalize
            
        Returns:
            Normalized domain (lowercase, no port)
        """
        domain = self._strip_port(domain)
        return domain.lower()
    
    def _check_domain_match(self, domain: str, trusted_list: List[str]) -> bool:
        """
        Check if domain matches any trusted domain.
        
        Args:
            domain: Domain to check (already normalized)
            trusted_list: List of trusted domains
            
        Returns:
            True if domain matches
        """
        for trusted in trusted_list:
            if self._is_exact_or_subdomain_match(domain, trusted):
                return True
        return False
    
    def _is_exact_or_subdomain_match(self, domain: str, trusted: str) -> bool:
        """
        Check if domain is exact match or subdomain of trusted domain.
        
        Args:
            domain: Domain to check
            trusted: Trusted domain pattern
            
        Returns:
            True if exact match or valid subdomain
        """
        return domain == trusted or domain.endswith(f'.{trusted}')