"""
Unit tests for circuit breaker module.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from qapi.circuit_breaker import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerStats,
    MultiServiceCircuitBreaker,
    circuit_breaker
)
from qapi.exceptions import CircuitBreakerError


class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""
    
    def test_stats_initialization(self):
        stats = CircuitBreakerStats()
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.rejected_calls == 0
        assert stats.last_failure_time is None
        assert stats.last_success_time is None
        assert stats.state_changes == []
    
    def test_success_rate(self):
        stats = CircuitBreakerStats()
        assert stats.success_rate() == 1.0  # No calls yet
        
        stats.total_calls = 10
        stats.successful_calls = 7
        assert stats.success_rate() == 0.7
    
    def test_failure_rate(self):
        stats = CircuitBreakerStats()
        assert stats.failure_rate() == 0.0  # No calls yet
        
        stats.total_calls = 10
        stats.failed_calls = 3
        assert stats.failure_rate() == 0.3


class TestCircuitBreaker:
    """Test CircuitBreaker class."""
    
    def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.is_half_open is False
    
    def test_successful_calls(self):
        cb = CircuitBreaker(failure_threshold=3)
        func = Mock(return_value="success")
        
        for _ in range(5):
            result = cb.call(func)
            assert result == "success"
        
        assert cb.state == CircuitState.CLOSED
        assert func.call_count == 5
        
        stats = cb.get_stats()
        assert stats.successful_calls == 5
        assert stats.failed_calls == 0
    
    def test_circuit_opens_on_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        func = Mock(side_effect=Exception("fail"))
        
        # First failures should pass through
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(func)
        
        # Circuit should be open now
        assert cb.state == CircuitState.OPEN
        
        # Next call should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(func)
        
        assert "is OPEN" in str(exc_info.value)
        assert func.call_count == 3  # No additional call made
    
    @patch('qapi.circuit_breaker.datetime')
    def test_circuit_half_open_after_timeout(self, mock_datetime):
        # Set up time progression
        current_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=60,
            success_threshold=2
        )
        func = Mock(side_effect=Exception("fail"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(func)
        
        assert cb.state == CircuitState.OPEN
        
        # Move time forward past recovery timeout
        mock_datetime.utcnow.return_value = current_time + timedelta(seconds=61)
        
        # Circuit should transition to half-open
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_circuit_closes_after_successful_half_open(self):
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0,  # Immediate recovery for testing
            success_threshold=2,
            half_open_max_calls=3
        )
        
        # Open the circuit
        func_fail = Mock(side_effect=Exception("fail"))
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(func_fail)
        
        # Force transition to half-open
        cb._transition_to_half_open()
        assert cb.state == CircuitState.HALF_OPEN
        
        # Successful calls in half-open
        func_success = Mock(return_value="success")
        for _ in range(2):
            result = cb.call(func_success)
            assert result == "success"
        
        # Circuit should be closed now
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_reopens_on_half_open_failure(self):
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0,
            success_threshold=2
        )
        
        # Open the circuit
        func_fail = Mock(side_effect=Exception("fail"))
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(func_fail)
        
        # Force transition to half-open
        cb._transition_to_half_open()
        assert cb.state == CircuitState.HALF_OPEN
        
        # Failure in half-open should reopen
        with pytest.raises(Exception):
            cb.call(func_fail)
        
        assert cb.state == CircuitState.OPEN
    
    def test_half_open_max_calls_limit(self):
        cb = CircuitBreaker(
            failure_threshold=2,
            half_open_max_calls=2
        )
        
        # Force to half-open state
        cb._transition_to_half_open()
        
        func = Mock(return_value="success")
        
        # First two calls should work
        cb.call(func)
        cb.call(func)
        
        # Third call should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(func)
        
        assert "max calls reached" in str(exc_info.value)
        assert func.call_count == 2
    
    def test_manual_reset(self):
        cb = CircuitBreaker(failure_threshold=2)
        func = Mock(side_effect=Exception("fail"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(func)
        
        assert cb.state == CircuitState.OPEN
        
        # Manual reset
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0
    
    def test_decorator_usage(self):
        cb = CircuitBreaker(failure_threshold=2)
        
        @cb
        def protected_function(x):
            if x < 0:
                raise ValueError("Negative value")
            return x * 2
        
        # Successful calls
        assert protected_function(5) == 10
        
        # Failures open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                protected_function(-1)
        
        # Circuit is open
        with pytest.raises(CircuitBreakerError):
            protected_function(5)
    
    def test_thread_safety(self):
        cb = CircuitBreaker(failure_threshold=5)
        results = []
        errors = []
        
        def worker(should_fail):
            try:
                if should_fail:
                    result = cb.call(Mock(side_effect=Exception("fail")))
                else:
                    result = cb.call(Mock(return_value="success"))
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i < 5,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have some successes and failures
        assert len(results) > 0
        assert len(errors) > 0


class TestMultiServiceCircuitBreaker:
    """Test MultiServiceCircuitBreaker class."""
    
    def test_get_or_create_breaker(self):
        multi = MultiServiceCircuitBreaker()
        
        # First call creates new breaker
        breaker1 = multi.get_breaker("service1")
        assert isinstance(breaker1, CircuitBreaker)
        
        # Second call returns same breaker
        breaker2 = multi.get_breaker("service1")
        assert breaker1 is breaker2
        
        # Different service gets different breaker
        breaker3 = multi.get_breaker("service2")
        assert breaker3 is not breaker1
    
    def test_call_through_service(self):
        multi = MultiServiceCircuitBreaker()
        func = Mock(return_value="success")
        
        result = multi.call("service1", func, 1, 2, key="value")
        assert result == "success"
        func.assert_called_once_with(1, 2, key="value")
    
    def test_reset_specific_service(self):
        multi = MultiServiceCircuitBreaker()
        
        # Open circuit for service1
        for _ in range(5):
            try:
                multi.call("service1", Mock(side_effect=Exception("fail")))
            except:
                pass
        
        # Verify it's open
        with pytest.raises(CircuitBreakerError):
            multi.call("service1", Mock())
        
        # Reset service1
        multi.reset("service1")
        
        # Should work now
        result = multi.call("service1", Mock(return_value="success"))
        assert result == "success"
    
    def test_reset_all_services(self):
        multi = MultiServiceCircuitBreaker()
        
        # Open circuits for multiple services
        for service in ["service1", "service2"]:
            for _ in range(5):
                try:
                    multi.call(service, Mock(side_effect=Exception("fail")))
                except:
                    pass
        
        # Reset all
        multi.reset()
        
        # All should work now
        for service in ["service1", "service2"]:
            result = multi.call(service, Mock(return_value="success"))
            assert result == "success"
    
    def test_get_all_stats(self):
        multi = MultiServiceCircuitBreaker()
        
        # Make some calls
        multi.call("service1", Mock(return_value="success"))
        try:
            multi.call("service2", Mock(side_effect=Exception("fail")))
        except:
            pass
        
        stats = multi.get_all_stats()
        assert "service1" in stats
        assert "service2" in stats
        assert stats["service1"].successful_calls == 1
        assert stats["service2"].failed_calls == 1
    
    def test_get_open_circuits(self):
        multi = MultiServiceCircuitBreaker(
            default_config={"failure_threshold": 2}
        )
        
        # Open service1
        for _ in range(2):
            try:
                multi.call("service1", Mock(side_effect=Exception("fail")))
            except:
                pass
        
        # Keep service2 closed
        multi.call("service2", Mock(return_value="success"))
        
        open_circuits = multi.get_open_circuits()
        assert "service1" in open_circuits
        assert "service2" not in open_circuits


class TestCircuitBreakerDecorator:
    """Test circuit_breaker decorator function."""
    
    def test_decorator_basic(self):
        @circuit_breaker(failure_threshold=2)
        def protected_function(x):
            if x < 0:
                raise ValueError("Negative")
            return x * 2
        
        # Success
        assert protected_function(5) == 10
        
        # Failures
        for _ in range(2):
            with pytest.raises(ValueError):
                protected_function(-1)
        
        # Circuit open
        with pytest.raises(CircuitBreakerError):
            protected_function(5)
    
    def test_decorator_with_name(self):
        @circuit_breaker(
            failure_threshold=2,
            name="my_service"
        )
        def protected_function():
            raise Exception("fail")
        
        # Trigger circuit
        for _ in range(2):
            with pytest.raises(Exception):
                protected_function()
        
        # Check error message has custom name
        with pytest.raises(CircuitBreakerError) as exc_info:
            protected_function()
        
        assert "my_service" in str(exc_info.value)
    
    def test_decorator_access_breaker_instance(self):
        @circuit_breaker(failure_threshold=3)
        def protected_function():
            return "success"
        
        # Access the breaker instance
        assert hasattr(protected_function, 'circuit_breaker')
        breaker = protected_function.circuit_breaker
        assert isinstance(breaker, CircuitBreaker)
        
        # Can manually reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED