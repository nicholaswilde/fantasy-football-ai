# :rocket: Getting Started

### :hammer_and_wrench: Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/nicholaswilde/fantasy-football-ai.git
    cd fantasy-football-ai
    ```

2.  **Install `task`:**
    Follow the instructions at [taskfile.dev/installation](https://taskfile.dev/installation) to install `task`.

3.  **Create a virtual environment:**
    ```bash
    task bootstrap
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4.  **Install dependencies:**
    ```bash
    task deps
    ```

### :gear: Configuration

To use the Gemini API, you need to configure your API key.

1.  Obtain an API key from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

2. Find your LEAGUE_ID from the URL of your ESPN fantasy football league.

3. Find your ESPN_S2 and SWID cookies from your browser after logging into your ESPN account. See [this discussion][].

4.  Create a `.env` file from the template:
    ```bash
    cp .env.tmpl .env
    ```

5.  Add your API key and ESPN credentials to the `.env` file:

    ??? abstract ".env"

        ```ini
        --8<-- ".env.tmpl"
        ```

6.  **Customize Scoring Rules (Optional)**:
    The project includes a `config.yaml` file in the root directory. You can modify this file to adjust the fantasy football scoring rules to match your league's settings. This allows for flexible customization without changing the Python code.

    ```yaml
    # config.yaml example
    scoring_rules:
        passing_yards: 0.04
        passing_touchdowns: 6
        # ... other scoring rules
    ```
