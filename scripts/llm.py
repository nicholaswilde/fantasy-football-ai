#!/usr/bin/env python3
################################################################################
#
# Script Name: llm.py
# ----------------
# Handles all interactions with the Language Learning Model (LLM).
#
# @author Nicholas Wilde, 0xb299a622
# @date 29 08 2025
# @version 0.1.0
#
################################################################################

import os
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
import sys

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger
from fantasy_ai.utils.retry import retry
from scripts.utils import load_config

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/llm.log')
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Global variables for configuration and LLM client, initialized later
_CONFIG = None
_LLM_SETTINGS = None
_LLM_PROVIDER = None
_LLM_MODEL = None
_CLIENT = None

def initialize_globals():
    """
    Initializes global configuration and LLM settings.
    This function should be called once at the application's entry point.
    """
    global _CONFIG, _LLM_SETTINGS, _LLM_PROVIDER, _LLM_MODEL, _CLIENT
    _CONFIG = load_config()
    _LLM_SETTINGS = _CONFIG.get('llm_settings', {})
    _LLM_PROVIDER = _LLM_SETTINGS.get('provider', 'google')
    _LLM_MODEL = _LLM_SETTINGS.get('model', 'gemini-pro')
    _CLIENT = None # Reset client

def configure_llm_api():
    """
    Configure the LLM API based on the provider with error handling.
    Assumes _LLM_PROVIDER, _LLM_MODEL, and _CLIENT globals are initialized.
    """
    global _CLIENT
    if _LLM_PROVIDER is None:
        raise ConfigurationError("LLM provider not initialized. Call initialize_globals() first.")

    try:
        if _LLM_PROVIDER == 'google':
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "Google API key not found. Please set the GOOGLE_API_KEY environment variable.",
                    api_name="Google Gemini"
                )
            genai.configure(api_key=api_key)
            logger.info("Google Gemini API configured.")
        elif _LLM_PROVIDER == 'openai':
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.",
                    api_name="OpenAI"
                )
            _CLIENT = OpenAI(api_key=api_key)
            logger.info("OpenAI API configured.")
        else:
            raise ConfigurationError(
                f"Unsupported LLM provider: {_LLM_PROVIDER}",
                config_key="llm_settings.provider"
            )
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            f"Failed to configure LLM API for provider {_LLM_PROVIDER}"
        )


@retry(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0
)
def ask_llm(question: str) -> str:
    """
    Sends a question to the configured LLM and returns the response with error handling.
    Assumes _LLM_PROVIDER, _LLM_MODEL, and _CLIENT globals are initialized.
    
    Raises:
        APIError: If there's an issue with the LLM API response.
        NetworkError: If there's a network connectivity issue.
        AuthenticationError: If LLM client is not configured or API key is invalid.
    """
    if _LLM_PROVIDER is None:
        raise ConfigurationError("LLM provider not initialized. Call initialize_globals() first.")

    try:
        logger.debug(f"Asking LLM: {question[:50]}...")
        if _LLM_PROVIDER == 'google':
            model = genai.GenerativeModel(_LLM_MODEL)
            response = model.generate_content(question)
            if not response.text:
                raise APIError("LLM returned an empty response.", api_name=_LLM_PROVIDER)
            logger.info("Received response from Google Gemini.")
            return response.text
        elif _LLM_PROVIDER == 'openai':
            if not _CLIENT:
                raise AuthenticationError("OpenAI client not configured.", api_name="OpenAI")
            response = _CLIENT.chat.completions.create(
                model=_LLM_MODEL,
                messages=[{"role": "user", "content": question}]
            )
            if not response.choices or not response.choices[0].message.content:
                raise APIError("LLM returned an empty response.", api_name=_LLM_PROVIDER)
            logger.info("Received response from OpenAI.")
            return response.choices[0].message.content.strip()
        else:
            raise ConfigurationError(f"Unsupported LLM provider: {_LLM_PROVIDER}")
    except (genai.types.BlockedPromptException, genai.types.HarmCategory) as e:
        raise APIError(f"LLM prompt blocked due to safety concerns: {e}", api_name=_LLM_PROVIDER, original_error=e)
    except (genai.types.APIError, OpenAI.APIError) as e:
        raise APIError(f"LLM API error: {e}", api_name=_LLM_PROVIDER, original_error=e)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise NetworkError(f"Network error during LLM API call: {e}", api_name=_LLM_PROVIDER, original_error=e)
    except Exception as e:
        raise wrap_exception(e, APIError, f"An unexpected error occurred during LLM API call: {e}", api_name=_LLM_PROVIDER)
