#!/usr/bin/env python3
"""
Main entry point for the Fantasy Football AI assistant with comprehensive error handling.

Handles user interactions and integrates various analytical tools with robust
error handling, retry logic, and proper API management.

@author Nicholas Wilde, 0xb299a622
@date 2025-08-23
@version 0.6.0
"""

import os
import sys
import yaml
import google.generativeai as genai
import openai
from openai import OpenAI
from dotenv import load_dotenv
import time
from pydantic import ValidationError

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError, 
    FileOperationError, DataValidationError, RateLimitError, wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger
from fantasy_ai.config_model import Config # Import the Pydantic Config model
from scripts.utils import load_config

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/fantasy_football_ai.log')
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration file path
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

# Global client variable
CLIENT = None

def get_llm_settings(config: Config) -> tuple:
    """
    Extract LLM settings from configuration with validation.
    
    Args:
        config: Validated configuration object (Pydantic Config model)
        
    Returns:
        Tuple of (provider, model, request_delay)
        
    Raises:
        ConfigurationError: If LLM settings are invalid
    """
    try:
        llm_settings = config.llm_settings
        
        provider = llm_settings.provider
        if provider not in ['google', 'openai']:
            raise ConfigurationError(
                f"Unsupported LLM provider: {provider}. Supported providers: google, openai",
                config_key="llm_settings.provider",
                config_file=CONFIG_FILE
            )
        
        model = llm_settings.model
        request_delay = llm_settings.openai_request_delay if llm_settings.openai_request_delay is not None else 0
        
        logger.info(f"LLM settings: provider={provider}, model={model}, delay={request_delay}")
        return provider, model, request_delay

    except ConfigurationError:
        raise  # Re-raise configuration errors
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            "Failed to extract LLM settings from configuration",
            config_key="llm_settings"
        )


def configure_llm_api(provider: str) -> OpenAI:
    """
    Configure the LLM API based on the provider with proper error handling.
    
    Args:
        provider: LLM provider ('google' or 'openai')
        
    Returns:
        OpenAI client if provider is 'openai', None otherwise
        
    Raises:
        AuthenticationError: If API credentials are missing or invalid
        ConfigurationError: If provider is unsupported
        APIError: If API configuration fails
    """
    logger.debug(f"Configuring LLM API for provider: {provider}")
    
    try:
        if provider == 'google':
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "Google API key not found. Please set the GOOGLE_API_KEY environment variable.",
                    api_name="Google Gemini",
                    credential_type="API_KEY"
                )
            genai.configure(api_key=api_key)
            logger.info("Google Gemini API configured successfully")
            return None
            
        elif provider == 'openai':
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.",
                    api_name="OpenAI",
                    credential_type="API_KEY"
                )
            client = OpenAI(api_key=api_key)
            logger.info("OpenAI API configured successfully")
            return client
            
        else:
            raise ConfigurationError(
                f"Unsupported LLM provider: {provider}",
                config_key="llm_settings.provider",
                config_file=CONFIG_FILE
            )
            
    except (AuthenticationError, ConfigurationError):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            f"Failed to configure {provider} API",
            api_name=provider
        )


@retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
def ask_google_gemini(question: str, model: str) -> str:
    """
    Send question to Google Gemini with retry logic.
    
    Args:
        question: User question
        model: Gemini model name
        
    Returns:
        AI response text
        
    Raises:
        APIError: If API call fails
        DataValidationError: If response is invalid
    """
    try:
        logger.debug(f"Sending question to Google Gemini: {question[:50]}...")
        
        model_obj = genai.GenerativeModel(model)
        response = model_obj.generate_content(question)
        
        if not response or not response.text:
            raise DataValidationError(
                "Google Gemini returned empty response",
                field_name="gemini_response",
                expected_type="non-empty text",
                actual_value="empty or None"
            )
        
        logger.info(f"Successfully received response from Google Gemini ({len(response.text)} chars)")
        return response.text
        
    except DataValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        error_msg = str(e).lower()
        if any(auth_term in error_msg for auth_term in ['401', 'unauthorized', 'invalid', 'forbidden']):
            raise wrap_exception(
                e, AuthenticationError,
                "Google Gemini authentication failed",
                api_name="Google Gemini",
                credential_type="API_KEY"
            )
        elif any(quota_term in error_msg for quota_term in ['quota', 'limit', 'rate']):
            raise wrap_exception(
                e, RateLimitError,
                "Google Gemini rate limit exceeded",
                api_name="Google Gemini"
            )
        else:
            raise wrap_exception(
                e, APIError,
                f"Google Gemini API error",
                api_name="Google Gemini"
            )


def ask_openai(question: str, model: str, client: OpenAI, request_delay: float = 0) -> str:
    """
    Send question to OpenAI with comprehensive error handling and retry logic.
    
    Args:
        question: User question
        model: OpenAI model name
        client: OpenAI client instance
        request_delay: Delay between requests
        
    Returns:
        AI response text
        
    Raises:
        APIError: If API call fails
        RateLimitError: If rate limit is exceeded
        AuthenticationError: If credentials are invalid
    """
    if not client:
        raise APIError(
            "OpenAI client not configured",
            api_name="OpenAI"
        )
    
    # Apply client-side delay
    if request_delay > 0:
        logger.debug(f"Applying request delay: {request_delay}s")
        time.sleep(request_delay)
    
    retries = 0
    max_retries = 5
    base_delay = 1  # seconds
    
    logger.debug(f"Sending question to OpenAI: {question[:50]}...")
    
    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": question}]
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise DataValidationError(
                    "OpenAI returned empty response",
                    field_name="openai_response",
                    expected_type="non-empty message content",
                    actual_value="empty or None"
                )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"Successfully received response from OpenAI ({len(result)} chars)")
            return result
            
        except openai.RateLimitError as e:
            retries += 1
            if retries >= max_retries:
                raise RateLimitError(
                    f"OpenAI rate limit exceeded after {max_retries} attempts",
                    api_name="OpenAI",
                    retry_after=getattr(e, 'retry_after', None),
                    original_error=e
                )
            
            delay = base_delay * (2 ** retries)
            logger.warning(f"OpenAI rate limit hit, retrying in {delay}s (attempt {retries}/{max_retries})")
            print(f"Rate limit hit. Retrying in {delay} seconds...")
            time.sleep(delay)
            
        except openai.AuthenticationError as e:
            raise AuthenticationError(
                "OpenAI authentication failed. Please check your API key.",
                api_name="OpenAI",
                credential_type="API_KEY",
                original_error=e
            )
            
        except openai.APIError as e:
            retries += 1
            if retries >= max_retries:
                raise wrap_exception(
                    e, APIError,
                    f"OpenAI API error after {max_retries} attempts",
                    api_name="OpenAI"
                )
            
            logger.warning(f"OpenAI API error, retrying in {base_delay}s (attempt {retries}/{max_retries}): {e}")
            print(f"OpenAI API Error: {e}. Retrying in {base_delay} seconds...")
            time.sleep(base_delay)
            
        except Exception as e:
            raise wrap_exception(
                e, APIError,
                f"Unexpected error during OpenAI API call",
                api_name="OpenAI"
            )
    
    raise APIError(
        f"Failed to get response from OpenAI after {max_retries} retries",
        api_name="OpenAI"
    )


def ask_llm(question: str, provider: str, model: str, client: OpenAI = None, request_delay: float = 0) -> str:
    """
    Send question to the configured LLM with comprehensive error handling.
    
    Args:
        question: User question
        provider: LLM provider
        model: Model name
        client: OpenAI client (if using OpenAI)
        request_delay: Request delay (for OpenAI)
        
    Returns:
        AI response text
        
    Raises:
        ConfigurationError: If provider is unsupported
        APIError: If API call fails
        DataValidationError: If response is invalid
    """
    try:
        if not question or not question.strip():
            raise DataValidationError(
                "Question cannot be empty",
                field_name="question",
                expected_type="non-empty string",
                actual_value="empty or None"
            )
        
        if provider == 'google':
            return ask_google_gemini(question, model)
        elif provider == 'openai':
            return ask_openai(question, model, client, request_delay)
        else:
            raise ConfigurationError(
                f"Unsupported LLM provider: {provider}",
                config_key="llm_settings.provider"
            )
            
    except (ConfigurationError, APIError, DataValidationError, AuthenticationError, RateLimitError):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            f"Unexpected error asking {provider} LLM",
            api_name=provider
        )

def main() -> int:
    """
    Main function with comprehensive error handling.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info("Starting Fantasy Football AI assistant")
        
        # Step 1: Load configuration
        logger.info("Step 1: Loading configuration")
        config = load_config()
        
        # Step 2: Extract LLM settings
        logger.info("Step 2: Extracting LLM settings")
        provider, model, request_delay = get_llm_settings(config)
        
        # Step 3: Configure LLM API
        logger.info(f"Step 3: Configuring {provider} API")
        client = configure_llm_api(provider)
        
        print("🏈 Welcome to the Fantasy Football AI!")
        print("You can ask questions about player stats, draft strategy, and more.")
        print(f"Using {provider.upper()} with model: {model}")
        print("Type 'quit' to exit.\n")
        
        question_count = 0
        while True:
            try:
                user_question = input(f"❓ Ask {provider} a question: ").strip()
                
                if user_question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Thanks for using Fantasy Football AI!")
                    break
                
                if not user_question:
                    print("Please enter a question or 'quit' to exit.")
                    continue
                
                question_count += 1
                logger.info(f"Processing question #{question_count}: {user_question[:50]}...")
                
                print(f"\n🤔 Asking {provider}: '{user_question}'")
                answer = ask_llm(user_question, provider, model, client, request_delay)
                
                print(f"\n🧠 {provider.capitalize()}'s Answer:")
                print("─" * 50)
                print(answer)
                print("─" * 50 + "\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except (APIError, RateLimitError, DataValidationError) as e:
                logger.error(f"Error processing question: {e.get_detailed_message()}")
                print(f"❌ Error: {e}")
                if isinstance(e, RateLimitError):
                    print("You may want to wait a moment before asking another question.")
                print("Please try again or type 'quit' to exit.\n")
            except Exception as e:
                logger.error(f"Unexpected error processing question: {e}")
                print(f"❌ An unexpected error occurred: {e}")
                print("Please try again or type 'quit' to exit.\n")
        
        logger.info(f"Session completed. Processed {question_count} questions.")
        print(f"\n✓ Session completed. Processed {question_count} questions.")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user.")
        return 130
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e.get_detailed_message()}")
        print(f"\n❌ Authentication Error: {e}")
        print("\nTroubleshooting:")
        if hasattr(e, 'api_name'):
            print(f"- Check your .env file contains a valid {e.api_name} API key")
        if hasattr(e, 'credential_type'):
            print(f"- Verify the {e.credential_type} is correctly set")
        return 1
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.get_detailed_message()}")
        print(f"\n❌ Configuration Error: {e}")
        print("\nTroubleshooting:")
        print("- Run 'task init' to create configuration file")
        print("- Check your config.yaml file for valid LLM settings")
        print("- Ensure the provider and model are correctly specified")
        return 1
    except APIError as e:
        logger.error(f"API error: {e.get_detailed_message()}")
        print(f"\n❌ API Error: {e}")
        print("\nTroubleshooting:")
        print("- Check your internet connection")
        print("- Verify your API credentials are valid")
        print("- The AI service may be temporarily unavailable")
        return 1
    except RateLimitError as e:
        logger.error(f"Rate limit error: {e.get_detailed_message()}")
        print(f"\n❌ Rate Limit Error: {e}")
        print("\nTroubleshooting:")
        print("- Wait a few minutes before trying again")
        print("- Consider upgrading your API plan for higher limits")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ An unexpected error occurred: {e}")
        print("Check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
