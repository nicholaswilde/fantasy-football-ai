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
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(question)
    return response.text


if __name__ == "__main__":
    try:
        configure_api()
        print("Welcome to the Fantasy Football AI!")
        print(
            "You can ask questions about player stats, draft strategy, "
            "and more."
        )

        # Example question
        example_question = (
            "Who are the top 5 running backs for the upcoming fantasy "
            "football season?"
        )
        print(f"\nAsking Gemini: '{example_question}'")

        # Get the answer from Gemini
        answer = ask_gemini(example_question)
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
