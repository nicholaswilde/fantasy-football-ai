# :football: Fantasy Football AI :robot:
[![task](https://img.shields.io/badge/Task-Enabled-brightgreen?style=for-the-badge&logo=task&logoColor=white)](https://taskfile.dev/#/)
[![docs](https://img.shields.io/github/actions/workflow/status/nicholaswilde/fantasy-football-ai/docs.yaml?label=docs&style=for-the-badge&branch=main)](https://github.com/nicholaswilde/fantasy-football-ai/actions/workflows/docs.yaml)

Using AI to dominate your fantasy football league. It's like having a secret weapon, but for nerds.

This project leverages Google's Gemini AI to provide data-driven insights and analysis for your fantasy football league. It helps you make informed decisions on player stats, team analysis, and trade suggestions. 

> [!WARNING]
> This project is currently in a development stage. Features and configurations are subject to change, and breaking changes may be introduced at any time.

## :rocket: TL;DR

1.  **Initial Setup**
    ```shell
    # Initialize env files
    task init
    
    # Edit .env with your credentials!
    
    # Bootstrap project using uv (creates virtual environment and installs dependencies)
    task bootstrap
    
    # Identify which team is yours and update config.yaml
    task identify_my_team
    ```

2.  **Weekly Update**
    ```shell
    # Automates data fetching, waiver wire analysis, trade suggestions, and reporting
    task weekly_update
    ```

3.  **Draft Preparation**
    ```shell
    task draft_prep
    ```

For detailed documentation, please visit the [project documentation](https://nicholaswilde.github.io/fantasy-football-ai/).

## :balance_scale: License

This project is licensed under the [Apache License 2.0](./LICENSE).

## :pencil: Author

This project was started in 2025 by [Nicholas Wilde](https://github.com/nicholaswilde/).
