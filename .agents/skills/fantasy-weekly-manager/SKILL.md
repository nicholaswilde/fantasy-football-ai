---
name: fantasy-weekly-manager
description: Automates the end-to-end weekly fantasy football update process, from data fetching to lineup suggestions.
---

# Fantasy Weekly Manager

This skill runs the complete weekly update lifecycle for the Fantasy Football AI project.

## Instructions
When the user asks you to run the weekly update or manage the week:
1. **Execute Task**: Run the main orchestration command: `task weekly_update`. 
   *IMPORTANT*: To save tokens, you MUST run this command using the `context-mode` MCP tools (`ctx_execute`), OR delegate it entirely to a `cavecrew-investigator` subagent. The `Taskfile.yml` has already been updated to enforce `LOG_LEVEL=WARNING`.
   This will:
   - Download the latest stats
   - Update the local roster
   - Get available players
   - Run pickup and trade suggestions
   - Generate the terminal report
2. **Review Logs**: Review the output in your context sandbox.
3. **Summarize for User**: Present a highly condensed, bulleted summary to the user highlighting:
   - Top 2 waiver wire pickup targets (and who to drop).
   - Any immediate glaring lineup issues (e.g., players on Bye weeks or injured).
   - One high-value trade target to consider.
