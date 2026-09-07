# :football: Fantasy Football AI :robot:

[![task](https://img.shields.io/badge/Task-Enabled-brightgreen?style=for-the-badge&logo=task&logoColor=white)](https://taskfile.dev/#/)

> Using AI to dominate your fantasy football league. It's like having a secret weapon, but for nerds.

This project leverages Google's Gemini AI to provide data-driven insights and analysis for your fantasy football league. The behavior and instructions for the AI agents are defined in `AGENTS.md` files throughout the repository. It helps you make informed decisions on player stats, team analysis, and trade suggestions.

> [!WARNING]
> This project is currently in a development stage. Features and configurations are subject to change, and breaking changes may be introduced at any time.

## :sparkles: Features

*   **Player Stat Analysis**: Downloads and processes weekly player statistics from the `nfl_data_py` library, including dynamic ADP data.
*   **Customizable Scoring Rules**: Define your league's scoring rules in `config.yaml` for accurate fantasy point calculations.
*   **Team Identification**: Easily identify and save your team from a list of all teams in the league.
*   **Report Generation**: Generates comprehensive Markdown reports summarizing draft recommendations, bye week conflicts, and trade suggestions.
*   **Team Analysis**: Uses the Gemini AI to analyze your team's roster and provide feedback.
*   **Trade Suggestions**: Identifies "buy-low" and "sell-high" trade candidates based on weekly performance versus season averages.
*   **Waiver Wire Gems**: Identifies high-upside waiver wire candidates based on recent usage trends and underperforming fantasy points.
*   **Live Draft Assistant**: Provides an interactive tool for real-time draft suggestions based on VBD and team needs.
*   **Available Player Downloads**: Fetches a list of all available players from your ESPN league.
*   **League Settings**: Downloads your current league settings, including scoring and roster rules.
*   **Customizable Tasks**: Uses `Taskfile` to easily run common commands for linting, installing dependencies, downloading data, and running analysis.

---

## :rocket: Getting Started

### :hammer_and_wrench: Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/nicholaswilde/fantasy-football-ai.git
    cd fantasy-football-ai
    ```

2.  **Install `task`:**
    Follow the instructions at [taskfile.dev/installation](https://taskfile.dev/installation) to install `task`.

3. **Install `uv`:**
    Follow the instructions at [python.org](https://www.python.org/downloads/) to install `python3` and `pip` (or just install `uv` directly from Astral).

### :gear: Configuration

To use the Gemini API, you need to configure your API key.

1.  Obtain an API key from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

2. Find your `LEAGUE_ID` and `TEAM_ID` from the URL of your ESPN fantasy football league when viewing your team's page (e.g. `leagueId=123456&teamId=7`).

3. Find your `ESPN_S2` and `SWID` cookies from your browser after logging into your ESPN account. 
    * **Using the Browser Extension (Recommended):**
        1. Download `espn-cookie-extractor.zip` from the [Releases](https://github.com/nicholaswilde/fantasy-football-ai/releases) page.
        2. Extract the ZIP file.
        3. Open Chrome/Edge and go to `chrome://extensions/`.
        4. Enable **Developer mode** in the top right corner.
        5. Click **Load unpacked** and select the extracted `extension` folder.
        6. Log into your ESPN account and navigate to your specific fantasy team's page. Click the new extension icon to extract your `SWID`, `ESPN_S2`, `LEAGUE_ID`, and `TEAM_ID`, then click **Copy to Clipboard**.
    * **Manual Method:** See [this discussion](https://github.com/cwendt94/espn-api/discussions/150) for instructions on using developer tools.

4.  Create a `.env` file from the template:

    ```bash
    task init
    ```

5.  Add your API key and ESPN credentials to the `.env` file.

### :memo: Bootstrap

1.  **Bootstrap the project:**
    This command will create a virtual environment, install all the necessary dependencies, and guide you through selecting your team.

    ```bash
    task bootstrap
    ```

2. **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

---

## :computer: Usage

This project uses `Taskfile.yml` to define and run tasks. You can see a list of all available tasks by running `task -l`.

### :calendar: Weekly Management

You can run the weekly workflow either with an AI agent or directly through the terminal:

#### 1. Via AI Agent (`fantasy-weekly-manager` Skill)

If you are using an AI coding assistant (such as Antigravity, Claude Code, or Gemini CLI), you can activate the built-in skill by prompting:

> *"Run the weekly update"* or *"Execute the fantasy-weekly-manager skill"*

The AI agent will:
- Run `task weekly_update` in the background.
- Review and evaluate the generated metrics and reports.
- Present a concise, actionable summary covering:
  - **Top waiver wire pickup targets** (and who to drop).
  - **Immediate lineup issues** (bye week conflicts, injured starters).
  - **High-value trade targets** to consider.

#### 2. Via Terminal Task

To execute the automated pipeline directly from your terminal:

```bash
task weekly_update
```

This task downloads the latest weekly stats, updates your roster, pulls available players, generates trade and pickup suggestions, and prints a formatted terminal report.

---

### :arrow_down: Download Fantasy Data

Download historical stats, projections, or ADP data using the `download` task:

```bash
# Download all data sets
task download -- all

# Download historical player stats (defaults to years in config.yaml)
task download -- stats

# Download stats for specific years
task download -- stats --years 2022 2023

# Download projections or ADP data
task download -- projections
task download -- adp
```

### :clipboard: Get Available Players

To get a list of available players for weekly pickups, run:

```bash
task get_available_players
```

### :bust_in_silhouette: Identify My Team

To select your team from a list of all teams in the league, run:

```bash
task identify_my_team
```
You will be prompted to enter the number corresponding to your team.

### :bar_chart: Get My Team Roster

To get your team's roster and create the `my_team.md` file, run:

```bash
task get_my_team_roster
```

### :video_game: Analyze Game Matchups

To analyze your team's performance or prepare for your upcoming matchup:

```bash
# Analyze your team's performance in the last game
task analyze -- last

# Analyze your upcoming fantasy football matchup against an opponent
task analyze -- next
```

### :page_with_curl: Generate Reports

To generate comprehensive analysis reports:

```bash
# Generate report in markdown
task report -- markdown

# View report directly in the terminal
task report -- terminal
```

### :gear: League & Player Analysis

#### Get League Settings
Download your league's settings from ESPN:
```bash
task get_league_settings
```

#### Refresh League Data
Refresh both league settings and available players in one command:
```bash
task refresh
```

#### Suggest Pickups
Get waiver wire pickup recommendations based on available players and team needs:
```bash
task suggest_pickups
```

#### Suggest Trades
Get trade suggestions based on player performance and stats:
```bash
task suggest_trades
```

#### Compare Fantasy Players
Compare fantasy football players side-by-side:
```bash
task compare_fantasy_players
```

#### Compare Roster Positions
Compare league roster requirements against your current roster composition:
```bash
task compare_roster_positions
```

### :pencil: Draft Management

#### Draft Preparation
Download all necessary draft data and start the draft assistant:
```bash
task draft_prep
```

#### Live Draft Assistant
Run the interactive live draft assistant:
```bash
task live_draft_assistant
```

### :star: Optimal Lineup Generator

To generate an optimal fantasy football lineup based on projected points and your roster settings, run:

```bash
task lineup_optimizer
```

### :stethoscope: Diagnostics & Utilities

```bash
# Check the health of all core systems and APIs
task health_check

# Show system status and recent activity
task status

# Create backup of important data files
task backup_data

# Clean old logs (keeps last 7 days)
task clean_logs
```

---

## :gear: Advanced Options

1.  **Customize Scoring Rules (Optional)**:
    The project includes a `config.yaml` file in the root directory. You can modify this file to adjust the fantasy football scoring rules to match your league's settings. 

2.  **Configure AI Provider (Optional)**:
    The `config.yaml` file also allows you to specify which AI provider to use (Gemini or OpenAI) and, for OpenAI, the specific model name.

3.  **Configure Year Settings (Optional)**:
    The `config.yaml` file also contains fields for `year` and `data_years` under the `league_settings` section.

---

## :wave: Contributing

First off, thank you for considering contributing to Fantasy Football AI! 

### :wrench: Development

To get started with development, you can use the `bootstrap` task to set up your environment:

```bash
task bootstrap
```

Before submitting a pull request, please ensure that your code is well-tested and follows the existing code style. You can run the following tasks to help you with this:

*   `task lint`: Lints the code with `ruff`.
*   `task format`: Formats the code using `ruff`.
*   `task test`: Runs the test suite.

### :art: Style Guide

This project follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code. We use `ruff` to enforce this style guide.

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

## :scales: License

[Apache License 2.0](./LICENSE)

## :pencil: Author

This project was started in 2025 by [Nicholas Wilde](https://nicholaswilde.io/)
