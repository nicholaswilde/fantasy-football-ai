# Error Handling in Fantasy Football AI

This document describes the comprehensive error handling system implemented in Fantasy Football AI, including custom exception hierarchy, retry mechanisms, logging, and best practices.

## Overview

The Fantasy Football AI project now includes a robust error handling system that provides:

- **Custom exception hierarchy** with meaningful context
- **Automatic retry mechanisms** with exponential backoff
- **Circuit breaker patterns** for failing services
- **Structured logging** with detailed error information
- **User-friendly error messages** with troubleshooting guidance

## Custom Exception Hierarchy

All Fantasy Football AI errors inherit from the base `FantasyFootballError` class, which provides context and detailed error information.

### Base Exception

```python
from fantasy_ai.errors import FantasyFootballError

try:
    # Some operation
    pass
except FantasyFootballError as e:
    print(f"Error: {e}")
    print(f"Details: {e.get_detailed_message()}")
    print(f"Context: {e.context}")
```

### Exception Types

#### NetworkError
Used for network-related failures (timeouts, connection errors, DNS failures).

```python
from fantasy_ai.errors import NetworkError

raise NetworkError(
    "Failed to connect to API",
    url="https://api.sleeper.app",
    status_code=500,
    retry_count=3
)
```

#### APIError
Used for external API failures (ESPN, Sleeper, etc.).

```python
from fantasy_ai.errors import APIError

raise APIError(
    "Invalid response from Sleeper API",
    api_name="Sleeper",
    endpoint="/v1/players/nfl",
    status_code=404
)
```

#### AuthenticationError
Used for authentication and authorization failures.

```python
from fantasy_ai.errors import AuthenticationError

raise AuthenticationError(
    "Invalid ESPN credentials",
    api_name="ESPN",
    credential_type="S2/SWID"
)
```

#### ConfigurationError
Used for configuration-related errors.

```python
from fantasy_ai.errors import ConfigurationError

raise ConfigurationError(
    "Missing required configuration",
    config_key="league_id",
    config_file="config.yaml"
)
```

#### FileIOError
Used for file I/O operation failures.

```python
from fantasy_ai.errors import FileIOError

raise FileIOError(
    "Permission denied writing file",
    file_path="/data/my_team.md",
    operation="write"
)
```

#### DataValidationError
Used for data validation failures.

```python
from fantasy_ai.errors import DataValidationError

raise DataValidationError(
    "Invalid player data",
    field_name="player_name",
    expected_type="str",
    actual_value=None
)
```

#### RateLimitError
Used for API rate limiting scenarios.

```python
from fantasy_ai.errors import RateLimitError

raise RateLimitError(
    "Rate limit exceeded",
    url="https://api.sleeper.app",
    retry_after=60
)
```

## Retry Mechanisms

### Basic Retry Decorator

The `@retry` decorator automatically retries functions that fail with transient errors:

```python
from fantasy_ai.utils.retry import retry
from fantasy_ai.errors import NetworkError

@retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
def fetch_data():
    # This function will be retried up to 3 times with exponential backoff
    response = requests.get("https://api.sleeper.app/v1/players/nfl")
    if response.status_code >= 500:
        raise NetworkError("Server error", status_code=response.status_code)
    return response.json()
```

### Advanced Retry with Circuit Breaker

For critical services, use the circuit breaker pattern:

```python
from fantasy_ai.utils.retry import retry_with_circuit_breaker

@retry_with_circuit_breaker(
    max_attempts=3,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60.0
)
def critical_api_call():
    # After 5 consecutive failures, the circuit opens for 60 seconds
    return external_api.fetch_data()
```

### Retry Configuration

- **max_attempts**: Maximum number of retry attempts (default: 3)
- **base_delay**: Initial delay between retries in seconds (default: 1.0)
- **backoff_factor**: Exponential backoff multiplier (default: 2.0)
- **max_delay**: Maximum delay between retries (default: 300.0 seconds)
- **jitter**: Add randomness to delays to avoid thundering herd (default: True)

## Exception Wrapping

Use the `wrap_exception` utility to convert third-party exceptions:

```python
from fantasy_ai.errors import wrap_exception, NetworkError
import requests

try:
    response = requests.get("https://api.example.com", timeout=5)
except requests.exceptions.RequestException as e:
    # Convert to our custom exception
    raise wrap_exception(
        e, NetworkError,
        "Failed to fetch data from API",
        url="https://api.example.com"
    )
```

## Logging Integration

### Setting Up Logging

```python
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging for your script
setup_logging(level='INFO', format_type='console', log_file='logs/my_script.log')
logger = get_logger(__name__)

# Log with different levels
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

### Structured Logging

Use JSON format for machine-readable logs:

```python
setup_logging(level='DEBUG', format_type='json', log_file='logs/app.log')
```

### Log Context

The logging system automatically captures context from exceptions:

```python
try:
    raise APIError("API failed", api_name="ESPN", endpoint="/league")
except APIError as e:
    logger.error(f"API error: {e}")
    # Logs include: timestamp, level, message, api_name, endpoint, etc.
```

## Error Handling Best Practices

### 1. Always Use Custom Exceptions

```python
# ❌ Don't do this
raise ValueError("Invalid player data")

# ✅ Do this instead  
raise DataValidationError(
    "Invalid player data",
    field_name="player_name",
    expected_type="str",
    actual_value=None
)
```

### 2. Provide Context

```python
# ❌ Minimal context
raise NetworkError("Request failed")

# ✅ Rich context
raise NetworkError(
    "Request failed after 3 retries",
    url="https://api.sleeper.app",
    status_code=500,
    retry_count=3
)
```

### 3. Handle Specific Exception Types

```python
try:
    fetch_team_data()
except AuthenticationError as e:
    print("Please check your ESPN credentials")
    print(f"Error: {e}")
except NetworkError as e:
    print("Network error occurred. Please try again.")
    print(f"Error: {e}")
except ConfigurationError as e:
    print("Configuration issue detected")
    print(f"Error: {e}")
```

### 4. Use Retry for Transient Failures

```python
@retry(max_attempts=3, base_delay=2.0)
def fetch_sleeper_data():
    # Automatically retried on NetworkError, RateLimitError, etc.
    return requests.get("https://api.sleeper.app/v1/players/nfl").json()
```

### 5. Log Errors Appropriately

```python
try:
    result = some_operation()
except FantasyFootballError as e:
    # Log structured error information
    logger.error(f"Operation failed: {e.get_detailed_message()}")
    # Show user-friendly message
    print(f"Error: {e}")
except Exception as e:
    # Log unexpected errors with full traceback
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise wrap_exception(e, UnknownError)
```

## Migration Guide

### For Existing Code

1. **Replace generic exceptions** with custom ones:
   ```python
   # Before
   raise Exception("API failed")
   
   # After
   raise APIError("API failed", api_name="ESPN")
   ```

2. **Add retry decorators** to network calls:
   ```python
   # Before
   def fetch_data():
       return requests.get(url).json()
   
   # After
   @retry(max_attempts=3)
   def fetch_data():
       return requests.get(url).json()
   ```

3. **Improve error handling** in main functions:
   ```python
   # Before
   try:
       main()
   except Exception as e:
       print(f"Error: {e}")
   
   # After
   try:
       main()
   except AuthenticationError as e:
       print(f"❌ Authentication Error: {e}")
       print("- Check your .env file credentials")
   except NetworkError as e:
       print(f"❌ Network Error: {e}")
       print("- Check your internet connection")
   ```

### Backward Compatibility

Existing code continues to work, but should be gradually migrated to use the new error handling system. The new exceptions are designed to be caught by generic `Exception` handlers until migration is complete.

## Testing Error Handling

Run the error handling test suite to verify functionality:

```bash
python3 scripts/test_error_handling.py
```

This test demonstrates:
- Custom exception hierarchy
- Exception wrapping
- Retry mechanisms
- Circuit breaker functionality
- Logging integration
- File operation error handling

## Configuration

### Environment Variables

- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT`: Set log format ('console', 'json', 'simple')

### Logging Configuration File

Use `log_config.yaml` for advanced logging configuration:

```yaml
version: 1
formatters:
  console:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    formatter: console
loggers:
  fantasy_ai:
    level: DEBUG
    handlers: [console]
```

## Examples

See the following files for complete examples:
- `scripts/download_data_improved.py` - Network operations with retry
- `scripts/get_my_team_improved.py` - ESPN API integration
- `scripts/test_error_handling.py` - Comprehensive error handling tests

## Support

If you encounter issues with the error handling system:

1. Check the log files in the `logs/` directory
2. Run the test suite to verify functionality
3. Review this documentation for proper usage patterns
4. Check existing improved scripts for implementation examples
