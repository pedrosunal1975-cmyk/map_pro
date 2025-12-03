"""
Namespace Normalization and Matching for Library Dependency Scanner.

Handles namespace URL normalization, taxonomy URL detection, and matching
namespaces to library configurations.

Location: engines/librarian/namespace_matching.py
"""

import re
from typing import Optional, Dict, Any, List, Tuple

from .scanner_models import ScannerConstants
from .taxonomy_config import get_taxonomies_for_market


class NamespaceNormalizer:
    """
    Normalizes namespace URLs for consistent matching.
    
    Handles various namespace format variations to ensure consistent
    matching against taxonomy configurations.
    """
    
    @staticmethod
    def normalize(namespace: str) -> Optional[str]:
        """
        Normalize namespace URL to canonical form.
        
        Normalization steps:
        1. Strip whitespace
        2. Validate URL format
        3. Remove trailing slashes
        4. Convert to lowercase
        
        Args:
            namespace: Raw namespace string
            
        Returns:
            Normalized namespace or None if invalid
            
        Example:
            >>> normalized = NamespaceNormalizer.normalize('HTTP://Example.com/2023/')
            >>> print(normalized)  # 'http://example.com/2023'
        """
        if not namespace or not isinstance(namespace, str):
            return None
        
        # Step 1: Clean whitespace
        namespace = namespace.strip()
        
        # Step 2: Validate URL format
        if not (namespace.startswith(ScannerConstants.HTTP_PREFIX) or 
                namespace.startswith(ScannerConstants.HTTPS_PREFIX)):
            return None
        
        # Step 3: Remove trailing slashes
        namespace = namespace.rstrip('/')
        
        # Step 4: Lowercase for consistency
        namespace = namespace.lower()
        
        return namespace
    
    @staticmethod
    def is_taxonomy_url(url: str) -> bool:
        """
        Check if URL appears to be a taxonomy reference.
        
        Uses keyword matching against known taxonomy domains and terms.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL likely references a taxonomy
            
        Example:
            >>> is_taxonomy = NamespaceNormalizer.is_taxonomy_url(
            ...     'http://fasb.org/us-gaap/2023'
            ... )
            >>> print(is_taxonomy)  # True
        """
        url_lower = url.lower()
        return any(
            indicator in url_lower 
            for indicator in ScannerConstants.TAXONOMY_INDICATORS
        )


class NamespaceMatcher:
    """
    Matches discovered namespaces to library configurations.
    
    Uses sophisticated matching logic including similarity scoring.
    """
    
    def __init__(self, logger):
        """
        Initialize namespace matcher.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def match_namespace_to_library(
        self, 
        namespace: str, 
        library_config: Dict[str, Any]
    ) -> bool:
        """
        Check if namespace matches library configuration.
        
        Uses exact match and similarity matching.
        
        Args:
            namespace: Namespace to match
            library_config: Library configuration dictionary
            
        Returns:
            True if namespace matches this library
        """
        # Ensure the library namespace is also normalized for comparison
        library_namespace = NamespaceNormalizer.normalize(
            library_config.get('namespace', '')
        )
        
        if not library_namespace:
            return False
        
        # 1. Exact match (handles the normalized us-gaap/2024 == us-gaap/2024 case)
        if namespace == library_namespace:
            return True
        
        # 2. Similarity match (handles us-gaap/2024-01-31 vs us-gaap/2024 case)
        return self.namespace_similarity_match(namespace, library_namespace)
    
    def namespace_similarity_match(self, ns1: str, ns2: str) -> bool:
        """
        Check if two namespaces are similar enough to match, primarily
        by comparing the path up to and including the year, allowing for
        date/version suffixes afterwards.
        
        Args:
            ns1: The first namespace (typically from the filing, e.g., shorter)
            ns2: The second namespace (typically from the config, e.g., normalized)
            
        Returns:
            True if namespaces are similar enough to be the same library.
        """
        # The goal is to find the common root up to the year and check the length difference
        
        # Extract the full year path component for both
        path_to_year_1, year1 = self._extract_key_components(ns1)
        path_to_year_2, year2 = self._extract_key_components(ns2)
        
        if not (year1 and year2 and year1 == year2):
            # Years must match exactly for similarity matching to proceed
            return False
            
        # Determine which namespace is the 'base' (shorter, likely the config/filing entry)
        # and which is the 'candidate' (longer, potentially with suffixes)
        if len(ns1) <= len(ns2):
            base_ns = ns1
            candidate_ns = ns2
        else:
            base_ns = ns2
            candidate_ns = ns1
            
        # Ensure the base namespace is a prefix of the candidate namespace
        if candidate_ns.startswith(base_ns):
            # Calculate the number of extra characters beyond the base
            extra_chars = len(candidate_ns) - len(base_ns)
            
            # Check if the extra characters are within the allowed tolerance
            if extra_chars <= ScannerConstants.YEAR_MATCH_TOLERANCE:
                self.logger.debug(
                    f"Similarity match (TOLERANCE={ScannerConstants.YEAR_MATCH_TOLERANCE}): "
                    f"'{base_ns}' is a prefix of '{candidate_ns}' with {extra_chars} "
                    f"extra chars."
                )
                return True

        # Fallback check: If both URLs share the same path leading up to the year
        # but have different suffixes (e.g., one has -01-31 and the other is empty),
        # this logic should cover it.
        # This is primarily for the case where BOTH have suffixes but the config
        # only has the short version (e.g., config is .../2024, filing is .../2024-01-31).
        
        # Final, robust check: Check if the common path without suffixes matches
        # The common path is the string up to and including the year
        if path_to_year_1 == path_to_year_2:
            return True
        
        return False
    
    def _extract_key_components(self, namespace: str) -> Tuple[str, str]:
        """
        Extract the path component up to the year, and the year itself.
        
        Args:
            namespace: Namespace URL
            
        Returns:
            Tuple of (path_to_year, year) strings (empty strings if not found)
        """
        # Regex to find the 4-digit year component preceded by a slash, capturing 
        # the entire path up to that point.
        match = re.search(r'(.*/(20\d{2}))', namespace)
        
        if match:
            # Group 1 is the full path up to and including the year (e.g., 'http://fasb.org/us-gaap/2024')
            path_to_year = match.group(1)
            # Group 2 is just the year (e.g., '2024')
            year = match.group(2)
            return path_to_year, year
        
        return '', ''


class LibraryMapper:
    """
    Maps namespaces to required library configurations.
    
    Coordinates namespace matching and library list assembly.
    """
    
    def __init__(self, logger):
        """
        Initialize library mapper.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.matcher = NamespaceMatcher(logger)
    
    def map_to_libraries(
        self, 
        namespaces: set, 
        market_type: str
    ) -> List[Dict[str, Any]]:
        """
        Map detected namespaces to required taxonomy libraries.
        
        Process:
        1. Get market-specific libraries
        2. Match each namespace to libraries
        3. Include required market libraries
        4. Log unmatched namespaces
        
        Args:
            namespaces: Set of detected namespaces
            market_type: Target market type
            
        Returns:
            List of required library configurations
        """
        required_libraries = []
        matched_namespaces = set()
        
        # Get market libraries
        market_libraries = get_taxonomies_for_market(
            market_type, 
            required_only=False
        )
        
        # Match namespaces to libraries
        for namespace in namespaces:
            # Normalize the filing namespace before matching
            normalized_namespace = NamespaceNormalizer.normalize(namespace)
            if not normalized_namespace:
                self.logger.debug(f"Skipping invalid namespace: {namespace}")
                continue
            
            library = self._find_matching_library(
                normalized_namespace, 
                market_libraries
            )
            
            if library:
                if library not in required_libraries:
                    required_libraries.append(library)
                matched_namespaces.add(namespace) # Use original namespace for tracking
        
        # Log unmatched namespaces
        self._log_unmatched_namespaces(namespaces, matched_namespaces)
        
        # Include required market libraries
        self._add_required_libraries(required_libraries, market_type)
        
        self.logger.info(
            f"Mapped to {len(required_libraries)} required libraries"
        )
        
        return required_libraries
    
    def _find_matching_library(
        self, 
        namespace: str, 
        libraries: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find library that matches namespace.
        
        Args:
            namespace: Normalized namespace to match
            libraries: List of library configurations
            
        Returns:
            Matching library configuration or None
        """
        for library in libraries:
            if self.matcher.match_namespace_to_library(namespace, library):
                return library
        
        return None
    
    def _log_unmatched_namespaces(
        self, 
        all_namespaces: set, 
        matched_namespaces: set
    ) -> None:
        """
        Log namespaces that couldn't be matched to libraries.
        
        Args:
            all_namespaces: All detected namespaces
            matched_namespaces: Successfully matched namespaces (original form)
        """
        unmatched = all_namespaces - matched_namespaces
        
        if unmatched:
            self.logger.warning(
                f"Unmatched namespaces: {sorted(list(unmatched))}"
            )
    
    def _add_required_libraries(
        self, 
        libraries: List[Dict[str, Any]], 
        market_type: str
    ) -> None:
        """
        Add required market libraries if not already included.
        
        Modifies the libraries list in place.
        
        Args:
            libraries: List of library configurations (modified in place)
            market_type: Target market type
        """
        required_libs = get_taxonomies_for_market(market_type, required_only=True)
        
        for lib in required_libs:
            if lib not in libraries:
                libraries.append(lib)


__all__ = ['NamespaceNormalizer', 'NamespaceMatcher', 'LibraryMapper']