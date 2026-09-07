---
name: fantasy-weekly-manager
description: Automates the end-to-end weekly fantasy football update process, from data fetching to lineup suggestions.
---

# Fantasy Weekly Manager

This skill runs the complete weekly update lifecycle for the Fantasy Football AI project.

## Instructions
When the user asks you to run the weekly update or manage the week:
1. **Execute Task**: Run the main orchestration command: `task weekly_update`. This will:
   - Download the latest stats
   - Update the local roster
   - Get available players
   - Run pickup and trade suggestions
   - Generate the terminal report
2. **Review Logs**: Quickly read through the terminal report and `logs/fantasy_ai.log` if any issues occurred.
3. **Summarize for User**: Present a highly condensed, bulleted summary to the user highlighting:
   - Top 2 waiver wire pickup targets (and who to drop).
   - Any immediate glaring lineup issues (e.g., players on Bye weeks or injured).
   - One high-value trade target to consider.
4. **Next Steps**: Offer to execute the `fantasy-blog-generator` skill to output a comprehensive blog post summarizing the findings for the week directly to the console.
