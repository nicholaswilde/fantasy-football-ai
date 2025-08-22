#!/usr/bin/env python3
################################################################################
#
# Script Name: fantasy_football_ai.py
# ----------------
# Main entry point for the Fantasy Football AI assistant, handling user interactions and integrating various analytical tools.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def configure_api():
    """Configure the Gemini API with the API key."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "API key not found. Please set the GOOGLE_API_KEY "
            "environment variable."
        )
    genai.configure(api_key=api_key)


def ask_gemini(question):
    """
    Sends a question to the Gemini model and returns the response.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(question)
    if not response.text:
        print("DEBUG: Gemini API returned an empty response for the text content.")
    return response.text


if __name__ == "__main__":
    try:
        configure_api()
        print("Welcome to the Fantasy Football AI!")
        print(
            "You can ask questions about player stats, draft strategy, "
            "and more."
        )

        answer = None # Initialize answer to None
        while True:
            user_question = input("Ask Gemini a question (or 'quit' to exit): ").strip()
            if user_question.lower() == 'quit':
                break
            else:
                print(f"\nAsking Gemini: '{user_question}'")
                answer = ask_gemini(user_question)
                print("\nGemini's Answer:")
                print(answer)
        

    except ValueError as e:
        print(f"Error: {e}")
        print(
            "Please make sure you have a .env file with your "
            "GOOGLE_API_KEY or have it set as an environment variable."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
