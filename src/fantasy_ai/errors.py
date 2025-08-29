#!/usr/bin/env python3
"""
Custom exception hierarchy for Fantasy Football AI.

This module provides a comprehensive set of custom exceptions that wrap
third-party errors and provide meaningful context for different failure modes.
"""

from typing import Any, Dict, Optional
import traceback


class FantasyFootballAIAgentError(Exception):
    """Base exception for all Fantasy Football AI errors."""
    
    def __init__(
        self, 
        message: str,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base Fantasy Football error. 
        
        Args:
            message: Human-readable error message
            original_error: The original exception that caused this error
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.original_error = original_error
        self.context = context or {}
        
    def __str__(self) -> str:
        """Return string representation with context."""
        base_msg = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg += f" (Context: {context_str})"
        return base_msg
    
    def get_detailed_message(self) -> str:
        """Get detailed error message including original error if available."""
        msg = str(self)
        if self.original_error:
            msg += f"\nCaused by: {type(self.original_error).__name__}: {self.original_error}"
        return msg


class ConfigurationError(FantasyFootballAIAgentError):
    """Exception raised for errors in configuration settings."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize configuration error. 
        
        Args:
            message: Error description
            config_key: The configuration key that caused the issue
            config_file: Path to the configuration file
            original_error: Original exception
        """
        context = {}
        if config_key:
            context["config_key"] = config_key
        if config_file:
            context["config_file"] = config_file
            
        super().__init__(message, original_error, context)
        self.config_key = config_key
        self.config_file = config_file


class DataProcessingError(FantasyFootballAIAgentError):
    """Exception raised for errors during data processing."""
    pass


class NetworkError(FantasyFootballAIAgentError):
    """Exception raised for network-related errors."""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        retry_count: int = 0,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize network error. 
        
        Args:
            message: Error description
            url: The URL that failed
            status_code: HTTP status code if applicable
            retry_count: Number of retries attempted
            original_error: Original exception
        """
        context = {"retry_count": retry_count}
        if url:
            context["url"] = url
        if status_code:
            context["status_code"] = status_code
            
        super().__init__(message, original_error, context)
        self.url = url
        self.status_code = status_code
        self.retry_count = retry_count


class RateLimitError(NetworkError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        url: Optional[str] = None,
        retry_after: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize rate limit error. 
        
        Args:
            message: Error description
            url: The URL that was rate limited
            retry_after: Seconds to wait before retrying
            original_error: Original exception
        """
        super().__init__(message, url, 429, 0, original_error)
        self.retry_after = retry_after
        if retry_after:
            self.context["retry_after"] = retry_after


class DataValidationError(FantasyFootballAIAgentError):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize data validation error. 
        
        Args:
            message: Error description
            field_name: Name of the field that failed validation
            expected_type: Expected data type
            actual_value: The actual value that failed validation
            original_error: Original exception
        """
        context = {}
        if field_name:
            context["field_name"] = field_name
        if expected_type:
            context["expected_type"] = expected_type
        if actual_value is not None:
            context["actual_value"] = str(actual_value)
            
        super().__init__(message, original_error, context)
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_value = actual_value


class FileOperationError(FantasyFootballAIAgentError):
    """Raised when file I/O operations fail."""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize file I/O error. 
        
        Args:
            message: Error description
            file_path: Path to the file that caused the error
            operation: The operation being performed (read, write, delete, etc.)
            original_error: Original exception
        """
        context = {}
        if file_path:
            context["file_path"] = file_path
        if operation:
            context["operation"] = operation
            
        super().__init__(message, original_error, context)
        self.file_path = file_path
        self.operation = operation

# For backward compatibility
FileIOError = FileOperationError


class APIError(FantasyFootballAIAgentError):
    """Raised when external API calls fail."""
    
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize API error. 
        
        Args:
            message: Error description
            api_name: Name of the API (e.g., 'ESPN', 'Sleeper')
            endpoint: The API endpoint that failed
            status_code: HTTP status code
            original_error: Original exception
        """
        context = {}
        if api_name:
            context["api_name"] = api_name
        if endpoint:
            context["endpoint"] = endpoint
        if status_code:
            context["status_code"] = status_code
            
        super().__init__(message, original_error, context)
        self.api_name = api_name
        self.endpoint = endpoint
        self.status_code = status_code


class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        api_name: Optional[str] = None,
        credential_type: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize authentication error. 
        
        Args:
            message: Error description
            api_name: Name of the API
            credential_type: Type of credential (API key, token, etc.)
            original_error: Original exception
        """
        super().__init__(message, api_name, None, 401, original_error)
        self.credential_type = credential_type
        if credential_type:
            self.context["credential_type"] = credential_type


class UnknownError(FantasyFootballAIAgentError):
    """Raised when an unexpected error occurs that doesn't fit other categories."""
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        original_error: Optional[Exception] = None,
        location: Optional[str] = None
    ):
        """
        Initialize unknown error. 
        
        Args:
            message: Error description
            original_error: Original exception
            location: Location where the error occurred (function, module, etc.)
        """
        context = {}
        if location:
            context["location"] = location
        else:
            # Try to get the calling function name
            try:
                frame = traceback.extract_stack()[-3]  # -1 is this function, -2 is caller, -3 is caller's caller
                context["location"] = f"{frame.filename}:{frame.name}:{frame.lineno}"
            except (IndexError, AttributeError):
                pass
                
        super().__init__(message, original_error, context)
        self.location = location


def wrap_exception(
    original_error: Exception,
    error_class: type = UnknownError,
    message: Optional[str] = None,
    **kwargs
) -> FantasyFootballAIAgentError:
    """
    Wrap a third-party exception in a Fantasy Football AI exception.
    
    Args:
        original_error: The original exception to wrap
        error_class: The Fantasy Football AI exception class to use
        message: Optional custom message (defaults to original error message)
        **kwargs: Additional arguments to pass to the error class
        
    Returns:
        A Fantasy Football AI exception wrapping the original error
    """
    if message is None:
        message = str(original_error)
    
    return error_class(
        message=message,
        original_error=original_error,
        **kwargs
    )