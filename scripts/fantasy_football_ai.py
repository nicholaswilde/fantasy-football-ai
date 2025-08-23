#!/usr/bin/env python3
################################################################################
#
# Script Name: fantasy_football_ai.py
# ----------------
# Main entry point for the Fantasy Football AI assistant, handling user interactions and integrating various analytical tools.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-23
# @version 0.5.0
#
################################################################################

import os
import sys
import yaml
import google.generativeai as genai
import openai
from openai import OpenAI
from dotenv import load_dotenv
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError, 
    RateLimitError, wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/fantasy_football_ai.log')
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()
LLM_SETTINGS = CONFIG.get('llm_settings', {})
LLM_PROVIDER = LLM_SETTINGS.get('provider', 'google')
LLM_MODEL = LLM_SETTINGS.get('model', 'gemini-pro')
OPENAI_REQUEST_DELAY = LLM_SETTINGS.get('openai_request_delay', 0) # Default to 0 if not set
CLIENT = None

def configure_llm_api():
    """Configure the LLM API based on the provider with proper error handling."""
    global CLIENT
    logger.debug(f"Configuring LLM API for provider: {LLM_PROVIDER}")
    
    try:
        if LLM_PROVIDER == 'google':
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "Google API key not found. Please set the GOOGLE_API_KEY environment variable.",
                    api_name="Google Gemini",
                    credential_type="API_KEY"
                )
            genai.configure(api_key=api_key)
            logger.info("Google Gemini API configured successfully")
            
        elif LLM_PROVIDER == 'openai':
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.",
                    api_name="OpenAI",
                    credential_type="API_KEY"
                )
            CLIENT = OpenAI(api_key=api_key)
            logger.info("OpenAI API configured successfully")
            
        else:
            raise ConfigurationError(
                f"Unsupported LLM provider: {LLM_PROVIDER}",
                config_key="llm_settings.provider",
                config_file=CONFIG_FILE
            )
            
    except Exception as e:
        if isinstance(e, (AuthenticationError, ConfigurationError)):
            raise  # Re-raise our custom exceptions
        else:
            raise wrap_exception(
                e, APIError,
                f"Failed to configure {LLM_PROVIDER} API",
                api_name=LLM_PROVIDER
            )

def ask_llm(question):
    """
    Sends a question to the configured LLM and returns the response.
    """
    if LLM_PROVIDER == 'google':
        model = genai.GenerativeModel(LLM_MODEL)
        response = model.generate_content(question)
        if not response.text:
            print(f"DEBUG: {LLM_PROVIDER} API returned an empty response for the text content.")
        return response.text
    elif LLM_PROVIDER == 'openai':
        if not CLIENT:
            raise ValueError("OpenAI client not configured.")
        
        # Apply client-side delay
        if OPENAI_REQUEST_DELAY > 0:
            time.sleep(OPENAI_REQUEST_DELAY)

        retries = 0
        max_retries = 5
        base_delay = 1 # seconds

        while retries < max_retries:
            try:
                response = CLIENT.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "user", "content": question}]
                )
                return response.choices[0].message.content.strip()
            except openai.RateLimitError as e: # Catch rate limit error specifically
                delay = base_delay * (2 ** retries)
                print(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                retries += 1
            except openai.APIError as e: # Catch other API errors
                print(f"OpenAI API Error: {e}. Retrying in {base_delay} seconds...")
                time.sleep(base_delay) # Simple retry for other API errors
                retries += 1
            except Exception as e: # Catch any other unexpected errors
                print(f"An unexpected error occurred during OpenAI API call: {e}")
                raise # Re-raise the exception

        raise Exception(f"Failed to get response from OpenAI after {max_retries} retries due to rate limits or other API/network errors.")
    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

def main():
    """
    Main function with comprehensive error handling.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info("Starting Fantasy Football AI assistant")
        
        # Configure LLM API
        configure_llm_api()
        
        print("🏈 Welcome to the Fantasy Football AI!")
        print("You can ask questions about player stats, draft strategy, and more.")
        print(f"Using {LLM_PROVIDER.upper()} with model: {LLM_MODEL}")
        print("Type 'quit' to exit.\n")
        
        question_count = 0
        while True:
            try:
                user_question = input(f"❓ Ask {LLM_PROVIDER} a question: ").strip()
                
                if user_question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Thanks for using Fantasy Football AI!")
                    break
                
                if not user_question:
                    print("Please enter a question or 'quit' to exit.")
                    continue
                
                question_count += 1
                logger.info(f"Processing question #{question_count}: {user_question[:50]}...")
                
                print(f"\n🤔 Asking {LLM_PROVIDER}: '{user_question}'")
                answer = ask_llm(user_question)
                
                print(f"\n🧠 {LLM_PROVIDER.capitalize()}'s Answer:")
                print("─" * 50)
                print(answer)
                print("─" * 50 + "\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing question: {e}")
                print(f"❌ Error processing your question: {e}")
                print("Please try again or type 'quit' to exit.\n")
        
        logger.info(f"Session completed. Processed {question_count} questions.")
        return 0
        
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e.get_detailed_message()}")
        print(f"\n❌ Authentication Error: {e}")
        print("\nTroubleshooting:")
        print(f"- Check your .env file contains a valid {e.api_name} API key")
        print(f"- Verify the {e.credential_type} is correctly set")
        return 1
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.get_detailed_message()}")
        print(f"\n❌ Configuration Error: {e}")
        print("\nTroubleshooting:")
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
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ An unexpected error occurred: {e}")
        print("Check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
