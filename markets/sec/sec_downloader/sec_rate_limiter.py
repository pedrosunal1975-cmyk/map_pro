"""
SEC Rate Limiter
================

Enforces SEC EDGAR's 10 requests per second rate limit.
Uses token bucket algorithm to ensure compliance.

SEC Guidelines:
- Maximum 10 requests per second
- Exceeding this limit can result in IP ban
- Rate limit is shared across all SEC operations (search + download)

Architecture:
- Token bucket algorithm for smooth rate limiting
- Thread-safe for concurrent operations
- Shared instance across SEC searcher and downloader

Save location: markets/sec/sec_downloader/sec_rate_limiter.py
"""

import asyncio
import time
from typing import Optional
from datetime import datetime, timezone
from collections import deque

from core.system_logger import get_logger

logger = get_logger(__name__, 'market')


class SECRateLimiter:
    """
    Rate limiter for SEC EDGAR API compliance.
    
    Implements token bucket algorithm to enforce 10 requests/second limit.
    Thread-safe and can be shared across multiple SEC components.
    """
    
    def __init__(
        self,
        requests_per_second: int = 10,
        burst_size: Optional[int] = None,
        enable_metrics: bool = True
    ):
        """
        Initialize SEC rate limiter.
        
        Args:
            requests_per_second: Maximum requests per second (default: 10)
            burst_size: Maximum burst size (default: same as rate)
            enable_metrics: Whether to track rate limit metrics
        """
        self.rate = requests_per_second
        self.burst_size = burst_size or requests_per_second
        
        # Token bucket state
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        
        # Metrics
        self.enable_metrics = enable_metrics
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0
        self.requests_last_second = deque(maxlen=requests_per_second * 2)
        
        logger.info(
            f"SEC rate limiter initialized: {self.rate} req/sec, burst: {self.burst_size}"
        )
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from the bucket (wait if necessary).
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
            
        Returns:
            Time waited in seconds (0 if no wait)
        """
        async with self.lock:
            wait_time = await self._acquire_tokens(tokens)
            
            # Update metrics
            if self.enable_metrics:
                self.total_requests += 1
                current_time = time.time()
                self.requests_last_second.append(current_time)
                
                if wait_time > 0:
                    self.total_waits += 1
                    self.total_wait_time += wait_time
            
            return wait_time
    
    async def _acquire_tokens(self, tokens: int) -> float:
        """
        Internal token acquisition with waiting.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time waited in seconds
        """
        wait_start = time.time()
        
        while True:
            # Refill tokens based on time elapsed
            now = time.time()
            time_passed = now - self.last_update
            self.last_update = now
            
            # Add tokens based on rate
            self.tokens = min(
                self.burst_size,
                self.tokens + time_passed * self.rate
            )
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                wait_time = time.time() - wait_start
                
                if wait_time > 0.001:  # Log significant waits
                    logger.debug(
                        f"Rate limit wait: {wait_time:.3f}s, tokens available: {self.tokens:.1f}"
                    )
                
                return wait_time
            
            # Calculate wait time for next token
            tokens_needed = tokens - self.tokens
            wait_seconds = tokens_needed / self.rate
            
            # Wait for tokens to refill
            await asyncio.sleep(wait_seconds)
    
    def check_available(self) -> bool:
        """
        Check if tokens are available without acquiring.
        
        Returns:
            True if at least 1 token is available
        """
        now = time.time()
        time_passed = now - self.last_update
        available_tokens = min(
            self.burst_size,
            self.tokens + time_passed * self.rate
        )
        return available_tokens >= 1
    
    def get_current_rate(self) -> float:
        """
        Get current request rate over last second.
        
        Returns:
            Requests per second over last second
        """
        if not self.enable_metrics or not self.requests_last_second:
            return 0.0
        
        now = time.time()
        one_second_ago = now - 1.0
        
        # Count requests in last second
        recent_requests = [
            ts for ts in self.requests_last_second 
            if ts > one_second_ago
        ]
        
        return len(recent_requests)
    
    def get_metrics(self) -> dict:
        """
        Get rate limiter metrics.
        
        Returns:
            Dictionary with rate limit statistics
        """
        if not self.enable_metrics:
            return {'metrics_enabled': False}
        
        avg_wait = self.total_wait_time / self.total_waits if self.total_waits > 0 else 0
        wait_percentage = (self.total_waits / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            'rate_limit': self.rate,
            'burst_size': self.burst_size,
            'current_tokens': round(self.tokens, 2),
            'total_requests': self.total_requests,
            'total_waits': self.total_waits,
            'total_wait_time': round(self.total_wait_time, 2),
            'average_wait': round(avg_wait, 3),
            'wait_percentage': round(wait_percentage, 1),
            'current_rate': round(self.get_current_rate(), 2),
            'metrics_enabled': True
        }
    
    def reset_metrics(self):
        """Reset all metrics counters."""
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0
        self.requests_last_second.clear()
        logger.debug("Rate limiter metrics reset")
    
    async def wait_if_needed(self) -> float:
        """
        Convenience method to wait if rate limit would be exceeded.
        
        Returns:
            Time waited in seconds
        """
        return await self.acquire(tokens=1)


# Global shared rate limiter instance for SEC operations
_shared_rate_limiter: Optional[SECRateLimiter] = None


def get_shared_sec_rate_limiter() -> SECRateLimiter:
    """
    Get shared SEC rate limiter instance.
    
    This ensures SEC searcher and downloader share the same rate limit,
    preventing combined operations from exceeding 10 req/sec.
    
    Returns:
        Shared SECRateLimiter instance
    """
    global _shared_rate_limiter
    
    if _shared_rate_limiter is None:
        _shared_rate_limiter = SECRateLimiter(
            requests_per_second=10,
            burst_size=10,
            enable_metrics=True
        )
        logger.info("Created shared SEC rate limiter")
    
    return _shared_rate_limiter


def reset_shared_rate_limiter():
    """Reset the shared rate limiter (useful for testing)."""
    global _shared_rate_limiter
    _shared_rate_limiter = None
    logger.debug("Shared rate limiter reset")


class RateLimitContext:
    """
    Context manager for rate-limited operations.
    
    Usage:
        async with RateLimitContext(rate_limiter):
            # Rate-limited operation
            response = await make_request()
    """
    
    def __init__(self, rate_limiter: SECRateLimiter, tokens: int = 1):
        """
        Initialize context.
        
        Args:
            rate_limiter: Rate limiter to use
            tokens: Number of tokens to acquire
        """
        self.rate_limiter = rate_limiter
        self.tokens = tokens
        self.wait_time = 0.0
    
    async def __aenter__(self):
        """Acquire tokens on enter."""
        self.wait_time = await self.rate_limiter.acquire(self.tokens)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Nothing to cleanup on exit."""
        return False
    
    def get_wait_time(self) -> float:
        """Get time waited for rate limit."""
        return self.wait_time