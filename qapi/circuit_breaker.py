"""
Circuit breaker pattern implementation for fault tolerance.

This module provides a circuit breaker to prevent cascading failures
in distributed systems by temporarily blocking calls to failing services.
"""

from typing import Callable, TypeVar, Optional, Any, Dict
from functools import wraps
from enum import Enum
from datetime import datetime, timedelta
import time
import logging
import threading
from dataclasses import dataclass, field

from .exceptions import CircuitBreakerError, APIError

T = TypeVar('T')
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit tripped, requests fail immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: list = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if the service has recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 2,
        half_open_max_calls: int = 3,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery (half-open)
            expected_exception: Exception type that triggers the breaker
            success_threshold: Successes needed in half-open to close
            half_open_max_calls: Max calls allowed in half-open state
            name: Optional name for the circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.half_open_max_calls = half_open_max_calls
        self.name = name or "CircuitBreaker"
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_state_change = datetime.utcnow()
        self._lock = threading.RLock()
        self._stats = CircuitBreakerStats()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for automatic transitions."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing)."""
        return self.state == CircuitState.HALF_OPEN
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of function execution
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function fails
        """
        with self._lock:
            if self.is_open:
                self._stats.rejected_calls += 1
                recovery_time = self._last_failure_time + timedelta(seconds=self.recovery_timeout)
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN",
                    service=self.name,
                    failure_count=self._failure_count,
                    recovery_time=recovery_time
                )
            
            if self.is_half_open:
                if self._half_open_calls >= self.half_open_max_calls:
                    self._stats.rejected_calls += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN with max calls reached",
                        service=self.name
                    )
                self._half_open_calls += 1
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.successful_calls += 1
            self._stats.last_success_time = datetime.utcnow()
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"Circuit '{self.name}' half-open success "
                    f"({self._success_count}/{self.success_threshold})"
                )
                
                if self._success_count >= self.success_threshold:
                    self._transition_to_closed()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0  # Reset failure count on success
    
    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            self._stats.last_failure_time = datetime.utcnow()
            self._last_failure_time = datetime.utcnow()
            
            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                logger.warning(
                    f"Circuit '{self.name}' failure "
                    f"({self._failure_count}/{self.failure_threshold})"
                )
                
                if self._failure_count >= self.failure_threshold:
                    self._transition_to_open()
            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return False
        
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._last_state_change = datetime.utcnow()
        self._stats.state_changes.append({
            "from": self._state,
            "to": CircuitState.OPEN,
            "timestamp": self._last_state_change
        })
        logger.error(
            f"Circuit breaker '{self.name}' transitioned to OPEN. "
            f"Will retry in {self.recovery_timeout} seconds."
        )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        previous_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._half_open_calls = 0
        self._last_state_change = datetime.utcnow()
        self._stats.state_changes.append({
            "from": previous_state,
            "to": CircuitState.HALF_OPEN,
            "timestamp": self._last_state_change
        })
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to HALF_OPEN. "
            f"Testing with up to {self.half_open_max_calls} calls."
        )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        previous_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_state_change = datetime.utcnow()
        self._stats.state_changes.append({
            "from": previous_state,
            "to": CircuitState.CLOSED,
            "timestamp": self._last_state_change
        })
        logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED. Service recovered.")
    
    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return self._stats
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use circuit breaker as a decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper


class MultiServiceCircuitBreaker:
    """
    Manages multiple circuit breakers for different services.
    """
    
    def __init__(self, default_config: Optional[Dict[str, Any]] = None):
        """
        Initialize multi-service circuit breaker.
        
        Args:
            default_config: Default configuration for new circuit breakers
        """
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = default_config or {
            "failure_threshold": 5,
            "recovery_timeout": 60,
            "success_threshold": 2
        }
        self._lock = threading.RLock()
    
    def get_breaker(self, service_name: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a service.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Circuit breaker for the service
        """
        with self._lock:
            if service_name not in self._breakers:
                self._breakers[service_name] = CircuitBreaker(
                    name=service_name,
                    **self._default_config
                )
            return self._breakers[service_name]
    
    def call(
        self,
        service_name: str,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function through service-specific circuit breaker.
        
        Args:
            service_name: Name of the service
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of function execution
        """
        breaker = self.get_breaker(service_name)
        return breaker.call(func, *args, **kwargs)
    
    def reset(self, service_name: Optional[str] = None):
        """
        Reset circuit breaker(s).
        
        Args:
            service_name: Specific service to reset, or None for all
        """
        with self._lock:
            if service_name:
                if service_name in self._breakers:
                    self._breakers[service_name].reset()
            else:
                for breaker in self._breakers.values():
                    breaker.reset()
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {
                name: breaker.get_stats()
                for name, breaker in self._breakers.items()
            }
    
    def get_open_circuits(self) -> List[str]:
        """Get list of services with open circuits."""
        with self._lock:
            return [
                name for name, breaker in self._breakers.items()
                if breaker.is_open
            ]


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    name: Optional[str] = None
):
    """
    Decorator to add circuit breaker protection to a function.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
        expected_exception: Exception type that triggers the breaker
        name: Optional name for the circuit breaker
    
    Returns:
        Decorated function with circuit breaker protection
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name or func.__name__
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)
        
        # Attach breaker instance for access if needed
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator