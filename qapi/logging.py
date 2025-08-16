"""
Structured logging infrastructure for API Builder.

This module provides comprehensive logging with context, sensitive data masking,
performance metrics, and different log levels per module.
"""

import logging
import json
import re
import time
import sys
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import traceback
from pathlib import Path

# Patterns for sensitive data that should be masked
SENSITIVE_PATTERNS = [
    (r'(password|passwd|pwd)[\"\']?\s*[:=]\s*[\"\']?([^\s\"\']+)', r'\1=***MASKED***'),
    (r'(token|api_key|apikey|auth|authorization)[\"\']?\s*[:=]\s*[\"\']?([^\s\"\']+)', r'\1=***MASKED***'),
    (r'(secret|private_key|priv_key)[\"\']?\s*[:=]\s*[\"\']?([^\s\"\']+)', r'\1=***MASKED***'),
    (r'Bearer\s+([^\s]+)', r'Bearer ***MASKED***'),
    (r'(email)[\"\']?\s*[:=]\s*[\"\']?([^\s\"\']+@[^\s\"\']+)', r'\1=***MASKED***'),
    (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '****-****-****-****'),  # Credit cards
    (r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****'),  # SSN
]


@dataclass
class LogContext:
    """Context information for structured logging."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    service: Optional[str] = None
    operation: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    extra: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {k: v for k, v in asdict(self).items() if v is not None}
        if 'extra' in result and result['extra']:
            result.update(result.pop('extra'))
        return result


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log records."""
    
    def __init__(self, patterns: Optional[List[tuple]] = None):
        super().__init__()
        self.patterns = patterns or SENSITIVE_PATTERNS
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log message and args."""
        # Mask message
        if hasattr(record, 'msg'):
            record.msg = self._mask_sensitive(str(record.msg))
        
        # Mask args if present
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._mask_sensitive(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self._mask_sensitive(str(v)) if isinstance(v, str) else v
                    for v in record.args
                )
        
        return True
    
    def _mask_sensitive(self, text: str) -> str:
        """Apply all masking patterns to text."""
        for pattern, replacement in self.patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_traceback: bool = True):
        super().__init__()
        self.include_traceback = include_traceback
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context if present
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'getMessage', 'context']:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info and self.include_traceback:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, default=str)


class ContextLogger:
    """Logger with context management capabilities."""
    
    def __init__(self, name: str, context: Optional[LogContext] = None):
        self.logger = logging.getLogger(name)
        self.context = context or LogContext()
        self._context_stack = []
    
    def _log_with_context(
        self,
        level: int,
        msg: str,
        *args,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log message with context."""
        log_extra = {'context': self.context.to_dict()}
        if extra:
            log_extra.update(extra)
        self.logger.log(level, msg, *args, extra=log_extra, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)
    
    @contextmanager
    def context_scope(self, **kwargs):
        """Temporarily add context for a scope."""
        old_context = LogContext(**asdict(self.context))
        
        # Update context with new values
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                if self.context.extra is None:
                    self.context.extra = {}
                self.context.extra[key] = value
        
        try:
            yield self
        finally:
            self.context = old_context


class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self, logger: Union[logging.Logger, ContextLogger]):
        self.logger = logger
    
    @contextmanager
    def measure(self, operation: str, **extra):
        """Measure and log operation duration."""
        start_time = time.perf_counter()
        extra_data = {'operation': operation, 'start_time': datetime.utcnow().isoformat()}
        extra_data.update(extra)
        
        try:
            yield
            duration = time.perf_counter() - start_time
            extra_data.update({
                'duration_ms': round(duration * 1000, 2),
                'status': 'success'
            })
            self.logger.info(f"Operation '{operation}' completed", extra=extra_data)
        except Exception as e:
            duration = time.perf_counter() - start_time
            extra_data.update({
                'duration_ms': round(duration * 1000, 2),
                'status': 'failed',
                'error': str(e)
            })
            self.logger.error(f"Operation '{operation}' failed", extra=extra_data)
            raise
    
    def log_performance(
        self,
        func: Callable = None,
        *,
        operation: Optional[str] = None,
        log_args: bool = False,
        log_result: bool = False
    ):
        """Decorator to log function performance."""
        def decorator(f: Callable) -> Callable:
            op_name = operation or f.__name__
            
            @wraps(f)
            def wrapper(*args, **kwargs):
                extra = {'operation': op_name}
                if log_args:
                    extra['args'] = str(args)
                    extra['kwargs'] = str(kwargs)
                
                with self.measure(op_name, **extra) as _:
                    result = f(*args, **kwargs)
                    if log_result:
                        self.logger.debug(f"Result: {result}", extra={'result': str(result)})
                    return result
            
            return wrapper
        
        if func is None:
            return decorator
        return decorator(func)


def setup_logging(
    level: str = "INFO",
    format_type: str = "structured",
    log_file: Optional[str] = None,
    mask_sensitive: bool = True,
    module_levels: Optional[Dict[str, str]] = None
) -> logging.Logger:
    """
    Set up comprehensive logging configuration.
    
    Args:
        level: Default log level
        format_type: "structured" for JSON, "simple" for text
        log_file: Optional file to write logs to
        mask_sensitive: Whether to mask sensitive data
        module_levels: Dict of module-specific log levels
    
    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Create formatter
    if format_type == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    if mask_sensitive:
        console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        if mask_sensitive:
            file_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(file_handler)
    
    # Set module-specific levels
    if module_levels:
        for module, module_level in module_levels.items():
            logging.getLogger(module).setLevel(getattr(logging, module_level.upper()))
    
    return root_logger


def get_logger(
    name: str,
    context: Optional[LogContext] = None
) -> ContextLogger:
    """
    Get a context-aware logger.
    
    Args:
        name: Logger name (usually __name__)
        context: Optional initial context
    
    Returns:
        ContextLogger instance
    """
    return ContextLogger(name, context)


class APICallLogger:
    """Specialized logger for API calls."""
    
    def __init__(self, logger: Union[logging.Logger, ContextLogger]):
        self.logger = logger
        self.perf_logger = PerformanceLogger(logger)
    
    def log_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        **extra
    ):
        """Log API request."""
        log_data = {
            'api_event': 'request',
            'method': method,
            'url': url,
            'headers': self._sanitize_headers(headers) if headers else None,
            'body_size': len(str(body)) if body else 0,
        }
        log_data.update(extra)
        self.logger.info(f"API Request: {method} {url}", extra=log_data)
    
    def log_response(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        duration_ms: Optional[float] = None,
        **extra
    ):
        """Log API response."""
        log_data = {
            'api_event': 'response',
            'status_code': status_code,
            'headers': self._sanitize_headers(headers) if headers else None,
            'body_size': len(str(body)) if body else 0,
            'duration_ms': duration_ms,
        }
        log_data.update(extra)
        
        log_level = logging.INFO
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        
        self.logger.log(
            log_level,
            f"API Response: {status_code}",
            extra=log_data
        )
    
    def log_error(
        self,
        error: Exception,
        method: Optional[str] = None,
        url: Optional[str] = None,
        **extra
    ):
        """Log API error."""
        log_data = {
            'api_event': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'method': method,
            'url': url,
        }
        log_data.update(extra)
        self.logger.error(f"API Error: {error}", extra=log_data, exc_info=True)
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers."""
        sensitive_headers = {
            'authorization', 'x-api-key', 'x-auth-token',
            'cookie', 'set-cookie', 'x-csrf-token'
        }
        return {
            k: '***MASKED***' if k.lower() in sensitive_headers else v
            for k, v in headers.items()
        }


# Convenience function for quick setup
def quick_setup(debug: bool = False) -> ContextLogger:
    """
    Quick setup for common logging configuration.
    
    Args:
        debug: Whether to enable debug logging
    
    Returns:
        Configured logger ready to use
    """
    setup_logging(
        level="DEBUG" if debug else "INFO",
        format_type="simple" if debug else "structured",
        mask_sensitive=True
    )
    return get_logger(__name__)