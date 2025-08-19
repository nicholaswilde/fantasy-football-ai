#!/usr/bin/env python3

import os
import google.generativeai as genai
from dotenv import load_dotenv
import argparse

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

def ask_gemini(question, model_name):
    """
    Sends a question to the Gemini model and returns the response.
    """
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(question)
    return response.text

def get_team_roster(roster_file="data/my_team.md"):
    """Reads the team roster from the specified file."""
    if not os.path.exists(roster_file):
        return None
    with open(roster_file, "r") as f:
        roster = f.read()
    return roster


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a fantasy football team using Gemini.")
    parser.add_argument("--model", default="models/gemini-1.5-flash-latest", help="The Gemini model to use for analysis.")
    args = parser.parse_args()

    try:
        configure_api()
        roster = get_team_roster()
        if not roster:
            print("Error: data/my_team.md not found. Please create it first.")
        else:
            prompt = f"Analyze my fantasy football team based on the following roster:\n\n{roster}"
            print(f"Asking Gemini ({args.model}) to analyze your team...")
            analysis = ask_gemini(prompt, args.model)
            print("\n--- Gemini's Analysis ---")
            print(analysis)

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")