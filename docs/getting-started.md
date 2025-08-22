# :rocket: Getting Started

### :hammer_and_wrench: Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/nicholaswilde/fantasy-football-ai.git
    cd fantasy-football-ai
    ```

2.  **Install `task`:**
    Follow the instructions at [taskfile.dev/installation](https://taskfile.dev/installation) to install `task`.

3.  **Bootstrap the project:**
    This command will create a virtual environment, install all the necessary dependencies, and guide you through selecting your team.

    === "Task"
    
        ```bash
        task bootstrap
        ```

5.  **Activate the virtual environment:**
    ```bash
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

### :gear: Configuration

To use the Gemini API, you need to configure your API key.

1.  Obtain an API key from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

2. Find your `LEAGUE_ID` from the URL of your ESPN fantasy football league.

3. Find your `ESPN_S2` and `SWID` cookies from your browser after logging into your ESPN account. See [this discussion](https://github.com/cwendt94/espn-api/discussions/150).

4.  Create a `.env` file from the template:

    === "Task"
    
        ```bash
        task init
        ```

6.  Add your API key and ESPN credentials to the `.env` file:

    ??? abstract ".env"

        ```ini
        --8<-- ".env.tmpl"
        ```

7.  **Customize Scoring Rules (Optional)**:
    The project includes a `config.yaml` file in the root directory. You can modify this file to adjust the fantasy football scoring rules to match your league's settings. This allows for flexible customization without changing the Python code.

    Alternatively, you can run the following command to automatically fetch the scoring rules from your league and update `config.yaml`:

    === "Task"
    
        ```bash
        task settings
        ```

    ```yaml
    # config.yaml example
    scoring_rules:
        every_25_passing_yards: 1.0
        td_pass: 6.0
        interceptions_thrown: -3.0
        # ... other scoring rules
    ```

9.  **Configure Year Settings (Optional)**:
    The `config.yaml` file also contains fields for `year` and `data_years` under the `league_settings` section.

    *   `year`: This field specifies the current year for your fantasy football league. It is used to fetch the correct league data.
    *   `data_years`: This is a list of years for which to download player stats. By default, it's set to the current and previous year.

    You can manually edit these fields in `config.yaml` to match your needs.

    ```yaml
    # config.yaml example
    league_settings:
        year: 2024
        data_years: [2023, 2024]
    ```
