---
name: Launch Error Handling Agent
about: Deploy Agent 3 for error handling and resilience
title: '[AGENT-3] Implement Error Handling & Resilience'
labels: agent-3-errors, automated, reliability
assignees: ''

---

@claude-ai You are Agent 3 (Error Handling & Resilience Engineer)

## 🎯 Your Mission
Implement comprehensive error handling and resilience patterns throughout the application.

## 📍 Working Branch
`feature/error-handling`

## ✅ Primary Tasks

### Core Implementation:
1. **Retry Logic** (`qapi/retry.py`)
   ```python
   def exponential_backoff(
       func: Callable,
       max_retries: int = 3,
       base_delay: float = 1.0,
       max_delay: float = 60.0,
       jitter: bool = True
   ) -> Any:
       """Implement with jitter for distributed systems."""
   ```

2. **Circuit Breaker** (`qapi/circuit_breaker.py`)
   ```python
   class CircuitBreaker:
       def __init__(self, failure_threshold=5, recovery_timeout=60):
           # States: CLOSED, OPEN, HALF_OPEN
           # Implement state transitions
   ```

3. **Custom Exceptions** (`qapi/exceptions.py`)
   ```python
   class APIError(Exception):
       """Base exception for all API errors."""
   
   class APIConnectionError(APIError):
       """Network connection failures."""
   
   class AuthenticationError(APIError):
       """Auth failures with retry hints."""
   
   class RateLimitError(APIError):
       """Rate limit with retry-after."""
   
   class ParseError(APIError):
       """Parsing failures with context."""
   
   class ValidationError(APIError):
       """Validation with specific fields."""
   ```

4. **Logging Infrastructure** (`qapi/logging.py`)
   - Structured logging with context
   - Different log levels per module
   - Sensitive data masking
   - Performance metrics logging

5. **Error Recovery** (`qapi/recovery.py`)
   - Graceful degradation strategies
   - Fallback mechanisms
   - Cache on failure
   - Queue for retry

## 📋 Specific Requirements

### Rate Limiting Handler:
```python
class RateLimiter:
    def handle_429(self, response):
        """Extract Retry-After header and wait."""
        
    def adaptive_throttling(self):
        """Slow down before hitting limits."""
```

### Network Resilience:
- Timeouts with incremental increases
- Connection pooling
- Keep-alive management
- DNS caching

### User-Friendly Errors:
```python
def format_user_error(error: Exception) -> str:
    """
    Convert technical errors to user-friendly messages.
    
    Examples:
    - ConnectionError -> "Unable to reach the API. Please check your internet connection."
    - 401 -> "Authentication failed. Please run 'auth get-token' to refresh."
    """
```

## 📊 Success Metrics
- [ ] Zero unhandled exceptions
- [ ] 99% success rate with retry
- [ ] Circuit breaker prevents cascading failures
- [ ] All errors have user-friendly messages
- [ ] Comprehensive logging without sensitive data

## 📚 Reference Documents
- Review `TODO.md` Week 2 tasks
- Follow `docs/ARCHITECTURE.md` patterns
- Check existing error handling in codebase

## 🔄 Coordination Notes
- Agent 2's parsers need ParseError handling
- Agent 1 will test your error scenarios
- Provide clear error types for all agents

## 📝 Deliverables
1. Complete error handling system
2. Resilience patterns implemented
3. Logging infrastructure
4. Unit tests for all error paths
5. PR to `develop` branch

---
*Start by implementing the retry logic with tests, then build up the error hierarchy. Create a draft PR early for visibility.*