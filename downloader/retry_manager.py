# File: /map_pro/engines/downloader/retry_manager.py

"""
Map Pro Retry Manager
====================

Protocol-agnostic retry logic with exponential backoff.
Works for any download protocol (HTTP, HTTPS, FTP, etc.).
"""

import asyncio
import time
from typing import Callable, Any, Optional, TypeVar, List
from dataclasses import dataclass
from enum import Enum

from core.system_logger import get_logger

logger = get_logger(__name__, 'engine')

T = TypeVar('T')

DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0
DEFAULT_MAX_BACKOFF = 60.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = DEFAULT_MAX_RETRIES
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF
    max_backoff: float = DEFAULT_MAX_BACKOFF
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retry_on_exceptions: Optional[List[type]] = None
    
    def __post_init__(self):
        """Set default retryable exceptions if not provided."""
        if self.retry_on_exceptions is None:
            import aiohttp
            import asyncio
            self.retry_on_exceptions = [
                aiohttp.ClientError,
                asyncio.TimeoutError,
                ConnectionError,
                OSError,
            ]


class RetryManager:
    """
    Manages retry logic with exponential backoff.
    
    Protocol-agnostic: works with any async operation.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry manager.
        
        Args:
            config: Retry configuration (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self.logger = logger
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.initial_backoff * (self.config.backoff_multiplier ** attempt)
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.initial_backoff * (attempt + 1)
        else:
            delay = self.config.initial_backoff
        
        return min(delay, self.config.max_backoff)
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-indexed)
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.config.max_retries:
            return False
        
        if self.config.retry_on_exceptions:
            return any(isinstance(exception, exc_type) for exc_type in self.config.retry_on_exceptions)
        
        return True
    
    async def execute_with_retry(
        self,
        operation: Callable[..., Any],
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute async operation with retry logic.
        
        Args:
            operation: Async callable to execute
            operation_name: Name for logging
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of successful operation
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.debug(
                    f"Attempt {attempt + 1}/{self.config.max_retries + 1}: {operation_name}"
                )
                
                result = await operation(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(
                        f"Operation succeeded after {attempt} retries: {operation_name}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    self.logger.error(
                        f"Non-retryable error or max retries exceeded: {operation_name} - error: {str(e)}, attempt: {attempt + 1}"
                    )
                    raise
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {operation_name} - error: {str(e)}, retry_in: {delay:.1f}s"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"All retry attempts exhausted: {operation_name} - total_attempts: {attempt + 1}, error: {str(e)}"
                    )
                    raise
        
        if last_exception:
            raise last_exception
    
    def execute_sync_with_retry(
        self,
        operation: Callable[..., Any],
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute synchronous operation with retry logic.
        
        Args:
            operation: Sync callable to execute
            operation_name: Name for logging
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of successful operation
            
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.debug(
                    f"Attempt {attempt + 1}/{self.config.max_retries + 1}: {operation_name}"
                )
                
                result = operation(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(
                        f"Operation succeeded after {attempt} retries: {operation_name}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    self.logger.error(
                        f"Non-retryable error or max retries exceeded: {operation_name} - error: {str(e)}, attempt: {attempt + 1}"
                    )
                    raise
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {operation_name} - error: {str(e)}, retry_in: {delay:.1f}s"
                    )
                    
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"All retry attempts exhausted: {operation_name} - total_attempts: {attempt + 1}, error: {str(e)}"
                    )
                    raise
        
        if last_exception:
            raise last_exception


async def retry_async(
    operation: Callable,
    operation_name: str = "async_operation",
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF
) -> Any:
    """
    Convenience function for async retry with default exponential backoff.
    
    Args:
        operation: Async callable to retry
        operation_name: Name for logging
        max_retries: Maximum retry attempts
        initial_backoff: Initial backoff delay in seconds
        
    Returns:
        Result of operation
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_backoff=initial_backoff
    )
    manager = RetryManager(config)
    return await manager.execute_with_retry(operation, operation_name)


def retry_sync(
    operation: Callable,
    operation_name: str = "sync_operation",
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF
) -> Any:
    """
    Convenience function for sync retry with default exponential backoff.
    
    Args:
        operation: Sync callable to retry
        operation_name: Name for logging
        max_retries: Maximum retry attempts
        initial_backoff: Initial backoff delay in seconds
        
    Returns:
        Result of operation
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_backoff=initial_backoff
    )
    manager = RetryManager(config)
    return manager.execute_sync_with_retry(operation, operation_name)