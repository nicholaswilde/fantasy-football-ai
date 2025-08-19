# :football: Fantasy Football AI :robot:

> Using AI to dominate your fantasy football league. It's like having a secret weapon, but for nerds.

This project leverages the power of Google's Gemini AI to provide data-driven insights and analysis for your fantasy football league. It helps you make informed decisions on player stats, team analysis, and trade suggestions.

## :sparkles: Features

*   **Player Stat Analysis**: Downloads and processes weekly player statistics from the `nfl_data_py` library.
*   **Team Analysis**: Uses the Gemini AI to analyze your team's roster and provide feedback.
*   **Trade Suggestions**: Identifies "buy-low" and "sell-high" trade candidates based on weekly performance versus season averages.
*   **Available Player Downloads**: Fetches a list of all available players from your ESPN league.
*   **League Settings**: Downloads your current league settings, including scoring and roster rules.
*   **Customizable Tasks**: Uses `Taskfile` to easily run common commands for linting, installing dependencies, downloading data, and running analysis.

## :rocket: Getting Started

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

    ```ini
    GOOGLE_API_KEY="YOUR_API_KEY"
    LEAGUE_ID="YOUR_LEAGUE_ID"
    ESPN_S2="YOUR_ESPN_S2"
    SWID="YOUR_SWID"
    ```

    ??? abstract ".env"

        ```ini
        --8<-- ".env.tmpl"
        ```
    
## :computer: Usage

This project uses `Taskfile.yml` to define and run tasks. You can see a list of all available tasks by running `task -l`.

### :arrow_down: Download Player Stats

To download the latest player stats (defaulting to the 2023 and 2024 seasons), run the following command:

```bash
task download
```

You can also specify the years to download by passing the `--years` argument:

```bash
task download -- --years 2022 2023
```

This will create a `player_stats.csv` file in the `data/` directory.

### :clipboard: Download Available Players

To get a list of available players for weekly pickups, run the following command:

```bash
task available_players
```

This will create an `available_players.csv` file in the `data/` directory.

### :bar_chart: Analyze Your Team

1.  Get your team's roster and create the `my_team.md` file by running the following command:
    ```bash
    task my_team
    ```

2.  Run the analysis script:
    ```bash
    task analyze
    ```

### :gear: Download League Settings

To download your league's settings, run the following command:

```bash
task settings
```

### :mag_right: Get Pickup Recommendations

To get pickup recommendations based on available players, their performance, and your team's needs, run:

```bash
task pickup
```

### :handshake: Get Trade Suggestions

To get trade suggestions based on the latest player stats, run:

```bash
task trade
```

## 👋 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.


## :scales: License

[Apache License 2.0](https://raw.githubusercontent.com/nicholaswilde/fantasy-football-ai/refs/heads/main/LICENSE)

## :pencil:Author

This project was started in 2025 by [Nicholas Wilde][2].

[1]: <https://github.com/cwendt94/espn-api/discussions/150#discussioncomment-133615>
[2]: <https://nicholaswilde.io/>
