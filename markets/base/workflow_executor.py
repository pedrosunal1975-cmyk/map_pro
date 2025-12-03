"""
Map Pro Market Workflow Executor
================================

Provides workflow execution patterns common across markets.
Handles retry logic, rate limiting, and operation sequencing.

Architecture: Workflow coordination without market-specific implementation.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta, timezone
import time

from core.system_logger import get_logger
from .error_classifier import error_classifier, ErrorCategory

logger = get_logger(__name__, 'market')


class WorkflowExecutor:
    """
    Executes market workflows with retry logic and rate limiting.
    
    Responsibilities:
    - Execute operations with retry logic
    - Apply rate limiting
    - Track operation history
    - Handle timeouts
    
    Does NOT handle:
    - Actual API calls (market plugins implement these)
    - Error classification (error_classifier handles this)
    - Success evaluation (success_evaluator handles this)
    """
    
    def __init__(self, market_name: str):
        """
        Initialize workflow executor.
        
        Args:
            market_name: Market identifier
        """
        self.market_name = market_name
        self.logger = get_logger(f"markets.{market_name}.workflow", 'market')
        
        # Rate limiting
        self.rate_limit_per_minute = 10  # Default, markets can override
        self.request_timestamps: List[datetime] = []
        
        # Retry configuration
        self.max_retries = 3
        self.base_retry_delay = 5  # seconds
        
        self.logger.debug(f"Workflow executor initialized for {market_name}")
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        max_retries: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with automatic retry on failure.
        
        Args:
            operation: Async function to execute
            operation_name: Name for logging
            max_retries: Optional override for max retries
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result from operation
            
        Raises:
            Exception: If all retries exhausted
        """
        max_attempts = max_retries if max_retries is not None else self.max_retries
        
        last_exception = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.debug(
                    f"Executing {operation_name} (attempt {attempt}/{max_attempts})"
                )
                
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Execute operation
                result = await operation(*args, **kwargs)
                
                # Record successful request
                self._record_request()
                
                if attempt > 1:
                    self.logger.info(
                        f"{operation_name} succeeded on attempt {attempt}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Classify error
                error_category = error_classifier.classify_exception(e)
                
                self.logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{max_attempts}): "
                    f"{error_category.value} - {str(e)}"
                )
                
                # Check if retryable
                if not error_classifier.is_retryable(error_category):
                    self.logger.error(
                        f"{operation_name} failed with non-retryable error: {error_category.value}"
                    )
                    raise
                
                # Last attempt - raise
                if attempt >= max_attempts:
                    self.logger.error(
                        f"{operation_name} failed after {max_attempts} attempts"
                    )
                    raise
                
                # Calculate retry delay
                retry_delay = error_classifier.get_retry_delay(error_category, attempt)
                
                self.logger.info(f"Retrying {operation_name} in {retry_delay} seconds")
                await asyncio.sleep(retry_delay)
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
    
    async def execute_batch(
        self,
        operations: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple operations with concurrency control.
        
        Args:
            operations: List of operation dictionaries with 'func' and 'args'
            max_concurrent: Maximum number of concurrent operations
            
        Returns:
            List of results
        """
        results = []
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(operation: Dict[str, Any], index: int):
            async with semaphore:
                try:
                    func = operation['func']
                    args = operation.get('args', ())
                    kwargs = operation.get('kwargs', {})
                    name = operation.get('name', f'operation_{index}')
                    
                    result = await self.execute_with_retry(func, name, *args, **kwargs)
                    
                    return {'success': True, 'result': result, 'index': index}
                    
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'index': index
                    }
        
        # Execute all operations
        tasks = [
            execute_with_semaphore(op, i)
            for i, op in enumerate(operations)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Log summary
        success_count = sum(1 for r in results if r.get('success', False))
        self.logger.info(
            f"Batch execution complete: {success_count}/{len(operations)} successful"
        )
        
        return results
    
    async def _apply_rate_limit(self):
        """Apply rate limiting before making request."""
        if self.rate_limit_per_minute <= 0:
            return  # No rate limiting
        
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(minutes=1)
        
        # Remove old timestamps
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if ts > cutoff_time
        ]
        
        # Check if at limit
        if len(self.request_timestamps) >= self.rate_limit_per_minute:
            # Calculate wait time
            oldest_request = min(self.request_timestamps)
            wait_until = oldest_request + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                self.logger.debug(f"Rate limit reached, waiting {wait_seconds:.1f}s")
                await asyncio.sleep(wait_seconds)
    
    def _record_request(self):
        """Record timestamp of request for rate limiting."""
        self.request_timestamps.append(datetime.now(timezone.utc))
    
    def set_rate_limit(self, requests_per_minute: int):
        """
        Set rate limit for this market.
        
        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.rate_limit_per_minute = requests_per_minute
        self.logger.info(f"Rate limit set to {requests_per_minute} requests/minute")
    
    def configure_retry(self, max_retries: int, base_delay: int):
        """
        Configure retry behavior.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for retries
        """
        self.max_retries = max_retries
        self.base_retry_delay = base_delay
        
        self.logger.info(
            f"Retry configured: max={max_retries}, base_delay={base_delay}s"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get workflow execution statistics.
        
        Returns:
            Statistics dictionary
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)
        
        recent_requests = [
            ts for ts in self.request_timestamps
            if ts > cutoff
        ]
        
        return {
            'market_name': self.market_name,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'requests_last_minute': len(recent_requests),
            'requests_until_limit': max(0, self.rate_limit_per_minute - len(recent_requests)),
            'max_retries': self.max_retries,
            'base_retry_delay': self.base_retry_delay
        }