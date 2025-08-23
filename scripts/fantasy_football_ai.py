#!/usr/bin/env python3
################################################################################
#
# Script Name: fantasy_football_ai.py
# ----------------
# Main entry point for the Fantasy Football AI assistant, handling user interactions and integrating various analytical tools.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-22
# @version 0.4.0
#
################################################################################

import os
import yaml
import google.generativeai as genai
import openai
from openai import OpenAI
from dotenv import load_dotenv
import time

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
    """Configure the LLM API based on the provider."""
    global CLIENT
    if LLM_PROVIDER == 'google':
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "API key not found. Please set the GOOGLE_API_KEY "
                "environment variable."
            )
        genai.configure(api_key=api_key)
    elif LLM_PROVIDER == 'openai':
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "API key not found. Please set the OPENAI_API_KEY "
                "environment variable."
            )
        CLIENT = OpenAI(api_key=api_key)
    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

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

if __name__ == "__main__":
    try:
        configure_llm_api()
        print("Welcome to the Fantasy Football AI!")
        print(
            "You can ask questions about player stats, draft strategy, "
            "and more."
        )

        answer = None # Initialize answer to None
        while True:
            user_question = input(f"Ask {LLM_PROVIDER} a question (or 'quit' to exit): ").strip()
            if user_question.lower() == 'quit':
                break
            else:
                print()
                print(f"Asking {LLM_PROVIDER}: '{user_question}'")
                answer = ask_llm(user_question)
                print()
                print(f"{LLM_PROVIDER.capitalize()}'s Answer:")
                print(answer)
        

    except ValueError as e:
        print(f"Error: {e}")
        print(
            "Please make sure you have a .env file with your API key for " + LLM_PROVIDER + " or have it set as an environment variable."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")