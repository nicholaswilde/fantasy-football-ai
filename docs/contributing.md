# :wave: Contributing

First off, thank you for considering contributing to Fantasy Football AI! It's people like you that make this project great.

## :memo: Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](/.github/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior.

## :rocket: Getting Started

To get started, you'll need to have the following installed:

*   [Python 3.10+](https://www.python.org/downloads/)
*   [Poetry](https://python-poetry.org/docs/#installation)
*   [Task](https://taskfile.dev/installation/)

Once you have the prerequisites installed, you can set up your development environment:

```bash
task bootstrap
```

This will create a virtual environment and install all the necessary dependencies.

## :wrench: Development

To get started with development, you can use the `bootstrap` task to set up your environment:

```bash
task bootstrap
```

This will create a virtual environment and install all the necessary dependencies.

Before submitting a pull request, please ensure that your code is well-tested and follows the existing code style. You can run the following tasks to help you with this:

*   `task lint`: Lints the code using `ruff`.
*   `task format`: Formats the code using `ruff`.
*   `task test`: Runs the test suite.

## :arrow_upper_right: Submitting a Pull Request

When submitting a pull request, please ensure that your code is well-tested and follows the existing code style.

1.  **Fork the repository**: Fork the project to your own GitHub account.
2.  **Create a new branch**: Create a new branch for your changes.
    ```bash
    git checkout -b feat/my-awesome-feature
    ```
3.  **Make your changes**: Make your changes to the codebase.
4.  **Run the tests**: Run the test suite to ensure that your changes don't break anything.
    ```bash
    task test
    ```
5.  **Lint and format your code**: Ensure that your code follows the existing code style.
    ```bash
    task lint
    task format
    ```
6.  **Commit your changes**: Commit your changes with a descriptive commit message.
    ```bash
    git commit -m "feat: add my awesome feature"
    ```
7.  **Push your changes**: Push your changes to your fork.
    ```bash
    git push origin feat/my-awesome-feature
    ```
8.  **Open a pull request**: Open a pull request from your fork to the main repository.

## :art: Style Guide

This project follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code. We use `ruff` to enforce this style guide.

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

### :robot: Agent Guidelines

This project utilizes AI agents, and their behavior and output are governed by specific guidelines defined in the `AGENTS.md` files located throughout the repository. These files ensure consistent and effective interaction with the AI. For more information, refer to the main [AGENTS.md](https://agents.md) document.

## :question: Questions

If you have any questions, feel free to open an issue.