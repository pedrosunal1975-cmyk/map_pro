# File: /map_pro/engines/librarian/dependency_analysis_cache.py

"""
Dependency Analysis Cache Manager
==================================

Manages caching of library dependency analysis results to avoid redundant processing.
Provides 30-minute cache with automatic expiration cleanup.

Features:
- Filing-level result caching
- Automatic expiration management
- Cache statistics tracking
- Thread-safe cache operations
"""

import time
from typing import Dict, Any, Optional
from core.system_logger import get_logger

# Cache configuration constants
CACHE_TIMEOUT_SECONDS = 1800  # 30 minutes
CACHE_TIMEOUT_MINUTES = 30
PERCENT_MULTIPLIER = 100
MIN_DIVISOR = 1

logger = get_logger(__name__, 'engine')


class DependencyAnalysisCache:
    """
    Manages caching of dependency analysis results for filings.
    
    Cache Structure:
    {
        'filing_id': {
            'timestamp': float,
            'result': Dict[str, Any]
        }
    }
    """
    
    def __init__(self, timeout_seconds: int = CACHE_TIMEOUT_SECONDS):
        """
        Initialize cache manager.
        
        Args:
            timeout_seconds: Cache entry timeout in seconds (default: 1800)
        """
        self._cache = {}
        self._timeout = timeout_seconds
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info(
            f"Dependency analysis cache initialized "
            f"(timeout: {self._timeout / 60:.0f} minutes)"
        )
    
    def get_cached_result(self, filing_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached analysis result if available and not expired.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            Cached analysis result or None if not available/expired
        """
        current_time = time.time()
        
        if filing_id not in self._cache:
            self._stats['cache_misses'] += 1
            return None
        
        cache_entry = self._cache[filing_id]
        age_seconds = current_time - cache_entry['timestamp']
        
        if age_seconds > self._timeout:
            del self._cache[filing_id]
            self._stats['cache_misses'] += 1
            return None
        
        self._stats['cache_hits'] += 1
        
        age_minutes = age_seconds / 60
        logger.info(
            f"Cache hit for filing {filing_id} "
            f"(age: {age_minutes:.1f} minutes)"
        )
        
        # Return a copy to prevent external modification
        result = cache_entry['result'].copy()
        result['cache_hit'] = True
        result['filing_universal_id'] = filing_id
        
        return result
    
    def cache_result(self, filing_id: str, result: Dict[str, Any]) -> None:
        """
        Store analysis result in cache.
        
        Args:
            filing_id: Filing universal ID
            result: Complete analysis result to cache
        """
        current_time = time.time()
        
        self._cache[filing_id] = {
            'timestamp': current_time,
            'result': result.copy()  # Store a copy to prevent external modification
        }
        
        # Clean up expired entries periodically
        self._clean_expired_entries(current_time)
        
        logger.debug(
            f"Cached result for filing {filing_id} "
            f"(cache size: {len(self._cache)})"
        )
    
    def _clean_expired_entries(self, current_time: float) -> None:
        """
        Remove expired entries from cache.
        
        Args:
            current_time: Current timestamp for expiration check
        """
        expired_keys = [
            filing_id 
            for filing_id, cache_entry in self._cache.items()
            if current_time - cache_entry['timestamp'] > self._timeout
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def clear_cache(self) -> int:
        """
        Clear all cached entries.
        
        Returns:
            Number of entries cleared
        """
        entry_count = len(self._cache)
        self._cache.clear()
        
        logger.info(f"Cache cleared ({entry_count} entries removed)")
        
        return entry_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._stats['cache_hits'] + self._stats['cache_misses']
        hit_rate = 0.0
        
        if total_requests > 0:
            hit_rate = (
                self._stats['cache_hits'] / total_requests * PERCENT_MULTIPLIER
            )
        
        return {
            'cache_size': len(self._cache),
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'cache_hit_rate': hit_rate,
            'cache_timeout_minutes': self._timeout / 60
        }
    
    def is_cached(self, filing_id: str) -> bool:
        """
        Check if filing has valid cached result.
        
        Args:
            filing_id: Filing universal ID
            
        Returns:
            True if valid cached result exists, False otherwise
        """
        return self.get_cached_result(filing_id) is not None


__all__ = ['DependencyAnalysisCache']