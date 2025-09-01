#!/usr/bin/env python3
"""
Test script to demonstrate the new error handling capabilities.

This script runs various error scenarios to show how the improved
error handling works in practice.
"""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    NetworkError, APIError, AuthenticationError, ConfigurationError,
    FileIOError, DataValidationError, RateLimitError, wrap_exception
)
from scripts.utils import load_config
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='DEBUG', format_type='console', log_file='logs/error_test.log')
logger = get_logger(__name__)


def test_custom_exceptions():
    """Test custom exception hierarchy and context."""
    print("\\n🧪 Testing Custom Exception Hierarchy")
    print("=" * 50)
    
    # Test basic exception with context
    try:
        raise NetworkError(
            "Failed to connect to API",
            url="https://api.example.com",
            status_code=500,
            retry_count=3
        )
    except NetworkError as e:
        print(f"✓ NetworkError caught: {e}")
        print(f"  Detailed message: {e.get_detailed_message()}")
        print(f"  Context: {e.context}")
    
    # Test authentication error
    try:
        raise AuthenticationError(
            "Invalid API key",
            api_name="ESPN",
            credential_type="API_KEY"
        )
    except AuthenticationError as e:
        print(f"✓ AuthenticationError caught: {e}")
    
    # Test configuration error
    try:
        raise ConfigurationError(
            "Missing required configuration",
            config_key="league_id",
            config_file="config.yaml"
        )
    except ConfigurationError as e:
        print(f"✓ ConfigurationError caught: {e}")
    
    # Test file IO error
    try:
        raise FileIOError(
            "Permission denied",
            file_path="/restricted/file.txt",
            operation="write"
        )
    except FileIOError as e:
        print(f"✓ FileIOError caught: {e}")
    
    # Test data validation error
    try:
        raise DataValidationError(
            "Invalid player data",
            field_name="player_name",
            expected_type="str",
            actual_value=None
        )
    except DataValidationError as e:
        print(f"✓ DataValidationError caught: {e}")


def test_exception_wrapping():
    """Test exception wrapping functionality."""
    print("\\n🔄 Testing Exception Wrapping")
    print("=" * 40)
    
    # Test wrapping a built-in exception
    try:
        # Simulate a real error
        result = 1 / 0
    except ZeroDivisionError as e:
        wrapped = wrap_exception(
            e, DataValidationError,
            "Division by zero in calculation",
            field_name="denominator",
            expected_type="non-zero number"
        )
        print(f"✓ Wrapped ZeroDivisionError: {wrapped}")
        print(f"  Original error: {wrapped.original_error}")
    
    # Test wrapping with automatic error detection
    try:
        import requests
        # This will fail due to invalid URL
        response = requests.get("not-a-url", timeout=1)
    except Exception as e:
        wrapped = wrap_exception(e, NetworkError, "Failed to make HTTP request")
        print(f"✓ Wrapped requests error: {wrapped}")


@retry(max_attempts=3, base_delay=0.5, backoff_factor=2.0)
def flaky_function(fail_count: int = 2):
    """A function that fails a few times before succeeding."""
    if not hasattr(flaky_function, 'attempts'):
        flaky_function.attempts = 0
    
    flaky_function.attempts += 1
    logger.info(f"Attempt {flaky_function.attempts} of flaky_function")
    
    if flaky_function.attempts <= fail_count:
        raise NetworkError(
            f"Simulated failure on attempt {flaky_function.attempts}",
            retry_count=flaky_function.attempts - 1
        )
    
    return f"Success after {flaky_function.attempts} attempts!"


@retry(max_attempts=2, base_delay=0.1)
def always_fails():
    """A function that always fails to test retry exhaustion."""
    raise APIError("This function always fails", status_code=500)


def test_retry_logic():
    """Test retry decorator functionality."""
    print("\\n🔄 Testing Retry Logic")
    print("=" * 30)
    
    # Test successful retry
    try:
        # Reset attempts counter
        if hasattr(flaky_function, 'attempts'):
            delattr(flaky_function, 'attempts')
        
        result = flaky_function(fail_count=2)
        print(f"✓ Retry success: {result}")
    except Exception as e:
        print(f"❌ Unexpected failure: {e}")
    
    # Test retry exhaustion
    try:
        always_fails()
        print("❌ Expected failure did not occur")
    except APIError as e:
        print(f"✓ Retry exhaustion handled correctly: {e}")
    
    # Test rate limit handling
    @retry(max_attempts=2, base_delay=0.1)
    def rate_limited_function():
        raise RateLimitError("Rate limit exceeded", retry_after=1)
    
    start_time = time.time()
    try:
        rate_limited_function()
    except RateLimitError:
        elapsed = time.time() - start_time
        print(f"✓ Rate limit retry with proper delay: {elapsed:.1f}s")


@retry_with_circuit_breaker(
    max_attempts=2, 
    base_delay=0.1,
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=2.0
)
def circuit_breaker_test():
    """Function for testing circuit breaker."""
    raise NetworkError("Service unavailable", status_code=503)


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("\\n⚡ Testing Circuit Breaker")
    print("=" * 35)
    
    # Trip the circuit breaker
    for i in range(4):  # This should trip after 3 failures
        try:
            circuit_breaker_test()
        except NetworkError as e:
            if "circuit breaker" in str(e).lower():
                print(f"✓ Circuit breaker opened after {i} failures")
                break
            else:
                print(f"  Attempt {i + 1} failed: {e}")
    else:
        print("❌ Circuit breaker did not open as expected")


def test_logging_integration():
    """Test logging integration with error handling."""
    print("\\n📝 Testing Logging Integration")
    print("=" * 40)
    
    # Test different log levels with exceptions
    logger.debug("Debug message before error")
    logger.info("Info message before error")
    
    try:
        raise APIError(
            "Test API error for logging",
            api_name="TestAPI",
            endpoint="/test"
        )
    except APIError as e:
        logger.error(f"API error occurred: {e}")
        logger.warning(f"This is a test warning: {e.get_detailed_message()}")
    
    print("✓ Check log file for detailed error information")


def test_file_operations():
    """Test file operation error handling."""
    print("\\n📁 Testing File Operation Errors")
    print("=" * 45)
    
    # Test permission error simulation
    try:
        # Try to write to a directory that doesn't exist
        nonexistent_dir = "/nonexistent/directory/file.txt"
        with open(nonexistent_dir, 'w') as f:
            f.write("test")
    except (PermissionError, FileNotFoundError, OSError) as e:
        wrapped = wrap_exception(
            e, FileIOError,
            f"Failed to write to {nonexistent_dir}",
            file_path=nonexistent_dir,
            operation="write"
        )
        print(f"✓ File operation error handled: {wrapped}")
    
    # Test successful file operation with error handling
    try:
        test_file = Path("test_file.txt")
        test_file.write_text("This is a test file")
        content = test_file.read_text()
        test_file.unlink()  # Clean up
        print(f"✓ Successful file operation: Read {len(content)} characters")
    except Exception as e:
        wrapped = wrap_exception(e, FileIOError, "File operation failed")
        print(f"❌ File operation error: {wrapped}")


def main():
    """Run all error handling tests."""
    print("🚀 Fantasy Football AI - Error Handling Test Suite")
    print("=" * 60)
    
    try:
        test_custom_exceptions()
        test_exception_wrapping()
        test_retry_logic()
        test_circuit_breaker()
        test_logging_integration()
        test_file_operations()
        
        print("\\n✅ All error handling tests completed!")
        print("Check the log file at 'logs/error_test.log' for detailed information.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        print(f"\\n❌ Test suite failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
