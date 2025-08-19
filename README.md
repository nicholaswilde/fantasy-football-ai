# :football: Fantasy Football AI :robot:

> Using AI to dominate your fantasy football league. It's like having a secret weapon, but for nerds.

This project leverages the power of Google's Gemini AI to provide data-driven insights and analysis for your fantasy football league. It helps you make informed decisions on player stats, team analysis, and trade suggestions.

## :sparkles: Features

*   **Player Stat Analysis**: Downloads and processes weekly player statistics from the `nfl_data_py` library.
*   **Team Analysis**: Uses the Gemini AI to analyze your team's roster and provide feedback.
*   **Trade Suggestions**: Identifies "buy-low" and "sell-high" trade candidates based on weekly performance versus season averages.
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

2.  Create a `.env` file from the template:
    ```bash
    cp .env.tmpl .env
    ```

3.  Add your API key to the `.env` file:
    ```
    GOOGLE_API_KEY="YOUR_API_KEY"
    ```

## :computer: Usage

This project uses `Taskfile.yml` to define and run tasks. You can see a list of all available tasks by running `task -l`.

### :arrow_down: Download Player Stats

To download the latest player stats, run the following command:

```bash
task download
```

This will create a `player_stats.csv` file in the `data/` directory.

### :clipboard: Manage Available Players

To provide Gemini with a list of available players for weekly pickups, create a `available_players.csv` file in the `data/` directory. This file should contain columns for `Player`, `Team`, `Position`, and `Availability` (e.g., 'Available', 'Waivers', 'Free Agent').

Example `data/available_players.csv`:

```csv
Player,Team,Position,Availability
Patrick Mahomes,KC,QB,Available
Bijan Robinson,ATL,RB,Waivers
Garrett Wilson,NYJ,WR,Free Agent
Travis Kelce,KC,TE,Available
Justin Tucker,BAL,K,Free Agent
```

### :bar_chart: Analyze Your Team

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