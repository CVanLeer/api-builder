"""
Unit tests for retry logic module.
"""

import pytest
import time
from unittest.mock import Mock, patch, call
from qapi.retry import (
    RetryStrategy,
    calculate_backoff_delay,
    exponential_backoff,
    retry_with_backoff,
    AdaptiveRetry
)
from qapi.exceptions import RetryableError, RateLimitError


class TestCalculateBackoffDelay:
    """Test backoff delay calculation."""
    
    def test_exponential_backoff(self):
        delay = calculate_backoff_delay(
            attempt=0, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.EXPONENTIAL, jitter=False
        )
        assert delay == 1.0
        
        delay = calculate_backoff_delay(
            attempt=1, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.EXPONENTIAL, jitter=False
        )
        assert delay == 2.0
        
        delay = calculate_backoff_delay(
            attempt=2, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.EXPONENTIAL, jitter=False
        )
        assert delay == 4.0
    
    def test_linear_backoff(self):
        delay = calculate_backoff_delay(
            attempt=0, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.LINEAR, jitter=False
        )
        assert delay == 1.0
        
        delay = calculate_backoff_delay(
            attempt=1, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.LINEAR, jitter=False
        )
        assert delay == 2.0
        
        delay = calculate_backoff_delay(
            attempt=2, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.LINEAR, jitter=False
        )
        assert delay == 3.0
    
    def test_fibonacci_backoff(self):
        delay = calculate_backoff_delay(
            attempt=0, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.FIBONACCI, jitter=False
        )
        assert delay == 1.0
        
        delay = calculate_backoff_delay(
            attempt=1, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.FIBONACCI, jitter=False
        )
        assert delay == 1.0
        
        delay = calculate_backoff_delay(
            attempt=2, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.FIBONACCI, jitter=False
        )
        assert delay == 2.0
        
        delay = calculate_backoff_delay(
            attempt=3, base_delay=1.0, max_delay=60.0,
            strategy=RetryStrategy.FIBONACCI, jitter=False
        )
        assert delay == 3.0
    
    def test_fixed_backoff(self):
        delay = calculate_backoff_delay(
            attempt=0, base_delay=5.0, max_delay=60.0,
            strategy=RetryStrategy.FIXED, jitter=False
        )
        assert delay == 5.0
        
        delay = calculate_backoff_delay(
            attempt=5, base_delay=5.0, max_delay=60.0,
            strategy=RetryStrategy.FIXED, jitter=False
        )
        assert delay == 5.0
    
    def test_max_delay_cap(self):
        delay = calculate_backoff_delay(
            attempt=10, base_delay=1.0, max_delay=10.0,
            strategy=RetryStrategy.EXPONENTIAL, jitter=False
        )
        assert delay == 10.0
    
    def test_jitter(self):
        # With jitter, delay should vary
        delays = set()
        for _ in range(10):
            delay = calculate_backoff_delay(
                attempt=2, base_delay=1.0, max_delay=60.0,
                strategy=RetryStrategy.EXPONENTIAL, jitter=True
            )
            delays.add(delay)
        # Should have different values due to jitter
        assert len(delays) > 1


class TestExponentialBackoff:
    """Test exponential backoff function."""
    
    @patch('time.sleep')
    def test_successful_on_first_try(self, mock_sleep):
        func = Mock(return_value="success")
        result = exponential_backoff(func)
        assert result == "success"
        func.assert_called_once()
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    def test_retry_on_exception(self, mock_sleep):
        func = Mock(side_effect=[Exception("fail"), "success"])
        result = exponential_backoff(func, max_retries=1)
        assert result == "success"
        assert func.call_count == 2
        mock_sleep.assert_called_once()
    
    @patch('time.sleep')
    def test_exhausted_retries(self, mock_sleep):
        func = Mock(side_effect=Exception("always fails"))
        with pytest.raises(Exception) as exc_info:
            exponential_backoff(func, max_retries=2)
        assert str(exc_info.value) == "always fails"
        assert func.call_count == 3  # Initial + 2 retries
        assert mock_sleep.call_count == 2
    
    @patch('time.sleep')
    def test_retry_on_specific_exception(self, mock_sleep):
        func = Mock(side_effect=[ValueError("retry this"), "success"])
        result = exponential_backoff(
            func,
            max_retries=1,
            retry_on=(ValueError,)
        )
        assert result == "success"
        assert func.call_count == 2
    
    @patch('time.sleep')
    def test_no_retry_on_other_exception(self, mock_sleep):
        func = Mock(side_effect=TypeError("don't retry"))
        with pytest.raises(TypeError):
            exponential_backoff(
                func,
                max_retries=1,
                retry_on=(ValueError,)
            )
        func.assert_called_once()
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    def test_custom_retry_condition(self, mock_sleep):
        func = Mock(side_effect=[Exception("retry"), Exception("don't"), "success"])
        
        def should_retry(e):
            return "retry" in str(e)
        
        with pytest.raises(Exception) as exc_info:
            exponential_backoff(
                func,
                max_retries=2,
                retry_if=should_retry
            )
        assert str(exc_info.value) == "don't"
        assert func.call_count == 2
    
    @patch('time.sleep')
    def test_rate_limit_retry_after(self, mock_sleep):
        func = Mock(side_effect=[
            RateLimitError("rate limited", retry_after=5),
            "success"
        ])
        result = exponential_backoff(func, max_retries=1)
        assert result == "success"
        mock_sleep.assert_called_once_with(5)
    
    @patch('time.sleep')
    def test_on_retry_callback(self, mock_sleep):
        on_retry = Mock()
        func = Mock(side_effect=[Exception("fail"), "success"])
        
        result = exponential_backoff(
            func,
            max_retries=1,
            on_retry=on_retry
        )
        assert result == "success"
        on_retry.assert_called_once()
        call_args = on_retry.call_args
        assert isinstance(call_args[0][0], Exception)
        assert call_args[0][1] == 0  # Attempt number


class TestRetryDecorator:
    """Test retry_with_backoff decorator."""
    
    @patch('time.sleep')
    def test_decorator_basic(self, mock_sleep):
        call_count = 0
        
        @retry_with_backoff(max_retries=2)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 3
    
    @patch('time.sleep')
    def test_decorator_with_arguments(self, mock_sleep):
        @retry_with_backoff(max_retries=1, strategy=RetryStrategy.LINEAR)
        def function_with_args(x, y):
            if x == 0:
                raise ValueError("x cannot be zero")
            return x + y
        
        # Should work normally
        assert function_with_args(1, 2) == 3
        
        # Should fail after retries
        with pytest.raises(ValueError):
            function_with_args(0, 2)


class TestAdaptiveRetry:
    """Test adaptive retry mechanism."""
    
    def test_adaptive_retry_success(self):
        adaptive = AdaptiveRetry(
            initial_max_retries=3,
            initial_base_delay=0.01
        )
        
        func = Mock(return_value="success")
        result = adaptive.execute(func)
        assert result == "success"
        func.assert_called_once()
        
        stats = adaptive.get_statistics()
        assert stats["total_attempts"] == 1
        assert stats["success_rate"] == 1.0
    
    @patch('time.sleep')
    def test_adaptive_retry_failure_then_success(self, mock_sleep):
        adaptive = AdaptiveRetry(
            initial_max_retries=2,
            initial_base_delay=0.01
        )
        
        func = Mock(side_effect=[Exception("fail"), "success"])
        result = adaptive.execute(func)
        assert result == "success"
        assert func.call_count == 2
    
    @patch('time.sleep')
    def test_adaptive_reduces_retries_on_success(self, mock_sleep):
        adaptive = AdaptiveRetry(
            initial_max_retries=3,
            initial_base_delay=0.01,
            success_threshold=2
        )
        
        func = Mock(return_value="success")
        
        # Multiple successes
        for _ in range(2):
            adaptive.execute(func)
        
        # Should have reduced max_retries
        assert adaptive.max_retries == 2
        assert adaptive.base_delay < 0.01
    
    @patch('time.sleep')
    def test_adaptive_increases_retries_on_failure(self, mock_sleep):
        adaptive = AdaptiveRetry(
            initial_max_retries=2,
            initial_base_delay=0.01,
            failure_threshold=2
        )
        
        func = Mock(side_effect=Exception("always fails"))
        
        # Multiple failures
        for _ in range(2):
            with pytest.raises(Exception):
                adaptive.execute(func)
        
        # Should have increased max_retries
        assert adaptive.max_retries == 3
        assert adaptive.base_delay > 0.01
    
    def test_adaptive_statistics(self):
        adaptive = AdaptiveRetry(
            initial_max_retries=2,
            initial_base_delay=0.01
        )
        
        # Some successes and failures
        func_success = Mock(return_value="success")
        func_fail = Mock(side_effect=Exception("fail"))
        
        adaptive.execute(func_success)
        with pytest.raises(Exception):
            adaptive.execute(func_fail)
        adaptive.execute(func_success)
        
        stats = adaptive.get_statistics()
        assert stats["total_attempts"] == 3
        assert stats["success_rate"] == 2/3
        assert stats["current_max_retries"] == adaptive.max_retries
        assert stats["current_base_delay"] == adaptive.base_delay