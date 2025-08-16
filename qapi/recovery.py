"""
Error recovery mechanisms for API Builder.

This module provides strategies for graceful degradation, fallback mechanisms,
caching on failure, and retry queuing.
"""

from typing import (
    Any, Callable, Dict, Optional, TypeVar, Union, List,
    Generic, Tuple
)
from functools import wraps, lru_cache
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pickle
import json
import hashlib
import logging
import threading
import queue
import time
from pathlib import Path
from contextlib import contextmanager

from .exceptions import APIError, APIConnectionError, TimeoutError as APITimeoutError
from .retry import exponential_backoff
from .circuit_breaker import CircuitBreaker

T = TypeVar('T')
logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Available recovery strategies."""
    FALLBACK = "fallback"          # Use fallback value/function
    CACHE = "cache"                # Use cached value if available
    DEGRADE = "degrade"            # Provide degraded service
    QUEUE = "queue"                # Queue for retry later
    FAIL_FAST = "fail_fast"        # Fail immediately
    DEFAULT = "default"            # Return default value


@dataclass
class CacheEntry(Generic[T]):
    """Entry in the recovery cache."""
    value: T
    timestamp: datetime
    ttl: Optional[timedelta] = None
    error_count: int = 0
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        if self.ttl is None:
            return True
        return datetime.utcnow() - self.timestamp < self.ttl


@dataclass
class RetryQueueItem:
    """Item in the retry queue."""
    func: Callable
    args: tuple
    kwargs: dict
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None


class RecoveryCache:
    """
    Cache for storing fallback values during failures.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[timedelta] = None,
        persistence_path: Optional[Path] = None
    ):
        """
        Initialize recovery cache.
        
        Args:
            max_size: Maximum cache size
            default_ttl: Default time-to-live for cache entries
            persistence_path: Optional path for persistent cache
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl or timedelta(hours=1)
        self._persistence_path = persistence_path
        self._lock = threading.RLock()
        
        # Load persistent cache if path provided
        if self._persistence_path and self._persistence_path.exists():
            self._load_cache()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if valid."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.is_valid():
                logger.debug(f"Cache hit for key: {key}")
                return entry.value
            elif entry:
                logger.debug(f"Cache expired for key: {key}")
                del self._cache[key]
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ):
        """Store value in cache."""
        with self._lock:
            # Enforce max size
            if len(self._cache) >= self._max_size:
                # Remove oldest entry
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].timestamp
                )
                del self._cache[oldest_key]
            
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=datetime.utcnow(),
                ttl=ttl or self._default_ttl
            )
            logger.debug(f"Cached value for key: {key}")
            
            # Persist if configured
            if self._persistence_path:
                self._save_cache()
    
    def invalidate(self, key: Optional[str] = None):
        """Invalidate cache entries."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()
            
            if self._persistence_path:
                self._save_cache()
    
    def _make_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function call."""
        key_parts = [
            func.__module__,
            func.__name__,
            str(args),
            str(sorted(kwargs.items()))
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self._persistence_path, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_cache(self):
        """Load cache from disk."""
        try:
            with open(self._persistence_path, 'rb') as f:
                self._cache = pickle.load(f)
            logger.info(f"Loaded {len(self._cache)} cache entries")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")


class RetryQueue:
    """
    Queue for operations that need to be retried later.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        worker_threads: int = 2,
        retry_interval: int = 60
    ):
        """
        Initialize retry queue.
        
        Args:
            max_size: Maximum queue size
            worker_threads: Number of worker threads
            retry_interval: Seconds between retry attempts
        """
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_size)
        self._worker_threads = worker_threads
        self._retry_interval = retry_interval
        self._running = False
        self._workers: List[threading.Thread] = []
        self._stats = {
            'queued': 0,
            'succeeded': 0,
            'failed': 0,
            'dropped': 0
        }
    
    def start(self):
        """Start retry queue workers."""
        if self._running:
            return
        
        self._running = True
        for i in range(self._worker_threads):
            worker = threading.Thread(
                target=self._worker,
                name=f"RetryWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"Started {self._worker_threads} retry workers")
    
    def stop(self):
        """Stop retry queue workers."""
        self._running = False
        for worker in self._workers:
            worker.join(timeout=5)
        self._workers.clear()
        logger.info("Stopped retry workers")
    
    def enqueue(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        max_retries: int = 3,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> bool:
        """
        Add operation to retry queue.
        
        Args:
            func: Function to retry
            args: Function arguments
            kwargs: Function keyword arguments
            max_retries: Maximum retry attempts
            callback: Success callback
            error_callback: Failure callback
        
        Returns:
            True if queued, False if queue full
        """
        kwargs = kwargs or {}
        item = RetryQueueItem(
            func=func,
            args=args,
            kwargs=kwargs,
            timestamp=datetime.utcnow(),
            max_retries=max_retries,
            callback=callback,
            error_callback=error_callback
        )
        
        try:
            # Priority based on timestamp (older first)
            priority = item.timestamp.timestamp()
            self._queue.put((priority, item), block=False)
            self._stats['queued'] += 1
            logger.info(f"Queued {func.__name__} for retry")
            return True
        except queue.Full:
            self._stats['dropped'] += 1
            logger.warning(f"Retry queue full, dropping {func.__name__}")
            return False
    
    def _worker(self):
        """Worker thread for processing retry queue."""
        while self._running:
            try:
                # Get item with timeout
                priority, item = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            
            # Check if it's time to retry
            elapsed = (datetime.utcnow() - item.timestamp).total_seconds()
            if elapsed < self._retry_interval:
                # Not time yet, put it back
                self._queue.put((priority, item))
                time.sleep(1)
                continue
            
            # Try to execute
            try:
                result = item.func(*item.args, **item.kwargs)
                self._stats['succeeded'] += 1
                logger.info(f"Retry succeeded for {item.func.__name__}")
                
                if item.callback:
                    item.callback(result)
            except Exception as e:
                item.retry_count += 1
                
                if item.retry_count < item.max_retries:
                    # Re-queue for another attempt
                    item.timestamp = datetime.utcnow()
                    new_priority = item.timestamp.timestamp()
                    self._queue.put((new_priority, item))
                    logger.warning(
                        f"Retry {item.retry_count}/{item.max_retries} "
                        f"failed for {item.func.__name__}: {e}"
                    )
                else:
                    self._stats['failed'] += 1
                    logger.error(
                        f"All retries exhausted for {item.func.__name__}: {e}"
                    )
                    
                    if item.error_callback:
                        item.error_callback(e)
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            **self._stats,
            'pending': self._queue.qsize()
        }


class GracefulDegradation:
    """
    Manages graceful degradation strategies for failing services.
    """
    
    def __init__(
        self,
        cache: Optional[RecoveryCache] = None,
        retry_queue: Optional[RetryQueue] = None
    ):
        """
        Initialize graceful degradation manager.
        
        Args:
            cache: Recovery cache instance
            retry_queue: Retry queue instance
        """
        self.cache = cache or RecoveryCache()
        self.retry_queue = retry_queue or RetryQueue()
        self._fallbacks: Dict[str, Callable] = {}
        self._defaults: Dict[str, Any] = {}
        self._degraded_modes: Dict[str, bool] = {}
    
    def register_fallback(
        self,
        service: str,
        fallback: Callable
    ):
        """Register fallback function for a service."""
        self._fallbacks[service] = fallback
        logger.info(f"Registered fallback for service: {service}")
    
    def register_default(
        self,
        service: str,
        default: Any
    ):
        """Register default value for a service."""
        self._defaults[service] = default
        logger.info(f"Registered default for service: {service}")
    
    def set_degraded_mode(
        self,
        service: str,
        degraded: bool = True
    ):
        """Set service to degraded mode."""
        self._degraded_modes[service] = degraded
        if degraded:
            logger.warning(f"Service '{service}' entering degraded mode")
        else:
            logger.info(f"Service '{service}' exiting degraded mode")
    
    def is_degraded(self, service: str) -> bool:
        """Check if service is in degraded mode."""
        return self._degraded_modes.get(service, False)
    
    def with_recovery(
        self,
        service: str,
        strategy: RecoveryStrategy = RecoveryStrategy.CACHE,
        cache_ttl: Optional[timedelta] = None,
        fallback: Optional[Callable] = None,
        default: Any = None,
        queue_on_failure: bool = False
    ):
        """
        Decorator to add recovery mechanisms to a function.
        
        Args:
            service: Service name
            strategy: Recovery strategy to use
            cache_ttl: Cache time-to-live
            fallback: Fallback function
            default: Default value
            queue_on_failure: Whether to queue for retry on failure
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                # Check if in degraded mode
                if self.is_degraded(service):
                    logger.warning(f"Service '{service}' is degraded, using recovery")
                    return self._apply_recovery(
                        service, func, args, kwargs,
                        strategy, cache_ttl, fallback, default
                    )
                
                # Try normal execution
                cache_key = self.cache._make_key(func, args, kwargs)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Cache successful result
                    if strategy == RecoveryStrategy.CACHE:
                        self.cache.set(cache_key, result, cache_ttl)
                    
                    return result
                
                except (APIConnectionError, APITimeoutError, APIError) as e:
                    logger.error(f"Service '{service}' failed: {e}")
                    
                    # Queue for retry if configured
                    if queue_on_failure and self.retry_queue:
                        self.retry_queue.enqueue(
                            func, args, kwargs,
                            callback=lambda r: self.cache.set(cache_key, r, cache_ttl)
                        )
                    
                    # Apply recovery strategy
                    return self._apply_recovery(
                        service, func, args, kwargs,
                        strategy, cache_ttl, fallback, default
                    )
            
            return wrapper
        return decorator
    
    def _apply_recovery(
        self,
        service: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
        strategy: RecoveryStrategy,
        cache_ttl: Optional[timedelta],
        fallback: Optional[Callable],
        default: Any
    ) -> Any:
        """Apply recovery strategy."""
        cache_key = self.cache._make_key(func, args, kwargs)
        
        if strategy == RecoveryStrategy.CACHE:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info(f"Using cached value for '{service}'")
                return cached
        
        if strategy == RecoveryStrategy.FALLBACK:
            fb = fallback or self._fallbacks.get(service)
            if fb:
                logger.info(f"Using fallback for '{service}'")
                return fb(*args, **kwargs)
        
        if strategy == RecoveryStrategy.DEFAULT:
            dv = default if default is not None else self._defaults.get(service)
            if dv is not None:
                logger.info(f"Using default value for '{service}'")
                return dv
        
        if strategy == RecoveryStrategy.QUEUE:
            if self.retry_queue:
                self.retry_queue.enqueue(func, args, kwargs)
                logger.info(f"Queued '{service}' for retry")
                # Return default or raise
                if default is not None:
                    return default
        
        # No recovery available
        raise APIError(f"Service '{service}' failed with no recovery available")


class RateLimiter:
    """
    Rate limiting handler with adaptive throttling.
    """
    
    def __init__(
        self,
        default_limit: int = 100,
        window_seconds: int = 60
    ):
        """
        Initialize rate limiter.
        
        Args:
            default_limit: Default rate limit
            window_seconds: Time window in seconds
        """
        self._limits: Dict[str, int] = {}
        self._windows: Dict[str, int] = {}
        self._counters: Dict[str, List[datetime]] = {}
        self._default_limit = default_limit
        self._window_seconds = window_seconds
        self._lock = threading.RLock()
        self._retry_after: Dict[str, datetime] = {}
    
    def check_limit(self, service: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        with self._lock:
            # Check if we have a retry-after time
            if service in self._retry_after:
                retry_time = self._retry_after[service]
                if datetime.utcnow() < retry_time:
                    seconds = (retry_time - datetime.utcnow()).seconds
                    return False, seconds
                else:
                    del self._retry_after[service]
            
            # Get or create counter
            if service not in self._counters:
                self._counters[service] = []
            
            # Clean old entries
            cutoff = datetime.utcnow() - timedelta(seconds=self._window_seconds)
            self._counters[service] = [
                ts for ts in self._counters[service]
                if ts > cutoff
            ]
            
            # Check limit
            limit = self._limits.get(service, self._default_limit)
            current_count = len(self._counters[service])
            
            if current_count >= limit:
                # Calculate retry-after
                oldest = min(self._counters[service])
                retry_after = (
                    oldest + timedelta(seconds=self._window_seconds) - datetime.utcnow()
                ).seconds
                return False, retry_after
            
            # Add current request
            self._counters[service].append(datetime.utcnow())
            return True, None
    
    def handle_429(
        self,
        service: str,
        response_headers: Dict[str, str]
    ) -> int:
        """
        Handle 429 response and extract retry-after.
        
        Returns:
            Seconds to wait before retry
        """
        retry_after = None
        
        # Check for Retry-After header
        if 'Retry-After' in response_headers:
            retry_value = response_headers['Retry-After']
            try:
                # Could be seconds or HTTP date
                retry_after = int(retry_value)
            except ValueError:
                # Try parsing as HTTP date
                try:
                    retry_date = datetime.strptime(
                        retry_value,
                        '%a, %d %b %Y %H:%M:%S GMT'
                    )
                    retry_after = (retry_date - datetime.utcnow()).seconds
                except ValueError:
                    retry_after = 60  # Default fallback
        
        # Check for X-RateLimit headers
        elif 'X-RateLimit-Reset' in response_headers:
            try:
                reset_timestamp = int(response_headers['X-RateLimit-Reset'])
                retry_after = max(0, reset_timestamp - int(time.time()))
            except (ValueError, KeyError):
                retry_after = 60
        else:
            retry_after = 60  # Default
        
        # Store retry-after time
        with self._lock:
            self._retry_after[service] = datetime.utcnow() + timedelta(seconds=retry_after)
        
        logger.warning(f"Rate limited on '{service}', retry after {retry_after} seconds")
        return retry_after
    
    def adaptive_throttling(
        self,
        service: str,
        current_rate: float,
        target_rate: float = 0.8
    ):
        """
        Adaptively throttle requests to stay under limits.
        
        Args:
            service: Service name
            current_rate: Current request rate (0-1)
            target_rate: Target rate to maintain
        """
        if current_rate > target_rate:
            # Calculate delay to reduce rate
            delay = (current_rate - target_rate) * self._window_seconds / self._default_limit
            logger.info(f"Throttling '{service}' by {delay:.2f} seconds")
            time.sleep(delay)