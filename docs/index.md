# :football: Fantasy Football AI :robot:

> Using AI to dominate your fantasy football league. It's like having a secret weapon, but for nerds.

This project leverages Google's Gemini AI to provide data-driven insights and analysis for your fantasy football league. It helps you make informed decisions on player stats, team analysis, and trade suggestions. To get started, clone the repository,

## :memo: TL;DR

1. Copy the `.env.tmpl` file to `.env`.

    === "Task"

        ```shell
        task init
        ```

2. Edit `.env`. 

3. Bootstrap the project.

    === "Task"

        ```shell
        task bootstrap
        ```

4. Perform weekly update

    === "Task"

        ```shell
        task weekly_update
        ```

5. Download data and create a draft strategy

    === "Task"

        ```shell
        task draft_prep
        ```

## :sparkles: Features

*   **Player Stat Analysis**: Downloads and processes weekly player statistics from the `nfl_data_py` library.
*   **Customizable Scoring Rules**: Define your league's scoring rules in `config.yaml` for accurate fantasy point calculations.
*   **Report Generation**: Generates comprehensive Markdown reports summarizing draft recommendations, bye week conflicts, and trade suggestions.
*   **Team Analysis**: Uses the Gemini AI to analyze your team's roster and provide feedback.
*   **Trade Suggestions**: Identifies "buy-low" and "sell-high" trade candidates based on weekly performance versus season averages.
*   **Available Player Downloads**: Fetches a list of all available players from your ESPN league.
*   **League Settings**: Downloads your current league settings, including scoring and roster rules.
*   **Customizable Tasks**: Uses `Taskfile` to easily run common commands for linting, installing dependencies, downloading data, and running analysis.

## 👋 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.


## :scales: License

[Apache License 2.0](https://raw.githubusercontent.com/nicholaswilde/fantasy-football-ai/refs/heads/main/LICENSE)

## :pencil:Author

This project was started in 2025 by [Nicholas Wilde](https://nicholaswilde.io/)
