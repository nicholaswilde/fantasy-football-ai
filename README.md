# :football: Fantasy Football AI

> Using AI to dominate your fantasy football league. It's like having a secret weapon, but for nerds.

This project leverages the power of Google's Gemini AI to provide data-driven insights and analysis for your fantasy football league. It helps you make informed decisions on player stats, team analysis, and trade suggestions.

## Features

*   **Player Stat Analysis**: Downloads and processes weekly player statistics from the `nfl_data_py` library.
*   **Team Analysis**: Uses the Gemini AI to analyze your team's roster and provide feedback.
*   **Trade Suggestions**: Identifies "buy-low" and "sell-high" trade candidates based on weekly performance versus season averages.
*   **Customizable Tasks**: Uses `Taskfile` to easily run common commands for linting, installing dependencies, downloading data, and running analysis.

## Getting Started

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

### Configuration

To use the Gemini API, you need to configure your API key.

1.  Obtain an API key from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

2.  Create a `.env` file from the template:
    ```bash
    cp .env.tmpl .env
    ```

3.  Add your API key to the `.env` file:
    ```
    GOOGLE_API_KEY="YOUR_API_KEY"
    ```

## Usage

This project uses `Taskfile.yml` to define and run tasks. You can see a list of all available tasks by running `task -l`.

### Download Player Stats

To download the latest player stats, run the following command:

```bash
task download
```

This will create a `player_stats.csv` file in the `data/` directory.

### Analyze Your Team

1.  Create a `my_team.md` file in the `data/` directory with your team's roster. You can use the following format:

    ```markdown
    # My Team

    ## QB
    - Player 1

    ## RB
    - Player 2
    - Player 3

    ## WR
    - Player 4
    - Player 5

    ## TE
    - Player 6

    ## FLEX
    - Player 7

    ## BENCH
    - Player 8
    - Player 9
    ```

2.  Run the analysis script:
    ```bash
task analyze
```

### Get Trade Suggestions

To get trade suggestions based on the latest player stats, run:

```bash
python3 scripts/trade_suggester.py
```

## 👋 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.