# :football: Fantasy Football AI :robot:

[![task](https://img.shields.io/badge/Task-Enabled-brightgreen?style=for-the-badge&logo=task&logoColor=white)](https://taskfile.dev/#/)
[![docs](https://img.shields.io/github/actions/workflow/status/nicholaswilde/fantasy-football-ai/docs.yaml?label=docs&style=for-the-badge&branch=main)](https://github.com/nicholaswilde/fantast-football-ai/actions/workflows/docs.yaml)

> Using AI to dominate your fantasy football league. It's like having a secret weapon, but for nerds.

This project leverages Google's Gemini AI to provide data-driven insights and analysis for your fantasy football league. It helps you make informed decisions on player stats, team analysis, and trade suggestions.

!!! warning "Development Version"

    This project is currently in a development stage. Features and configurations are subject to change, and breaking changes may be introduced at any time.

## :rocket: TL;DR

1.  **Initial Setup**
    ```shell
    task init
    # Edit .env with your credentials
    task bootstrap
    # Identity which team is yours
    ```

2.  **Weekly Update**
    ```shell
    task weekly_update
    ```

3.  **Draft Preparation**
    ```shell
    task draft_prep
    ```

## :sparkles: Features

*   **Player Stat Analysis**: Downloads and processes weekly player statistics from the `nfl_data_py` library.
*   **Customizable Scoring Rules**: Define your league's scoring rules in `config.yaml` for accurate fantasy point calculations.
*   **Team Identification**: Easily identify and save your team from a list of all teams in the league.
*   **Report Generation**: Generates comprehensive Markdown reports summarizing draft recommendations, bye week conflicts, and trade suggestions.
*   **Team Analysis**: Uses the Gemini AI to analyze your team's roster and provide feedback.
*   **Trade Suggestions**: Identifies "buy-low" and "sell-high" trade candidates based on weekly performance versus season averages.
*   **Available Player Downloads**: Fetches a list of all available players from your ESPN league.
*   **League Settings**: Downloads your current league settings, including scoring and roster rules.
*   **Customizable Tasks**: Uses `Taskfile` to easily run common commands for linting, installing dependencies, downloading data, and running analysis.

## :scales: License

[Apache License 2.0](https://raw.githubusercontent.com/nicholaswilde/fantasy-football-ai/refs/heads/main/LICENSE)

## :pencil:Author

This project was started in 2025 by [Nicholas Wilde](https://nicholaswilde.io/)
