# Fantasy Football AI with Gemini

This project uses Google's Gemini AI to provide analysis and insights for fantasy football, including player stats, draft recommendations, and more.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/fantasy-football.git
    cd fantasy-football
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

To use the Gemini API, you need to configure your API key.

1.  Obtain an API key from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

2.  Set the API key as an environment variable:
    ```bash
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```
    On Windows, use the following command:
    ```bash
    set GOOGLE_API_KEY="YOUR_API_KEY"
    ```

## Usage

Run the main script to interact with the Fantasy Football AI:

```bash
python fantasy_football_ai.py
```

You can modify the `fantasy_football_ai.py` script to ask different questions or perform other tasks. For example, you could ask for a comparison between two players or for a list of sleeper picks for the upcoming season.
