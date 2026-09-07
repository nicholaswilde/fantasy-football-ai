---
name: release-summary
description: Generates a clean, professional GitHub release summary by analyzing git logs and updating the release via the GitHub CLI.
---
# /release-summary [range]

Generates a clean, professional GitHub release summary based on git logs.

## Description
This skill leverages the agent to retrieve git commit logs, format them into a structured markdown summary (e.g., Features, Bug Fixes, Chores), and update the existing GitHub release notes using the GitHub CLI (`gh`).

## Protocol

1. If no range is provided, identify the latest two tags to determine the target range.
2. Retrieve the git logs for the target range:
   ```bash
   rtk git log <range> --oneline
   ```
3. Analyze the commit messages and generate a structured markdown summary. Keep it clean and professional.
4. Update the existing GitHub release using the generated notes. (Remember to pipe to `cat` as per the global rules):
   ```bash
   rtk gh release edit <tag> --notes "<your generated markdown notes>" | cat
   ```
