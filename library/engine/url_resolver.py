# Path: library/engine/url_resolver.py
"""
URL Resolver - CORRECTED ARCHITECTURE

Resolves namespace URIs to taxonomy library download URLs.
CRITICAL PRINCIPLE: Trust company declarations FIRST, use patterns as FALLBACK.

Architecture (CORRECT):
1. PRIMARY: Extract and construct URL directly from declared namespace URI
2. FALLBACK: Use searcher.TaxonomyRecognizer only if direct construction fails

NO HARDCODED VALUES - all configuration imported from constants.py
"""

from typing import Dict, Any, List, Set, Optional
from urllib.parse import urlparse

from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT
from library.engine.constants import (
    STANDARD_AUTHORITIES,
    COMPILED_COMPANY_PATTERNS,
    RESERVED_TAXONOMY_NAMES,
    URL_PATTERN_PRIMARY,
    is_valid_version,
    is_company_extension,
    is_included_taxonomy,
    get_authority_transform,
)

logger = get_logger(__name__, 'engine')


class URLResolver:
    """
    Resolves namespace URIs to download URLs.
    
    ARCHITECTURE: Declared URLs first, pattern matching as fallback.
    
    Key principles:
    - Trust company's declared namespaces (primary source)
    - Extract taxonomy info directly from namespace structure
    - Use TaxonomyRecognizer only as fallback
    - Skip company-specific extensions
    
    Example:
        resolver = URLResolver()
        
        # Resolve with primary + fallback
        result = resolver.resolve_namespace(
            'http://xbrl.sec.gov/dei/2024',
            use_fallback=True
        )
    """
    
    def __init__(self):
        """Initialize URL resolver."""
        logger.debug(f"{LOG_PROCESS} Initializing URL resolver")
        
        # Lazy load TaxonomyRecognizer (only if needed for fallback)
        self._recognizer = None
        
        logger.info(f"{LOG_OUTPUT} URL resolver initialized (fallback mode available)")
    
    def resolve_namespace(
        self,
        namespace: str,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Resolve namespace to taxonomy metadata with download URL.
        
        PRIMARY: Direct URL construction from namespace
        FALLBACK: TaxonomyRecognizer pattern matching (if use_fallback=True)
        
        Args:
            namespace: Taxonomy namespace URI
            use_fallback: Whether to use TaxonomyRecognizer if direct fails
            
        Returns:
            Dictionary with taxonomy metadata
        """
        logger.debug(f"{LOG_INPUT} Resolving namespace: {namespace}")
        
        # Check if company-specific extension
        if self._is_company_extension(namespace):
            logger.info(f"{LOG_OUTPUT} Skipping company extension: {namespace}")
            return self._create_company_extension_result(namespace)
        
        # PRIMARY: Try direct URL construction
        direct_result = self._construct_url_directly(namespace)
        
        # Check if this is an included taxonomy (like country, currency, etc.)
        if direct_result['recognized']:
            taxonomy_name = direct_result['taxonomy_name']
            if is_included_taxonomy(taxonomy_name):
                logger.info(
                    f"{LOG_OUTPUT} Taxonomy '{taxonomy_name}' is included in parent taxonomies "
                    f"(us-gaap/dei) - marking as included"
                )
                return self._create_included_taxonomy_result(namespace, direct_result)
        
        if direct_result['recognized']:
            logger.info(
                f"{LOG_OUTPUT} Resolved directly: {namespace} → "
                f"{direct_result['taxonomy_name']} v{direct_result['version']}"
            )
            return direct_result
        
        # FALLBACK: Use TaxonomyRecognizer if enabled
        if use_fallback:
            logger.info(f"{LOG_PROCESS} Direct construction failed, using fallback")
            fallback_result = self._resolve_with_recognizer(namespace)
            
            if fallback_result['recognized']:
                logger.info(
                    f"{LOG_OUTPUT} Resolved via fallback: {namespace} → "
                    f"{fallback_result['taxonomy_name']} v{fallback_result['version']}"
                )
                return fallback_result
        
        # Could not resolve
        logger.warning(f"{LOG_OUTPUT} Could not resolve namespace: {namespace}")
        return self._create_unknown_result(namespace)
    
    def batch_resolve(
        self,
        namespaces: Set[str],
        use_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Resolve multiple namespaces.
        
        Args:
            namespaces: Set of namespace URIs
            use_fallback: Whether to use fallback for each namespace
            
        Returns:
            List of resolved metadata dictionaries
        """
        logger.info(f"{LOG_INPUT} Batch resolving {len(namespaces)} namespaces")
        
        results = []
        for namespace in namespaces:
            result = self.resolve_namespace(namespace, use_fallback=use_fallback)
            results.append(result)
        
        recognized_count = sum(1 for r in results if r['recognized'])
        logger.info(
            f"{LOG_OUTPUT} Batch resolved: {recognized_count}/{len(namespaces)} recognized"
        )
        
        return results
    
    def _is_company_extension(self, namespace: str) -> bool:
        """
        Check if namespace is a company-specific extension.
        
        Uses patterns from constants.py
        
        Args:
            namespace: Namespace URI
            
        Returns:
            True if company extension
        """
        # Parse namespace to get authority
        parsed = urlparse(namespace)
        authority = parsed.netloc
        
        # Use constants function
        return is_company_extension(namespace, authority)
    
    def _construct_url_directly(self, namespace: str) -> Dict[str, Any]:
        """
        Construct download URL directly from namespace structure.
        
        PRIMARY METHOD: Extract and construct URL from declared namespace.
        Uses smart authority transformation from constants.py
        
        Args:
            namespace: Namespace URI
            
        Returns:
            Metadata dictionary with constructed URL
        """
        # Parse namespace URI
        parsed = urlparse(namespace)
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        
        # Extract taxonomy and version from path
        if len(path_parts) < 1:
            return self._create_unknown_result(namespace)
        
        taxonomy_name = path_parts[0] if len(path_parts) >= 1 else None
        version = path_parts[1] if len(path_parts) >= 2 else 'unknown'
        
        # Validate version using constants function
        if not is_valid_version(version):
            version = 'unknown'
        
        if not taxonomy_name or version == 'unknown':
            return self._create_unknown_result(namespace)
        
        # Check if taxonomy name is reserved
        if taxonomy_name.lower() in RESERVED_TAXONOMY_NAMES:
            return self._create_unknown_result(namespace)
        
        # Extract authority domain
        authority = parsed.netloc
        
        # Apply smart authority transformation from constants
        download_authority = get_authority_transform(authority)
        
        # Construct URL using pattern from constants
        download_url = URL_PATTERN_PRIMARY.format(
            authority=download_authority,
            taxonomy=taxonomy_name,
            version=version
        )
        
        return {
            'taxonomy_name': taxonomy_name,
            'version': version,
            'namespace': namespace,
            'download_url': download_url,
            'authority': authority,
            'source': 'direct',
            'is_company_extension': False,
            'recognized': True,
            'needs_verification': True
        }
    
    def _resolve_with_recognizer(self, namespace: str) -> Dict[str, Any]:
        """
        Resolve namespace using TaxonomyRecognizer (fallback).
        
        Args:
            namespace: Namespace URI
            
        Returns:
            Metadata dictionary from TaxonomyRecognizer
        """
        # Lazy load recognizer
        if self._recognizer is None:
            try:
                from searcher.engine import TaxonomyRecognizer
                self._recognizer = TaxonomyRecognizer()
                logger.info(f"{LOG_PROCESS} Loaded TaxonomyRecognizer for fallback")
            except ImportError as e:
                logger.error(f"Cannot import TaxonomyRecognizer: {e}")
                return self._create_unknown_result(namespace)
        
        # Use recognizer to match namespace
        try:
            result = self._recognizer.match_namespace(namespace)
            
            if result and result.get('recognized'):
                # Add source flag
                result['source'] = 'fallback'
                result['is_company_extension'] = False
                return result
            else:
                return self._create_unknown_result(namespace)
                
        except Exception as e:
            logger.error(f"Error in TaxonomyRecognizer: {e}")
            return self._create_unknown_result(namespace)
    
    def _create_company_extension_result(self, namespace: str) -> Dict[str, Any]:
        """Create result for company-specific extension (skip)."""
        return {
            'taxonomy_name': 'company-extension',
            'version': 'unknown',
            'namespace': namespace,
            'download_url': '',
            'authority': '',
            'source': 'skipped',
            'is_company_extension': True,
            'recognized': False
        }
    
    def _create_included_taxonomy_result(self, namespace: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create result for included taxonomy (bundled in parent taxonomies).
        
        These taxonomies don't need separate downloads - they're already
        included in us-gaap or dei.
        """
        return {
            'taxonomy_name': metadata['taxonomy_name'],
            'version': metadata['version'],
            'namespace': namespace,
            'download_url': '',  # No separate download needed
            'authority': metadata['authority'],
            'source': 'included',
            'is_company_extension': False,
            'is_included_taxonomy': True,
            'recognized': True,  # We recognize it, but don't download separately
            'included_in': ['us-gaap', 'dei'],  # Parent taxonomies
        }
    
    def _create_unknown_result(self, namespace: str) -> Dict[str, Any]:
        """Create result for unrecognized namespace."""
        return {
            'taxonomy_name': 'unknown',
            'version': 'unknown',
            'namespace': namespace,
            'download_url': '',
            'authority': '',
            'source': 'unknown',
            'is_company_extension': False,
            'recognized': False
        }
    
    def get_required_libraries(
        self,
        namespaces: Set[str],
        use_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get list of required taxonomy libraries from namespaces.
        
        Filters out:
        - Company extensions
        - Unrecognized namespaces
        - Duplicates
        
        Args:
            namespaces: Set of namespace URIs from parsed.json
            use_fallback: Whether to use fallback resolution
            
        Returns:
            List of unique taxonomy library metadata
        """
        logger.info(f"{LOG_INPUT} Getting required libraries from {len(namespaces)} namespaces")
        
        # Resolve all namespaces
        all_results = self.batch_resolve(namespaces, use_fallback=use_fallback)
        
        # Filter out company extensions, unknowns, and included taxonomies
        libraries = [
            r for r in all_results
            if r['recognized'] 
            and not r['is_company_extension']
            and not r.get('is_included_taxonomy', False)  # Skip included taxonomies
        ]
        
        # Deduplicate by (taxonomy_name, version)
        unique_libs = {}
        for lib in libraries:
            key = (lib['taxonomy_name'], lib['version'])
            if key not in unique_libs:
                unique_libs[key] = lib
        
        result_list = list(unique_libs.values())
        
        logger.info(f"{LOG_OUTPUT} Required libraries: {len(result_list)}")
        
        return result_list


__all__ = ['URLResolver']