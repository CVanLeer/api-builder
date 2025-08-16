"""
Retry logic and resilience patterns for API calls.

This module provides comprehensive retry mechanisms with exponential backoff,
jitter, and intelligent retry strategies for distributed systems.
"""

from typing import TypeVar, Callable, Any, Optional, Tuple, Type, Union, List
from functools import wraps
import time
import random
import logging
from datetime import datetime, timedelta
from enum import Enum

from .exceptions import (
    APIError,
    RetryableError,
    RateLimitError,
    APIConnectionError,
    TimeoutError,
    CircuitBreakerError
)

T = TypeVar('T')
logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Different retry strategies available."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    FIXED = "fixed"


def calculate_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    jitter: bool = True
) -> float:
    """
    Calculate the backoff delay for a given attempt.
    
    Args:
        attempt: The current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        strategy: The retry strategy to use
        jitter: Whether to add random jitter
    
    Returns:
        The calculated delay in seconds
    """
    if strategy == RetryStrategy.EXPONENTIAL:
        delay = min(base_delay * (2 ** attempt), max_delay)
    elif strategy == RetryStrategy.LINEAR:
        delay = min(base_delay * (attempt + 1), max_delay)
    elif strategy == RetryStrategy.FIBONACCI:
        # Generate fibonacci number for the attempt
        a, b = 1, 1
        for _ in range(attempt):
            a, b = b, a + b
        delay = min(base_delay * a, max_delay)
    else:  # FIXED
        delay = base_delay
    
    if jitter:
        # Add jitter: random value between 0 and delay/2
        jitter_amount = random.uniform(0, delay / 2)
        delay = delay - (delay / 4) + jitter_amount
    
    return delay


def exponential_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
    retry_if: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> T:
    """
    Retry a function with exponential backoff and jitter.
    
    Args:
        func: The function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        jitter: Whether to add random jitter to prevent thundering herd
        retry_on: Tuple of exception types to retry on
        retry_if: Custom function to determine if we should retry
        on_retry: Callback function called on each retry
    
    Returns:
        The result of the function call
    
    Raises:
        The last exception if all retries are exhausted
    """
    retry_on = retry_on or (Exception,)
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except retry_on as e:
            last_exception = e
            
            # Check if this is the last attempt
            if attempt >= max_retries:
                logger.error(f"All {max_retries} retries exhausted for {func.__name__}")
                raise
            
            # Check custom retry condition
            if retry_if and not retry_if(e):
                logger.debug(f"Custom retry condition returned False for {e}")
                raise
            
            # Check if error is retryable
            if isinstance(e, RetryableError) and not e.should_retry():
                logger.debug(f"Error indicated it should not be retried: {e}")
                raise
            
            # Special handling for rate limit errors
            if isinstance(e, RateLimitError) and e.retry_after:
                delay = e.retry_after
                logger.info(f"Rate limited. Waiting {delay} seconds as requested by server")
            else:
                delay = calculate_backoff_delay(
                    attempt,
                    base_delay,
                    max_delay,
                    RetryStrategy.EXPONENTIAL,
                    jitter
                )
            
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}. "
                f"Retrying in {delay:.2f} seconds. Error: {e}"
            )
            
            # Call retry callback if provided
            if on_retry:
                on_retry(e, attempt)
            
            time.sleep(delay)
    
    raise last_exception


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
    retry_if: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying functions with configurable backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        jitter: Whether to add random jitter
        strategy: The retry strategy to use
        retry_on: Tuple of exception types to retry on
        retry_if: Custom function to determine if we should retry
        on_retry: Callback function called on each retry
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            retry_on_exceptions = retry_on or (Exception,)
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on_exceptions as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        logger.error(
                            f"All {max_retries} retries exhausted for {func.__name__}"
                        )
                        raise
                    
                    if retry_if and not retry_if(e):
                        raise
                    
                    if isinstance(e, RetryableError) and not e.should_retry():
                        raise
                    
                    # Handle rate limiting
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = e.retry_after
                    else:
                        delay = calculate_backoff_delay(
                            attempt,
                            base_delay,
                            max_delay,
                            strategy,
                            jitter
                        )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for "
                        f"{func.__name__}. Retrying in {delay:.2f} seconds. Error: {e}"
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


class AdaptiveRetry:
    """
    Adaptive retry mechanism that adjusts retry strategy based on error patterns.
    """
    
    def __init__(
        self,
        initial_max_retries: int = 3,
        initial_base_delay: float = 1.0,
        max_delay: float = 60.0,
        success_threshold: int = 10,
        failure_threshold: int = 5
    ):
        """
        Initialize adaptive retry mechanism.
        
        Args:
            initial_max_retries: Starting maximum retries
            initial_base_delay: Starting base delay
            max_delay: Maximum allowed delay
            success_threshold: Successes before reducing retries
            failure_threshold: Failures before increasing retries
        """
        self.max_retries = initial_max_retries
        self.base_delay = initial_base_delay
        self.max_delay = max_delay
        self.success_threshold = success_threshold
        self.failure_threshold = failure_threshold
        
        self.success_count = 0
        self.failure_count = 0
        self.total_attempts = 0
        self.total_retries = 0
    
    def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with adaptive retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of function execution
        """
        last_exception = None
        retries_used = 0
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self._record_success(retries_used)
                return result
            except Exception as e:
                last_exception = e
                retries_used = attempt
                
                if attempt >= self.max_retries:
                    self._record_failure(retries_used)
                    raise
                
                # Check if error is retryable
                if isinstance(e, APIError):
                    if isinstance(e, RetryableError) and not e.should_retry():
                        self._record_failure(retries_used)
                        raise
                
                # Calculate delay
                if isinstance(e, RateLimitError) and e.retry_after:
                    delay = e.retry_after
                else:
                    delay = calculate_backoff_delay(
                        attempt,
                        self.base_delay,
                        self.max_delay,
                        RetryStrategy.EXPONENTIAL,
                        True
                    )
                
                logger.warning(
                    f"Adaptive retry attempt {attempt + 1}/{self.max_retries + 1}. "
                    f"Waiting {delay:.2f} seconds. Error: {e}"
                )
                
                time.sleep(delay)
        
        self._record_failure(retries_used)
        raise last_exception
    
    def _record_success(self, retries_used: int):
        """Record a successful execution."""
        self.success_count += 1
        self.failure_count = 0  # Reset failure count on success
        self.total_attempts += 1
        self.total_retries += retries_used
        
        # Adapt: Reduce retries if consistently successful
        if self.success_count >= self.success_threshold:
            self.max_retries = max(1, self.max_retries - 1)
            self.base_delay = max(0.5, self.base_delay * 0.8)
            self.success_count = 0
            logger.info(
                f"Adaptive retry: Reduced to {self.max_retries} retries, "
                f"{self.base_delay:.1f}s base delay"
            )
    
    def _record_failure(self, retries_used: int):
        """Record a failed execution."""
        self.failure_count += 1
        self.success_count = 0  # Reset success count on failure
        self.total_attempts += 1
        self.total_retries += retries_used
        
        # Adapt: Increase retries if consistently failing
        if self.failure_count >= self.failure_threshold:
            self.max_retries = min(10, self.max_retries + 1)
            self.base_delay = min(5.0, self.base_delay * 1.5)
            self.failure_count = 0
            logger.info(
                f"Adaptive retry: Increased to {self.max_retries} retries, "
                f"{self.base_delay:.1f}s base delay"
            )
    
    def get_statistics(self) -> dict:
        """Get retry statistics."""
        success_rate = (
            (self.total_attempts - self.failure_count) / self.total_attempts
            if self.total_attempts > 0 else 0
        )
        avg_retries = (
            self.total_retries / self.total_attempts
            if self.total_attempts > 0 else 0
        )
        
        return {
            "total_attempts": self.total_attempts,
            "success_rate": success_rate,
            "average_retries": avg_retries,
            "current_max_retries": self.max_retries,
            "current_base_delay": self.base_delay
        }