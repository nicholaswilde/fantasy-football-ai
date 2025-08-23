#!/usr/bin/env python3
"""
Retry utility with exponential backoff for Fantasy Football AI.

This module provides a decorator and utility functions for retrying operations
that may fail transiently, such as network requests or database operations.
"""

import functools
import random
import time
import logging
from typing import Callable, Type, Tuple, Any, Optional, Union

from ..errors import NetworkError, RateLimitError, APIError, FantasyFootballError

logger = logging.getLogger(__name__)

# Default retryable exceptions
DEFAULT_RETRYABLE_EXCEPTIONS = (
    NetworkError,
    RateLimitError,
    ConnectionError,
    TimeoutError,
)


def calculate_backoff_delay(
    attempt: int, 
    base_delay: float = 1.0, 
    backoff_factor: float = 2.0, 
    max_delay: float = 300.0,
    jitter: bool = True
) -> float:
    """
    Calculate the delay for exponential backoff with optional jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        base_delay: Initial delay in seconds
        backoff_factor: Multiplication factor for each retry
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter to prevent thundering herd
        
    Returns:
        Delay in seconds before next retry
    """
    # Calculate exponential delay
    delay = base_delay * (backoff_factor ** attempt)
    
    # Cap at max_delay
    delay = min(delay, max_delay)
    
    # Add jitter if requested (±25% of the calculated delay)
    if jitter:
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
        
    # Ensure delay is never negative
    return max(delay, 0)


def should_retry_exception(
    exception: Exception,
    retryable_exceptions: Tuple[Type[Exception], ...],
    attempt: int,
    max_attempts: int
) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: The exception that occurred
        retryable_exceptions: Tuple of exception types that are retryable
        attempt: Current attempt number (0-based)
        max_attempts: Maximum number of attempts allowed
        
    Returns:
        True if the operation should be retried, False otherwise
    """
    # Don't retry if we've exceeded max attempts
    if attempt >= max_attempts:
        return False
    
    # Check if it's a retryable exception type
    if not isinstance(exception, retryable_exceptions):
        return False
    
    # Special handling for rate limit errors - always retry with proper delay
    if isinstance(exception, RateLimitError):
        return True
        
    # For HTTP errors, only retry on server errors (5xx) and some client errors
    if isinstance(exception, (NetworkError, APIError)):
        status_code = getattr(exception, 'status_code', None)
        if status_code:
            # Retry on server errors (5xx) and rate limits (429)
            if 500 <= status_code < 600 or status_code == 429:
                return True
            # Don't retry on client errors (4xx) except for rate limits
            if 400 <= status_code < 500:
                return False
                
    return True


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 300.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Decorator that adds retry logic with exponential backoff to a function.
    
    Args:
        max_attempts: Maximum number of attempts (including the first one)
        base_delay: Initial delay between retries in seconds
        backoff_factor: Factor by which delay increases each retry
        max_delay: Maximum delay between retries in seconds
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called before each retry
        
    Example:
        @retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
        def fetch_data():
            # This function will be retried up to 3 times with exponential backoff
            return requests.get("https://api.example.com/data")
    """
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry this exception
                    if not should_retry_exception(e, retryable_exceptions, attempt, max_attempts):
                        logger.debug(f"Not retrying exception {type(e).__name__}: {e}")
                        raise
                    
                    # Calculate delay for next attempt
                    if attempt < max_attempts - 1:  # Don't delay after the last attempt
                        delay = calculate_backoff_delay(
                            attempt, base_delay, backoff_factor, max_delay, jitter
                        )
                        
                        # Special handling for rate limit errors
                        if isinstance(e, RateLimitError) and hasattr(e, 'retry_after') and e.retry_after:
                            delay = max(delay, e.retry_after)
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: "
                            f"{type(e).__name__}: {e}. Retrying in {delay:.2f} seconds..."
                        )
                        
                        # Call retry callback if provided
                        if on_retry:
                            try:
                                on_retry(e, attempt + 1, delay)
                            except Exception as callback_error:
                                logger.error(f"Error in retry callback: {callback_error}")
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: "
                            f"{type(e).__name__}: {e}"
                        )
            
            # If we get here, all attempts failed
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def retry_with_circuit_breaker(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 300.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: float = 60.0
):
    """
    Advanced retry decorator with circuit breaker functionality.
    
    This decorator implements a simple circuit breaker pattern in addition to retries.
    After a certain number of consecutive failures, it will "open" the circuit and
    fail fast for a timeout period before allowing attempts again.
    
    Args:
        max_attempts: Maximum number of attempts per call
        base_delay: Initial delay between retries
        backoff_factor: Factor by which delay increases each retry
        max_delay: Maximum delay between retries
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Exception types to retry on
        circuit_breaker_threshold: Number of consecutive failures to open circuit
        circuit_breaker_timeout: Seconds to wait before allowing attempts again
        
    Note:
        This is a simplified circuit breaker implementation. For production use,
        consider using a more sophisticated library like pybreaker.
    """
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS
    
    # Simple circuit breaker state (in production, this should be more sophisticated)
    circuit_state = {
        'failures': 0,
        'last_failure_time': 0,
        'is_open': False
    }
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_time = time.time()
            
            # Check circuit breaker state
            if circuit_state['is_open']:
                if current_time - circuit_state['last_failure_time'] > circuit_breaker_timeout:
                    # Reset circuit breaker
                    circuit_state['is_open'] = False
                    circuit_state['failures'] = 0
                    logger.info(f"Circuit breaker reset for {func.__name__}")
                else:
                    raise NetworkError(
                        f"Circuit breaker is open for {func.__name__}. "
                        f"Try again after {circuit_breaker_timeout} seconds."
                    )
            
            # Try the operation with retries
            try:
                # Use the regular retry logic
                @retry(
                    max_attempts=max_attempts,
                    base_delay=base_delay,
                    backoff_factor=backoff_factor,
                    max_delay=max_delay,
                    jitter=jitter,
                    retryable_exceptions=retryable_exceptions
                )
                def _wrapped():
                    return func(*args, **kwargs)
                
                result = _wrapped()
                
                # Reset failure count on success
                circuit_state['failures'] = 0
                return result
                
            except Exception as e:
                # Update circuit breaker state on failure
                circuit_state['failures'] += 1
                circuit_state['last_failure_time'] = current_time
                
                if circuit_state['failures'] >= circuit_breaker_threshold:
                    circuit_state['is_open'] = True
                    logger.error(
                        f"Circuit breaker opened for {func.__name__} after "
                        f"{circuit_state['failures']} consecutive failures"
                    )
                
                raise
        
        return wrapper
    return decorator
